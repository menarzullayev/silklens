"""SQL repository implementations for billing.

Hand-written SQL (consistent with the heritage/identity pattern). All inserts
use parameter binding; jsonb columns are passed as JSON strings cast inside SQL.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.billing.entities import (
    Entitlement,
    Invoice,
    InvoiceStatus,
    PaymentIntent,
    PaymentStatus,
    Plan,
    PlanFeatures,
    Price,
    PricingZone,
    Subscription,
    SubscriptionStatus,
)


def _json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)


# ----------------------------------------------------------------------
# Plans + prices
# ----------------------------------------------------------------------


class SqlPlanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def list_with_prices(
        self, pricing_zone_slug: str | None
    ) -> tuple[tuple[Plan, Price | None], ...]:
        zone_clause = "pz.slug = :zone" if pricing_zone_slug else "pz.slug = 'cis'"
        params: dict[str, object] = {}
        if pricing_zone_slug:
            params["zone"] = pricing_zone_slug
        result = await self._s.execute(
            text(
                f"""
                SELECT
                    p.id AS plan_id,
                    p.tenant_id,
                    p.product_id,
                    pr.slug AS product_slug,
                    p.slug AS plan_slug,
                    p.name AS plan_name,
                    p.billing_period,
                    p.trial_days,
                    p.is_default,
                    p.is_active,
                    px.amount AS price_amount,
                    px.currency AS price_currency,
                    px.effective_from AS price_effective_from,
                    px.pricing_zone_id,
                    pz.slug AS pricing_zone_slug
                FROM product_plans p
                JOIN products pr ON pr.id = p.product_id
                LEFT JOIN pricing_zones pz ON {zone_clause}
                LEFT JOIN prices px
                    ON px.plan_id = p.id
                   AND px.pricing_zone_id = pz.id
                   AND px.is_active
                   AND (px.effective_until IS NULL OR px.effective_until > now())
                WHERE p.is_active
                ORDER BY pr.slug, p.sort_order, p.slug
                """  # noqa: S608
            ),
            params,
        )
        out: list[tuple[Plan, Price | None]] = []
        for row in result.all():
            m = row._mapping  # type: ignore[attr-defined]
            plan = Plan(
                id=m["plan_id"],
                tenant_id=m["tenant_id"],
                product_id=m["product_id"],
                product_slug=m["product_slug"],
                slug=m["plan_slug"],
                name=dict(m["plan_name"]) if m["plan_name"] else {},
                billing_period=m["billing_period"],
                trial_days=int(m["trial_days"]),
                is_default=bool(m["is_default"]),
                is_active=bool(m["is_active"]),
            )
            price = None
            if m["price_amount"] is not None:
                price = Price(
                    plan_id=m["plan_id"],
                    pricing_zone_id=m["pricing_zone_id"],
                    pricing_zone_slug=m["pricing_zone_slug"],
                    currency=m["price_currency"],
                    amount=Decimal(m["price_amount"]),
                    effective_from=m["price_effective_from"],
                )
            out.append((plan, price))
        return tuple(out)

    async def get_by_slug(self, plan_slug: str) -> Plan | None:
        row = (
            await self._s.execute(
                text(
                    """
                    SELECT
                        p.id, p.tenant_id, p.product_id, pr.slug AS product_slug,
                        p.slug, p.name, p.billing_period, p.trial_days,
                        p.is_default, p.is_active
                    FROM product_plans p
                    JOIN products pr ON pr.id = p.product_id
                    WHERE p.slug = :slug
                    LIMIT 1
                    """
                ),
                {"slug": plan_slug},
            )
        ).one_or_none()
        if row is None:
            return None
        m = row._mapping
        return Plan(
            id=m["id"],
            tenant_id=m["tenant_id"],
            product_id=m["product_id"],
            product_slug=m["product_slug"],
            slug=m["slug"],
            name=dict(m["name"]) if m["name"] else {},
            billing_period=m["billing_period"],
            trial_days=int(m["trial_days"]),
            is_default=bool(m["is_default"]),
            is_active=bool(m["is_active"]),
        )

    async def get_pricing_zone(self, slug: str) -> PricingZone | None:
        row = (
            await self._s.execute(
                text(
                    """
                    SELECT id, slug, name, country_codes, default_currency, purchasing_power_index
                    FROM pricing_zones
                    WHERE slug = :slug AND is_active
                    """
                ),
                {"slug": slug},
            )
        ).one_or_none()
        if row is None:
            return None
        m = row._mapping  # type: ignore[attr-defined]
        return PricingZone(
            id=m["id"],
            slug=m["slug"],
            name=dict(m["name"]) if m["name"] else {},
            country_codes=tuple(m["country_codes"]) if m["country_codes"] else (),
            default_currency=m["default_currency"],
            purchasing_power_index=Decimal(m["purchasing_power_index"]),
        )

    async def get_price(self, plan_id: UUID, pricing_zone_slug: str) -> Price | None:
        row = (
            await self._s.execute(
                text(
                    """
                    SELECT
                        px.plan_id, px.pricing_zone_id, pz.slug AS zone_slug,
                        px.currency, px.amount, px.effective_from
                    FROM prices px
                    JOIN pricing_zones pz ON pz.id = px.pricing_zone_id
                    WHERE px.plan_id = :plan_id
                      AND pz.slug = :zone
                      AND px.is_active
                      AND (px.effective_until IS NULL OR px.effective_until > now())
                    ORDER BY px.effective_from DESC
                    LIMIT 1
                    """
                ),
                {"plan_id": plan_id, "zone": pricing_zone_slug},
            )
        ).one_or_none()
        if row is None:
            return None
        m = row._mapping  # type: ignore[attr-defined]
        return Price(
            plan_id=m["plan_id"],
            pricing_zone_id=m["pricing_zone_id"],
            pricing_zone_slug=m["zone_slug"],
            currency=m["currency"],
            amount=Decimal(m["amount"]),
            effective_from=m["effective_from"],
        )

    async def get_plan_features(self, plan_id: UUID) -> tuple[tuple[str, bool, int | None], ...]:
        result = await self._s.execute(
            text(
                """
                SELECT feature_key, enabled, limit_value
                FROM plan_features
                WHERE plan_id = :plan_id
                """
            ),
            {"plan_id": plan_id},
        )
        return tuple(
            (
                m["feature_key"],
                bool(m["enabled"]),
                int(m["limit_value"]) if m["limit_value"] is not None else None,
            )
            for m in (r._mapping for r in result.all())  # type: ignore[attr-defined]
        )

    async def get_features_full(self, plan_id: UUID) -> tuple[PlanFeatures, ...]:
        result = await self._s.execute(
            text(
                """
                SELECT feature_key, enabled, limit_value, soft_limit
                FROM plan_features WHERE plan_id = :plan_id
                """
            ),
            {"plan_id": plan_id},
        )
        return tuple(
            PlanFeatures(
                feature_key=m["feature_key"],
                enabled=bool(m["enabled"]),
                limit_value=int(m["limit_value"]) if m["limit_value"] is not None else None,
                soft_limit=int(m["soft_limit"]) if m["soft_limit"] is not None else None,
            )
            for m in (r._mapping for r in result.all())  # type: ignore[attr-defined]
        )


# ----------------------------------------------------------------------
# Subscriptions
# ----------------------------------------------------------------------


_SUB_COLS = """
    s.id, s.tenant_id, s.user_id, s.residency_region,
    s.plan_id, p.slug AS plan_slug, s.status,
    s.current_period_start, s.current_period_end,
    s.trial_ends_at, s.cancel_at_period_end,
    s.canceled_at, s.ended_at, s.created_at, s.updated_at
