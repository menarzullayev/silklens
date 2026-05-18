"""Billing repository protocols — interfaces only."""

from __future__ import annotations

from decimal import Decimal
from typing import Protocol
from uuid import UUID

from src.domain.billing.entities import (
    Entitlement,
    Invoice,
    PaymentIntent,
    PaymentStatus,
    Plan,
    Price,
    PricingZone,
    Subscription,
    SubscriptionStatus,
)


class SubscriptionRepository(Protocol):
    async def get_active_for_user(
        self, user_id: UUID, residency_region: str
    ) -> Subscription | None: ...

    async def get_by_id(self, subscription_id: UUID) -> Subscription | None: ...

    async def create(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        residency_region: str,
        plan_id: UUID,
        status: SubscriptionStatus,
        trial_ends_at: object | None,
        period_days: int,
    ) -> Subscription: ...

    async def update_status(
        self,
        subscription_id: UUID,
        *,
        status: SubscriptionStatus | None = None,
        cancel_at_period_end: bool | None = None,
        ended_at: object | None = None,
        canceled_at: object | None = None,
    ) -> Subscription: ...

    async def trial_used(self, user_id: UUID, residency_region: str, plan_id: UUID) -> bool: ...

    async def record_trial(
        self,
        user_id: UUID,
        residency_region: str,
        plan_id: UUID,
        days: int,
    ) -> None: ...

    async def append_event(
        self,
        subscription_id: UUID,
        event: str,
        from_status: str | None,
        to_status: str | None,
        payload: dict[str, object],
    ) -> None: ...


class PaymentRepository(Protocol):
    async def get_intent_by_key(self, idempotency_key: str) -> PaymentIntent | None: ...

    async def get_intent(self, intent_id: UUID) -> PaymentIntent | None: ...

    async def create_intent(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        residency_region: str,
        subscription_id: UUID | None,
        idempotency_key: str,
        amount: Decimal,
        currency: str,
    ) -> PaymentIntent: ...

    async def update_intent_status(
        self,
        intent_id: UUID,
        *,
        status: PaymentStatus,
        failure_reason: str | None = None,
    ) -> PaymentIntent: ...

    async def link_intent_to_subscription(
        self, intent_id: UUID, subscription_id: UUID
    ) -> PaymentIntent: ...

    async def record_payment(
        self,
        *,
        intent_id: UUID,
        provider: str,
        provider_charge_id: str,
        captured_amount: Decimal,
        currency: str,
    ) -> UUID: ...

    async def webhook_event_exists(self, provider: str, provider_event_id: str) -> bool: ...

    async def record_webhook_event(
        self,
        *,
        provider: str,
        provider_event_id: str,
        event_type: str,
        payload: dict[str, object],
    ) -> UUID: ...


class InvoiceRepository(Protocol):
    async def list_for_user(
        self, user_id: UUID, residency_region: str, *, limit: int, offset: int
    ) -> tuple[tuple[Invoice, ...], int]: ...

    async def create(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        residency_region: str,
        subscription_id: UUID | None,
        total: Decimal,
        currency: str,
    ) -> Invoice: ...


class EntitlementRepository(Protocol):
    async def list_for_user(
        self, user_id: UUID, residency_region: str
    ) -> tuple[Entitlement, ...]: ...

    async def get_for_feature(
        self, user_id: UUID, residency_region: str, feature_key: str
    ) -> Entitlement | None: ...

    async def upsert_from_plan(
        self,
        user_id: UUID,
        residency_region: str,
        plan_id: UUID,
    ) -> int: ...

    async def revoke_all_for_plan(
        self, user_id: UUID, residency_region: str, plan_id: UUID
    ) -> int: ...


class PlanRepository(Protocol):
    async def list_with_prices(
        self, pricing_zone_slug: str | None
    ) -> tuple[tuple[Plan, Price | None], ...]: ...

    async def get_by_slug(self, plan_slug: str) -> Plan | None: ...

    async def get_pricing_zone(self, slug: str) -> PricingZone | None: ...

    async def get_price(self, plan_id: UUID, pricing_zone_slug: str) -> Price | None: ...

    async def get_plan_features(
        self, plan_id: UUID
    ) -> tuple[tuple[str, bool, int | None], ...]: ...
