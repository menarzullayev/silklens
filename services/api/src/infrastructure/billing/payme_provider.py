"""Payme (Paycom) payment provider — Uzbekistan.

Payme is the dominant Uzbek payment gateway. Its public Merchant API is **JSON-RPC
2.0 over HTTP**, with webhooks signed by HTTP Basic auth.

Real charges require a Paycom merchant account; until ``PAYME_MERCHANT_ID`` and
``PAYME_SECRET_KEY`` are populated this adapter delegates the actual money-moving
calls to :class:`MockPaymentProvider` (FAZA-5 sandbox-shape pattern) while
keeping the **wire envelope** (Basic-auth header, JSON-RPC method names, tiyin
amount conversion) production-faithful so the router and idempotency machinery
are exercised end-to-end in tests.

Three production-grade contracts:

1. **Basic-auth verification on webhooks.** ``verify_webhook`` matches
   ``Authorization: Basic <base64(merchant_id:secret)>`` against the configured
   pair. Any mismatch raises :class:`InvalidWebhookSignature` so the router can
   return ``401``.
2. **Tiyin conversion.** All Payme amounts travel in tiyin (1 UZS = 100 tiyin).
   The provider accepts UZS major units in ``amount`` and converts internally so
   the rest of the domain stays in NUMERIC major units.
3. **Soft-fail when keys absent.** :class:`ProviderUnavailable` is raised so the
   router can present a 503 cleanly.

Payme JSON-RPC methods we map to internal events
(see https://developer.help.paycom.uz/metody-merchant-api/):

  * ``CheckPerformTransaction`` — pre-check: can this user pay this amount?
  * ``CreateTransaction``       — Payme reserves funds (intent created)
  * ``PerformTransaction``      — funds captured (intent succeeded)
  * ``CancelTransaction``       — refund or cancel
  * ``CheckTransaction``        — Payme polls our transaction state
"""

from __future__ import annotations

import base64
import secrets
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from src.core.logging import get_logger
from src.domain.billing.errors import (
    InvalidWebhookSignature,
    ProviderUnavailable,
)
from src.infrastructure.billing.mock_provider import MockPaymentProvider

log = get_logger("silklens.billing.payme")


# Payme JSON-RPC method names → internal event-type slug. The router uses the
# slug to drive the same per-event handlers that Stripe does.
PAYME_METHOD_TO_EVENT: dict[str, str] = {
    "CheckPerformTransaction": "payme.check_perform.v1",
    "CreateTransaction": "payme.transaction_created.v1",
    "PerformTransaction": "payme.transaction_performed.v1",
    "CancelTransaction": "payme.transaction_canceled.v1",
    "CheckTransaction": "payme.transaction_checked.v1",
    "GetStatement": "payme.statement.v1",
}


@dataclass(slots=True, frozen=True)
class ParsedPaymeEvent:
    """Canonical shape we hand back from ``verify_webhook``.

    Kept dataclass-light so the router can route on ``event_type`` without
    importing Payme internals.
    """

    method: str
    event_type: str
    provider_event_id: str
    params: dict[str, Any]
    raw: dict[str, Any]


def uzs_to_tiyin(amount_uzs: Decimal) -> int:
    """1 UZS = 100 tiyin. Payme API always speaks in tiyin."""
    return int((amount_uzs * Decimal(100)).quantize(Decimal("1")))


def tiyin_to_uzs(amount_tiyin: int) -> Decimal:
    return (Decimal(amount_tiyin) / Decimal(100)).quantize(Decimal("0.01"))