"""


def _sub_from_row(row: object) -> Subscription:
    m = row._mapping  # type: ignore[attr-defined]
    return Subscription(
        id=m["id"],
        tenant_id=m["tenant_id"],
        user_id=m["user_id"],
        residency_region=m["residency_region"],
        plan_id=m["plan_id"],
        plan_slug=m["plan_slug"],
        status=SubscriptionStatus(m["status"]),
        current_period_start=m["current_period_start"],
        current_period_end=m["current_period_end"],
        trial_ends_at=m["trial_ends_at"],
        cancel_at_period_end=bool(m["cancel_at_period_end"]),
        canceled_at=m["canceled_at"],
        ended_at=m["ended_at"],
        created_at=m["created_at"],
        updated_at=m["updated_at"],
    )


class SqlSubscriptionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get_active_for_user(
        self, user_id: UUID, residency_region: str
    ) -> Subscription | None:
        row = (
            await self._s.execute(
                text(
                    f"""
                    SELECT {_SUB_COLS}
                    FROM subscriptions s
                    JOIN product_plans p ON p.id = s.plan_id
                    WHERE s.user_id = :uid
                      AND s.residency_region = :region
                      AND s.status IN ('trial','active','past_due','paused')
                    ORDER BY s.created_at DESC
                    LIMIT 1
                    """  # noqa: S608
                ),
                {"uid": user_id, "region": residency_region},
            )
        ).one_or_none()
        return _sub_from_row(row) if row else None

    async def get_by_id(self, subscription_id: UUID) -> Subscription | None:
        row = (
            await self._s.execute(
                text(
                    f"""
                    SELECT {_SUB_COLS}
                    FROM subscriptions s
                    JOIN product_plans p ON p.id = s.plan_id
                    WHERE s.id = :id
                    """  # noqa: S608
                ),
                {"id": subscription_id},
            )
        ).one_or_none()
        return _sub_from_row(row) if row else None

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
    ) -> Subscription:
        now = datetime.now(UTC)
        period_end = now + timedelta(days=max(period_days, 1))
        result = await self._s.execute(
            text(
                """
                INSERT INTO subscriptions (
                    tenant_id, user_id, residency_region, plan_id, status,
                    current_period_start, current_period_end, trial_ends_at
                ) VALUES (
                    :tenant, :uid, :region, :plan, :status,
                    :start, :end, :trial_end
                )
                RETURNING id, status, current_period_start, current_period_end,
                          trial_ends_at, cancel_at_period_end, canceled_at,
                          ended_at, created_at, updated_at
                """
            ),
            {
                "tenant": tenant_id,
                "uid": user_id,
                "region": residency_region,
                "plan": plan_id,
                "status": status.value,
                "start": now,
                "end": period_end,
                "trial_end": trial_ends_at,
            },
        )
        m = result.one()._mapping  # type: ignore[attr-defined]

        # Insert a subscription_item row matching the plan's product.
        await self._s.execute(
            text(
                """
                INSERT INTO subscription_items (subscription_id, product_id, plan_id, quantity)
                SELECT :sid, p.product_id, p.id, 1
                FROM product_plans p WHERE p.id = :plan
                """
            ),
            {"sid": m["id"], "plan": plan_id},
        )

        # Lookup plan slug for the returned entity.
        slug_row = (
            await self._s.execute(
                text("SELECT slug FROM product_plans WHERE id = :id"),
                {"id": plan_id},
            )
        ).scalar_one()

        await self._s.execute(
            text(
                """
                SELECT app.emit_event(
                    :tenant, 'subscription.created.v1', 'subscription', :sid,
                    CAST(:payload AS jsonb)
                )
                """
            ),
            {
                "tenant": tenant_id,
                "sid": m["id"],
                "payload": _json(
                    {
                        "plan_id": str(plan_id),
                        "user_id": str(user_id),
                        "status": status.value,
                    }
                ),
            },
        )

        await self._s.commit()
        return Subscription(
            id=m["id"],
            tenant_id=tenant_id,
            user_id=user_id,
            residency_region=residency_region,
            plan_id=plan_id,
            plan_slug=slug_row,
            status=SubscriptionStatus(m["status"]),
            current_period_start=m["current_period_start"],
            current_period_end=m["current_period_end"],
            trial_ends_at=m["trial_ends_at"],
            cancel_at_period_end=bool(m["cancel_at_period_end"]),
            canceled_at=m["canceled_at"],
            ended_at=m["ended_at"],
            created_at=m["created_at"],
            updated_at=m["updated_at"],
        )

    async def update_status(
        self,
        subscription_id: UUID,
        *,
        status: SubscriptionStatus | None = None,
        cancel_at_period_end: bool | None = None,
        ended_at: object | None = None,
        canceled_at: object | None = None,
    ) -> Subscription:
        sets: list[str] = []
        params: dict[str, object] = {"id": subscription_id}
        if status is not None:
            sets.append("status = :status")
            params["status"] = status.value
        if cancel_at_period_end is not None:
            sets.append("cancel_at_period_end = :capse")
            params["capse"] = cancel_at_period_end
        if ended_at is not None:
            sets.append("ended_at = :ended_at")
            params["ended_at"] = ended_at
        if canceled_at is not None:
            sets.append("canceled_at = :canceled_at")
            params["canceled_at"] = canceled_at
        if sets:
            await self._s.execute(
                text(
                    f"UPDATE subscriptions SET {', '.join(sets)} WHERE id = :id"  # noqa: S608
                ),
                params,
            )
            await self._s.commit()
        updated = await self.get_by_id(subscription_id)
        if updated is None:
            raise RuntimeError("subscription disappeared after update")
        return updated

    async def trial_used(self, user_id: UUID, residency_region: str, plan_id: UUID) -> bool:
        row = (
            await self._s.execute(
                text(
                    """
                    SELECT 1 FROM trials
                    WHERE user_id = :uid AND residency_region = :region
                      AND plan_id = :plan LIMIT 1
                    """
                ),
                {"uid": user_id, "region": residency_region, "plan": plan_id},
            )
        ).one_or_none()
        return row is not None

    async def record_trial(
        self,
        user_id: UUID,
        residency_region: str,
        plan_id: UUID,
        days: int,
    ) -> None:
        now = datetime.now(UTC)
        await self._s.execute(
            text(
                """
                INSERT INTO trials (user_id, residency_region, plan_id, started_at, ends_at)
                VALUES (:uid, :region, :plan, :start, :end)
                ON CONFLICT (user_id, residency_region, plan_id) DO NOTHING
                """
            ),
            {
                "uid": user_id,
                "region": residency_region,
                "plan": plan_id,
                "start": now,
                "end": now + timedelta(days=max(days, 1)),
            },
        )
        await self._s.commit()

    async def append_event(
        self,
        subscription_id: UUID,
        event: str,
        from_status: str | None,
        to_status: str | None,
        payload: dict[str, object],
    ) -> None:
        await self._s.execute(
            text(
                """
                INSERT INTO subscription_events (
                    subscription_id, event, from_status, to_status, payload
                ) VALUES (:sid, :event, :from_s, :to_s, CAST(:payload AS jsonb))
                """
            ),
            {
                "sid": subscription_id,
                "event": event,
                "from_s": from_status,
                "to_s": to_status,
                "payload": _json(payload),
            },
        )
        await self._s.commit()


# ----------------------------------------------------------------------
# Payments
# ----------------------------------------------------------------------


def _intent_from_row(row: object) -> PaymentIntent:
    m = row._mapping  # type: ignore[attr-defined]
    return PaymentIntent(
        id=m["id"],
        tenant_id=m["tenant_id"],
        user_id=m["user_id"],
        residency_region=m["residency_region"],
        subscription_id=m["subscription_id"],
        idempotency_key=m["idempotency_key"],
        amount=Decimal(m["amount"]),
        currency=m["currency"],
        status=PaymentStatus(m["status"]),
        failure_reason=m["failure_reason"],
        created_at=m["created_at"],
    )


class SqlPaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get_intent_by_key(self, idempotency_key: str) -> PaymentIntent | None:
        row = (
            await self._s.execute(
                text(
                    """
                    SELECT id, tenant_id, user_id, residency_region, subscription_id,
                           idempotency_key, amount, currency, status, failure_reason, created_at
                    FROM payment_intents WHERE idempotency_key = :k LIMIT 1
                    """
                ),
                {"k": idempotency_key},
            )
        ).one_or_none()
        return _intent_from_row(row) if row else None

    async def get_intent(self, intent_id: UUID) -> PaymentIntent | None:
        row = (
            await self._s.execute(
                text(
                    """
                    SELECT id, tenant_id, user_id, residency_region, subscription_id,
                           idempotency_key, amount, currency, status, failure_reason, created_at
                    FROM payment_intents WHERE id = :id
                    """
                ),
                {"id": intent_id},
            )
        ).one_or_none()
        return _intent_from_row(row) if row else None

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
    ) -> PaymentIntent:
        result = await self._s.execute(
            text(
                """
                INSERT INTO payment_intents (
                    tenant_id, user_id, residency_region, subscription_id,
                    idempotency_key, amount, currency, status
                ) VALUES (
                    :tenant, :uid, :region, :sub, :k, :amount, :ccy, 'requires_payment'
                )
                RETURNING id, tenant_id, user_id, residency_region, subscription_id,
                          idempotency_key, amount, currency, status, failure_reason, created_at
                """
            ),
            {
                "tenant": tenant_id,
                "uid": user_id,
                "region": residency_region,
                "sub": subscription_id,
                "k": idempotency_key,
                "amount": amount,
                "ccy": currency,
            },
        )
        await self._s.commit()
        return _intent_from_row(result.one())

    async def update_intent_status(
        self,
        intent_id: UUID,
        *,
        status: PaymentStatus,
        failure_reason: str | None = None,
    ) -> PaymentIntent:
        await self._s.execute(
            text(
                """
                UPDATE payment_intents SET status = :status, failure_reason = :reason
                WHERE id = :id
                """
            ),
            {"id": intent_id, "status": status.value, "reason": failure_reason},
        )
        await self._s.commit()
        updated = await self.get_intent(intent_id)
        if updated is None:
            raise RuntimeError("intent disappeared after update")
        return updated

    async def link_intent_to_subscription(
        self, intent_id: UUID, subscription_id: UUID
    ) -> PaymentIntent:
        await self._s.execute(
            text("UPDATE payment_intents SET subscription_id = :sid WHERE id = :id"),
            {"id": intent_id, "sid": subscription_id},
        )
        await self._s.commit()
        updated = await self.get_intent(intent_id)
        if updated is None:
            raise RuntimeError("intent disappeared after linking")
        return updated

    async def record_payment(
        self,
        *,
        intent_id: UUID,
        provider: str,
        provider_charge_id: str,
        captured_amount: Decimal,
        currency: str,
    ) -> UUID:
        result = await self._s.execute(
            text(
                """
                INSERT INTO payments (
                    intent_id, provider, provider_charge_id, captured_amount, currency
                ) VALUES (:iid, :provider, :charge, :amount, :ccy)
                ON CONFLICT (provider, provider_charge_id) DO NOTHING
                RETURNING id
                """
            ),
            {
                "iid": intent_id,
                "provider": provider,
                "charge": provider_charge_id,
                "amount": captured_amount,
                "ccy": currency,
            },
        )
        # MED-B1: only emit `payment.captured.v1` when the INSERT actually
        # created a new row. Re-emitting on a duplicate would double-fire the
        # downstream side-effects (subscription activation, entitlement
        # grants, …) and the outbox consumer has no application-level guard
        # against that.
        row = result.one_or_none()
        if row is not None:
            await self._s.execute(
                text(
                    """
                    SELECT app.emit_event(
                        (SELECT tenant_id FROM payment_intents WHERE id = :iid),
                        'payment.captured.v1', 'payment', :iid,
                        CAST(:payload AS jsonb)
                    )
                    """
                ),
                {
                    "iid": intent_id,
                    "payload": _json(
                        {
                            "provider": provider,
                            "amount": str(captured_amount),
                            "currency": currency,
                        }
                    ),
                },
            )
        await self._s.commit()
        if row is None:
            # Already existed — return the existing id.
            return (
                await self._s.execute(
                    text("SELECT id FROM payments WHERE provider = :p AND provider_charge_id = :c"),
                    {"p": provider, "c": provider_charge_id},
                )
            ).scalar_one()
        return row._mapping["id"]  # type: ignore[attr-defined]

    async def webhook_event_exists(self, provider: str, provider_event_id: str) -> bool:
        row = (
            await self._s.execute(
                text(
                    """
                    SELECT 1 FROM payment_webhook_events
                    WHERE provider = :p AND provider_event_id = :e LIMIT 1
                    """
                ),
                {"p": provider, "e": provider_event_id},
            )
        ).one_or_none()
        return row is not None

    async def record_webhook_event(
        self,
        *,
        provider: str,
        provider_event_id: str,
        event_type: str,
        payload: dict[str, object],
    ) -> UUID:
        result = await self._s.execute(
            text(
                """
                INSERT INTO payment_webhook_events (
                    provider, provider_event_id, event_type, payload
                ) VALUES (:p, :e, :t, CAST(:payload AS jsonb))
                ON CONFLICT (provider, provider_event_id) DO NOTHING
                RETURNING id
                """
            ),
            {
                "p": provider,
                "e": provider_event_id,
                "t": event_type,
                "payload": _json(payload),
            },
        )
        await self._s.commit()
        row = result.one_or_none()
        if row is None:
            return (
                await self._s.execute(
                    text(
                        "SELECT id FROM payment_webhook_events "
                        "WHERE provider = :p AND provider_event_id = :e"
                    ),
                    {"p": provider, "e": provider_event_id},
                )
            ).scalar_one()
        return row._mapping["id"]  # type: ignore[attr-defined]


# ----------------------------------------------------------------------
# Invoices
# ----------------------------------------------------------------------


class SqlInvoiceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def list_for_user(
        self, user_id: UUID, residency_region: str, *, limit: int, offset: int
    ) -> tuple[tuple[Invoice, ...], int]:
        count_row = await self._s.execute(
            text(
                "SELECT count(*) FROM invoices WHERE user_id = :uid AND residency_region = :region"
            ),
            {"uid": user_id, "region": residency_region},
        )
        total = count_row.scalar_one()
        result = await self._s.execute(
            text(
                """
                SELECT id, tenant_id, user_id, residency_region, subscription_id,
                       number, total, currency, status, period_start, period_end,
                       issued_at, paid_at, pdf_url, created_at
                FROM invoices
                WHERE user_id = :uid AND residency_region = :region
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            {
                "uid": user_id,
                "region": residency_region,
                "limit": limit,
                "offset": offset,
            },
        )
        items: list[Invoice] = []
        for r in result.all():
            m = r._mapping  # type: ignore[attr-defined]
            items.append(
                Invoice(
                    id=m["id"],
                    tenant_id=m["tenant_id"],
                    user_id=m["user_id"],
                    residency_region=m["residency_region"],
                    subscription_id=m["subscription_id"],
                    number=m["number"],
                    total=Decimal(m["total"]),
                    currency=m["currency"],
                    status=InvoiceStatus(m["status"]),
                    period_start=m["period_start"],
                    period_end=m["period_end"],
                    issued_at=m["issued_at"],
                    paid_at=m["paid_at"],
                    pdf_url=m["pdf_url"],
                    created_at=m["created_at"],
                )
            )
        return tuple(items), int(total)

    async def create(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        residency_region: str,
        subscription_id: UUID | None,
        total: Decimal,
        currency: str,
    ) -> Invoice:
        # MED-B2: ``number`` is generated by the ``tg_invoice_number`` BEFORE
        # INSERT trigger (migration 0052) from ``invoices_number_seq``. We
        # used to pass ``''`` so the trigger would overwrite it; the column
        # is now omitted entirely and the trigger fills the NULL with the
        # canonical SLN-YYYY-NNNNNNN value. Single source of truth for the
        # numbering scheme stays in SQL.
        result = await self._s.execute(
            text(
                """
                INSERT INTO invoices (
                    tenant_id, user_id, residency_region, subscription_id,
                    total, currency, status, issued_at
                ) VALUES (
                    :tenant, :uid, :region, :sub,
                    :total, :ccy, 'open', now()
                )
                RETURNING id, number, total, currency, status, period_start,
                          period_end, issued_at, paid_at, pdf_url, created_at
                """
            ),
            {
                "tenant": tenant_id,
                "uid": user_id,
                "region": residency_region,
                "sub": subscription_id,
                "total": total,
                "ccy": currency,
            },
        )
        await self._s.commit()
        m = result.one()._mapping  # type: ignore[attr-defined]
        return Invoice(
            id=m["id"],
            tenant_id=tenant_id,
            user_id=user_id,
            residency_region=residency_region,
            subscription_id=subscription_id,
            number=m["number"],
            total=Decimal(m["total"]),
            currency=m["currency"],
            status=InvoiceStatus(m["status"]),
            period_start=m["period_start"],
            period_end=m["period_end"],
            issued_at=m["issued_at"],
            paid_at=m["paid_at"],
            pdf_url=m["pdf_url"],
            created_at=m["created_at"],
        )


