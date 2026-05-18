"""Billing application service.

Orchestrates plan lookup, subscription state machine, payment intent creation
and entitlement resolution. Real provider integrations land in FAZA 4; this
service interacts only with the abstract PaymentProvider protocol so we can
slot in MockPaymentProvider today and StripeProvider later.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from src.domain.billing.entities import (
    EntitlementDecision,
    Invoice,
    PaymentStatus,
    Plan,
    Price,
    StartSubscriptionResult,
    Subscription,
    SubscriptionStatus,
)
from src.domain.billing.errors import (
    AlreadySubscribed,
    InvalidWebhookProvider,
    PaymentFailed,
    PlanNotFound,
    PriceNotFound,
    SubscriptionNotFound,
)
from src.domain.billing.repository import (
    EntitlementRepository,
    InvoiceRepository,
    PaymentRepository,
    PlanRepository,
    SubscriptionRepository,
)

VALID_WEBHOOK_PROVIDERS = frozenset({"stripe", "payme", "click", "apple_iap", "google_iap"})

_BILLING_DAYS_BY_PERIOD: dict[str, int] = {
    "monthly": 30,
    "quarterly": 90,
    "yearly": 365,
    "lifetime": 36500,
    "one_time": 30,
}


@dataclass(slots=True, frozen=True)
class _AuthCtx:
    user_id: UUID
    tenant_id: UUID
    residency_region: str


class PaymentProvider(Protocol):
    """Abstract payment provider — mock now, Stripe/Payme/Click later."""

    name: str

    async def create_payment_intent(
        self,
        *,
        amount: Decimal,
        currency: str,
        customer_ref: str,
        idempotency_key: str,
    ) -> dict[str, str]: ...

    async def confirm_payment_intent(
        self, *, intent_id: str, payment_method_token: str
    ) -> dict[str, str]: ...


class BillingService:
    def __init__(
        self,
        *,
        plans: PlanRepository,
        subscriptions: SubscriptionRepository,
        payments: PaymentRepository,
        invoices: InvoiceRepository,
        entitlements: EntitlementRepository,
        provider: PaymentProvider,
    ) -> None:
        self._plans = plans
        self._subs = subscriptions
        self._payments = payments
        self._invoices = invoices
        self._entitlements = entitlements
        self._provider = provider

    # ------------------------------------------------------------------
    # public catalog
    # ------------------------------------------------------------------

    async def list_plans(
        self, *, pricing_zone_slug: str | None = None
    ) -> tuple[tuple[Plan, Price | None], ...]:
        return await self._plans.list_with_prices(pricing_zone_slug)

    # ------------------------------------------------------------------
    # subscription state machine
    # ------------------------------------------------------------------

    async def get_current_subscription(
        self, *, user_id: UUID, residency_region: str
    ) -> Subscription | None:
        return await self._subs.get_active_for_user(user_id, residency_region)

    async def start_subscription(
        self,
        *,
        user_id: UUID,
        tenant_id: UUID,
        residency_region: str,
        plan_slug: str,
        payment_method_token: str,
        pricing_zone_slug: str | None,
        idempotency_key: str,
    ) -> StartSubscriptionResult:
        # 1. Idempotency: if we've already created the intent, short-circuit.
        existing_intent = await self._payments.get_intent_by_key(idempotency_key)
        if existing_intent is not None:
            sub = None
            if existing_intent.subscription_id is not None:
                sub = await self._subs.get_by_id(existing_intent.subscription_id)
            if sub is not None:
                return StartSubscriptionResult(subscription=sub, payment_intent=existing_intent)

        # 2. Resolve the plan + active sub state.
        plan = await self._plans.get_by_slug(plan_slug)
        if plan is None or not plan.is_active:
            raise PlanNotFound(f"plan '{plan_slug}' is not available")

        existing_sub = await self._subs.get_active_for_user(user_id, residency_region)
        if existing_sub is not None and existing_sub.status in {
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.TRIAL,
        }:
            raise AlreadySubscribed("user already has an active subscription")

        # 3. Trial fast-path.
        if plan.trial_days > 0 and not await self._subs.trial_used(
            user_id, residency_region, plan.id
        ):
            sub = await self._create_trial(
                tenant_id=tenant_id,
                user_id=user_id,
                residency_region=residency_region,
                plan=plan,
            )
            await self._entitlements.upsert_from_plan(user_id, residency_region, plan.id)
            return StartSubscriptionResult(subscription=sub, payment_intent=None)

        # 4. Paid path: resolve price.
        zone_slug = pricing_zone_slug or "cis"
        price = await self._plans.get_price(plan.id, zone_slug)
        if price is None:
            raise PriceNotFound(f"no price for plan '{plan_slug}' in zone '{zone_slug}'")

        # 5. Create payment intent record (DB) + delegate to provider.
        intent = await self._payments.create_intent(
            tenant_id=tenant_id,
            user_id=user_id,
            residency_region=residency_region,
            subscription_id=None,
            idempotency_key=idempotency_key,
            amount=price.amount,
            currency=price.currency,
        )
        provider_meta = await self._provider.create_payment_intent(
            amount=price.amount,
            currency=price.currency,
            customer_ref=str(user_id),
            idempotency_key=idempotency_key,
        )

        # 6. Confirm with mock provider; in production this would be async via webhook.
        confirm = await self._provider.confirm_payment_intent(
            intent_id=provider_meta["id"],
            payment_method_token=payment_method_token,
        )
        if confirm.get("status") != "succeeded":
            failure = confirm.get("failure_code", "unknown")
            await self._payments.update_intent_status(
                intent.id, status=PaymentStatus.FAILED, failure_reason=failure
            )
            raise PaymentFailed(failure)

        # 7. Record provider charge, flip intent succeeded, create subscription.
        await self._payments.record_payment(
            intent_id=intent.id,
            provider=self._provider.name,
            provider_charge_id=provider_meta["id"],
            captured_amount=price.amount,
            currency=price.currency,
        )
        intent = await self._payments.update_intent_status(
            intent.id, status=PaymentStatus.SUCCEEDED
        )
        # Business metric: bump the revenue counter once the charge actually
        # succeeded. Non-USD currencies count their notional amount — the
        # Grafana dashboard renames the panel accordingly until we wire FX.
        try:
            from src.core.metrics import business_revenue_usd_total

            business_revenue_usd_total.inc(float(price.amount))
        except Exception:  # noqa: S110
            # Observability is best-effort — never break a real payment.
            pass

        sub = await self._subs.create(
            tenant_id=tenant_id,
            user_id=user_id,
            residency_region=residency_region,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE,
            trial_ends_at=None,
            period_days=_BILLING_DAYS_BY_PERIOD.get(plan.billing_period, 30),
        )
        await self._subs.append_event(
            sub.id,
            "activated",
            None,
            SubscriptionStatus.ACTIVE.value,
            {"plan_id": str(plan.id), "intent_id": str(intent.id)},
        )
        await self._entitlements.upsert_from_plan(user_id, residency_region, plan.id)

        # Link the intent to its newly minted subscription so an idempotent
        # retry of POST /subscriptions can short-circuit straight back to the
        # existing pair instead of trying to start a fresh subscription.
        intent = await self._payments.link_intent_to_subscription(intent.id, sub.id)
        return StartSubscriptionResult(subscription=sub, payment_intent=intent)

    async def _create_trial(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        residency_region: str,
        plan: Plan,
    ) -> Subscription:
        now = datetime.now(UTC)
        trial_ends_at = now + timedelta(days=plan.trial_days)
        sub = await self._subs.create(
            tenant_id=tenant_id,
            user_id=user_id,
            residency_region=residency_region,
            plan_id=plan.id,
            status=SubscriptionStatus.TRIAL,
            trial_ends_at=trial_ends_at,
            period_days=plan.trial_days,
        )
        await self._subs.record_trial(user_id, residency_region, plan.id, plan.trial_days)
        await self._subs.append_event(
            sub.id,
            "trial_started",
            None,
            SubscriptionStatus.TRIAL.value,
            {"plan_id": str(plan.id), "trial_days": plan.trial_days},
        )
        return sub

    async def cancel_subscription(
        self,
        *,
        user_id: UUID,
        residency_region: str,
        at_period_end: bool = True,
    ) -> Subscription:
        sub = await self._subs.get_active_for_user(user_id, residency_region)
        if sub is None:
            raise SubscriptionNotFound("no active subscription")
        now = datetime.now(UTC)
        if at_period_end:
            updated = await self._subs.update_status(
                sub.id, cancel_at_period_end=True, canceled_at=now
            )
        else:
            updated = await self._subs.update_status(
                sub.id,
                status=SubscriptionStatus.CANCELED,
                cancel_at_period_end=False,
                canceled_at=now,
                ended_at=now,
            )
            await self._entitlements.revoke_all_for_plan(user_id, residency_region, sub.plan_id)
        await self._subs.append_event(
            sub.id,
            "canceled",
            sub.status.value,
            updated.status.value,
            {"at_period_end": at_period_end},
        )
        return updated

    async def resume_subscription(self, *, user_id: UUID, residency_region: str) -> Subscription:
        sub = await self._subs.get_active_for_user(user_id, residency_region)
        if sub is None:
            raise SubscriptionNotFound("no subscription to resume")
        if not sub.cancel_at_period_end:
            return sub
        updated = await self._subs.update_status(
            sub.id, cancel_at_period_end=False, canceled_at=None
        )
        await self._subs.append_event(sub.id, "resumed", sub.status.value, updated.status.value, {})
        return updated

    # ------------------------------------------------------------------
    # invoices + entitlements
    # ------------------------------------------------------------------

    async def list_invoices(
        self, *, user_id: UUID, residency_region: str, limit: int, offset: int
    ) -> tuple[tuple[Invoice, ...], int]:
        return await self._invoices.list_for_user(
            user_id, residency_region, limit=limit, offset=offset
        )

    async def check_entitlement(
        self,
        *,
        user_id: UUID,
        residency_region: str,
        feature_key: str,
    ) -> EntitlementDecision:
        ent = await self._entitlements.get_for_feature(user_id, residency_region, feature_key)
        if ent is not None:
            return EntitlementDecision(
                feature_key=feature_key,
                granted=ent.granted,
                limit_value=ent.limit_value,
                source=ent.source,
                reason="ok" if ent.granted else "revoked",
            )
        # Fall back to plan computation.
        sub = await self._subs.get_active_for_user(user_id, residency_region)
        if sub is None or sub.status not in {
            SubscriptionStatus.TRIAL,
            SubscriptionStatus.ACTIVE,
        }:
            return EntitlementDecision(
                feature_key=feature_key,
                granted=False,
                source="plan",
                reason="no_active_subscription",
            )
        plan_features = await self._plans.get_plan_features(sub.plan_id)
        for fk, enabled, limit in plan_features:
            if fk == feature_key:
                return EntitlementDecision(
                    feature_key=feature_key,
                    granted=enabled,
                    limit_value=limit,
                    source="plan",
                    reason="ok" if enabled else "feature_disabled",
                )
        return EntitlementDecision(
            feature_key=feature_key,
            granted=False,
            source="plan",
            reason="feature_not_in_plan",
        )

    # ------------------------------------------------------------------
    # webhooks
    # ------------------------------------------------------------------

    async def record_webhook(
        self,
        *,
        provider: str,
        provider_event_id: str,
        event_type: str,
        payload: dict[str, object],
    ) -> bool:
        """Idempotent webhook handling. Returns True if newly stored, False if duplicate."""
        if provider not in VALID_WEBHOOK_PROVIDERS:
            raise InvalidWebhookProvider(provider)
        if await self._payments.webhook_event_exists(provider, provider_event_id):
            return False
        await self._payments.record_webhook_event(
            provider=provider,
            provider_event_id=provider_event_id,
            event_type=event_type,
            payload=payload,
        )
        return True

    # ------------------------------------------------------------------
    # Real-provider webhook event handlers (FAZA 4 — Stripe et al)
    # ------------------------------------------------------------------
    #
    # These translate provider-shaped events into our internal state.
    # ``record_webhook`` MUST be called first so the
    # ``payment_webhook_events.UNIQUE(provider, provider_event_id)`` index
    # guarantees we never process the same event twice.

    async def handle_payment_succeeded(
        self,
        *,
        provider: str,
        provider_charge_id: str,
        amount: Decimal,
        currency: str,
        metadata: dict[str, object] | None = None,
    ) -> None:
        """Finalize the intent → payment row on a verified ``payment_intent.succeeded``."""
        intent = None
        if metadata and "idempotency_key" in metadata:
            intent = await self._payments.get_intent_by_key(str(metadata["idempotency_key"]))
        if intent is None:
            # Without a linkable intent we still record the charge for accounting,
            # but skip subscription state transitions (no user context available).
            return
        await self._payments.record_payment(
            intent_id=intent.id,
            provider=provider,
            provider_charge_id=provider_charge_id,
            captured_amount=amount,
            currency=currency,
        )
        if intent.status != PaymentStatus.SUCCEEDED:
            await self._payments.update_intent_status(intent.id, status=PaymentStatus.SUCCEEDED)

    async def mark_payment_failed(
        self,
        *,
        provider_charge_id: str,
        failure_code: str,
        metadata: dict[str, object] | None = None,
    ) -> None:
        """Mark an intent as ``failed`` on ``payment_intent.payment_failed``."""
        _ = provider_charge_id  # reserved for charge-keyed lookup once we store it
        intent = None
        if metadata and "idempotency_key" in metadata:
            intent = await self._payments.get_intent_by_key(str(metadata["idempotency_key"]))
        if intent is None:
            return
        if intent.status != PaymentStatus.FAILED:
            await self._payments.update_intent_status(
                intent.id, status=PaymentStatus.FAILED, failure_reason=failure_code
            )

    async def mark_subscription_canceled_external(
        self,
        *,
        provider_subscription_id: str,
    ) -> None:
        """Handle ``customer.subscription.deleted`` from the upstream provider.

        Placeholder until ``subscriptions.provider_subscription_id`` lands;
        keeps the webhook router exhaustive so unknown events can't slip past.
        """
        _ = provider_subscription_id

    async def handle_invoice_event(
        self,
        *,
        provider_invoice_id: str,
        succeeded: bool,
    ) -> None:
        """Handle ``invoice.payment_succeeded`` / ``invoice.payment_failed``.

        Placeholder until ``invoices.provider_invoice_id`` lands.
        """
        _ = provider_invoice_id, succeeded
