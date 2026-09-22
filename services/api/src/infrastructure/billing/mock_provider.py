"""Mock payment provider for FAZA 1.

Deterministic, in-memory, no external service contact. Tokens starting with
`fail_` produce a failed confirmation so test suites can exercise the failure
path. Tokens starting with `decline_` produce a hard decline; anything else
succeeds.
"""

from __future__ import annotations

import secrets
from decimal import Decimal

from src.core.logging import get_logger

log = get_logger("silklens.billing.mock")


class MockPaymentProvider:
    """Implements the `PaymentProvider` protocol from the domain layer."""

    name: str = "mock"

    def __init__(self) -> None:
        self._intents: dict[str, dict[str, str]] = {}

    async def create_payment_intent(
        self,
        *,
        amount: Decimal,
        currency: str,
        customer_ref: str,
        idempotency_key: str,
    ) -> dict[str, str]:
        # idempotency: same key returns same intent metadata.
        if idempotency_key in self._intents:
            return self._intents[idempotency_key]
        intent_id = f"pi_mock_{secrets.token_hex(8)}"
        client_secret = f"{intent_id}_secret_{secrets.token_urlsafe(12)}"
        record = {
            "id": intent_id,
            "client_secret": client_secret,
            "amount": str(amount),
            "currency": currency,
            "customer_ref": customer_ref,
        }
        self._intents[idempotency_key] = record
        log.info(
            "billing.mock.create_intent",
            intent_id=intent_id,
            amount=str(amount),
            currency=currency,
        )
        return record

    async def confirm_payment_intent(
        self, *, intent_id: str, payment_method_token: str
    ) -> dict[str, str]:
        if payment_method_token.startswith("fail_"):
            log.info(
                "billing.mock.confirm.failed",
                intent_id=intent_id,
                reason="card_declined",
            )
            return {"status": "failed", "failure_code": "card_declined"}
        if payment_method_token.startswith("decline_"):
            log.info(
                "billing.mock.confirm.declined",
                intent_id=intent_id,
                reason="insufficient_funds",
            )
            return {"status": "failed", "failure_code": "insufficient_funds"}
        log.info("billing.mock.confirm.succeeded", intent_id=intent_id)
        return {"status": "succeeded", "intent_id": intent_id}
