"""Real Stripe payment provider.

Implements the ``PaymentProvider`` protocol against the official ``stripe``
SDK. Three production-grade rules are enforced:

1. **Signature verification on webhooks.** ``verify_webhook`` proxies to
   ``stripe.Webhook.construct_event`` so a missing / forged / replayed
   signature header raises :class:`BillingError("invalid_signature")` and the
   router can return ``401``.
2. **Idempotency on every state-changing call.** Both ``create_payment_intent``
   and ``confirm_payment_intent`` pass an ``idempotency_key`` to Stripe, so a
   retried HTTP call short-circuits to the original Stripe response instead of
   producing a second charge.
3. **Soft-fail when the SDK or keys are missing.** Tests stay mocked and CI
   never tries to reach the network — :class:`BillingError("provider_unavailable")`
   is raised so the service layer can present a 503 cleanly.

Stripe error codes are mapped to our typed billing errors at the call boundary
so the rest of the system never imports ``stripe`` directly.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from src.core.logging import get_logger
from src.domain.billing.errors import (
    BillingError,
    InvalidWebhookSignature,
    PaymentFailed,
    ProviderUnavailable,
)

log = get_logger("silklens.billing.stripe")


_ZERO_DECIMAL_CCYS: frozenset[str] = frozenset(
    {
        # ISO-4217 zero-decimal currencies per
        # https://docs.stripe.com/currencies#zero-decimal — Stripe expects the
        # amount as the major unit for these (e.g. ¥500 not ¥50000).
        "BIF",
        "CLP",
        "DJF",
        "GNF",
        "JPY",
        "KMF",
        "KRW",
        "MGA",
        "PYG",
        "RWF",
        "UGX",
        "VND",
        "VUV",
        "XAF",
        "XOF",
        "XPF",
    }
)


def _to_minor_units(amount: Decimal, currency: str) -> int:
    """Convert a NUMERIC(20,4) major-unit amount to Stripe's smallest unit."""
    if currency.upper() in _ZERO_DECIMAL_CCYS:
        return int(amount.quantize(Decimal("1")))
    return int((amount * Decimal(100)).quantize(Decimal("1")))


