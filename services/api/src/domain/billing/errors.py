"""Billing-domain errors."""
# ruff: noqa: N818

from __future__ import annotations


class BillingError(Exception):
    code: str = "billing.unknown"
    status_code: int = 400


class PlanNotFound(BillingError):
    code = "billing.plan_not_found"
    status_code = 404


class PriceNotFound(BillingError):
    code = "billing.price_not_found"
    status_code = 404


class PricingZoneNotFound(BillingError):
    code = "billing.pricing_zone_not_found"
    status_code = 404


class SubscriptionNotFound(BillingError):
    code = "billing.subscription_not_found"
    status_code = 404


class PaymentFailed(BillingError):
    code = "billing.payment_failed"
    status_code = 402

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class InsufficientPermissions(BillingError):
    code = "billing.insufficient_permissions"
    status_code = 403


class AlreadySubscribed(BillingError):
    code = "billing.already_subscribed"
    status_code = 409


class TrialAlreadyUsed(BillingError):
    code = "billing.trial_already_used"
    status_code = 409


class InvalidWebhookProvider(BillingError):
    code = "billing.invalid_webhook_provider"
    status_code = 422


class IdempotencyKeyConflict(BillingError):
    """Re-using an idempotency key with different params."""

    code = "billing.idempotency_conflict"
    status_code = 409


class ProviderUnavailable(BillingError):
    """Real provider keys not configured or upstream API unreachable."""

    code = "billing.provider_unavailable"
    status_code = 503


class InvalidWebhookSignature(BillingError):
    """Stripe-Signature header verification failed."""

    code = "billing.webhook_invalid_signature"
    status_code = 401
