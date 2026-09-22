"""Billing service factory.

Multi-provider, per-currency routing.

Resolution order for a payment (highest priority wins):

1. **Explicit ``currency`` argument** — if the admin's per-currency map
   (loaded from ``system_settings.billing.provider_by_currency.<CCY>``) names a
   provider, use it.
2. **Default override** — ``billing.provider_by_currency.default`` from
   ``system_settings`` if present.
3. **Global ``SILKLENS_PAYMENT_PROVIDER``** env flag (build-time).
4. **MockPaymentProvider** as the always-safe terminal fallback.

The factory **never** raises on misconfiguration; if the selected real provider
is missing credentials it soft-falls-back to :class:`MockPaymentProvider` with a
structured warning so a half-configured deployment never crashes a request.

This module remains synchronous for the legacy callers; ``build_billing_service``
keeps its FAZA-1 signature so existing routes don't need to change. New
currency-aware code paths call :func:`build_payment_provider_for_currency`.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.core.settings import Settings, get_settings
from src.domain.billing.service import BillingService, PaymentProvider
from src.infrastructure.billing.click_provider import ClickPaymentProvider
from src.infrastructure.billing.mock_provider import MockPaymentProvider
from src.infrastructure.billing.payme_provider import PaymePaymentProvider
from src.infrastructure.billing.paypal_provider import PayPalPaymentProvider
from src.infrastructure.billing.repository import (
    SqlEntitlementRepository,
    SqlInvoiceRepository,
    SqlPaymentRepository,
    SqlPlanRepository,
    SqlSubscriptionRepository,
)
from src.infrastructure.billing.stripe_provider import StripeProvider

log = get_logger("silklens.billing.factory")


# Static fallback map used when no DB overrides have been seeded yet. Kept in
# sync with migration 0082_provider_routing's INSERT statements.
DEFAULT_PROVIDER_BY_CURRENCY: dict[str, str] = {
    "UZS": "payme",
    "USD": "stripe",
    "EUR": "stripe",
    "GBP": "stripe",
    "RUB": "stripe",
}


def _build_named_provider(name: str, settings: Settings) -> PaymentProvider:
    """Instantiate a provider by name, soft-falling-back to mock on missing creds.

    All five providers implement the ``PaymentProvider`` protocol structurally;
    each one self-reports unavailability through ``ProviderUnavailable`` at
    call-time so the factory only has to confirm *something* concrete comes
    back here.
    """
    n = name.strip().lower()
    if n == "stripe":
        secret = settings.stripe_secret_key.get_secret_value().strip()
        webhook_secret = settings.stripe_webhook_secret.get_secret_value().strip()
        if not secret:
            log.warning("billing.factory.stripe_keys_missing", fallback="mock")
            return MockPaymentProvider()
        return StripeProvider(api_key=secret, webhook_secret=webhook_secret)
    if n == "payme":
        merchant_id = settings.payme_merchant_id.strip()
        secret = settings.payme_secret_key.get_secret_value().strip()
        if not merchant_id or not secret:
            log.warning("billing.factory.payme_keys_missing", fallback="mock")
            return MockPaymentProvider()
        return PaymePaymentProvider(
            merchant_id=merchant_id,
            secret_key=secret,
            endpoint=settings.payme_endpoint,
        )
    if n == "click":
        service_id = settings.click_service_id.strip()
        secret = settings.click_secret_key.get_secret_value().strip()
        if not service_id or not secret:
            log.warning("billing.factory.click_keys_missing", fallback="mock")
            return MockPaymentProvider()
        return ClickPaymentProvider(
            service_id=service_id,
            merchant_id=settings.click_merchant_id.strip(),
            secret_key=secret,
            endpoint=settings.click_endpoint,
        )
    if n == "paypal":
        client_id = settings.paypal_client_id.strip()
        client_secret = settings.paypal_client_secret.get_secret_value().strip()
        if not client_id or not client_secret:
            log.warning("billing.factory.paypal_keys_missing", fallback="mock")
            return MockPaymentProvider()
        return PayPalPaymentProvider(
            client_id=client_id,
            client_secret=client_secret,
            webhook_id=settings.paypal_webhook_id.strip(),
            environment=settings.paypal_environment,
        )
    # ``mock`` or unknown name → MockPaymentProvider (the safe terminal).
    if n != "mock":
        log.warning("billing.factory.unknown_provider", provided=name, fallback="mock")
    return MockPaymentProvider()


def build_payment_provider(settings: Settings | None = None) -> PaymentProvider:
    """Return the provider matching the global ``SILKLENS_PAYMENT_PROVIDER`` flag.

    Soft-falls-back to :class:`MockPaymentProvider` on missing credentials —
    important for dev workstations that flip the env var early but haven't yet
    populated the secret.
    """
    s = settings or get_settings()
    return _build_named_provider(s.payment_provider, s)


def build_payment_provider_for_currency(
    currency: str,
    *,
    overrides: dict[str, str] | None = None,
    settings: Settings | None = None,
) -> PaymentProvider:
    """Pick a provider by ISO-4217 currency, honouring admin overrides.

    Parameters
    ----------
    currency:
        ISO-4217 alpha-3 code (case-insensitive). Empty / unknown values fall
        through to the global ``payment_provider`` env flag.
    overrides:
        Optional admin-supplied mapping (typically loaded from
        ``system_settings.billing.provider_by_currency.*`` at request time).
        Keys may include an explicit ``default`` slot.
    """
    s = settings or get_settings()
    ccy = (currency or "").strip().upper()

    merged: dict[str, str] = {**DEFAULT_PROVIDER_BY_CURRENCY}
    if overrides:
        for k, v in overrides.items():
            merged[k.upper()] = v

    if ccy and ccy in merged:
        return _build_named_provider(merged[ccy], s)
    if "DEFAULT" in merged:
        return _build_named_provider(merged["DEFAULT"], s)
    return build_payment_provider(s)


async def load_provider_overrides(db: AsyncSession) -> dict[str, str]:
    """Load ``billing.provider_by_currency.*`` rows from ``system_settings``.

    The map is keyed by ISO-4217 alpha-3 (uppercase) or the special key
    ``DEFAULT``. Missing rows return ``{}`` — callers fall back to the static
    :data:`DEFAULT_PROVIDER_BY_CURRENCY` table.
    """
    from sqlalchemy import text

    try:
        result = await db.execute(
            text(
                """
                SELECT key, value
                  FROM system_settings
                 WHERE key LIKE 'billing.provider_by_currency.%'
                """
            )
        )
    except Exception as exc:
        log.warning("billing.factory.load_overrides_failed", error=str(exc))
        return {}
    rows = result.fetchall()
    out: dict[str, str] = {}
    for row in rows:
        key = str(row[0])
        value = row[1]
        # The value column is jsonb; SQLAlchemy returns str/dict depending on
        # driver. Both shapes resolve to a provider name string.
        if isinstance(value, dict):
            provider = str(value.get("provider") or value.get("value") or "").strip()
        elif isinstance(value, str):
            provider = value.strip().strip('"')
        else:
            provider = str(value).strip().strip('"')
        if not provider:
            continue
        ccy = key.rsplit(".", 1)[-1].upper()
        out[ccy] = provider
    return out


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


def build_payme_provider_from_settings(
    settings: Settings | None = None,
) -> PaymePaymentProvider | None:
    """Return a configured PaymePaymentProvider for webhook verification, or None."""
    s = settings or get_settings()
    merchant_id = s.payme_merchant_id.strip()
    secret = s.payme_secret_key.get_secret_value().strip()
    if not merchant_id or not secret:
        return None
    return PaymePaymentProvider(
        merchant_id=merchant_id, secret_key=secret, endpoint=s.payme_endpoint
    )


def build_click_provider_from_settings(
    settings: Settings | None = None,
) -> ClickPaymentProvider | None:
    """Return a configured ClickPaymentProvider for webhook verification, or None."""
    s = settings or get_settings()
    service_id = s.click_service_id.strip()
    secret = s.click_secret_key.get_secret_value().strip()
    if not service_id or not secret:
        return None
    return ClickPaymentProvider(
        service_id=service_id,
        merchant_id=s.click_merchant_id.strip(),
        secret_key=secret,
        endpoint=s.click_endpoint,
    )


def build_paypal_provider_from_settings(
    settings: Settings | None = None,
) -> PayPalPaymentProvider | None:
    """Return a configured PayPalPaymentProvider for webhook verification, or None."""
    s = settings or get_settings()
    client_id = s.paypal_client_id.strip()
    client_secret = s.paypal_client_secret.get_secret_value().strip()
    webhook_id = s.paypal_webhook_id.strip()
    if not client_id or not client_secret or not webhook_id:
        return None
    return PayPalPaymentProvider(
        client_id=client_id,
        client_secret=client_secret,
        webhook_id=webhook_id,
        environment=s.paypal_environment,
    )


__all__: list[Any] = [
    "DEFAULT_PROVIDER_BY_CURRENCY",
    "build_billing_service",
    "build_click_provider_from_settings",
    "build_payme_provider_from_settings",
    "build_payment_provider",
    "build_payment_provider_for_currency",
    "build_paypal_provider_from_settings",
    "build_stripe_provider_from_settings",
    "is_real_stripe_active",
    "load_provider_overrides",
]
