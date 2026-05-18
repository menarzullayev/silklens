"""Billing service factory.

Picks ``StripeProvider`` when ``settings.payment_provider == "stripe"`` AND
``SILKLENS_STRIPE_SECRET_KEY`` is populated. Otherwise falls back to the
deterministic ``MockPaymentProvider`` — both for tests and for prod
mis-configuration safety. The settings flag never crashes a request; it just
degrades behaviour from "real charges" to "mock charges" with a warning log.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.core.settings import Settings, get_settings
from src.domain.billing.service import BillingService, PaymentProvider
from src.infrastructure.billing.mock_provider import MockPaymentProvider
from src.infrastructure.billing.repository import (
    SqlEntitlementRepository,
    SqlInvoiceRepository,
    SqlPaymentRepository,
    SqlPlanRepository,
    SqlSubscriptionRepository,
)
from src.infrastructure.billing.stripe_provider import StripeProvider

log = get_logger("silklens.billing.factory")


def build_payment_provider(settings: Settings | None = None) -> PaymentProvider:
    """Return the active payment provider per settings.

    Soft-falls back to :class:`MockPaymentProvider` when the Stripe path is
    selected but keys are not configured — important for dev workstations
    that flip the env var early but haven't yet populated the secret.
    """
    s = settings or get_settings()
    if s.payment_provider == "stripe":
        secret = s.stripe_secret_key.get_secret_value().strip()
        webhook_secret = s.stripe_webhook_secret.get_secret_value().strip()
        if not secret:
            log.warning(
                "billing.factory.stripe_keys_missing",
                action="falling_back_to_mock",
            )
            return MockPaymentProvider()
        return StripeProvider(api_key=secret, webhook_secret=webhook_secret)
    return MockPaymentProvider()


def build_billing_service(
    db: AsyncSession,
    *,
    provider: PaymentProvider | None = None,
    settings: Settings | None = None,
) -> BillingService:
    """Assemble a ``BillingService`` for the request-scoped session."""
    return BillingService(
        plans=SqlPlanRepository(db),
        subscriptions=SqlSubscriptionRepository(db),
        payments=SqlPaymentRepository(db),
        invoices=SqlInvoiceRepository(db),
        entitlements=SqlEntitlementRepository(db),
        provider=provider or build_payment_provider(settings),
    )


def is_real_stripe_active(settings: Settings | None = None) -> bool:
    """Cheap predicate the router uses to pick the verification path."""
    s = settings or get_settings()
    return (
        s.payment_provider == "stripe"
        and bool(s.stripe_secret_key.get_secret_value().strip())
        and bool(s.stripe_webhook_secret.get_secret_value().strip())
    )


def build_stripe_provider_from_settings(
    settings: Settings | None = None,
) -> StripeProvider | None:
    """Return a configured StripeProvider for webhook verification, or None."""
    s = settings or get_settings()
    secret = s.stripe_secret_key.get_secret_value().strip()
    webhook_secret = s.stripe_webhook_secret.get_secret_value().strip()
    if not webhook_secret:
        return None
    return StripeProvider(api_key=secret or None, webhook_secret=webhook_secret)


__all__: list[Any] = [
    "build_billing_service",
    "build_payment_provider",
    "build_stripe_provider_from_settings",
    "is_real_stripe_active",
]