# ----------------------------------------------------------------------
# Entitlements
# ----------------------------------------------------------------------


class SqlEntitlementRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def list_for_user(self, user_id: UUID, residency_region: str) -> tuple[Entitlement, ...]:
        result = await self._s.execute(
            text(
                """
                SELECT user_id, residency_region, feature_key, granted,
                       limit_value, source, source_id, effective_until
                FROM entitlements
                WHERE user_id = :uid AND residency_region = :region
                """
            ),
            {"uid": user_id, "region": residency_region},
        )
        out: list[Entitlement] = []
        for r in result.all():
            m = r._mapping  # type: ignore[attr-defined]
            out.append(
                Entitlement(
                    user_id=m["user_id"],
                    residency_region=m["residency_region"],
                    feature_key=m["feature_key"],
                    granted=bool(m["granted"]),
                    limit_value=int(m["limit_value"]) if m["limit_value"] is not None else None,
                    source=m["source"],
                    source_id=m["source_id"],
                    effective_until=m["effective_until"],
                )
            )
        return tuple(out)

    async def get_for_feature(
        self, user_id: UUID, residency_region: str, feature_key: str
    ) -> Entitlement | None:
        row = (
            await self._s.execute(
                text(
                    """
                    SELECT user_id, residency_region, feature_key, granted,
                           limit_value, source, source_id, effective_until
                    FROM entitlements
                    WHERE user_id = :uid AND residency_region = :region AND feature_key = :fk
                    """
                ),
                {"uid": user_id, "region": residency_region, "fk": feature_key},
            )
        ).one_or_none()
        if row is None:
            return None
        m = row._mapping  # type: ignore[attr-defined]
        return Entitlement(
            user_id=m["user_id"],
            residency_region=m["residency_region"],
            feature_key=m["feature_key"],
            granted=bool(m["granted"]),
            limit_value=int(m["limit_value"]) if m["limit_value"] is not None else None,
            source=m["source"],
            source_id=m["source_id"],
            effective_until=m["effective_until"],
        )

    async def upsert_from_plan(
        self,
        user_id: UUID,
        residency_region: str,
        plan_id: UUID,
    ) -> int:
        result = await self._s.execute(
            text(
                """
                INSERT INTO entitlements (
                    user_id, residency_region, feature_key,
                    granted, limit_value, source, source_id
                )
                SELECT :uid, :region, pf.feature_key, pf.enabled, pf.limit_value,
                       'plan', :plan
                FROM plan_features pf
                WHERE pf.plan_id = :plan
                ON CONFLICT (user_id, residency_region, feature_key) DO UPDATE
                  SET granted = EXCLUDED.granted,
                      limit_value = EXCLUDED.limit_value,
                      source = EXCLUDED.source,
                      source_id = EXCLUDED.source_id
                RETURNING feature_key
                """
            ),
            {"uid": user_id, "region": residency_region, "plan": plan_id},
        )
        rows = result.all()
        await self._s.commit()
        return len(rows)

    async def revoke_all_for_plan(self, user_id: UUID, residency_region: str, plan_id: UUID) -> int:
        result = await self._s.execute(
            text(
                """
                UPDATE entitlements SET granted = false
                WHERE user_id = :uid AND residency_region = :region
                  AND source = 'plan' AND source_id = :plan
                RETURNING feature_key
                """
            ),
            {"uid": user_id, "region": residency_region, "plan": plan_id},
        )
        rows = result.all()
        await self._s.commit()
        return len(rows)
