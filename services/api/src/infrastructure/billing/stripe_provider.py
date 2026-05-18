"""Stripe provider stub — interface placeholder for FAZA 4 real integration.

Signature-compatible with `PaymentProvider`. Every method raises
NotImplementedError because real Stripe integration is out of scope for FAZA 1.
"""

from __future__ import annotations

from decimal import Decimal


class StripeProvider:
    """Stub Stripe-backed PaymentProvider.

    Lands real behaviour in FAZA 4 once the live API key + webhook signing
    rotation policy ships.
    """

    name: str = "stripe"

    def __init__(self, *, api_key: str | None = None) -> None:
        self._api_key = api_key

    async def create_payment_intent(
        self,
        *,
        amount: Decimal,
        currency: str,
        customer_ref: str,
        idempotency_key: str,
    ) -> dict[str, str]:
        raise NotImplementedError("StripeProvider.create_payment_intent — FAZA 4")

    async def confirm_payment_intent(
        self, *, intent_id: str, payment_method_token: str
    ) -> dict[str, str]:
        raise NotImplementedError("StripeProvider.confirm_payment_intent — FAZA 4")

    async def verify_webhook(self, *, payload: bytes, signature: str) -> dict[str, object]:
        raise NotImplementedError("StripeProvider.verify_webhook — FAZA 4")