class PaymePaymentProvider:
    """Sandbox-shape Payme adapter (FAZA-5).

    Behaves exactly like a real Payme client at the **API boundary** (Basic-auth
    header, tiyin amounts, JSON-RPC method routing) but delegates actual charge
    confirmation to a private :class:`MockPaymentProvider` so the test suite and
    dev environments can drive the full flow with no live merchant keys.
    """

    name: str = "payme"

    def __init__(
        self,
        *,
        merchant_id: str | None = None,
        secret_key: str | None = None,
        endpoint: str | None = None,
    ) -> None:
        self._merchant_id = (merchant_id or "").strip()
        self._secret_key = (secret_key or "").strip()
        self._endpoint = (endpoint or "https://checkout.paycom.uz").rstrip("/")
        self._mock = MockPaymentProvider()

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
        if not self._merchant_id or not self._secret_key:
            raise ProviderUnavailable("provider_unavailable")
        # Payme only operates in UZS. Reject anything else early so the router
        # falls back to a different provider per the per-currency routing map.
        if currency.upper() != "UZS":
            raise ProviderUnavailable("payme_currency_unsupported")

        # Real Payme integration: build a signed merchant checkout URL with the
        # amount in tiyin, account.user reference, and idempotent return URL.
        amount_tiyin = uzs_to_tiyin(amount)
        # Merchant param string is base64'd into the m= URL query param. We
        # mimic that format so downstream tests can assert on the URL shape.
        params = (
            f"m={self._merchant_id};"
            f"ac.customer_ref={customer_ref};"
            f"a={amount_tiyin};"
            f"c={idempotency_key}"
        )
        token = base64.b64encode(params.encode("utf-8")).decode("ascii")
        payment_url = f"{self._endpoint}/{token}"

        # Until real-checkout completion arrives via webhook, persist the intent
        # shape via the mock so confirmation/idempotency still work for tests.
        intent = await self._mock.create_payment_intent(
            amount=amount,
            currency=currency,
            customer_ref=customer_ref,
            idempotency_key=idempotency_key,
        )
        out = dict(intent)
        out["id"] = (
            f"payme_{secrets.token_hex(8)}" if intent["id"].startswith("pi_mock") else intent["id"]
        )
        out["payment_url"] = payment_url
        out["amount_tiyin"] = str(amount_tiyin)
        log.info(
            "billing.payme.create_intent",
            intent_id=out["id"],
            amount_uzs=str(amount),
            amount_tiyin=amount_tiyin,
        )
        return out

    async def confirm_payment_intent(
        self, *, intent_id: str, payment_method_token: str
    ) -> dict[str, str]:
        # In production Payme confirmation arrives via ``PerformTransaction``
        # webhook, not synchronously. The sandbox shape mirrors the mock so the
        # service's request/response path stays exercisable in tests.
        if not self._merchant_id or not self._secret_key:
            raise ProviderUnavailable("provider_unavailable")
        return await self._mock.confirm_payment_intent(
            intent_id=intent_id,
            payment_method_token=payment_method_token,
        )

    # ------------------------------------------------------------------
    # Webhook verification + JSON-RPC parsing
    # ------------------------------------------------------------------

    def verify_webhook(
        self,
        *,
        headers: dict[str, str] | Any,
        body: dict[str, Any],
    ) -> ParsedPaymeEvent:
        """Validate ``Authorization: Basic <merchant_id:secret>`` + parse JSON-RPC.

        Raises ``InvalidWebhookSignature`` on:
          * Missing / malformed Authorization header
          * Wrong scheme (not Basic)
          * base64 payload doesn't decode to ``<merchant_id>:<secret>``
        """
        if not self._merchant_id or not self._secret_key:
            raise ProviderUnavailable("provider_unavailable")

        auth_header = ""
        # Accept dict-likes (Starlette headers are case-insensitive but expose
        # plain dict semantics in tests).
        if hasattr(headers, "get"):
            auth_header = headers.get("Authorization") or headers.get("authorization") or ""
        if not auth_header:
            raise InvalidWebhookSignature("missing_authorization")

        scheme, _, value = auth_header.strip().partition(" ")
        if scheme.lower() != "basic" or not value:
            raise InvalidWebhookSignature("invalid_scheme")
        try:
            decoded = base64.b64decode(value.strip()).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise InvalidWebhookSignature("malformed_basic") from exc

        # Payme convention: the username may be literal "Paycom" or the
        # merchant_id itself. Accept either, then verify the secret matches.
        login, _, password = decoded.partition(":")
        # SEC-W56-001: constant-time comparison defeats timing-oracle attacks on
        # the webhook secret; Python string inequality short-circuits on first
        # differing byte, leaking information via response latency.
        import hmac as _hmac

        if not _hmac.compare_digest(password.encode(), self._secret_key.encode()):
            raise InvalidWebhookSignature("bad_secret")
        accepted_logins = {b"Paycom", self._merchant_id.encode()}
        if not any(_hmac.compare_digest(login.encode(), a) for a in accepted_logins):
            raise InvalidWebhookSignature("bad_login")

        # JSON-RPC envelope: {jsonrpc, id, method, params}
        method = str(body.get("method") or "")
        if method not in PAYME_METHOD_TO_EVENT:
            log.warning("billing.payme.webhook.unknown_method", method=method)
            # Still hand the router a structured event so the row lands; just
            # tag it ``payme.unknown.v1``.
            event_type = "payme.unknown.v1"
        else:
            event_type = PAYME_METHOD_TO_EVENT[method]

        params = body.get("params") or {}
        if not isinstance(params, dict):
            params = {}
        rpc_id = body.get("id")
        if params.get("id"):
            provider_event_id = str(params.get("id"))
        else:
            provider_event_id = f"payme_evt_{rpc_id or secrets.token_hex(6)}"

        return ParsedPaymeEvent(
            method=method,
            event_type=event_type,
            provider_event_id=provider_event_id,
            params=params,
            raw=body,
        )


__all__ = [
    "PAYME_METHOD_TO_EVENT",
    "ParsedPaymeEvent",
    "PaymePaymentProvider",
    "tiyin_to_uzs",
    "uzs_to_tiyin",
]
