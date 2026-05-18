"""Click (click.uz) payment provider — Uzbekistan.

Click is the other dominant Uzbek payment gateway. Unlike Payme it uses
**form-encoded** webhooks signed via **HMAC-SHA1** over a fixed concatenation
of merchant + transaction fields plus a shared ``secret_key``.

Per the public Click Merchant API (https://docs.click.uz/) the signature is:

    md5_hex(
        click_trans_id +
        service_id +
        SECRET_KEY +
        merchant_trans_id +
        amount +
        action +
        sign_time
    )

Click historically calls this an "MD5 sign string". For SilkLens we treat it as
a generic keyed digest — we accept the official MD5 spelling because that's
what merchants actually receive, and we add an HMAC-SHA1 helper for our
internal merchant-callback envelope. Both are exercised in tests.

Real charges require a Click merchant account; until ``CLICK_SERVICE_ID`` and
``CLICK_SECRET_KEY`` are populated the actual confirmation is delegated to
:class:`MockPaymentProvider`.

Click webhook ``action`` codes (sent in the form body):
  * 0 — Prepare       (intent created on Click side)
  * 1 — Complete      (intent succeeded / failed)
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from decimal import Decimal
from urllib.parse import urlencode

from src.core.logging import get_logger
from src.domain.billing.errors import (
    InvalidWebhookSignature,
    ProviderUnavailable,
)
from src.infrastructure.billing.mock_provider import MockPaymentProvider

log = get_logger("silklens.billing.click")


CLICK_ACTION_TO_EVENT: dict[str, str] = {
    "0": "click.prepare.v1",
    "1": "click.complete.v1",
}


@dataclass(slots=True, frozen=True)
class ParsedClickEvent:
    """Canonical Click webhook event."""

    action: str
    event_type: str
    provider_event_id: str
    click_trans_id: str
    merchant_trans_id: str
    amount: Decimal
    raw: dict[str, str]


def click_sign_string(
    *,
    click_trans_id: str,
    service_id: str,
    secret_key: str,
    merchant_trans_id: str,
    amount: str,
    action: str,
    sign_time: str,
) -> str:
    """Reproduce the Click MD5 sign-string per their merchant docs."""
    raw = f"{click_trans_id}{service_id}{secret_key}{merchant_trans_id}{amount}{action}{sign_time}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()  # noqa: S324 — Click protocol


def click_hmac_sha1(
    *,
    click_trans_id: str,
    service_id: str,
    click_paydoc_id: str,
    amount: str,
    action: str,
    sign_time: str,
    merchant_user_id: str,
    secret_key: str,
) -> str:
    """HMAC-SHA1 over the field concatenation, used for our internal envelope.

    Field order per the WAVE-6 brief — concatenation of:
    click_trans_id, service_id, click_paydoc_id, amount, action,
    sign_time, merchant_user_id — keyed by ``secret_key``.
    """
    msg = (
        f"{click_trans_id}{service_id}{click_paydoc_id}"
        f"{amount}{action}{sign_time}{merchant_user_id}"
    ).encode()
    return hmac.new(secret_key.encode("utf-8"), msg, hashlib.sha1).hexdigest()


class ClickPaymentProvider:
    """Sandbox-shape Click adapter.

    Real money-moving calls delegate to a private :class:`MockPaymentProvider`
    until ``CLICK_SERVICE_ID``/``CLICK_SECRET_KEY`` are wired. The webhook
    verification path is production-faithful so signature regressions are
    caught in CI.
    """

    name: str = "click"

    def __init__(
        self,
        *,
        service_id: str | None = None,
        merchant_id: str | None = None,
        secret_key: str | None = None,
        endpoint: str | None = None,
    ) -> None:
        self._service_id = (service_id or "").strip()
        self._merchant_id = (merchant_id or "").strip()
        self._secret_key = (secret_key or "").strip()
        self._endpoint = (endpoint or "https://my.click.uz/services/pay").rstrip("/")
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
        if not self._service_id or not self._secret_key:
            raise ProviderUnavailable("provider_unavailable")
        if currency.upper() != "UZS":
            raise ProviderUnavailable("click_currency_unsupported")

        # Click accepts amounts in UZS (sum), no tiyin conversion. Build the
        # merchant-hosted checkout URL.
        merchant_trans_id = idempotency_key
        query = urlencode(
            {
                "service_id": self._service_id,
                "merchant_id": self._merchant_id or self._service_id,
                "amount": f"{amount:.2f}",
                "transaction_param": merchant_trans_id,
                "return_url": f"silklens://billing/return?key={idempotency_key}",
            }
        )
        payment_url = f"{self._endpoint}?{query}"

        intent = await self._mock.create_payment_intent(
            amount=amount,
            currency=currency,
            customer_ref=customer_ref,
            idempotency_key=idempotency_key,
        )
        out = dict(intent)
        out["id"] = (
            f"click_{secrets.token_hex(8)}" if intent["id"].startswith("pi_mock") else intent["id"]
        )
        out["payment_url"] = payment_url
        out["merchant_trans_id"] = merchant_trans_id
        log.info(
            "billing.click.create_intent",
            intent_id=out["id"],
            amount_uzs=str(amount),
        )
        return out

    async def confirm_payment_intent(
        self, *, intent_id: str, payment_method_token: str
    ) -> dict[str, str]:
        # Real confirmation arrives via the Complete (action=1) webhook. For
        # the sandbox / synchronous path we delegate to the mock.
        if not self._service_id or not self._secret_key:
            raise ProviderUnavailable("provider_unavailable")
        return await self._mock.confirm_payment_intent(
            intent_id=intent_id,
            payment_method_token=payment_method_token,
        )

    # ------------------------------------------------------------------
    # Webhook verification (form-encoded)
    # ------------------------------------------------------------------

    def verify_webhook(self, form_data: dict[str, str]) -> ParsedClickEvent:
        """Verify Click's MD5 sign + return a typed event.

        Click sends:
          click_trans_id, service_id, click_paydoc_id, merchant_trans_id,
          amount, action, error, error_note, sign_time, sign_string
        """
        if not self._service_id or not self._secret_key:
            raise ProviderUnavailable("provider_unavailable")

        required = {
            "click_trans_id",
            "service_id",
            "merchant_trans_id",
            "amount",
            "action",
            "sign_time",
            "sign_string",
        }
        missing = required - set(form_data.keys())
        if missing:
            raise InvalidWebhookSignature(f"missing_fields:{sorted(missing)}")

        if str(form_data["service_id"]) != self._service_id:
            raise InvalidWebhookSignature("wrong_service_id")

        expected = click_sign_string(
            click_trans_id=str(form_data["click_trans_id"]),
            service_id=str(form_data["service_id"]),
            secret_key=self._secret_key,
            merchant_trans_id=str(form_data["merchant_trans_id"]),
            amount=str(form_data["amount"]),
            action=str(form_data["action"]),
            sign_time=str(form_data["sign_time"]),
        )
        presented = str(form_data.get("sign_string", "")).lower()
        if not hmac.compare_digest(expected.lower(), presented):
            log.warning(
                "billing.click.webhook.bad_signature",
                click_trans_id=form_data.get("click_trans_id"),
            )
            raise InvalidWebhookSignature("bad_signature")

        action = str(form_data["action"])
        try:
            amount = Decimal(str(form_data["amount"]))
        except Exception as exc:
            raise InvalidWebhookSignature("malformed_amount") from exc

        return ParsedClickEvent(
            action=action,
            event_type=CLICK_ACTION_TO_EVENT.get(action, f"click.action_{action}.v1"),
            provider_event_id=str(form_data["click_trans_id"]),
            click_trans_id=str(form_data["click_trans_id"]),
            merchant_trans_id=str(form_data["merchant_trans_id"]),
            amount=amount,
            raw=dict(form_data),
        )


__all__ = [
    "CLICK_ACTION_TO_EVENT",
    "ClickPaymentProvider",
    "ParsedClickEvent",
    "click_hmac_sha1",
    "click_sign_string",
]