class StripeProvider:
    """Production Stripe-backed ``PaymentProvider``.

    The class lazily imports the ``stripe`` SDK so installations without the
    ``[billing]`` extra (and CI runs without ``SILKLENS_STRIPE_SECRET_KEY``)
    don't pay the import cost. Construction with missing keys is a no-op; the
    failure is raised the first time a network-touching method is invoked.
    """

    name: str = "stripe"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        webhook_secret: str | None = None,
    ) -> None:
        self._api_key = (api_key or "").strip() or None
        self._webhook_secret = (webhook_secret or "").strip() or None
        self._stripe: Any | None = None

    # ------------------------------------------------------------------
    # SDK plumbing
    # ------------------------------------------------------------------

    def _client(self) -> Any:
        if self._stripe is not None:
            return self._stripe
        if not self._api_key:
            raise ProviderUnavailable("provider_unavailable")
        try:
            import stripe
        except ImportError as exc:  # pragma: no cover — covered by [billing] extra
            raise ProviderUnavailable("provider_unavailable") from exc
        # Stripe SDK stores api_key on the module — assign here so future
        # imports inherit the same key in this process.
        stripe.api_key = self._api_key
        self._stripe = stripe
        return stripe

    def _map_stripe_error(self, exc: Exception) -> BillingError:
        """Translate Stripe-typed errors to our typed BillingError hierarchy."""
        try:
            import stripe
        except ImportError:  # pragma: no cover
            return BillingError(str(exc))

        if isinstance(exc, stripe.CardError):
            code = getattr(exc, "code", None) or "card_declined"
            return PaymentFailed(str(code))
        if isinstance(exc, stripe.RateLimitError):
            return ProviderUnavailable("provider_rate_limited")
        if isinstance(exc, stripe.AuthenticationError):
            return ProviderUnavailable("provider_unavailable")
        if isinstance(exc, stripe.InvalidRequestError):
            return BillingError(f"invalid_request:{exc}")
        if isinstance(exc, stripe.APIConnectionError | stripe.APIError):
            return ProviderUnavailable("provider_unavailable")
        if isinstance(exc, stripe.StripeError):
            return BillingError(f"stripe_error:{exc}")
        return BillingError(str(exc))

    # ------------------------------------------------------------------
    # PaymentProvider protocol
    # ------------------------------------------------------------------

    async def create_payment_intent(
        self,
        *,
        amount: Decimal,
        currency: str,
        customer_ref: str,
        idempotency_key: str,
    ) -> dict[str, str]:
        stripe = self._client()
        try:
            intent = await stripe.PaymentIntent.create_async(
                amount=_to_minor_units(amount, currency),
                currency=currency.lower(),
                metadata={"customer_ref": customer_ref},
                automatic_payment_methods={"enabled": True},
                idempotency_key=idempotency_key,
            )
        except Exception as exc:  # typed mapping below
            mapped = self._map_stripe_error(exc)
            log.warning(
                "billing.stripe.create_intent.failed",
                error=mapped.code,
                detail=str(exc),
            )
            raise mapped from exc
        log.info(
            "billing.stripe.create_intent",
            intent_id=intent["id"],
            amount=str(amount),
            currency=currency,
        )
        return {
            "id": str(intent["id"]),
            "client_secret": str(intent.get("client_secret") or ""),
            "amount": str(amount),
            "currency": currency,
            "customer_ref": customer_ref,
        }

    async def confirm_payment_intent(
        self, *, intent_id: str, payment_method_token: str
    ) -> dict[str, str]:
        stripe = self._client()
        # Build a deterministic idempotency key from the intent + method token
        # so a duplicate confirmation never races a second charge.
        idem = f"confirm:{intent_id}:{payment_method_token[:16]}"
        try:
            intent = await stripe.PaymentIntent.confirm_async(
                intent_id,
                payment_method=payment_method_token,
                idempotency_key=idem,
            )
        except Exception as exc:  # typed mapping below
            mapped = self._map_stripe_error(exc)
            log.warning(
                "billing.stripe.confirm.failed",
                intent_id=intent_id,
                error=mapped.code,
                detail=str(exc),
            )
            if isinstance(mapped, PaymentFailed):
                return {"status": "failed", "failure_code": mapped.reason}
            raise mapped from exc

        status = str(intent.get("status") or "")
        if status == "succeeded":
            log.info("billing.stripe.confirm.succeeded", intent_id=intent_id)
            return {"status": "succeeded", "intent_id": intent_id}
        if status in {"requires_action", "requires_confirmation", "processing"}:
            # Stripe SCA flow — caller's webhook handler will close the loop.
            return {"status": status, "intent_id": intent_id}
        # Anything else is a failure code.
        last_error = intent.get("last_payment_error") or {}
        failure_code = str(last_error.get("code") or "payment_failed")
        return {"status": "failed", "failure_code": failure_code}

    # ------------------------------------------------------------------
    # Webhook verification
    # ------------------------------------------------------------------

    def verify_webhook(self, *, payload: bytes, signature: str) -> dict[str, Any]:
        """Verify the Stripe-Signature header and return the parsed event.

        Raises ``BillingError('invalid_signature')`` on any verification
        failure (missing secret, bad signature, malformed body, replayed
        timestamp outside the tolerance window).
        """
        if not self._webhook_secret:
            raise ProviderUnavailable("provider_unavailable")
        try:
            import stripe
        except ImportError as exc:  # pragma: no cover
            raise ProviderUnavailable("provider_unavailable") from exc

        try:
            event = stripe.Webhook.construct_event(  # type: ignore[no-untyped-call]
                payload=payload,
                sig_header=signature,
                secret=self._webhook_secret,
            )
        except (stripe.SignatureVerificationError, ValueError) as exc:
            log.warning("billing.stripe.webhook.invalid_signature", detail=str(exc))
            raise InvalidWebhookSignature("invalid_signature") from exc

        from typing import cast

        # ``stripe.Event`` is dict-like (subclasses ``StripeObject``). Use the
        # SDK-supplied serializer to get a plain dict so callers don't need to
        # import the SDK to inspect fields.
        if hasattr(event, "to_dict_recursive"):
            return cast("dict[str, Any]", event.to_dict_recursive())
        if hasattr(event, "to_dict"):
            return cast("dict[str, Any]", event.to_dict())
        return {k: event[k] for k in event.keys()}  # noqa: SIM118
