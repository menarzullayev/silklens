"""Billing API endpoints.

Public:
  GET  /v1/billing/plans?pricing_zone=cis      — list plans + prices
  POST /v1/billing/webhooks/{provider}         — provider webhook ingress

Authenticated:
  GET  /v1/billing/me/subscription              — current subscription (or null)
  POST /v1/billing/subscriptions                — start a subscription
  POST /v1/billing/subscriptions/cancel         — cancel (at period end by default)
  POST /v1/billing/subscriptions/resume         — undo cancel-at-period-end
  GET  /v1/billing/me/invoices                  — paginated invoice list
  GET  /v1/billing/me/entitlements              — materialised entitlements
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.domain.billing.errors import BillingError
from src.domain.billing.service import BillingService
from src.infrastructure.billing.mock_provider import MockPaymentProvider
from src.infrastructure.billing.repository import (
    SqlEntitlementRepository,
    SqlInvoiceRepository,
    SqlPaymentRepository,
    SqlPlanRepository,
    SqlSubscriptionRepository,
)
from src.middleware.auth import CurrentUserDep

router = APIRouter(prefix="/v1/billing", tags=["billing"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _service(db: AsyncSession) -> BillingService:
    return BillingService(
        plans=SqlPlanRepository(db),
        subscriptions=SqlSubscriptionRepository(db),
        payments=SqlPaymentRepository(db),
        invoices=SqlInvoiceRepository(db),
        entitlements=SqlEntitlementRepository(db),
        provider=MockPaymentProvider(),
    )


# --- Schemas ---------------------------------------------------------------


class PriceOut(BaseModel):
    pricing_zone_slug: str
    currency: str
    amount: Decimal
    effective_from: datetime


class PlanOut(BaseModel):
    id: UUID
    slug: str
    product_slug: str
    name: dict[str, str]
    billing_period: str
    trial_days: int
    is_default: bool
    price: PriceOut | None = None


class PlansOut(BaseModel):
    items: list[PlanOut]
    pricing_zone: str | None


class SubscriptionOut(BaseModel):
    id: UUID
    plan_id: UUID
    plan_slug: str
    status: str
    current_period_start: datetime
    current_period_end: datetime
    trial_ends_at: datetime | None
    cancel_at_period_end: bool
    canceled_at: datetime | None
    ended_at: datetime | None


class PaymentIntentOut(BaseModel):
    id: UUID
    idempotency_key: str
    amount: Decimal
    currency: str
    status: str
    failure_reason: str | None


class StartSubscriptionRequest(BaseModel):
    plan_slug: str = Field(min_length=2, max_length=64)
    payment_method_token: str = Field(min_length=1, max_length=256)
    pricing_zone_slug: str | None = Field(default=None, min_length=2, max_length=32)


class StartSubscriptionResponse(BaseModel):
    subscription: SubscriptionOut
    payment_intent: PaymentIntentOut | None


class CancelSubscriptionRequest(BaseModel):
    at_period_end: bool = True


class InvoiceOut(BaseModel):
    id: UUID
    number: str
    total: Decimal
    currency: str
    status: str
    issued_at: datetime | None
    paid_at: datetime | None


class InvoicesOut(BaseModel):
    items: list[InvoiceOut]
    total: int
    limit: int
    offset: int


class EntitlementOut(BaseModel):
    feature_key: str
    granted: bool
    limit_value: int | None
    source: str


class EntitlementsOut(BaseModel):
    items: list[EntitlementOut]


class WebhookResult(BaseModel):
    received: bool
    duplicate: bool


# --- Helpers ---------------------------------------------------------------


def _sub_out(sub: Any) -> SubscriptionOut:
    return SubscriptionOut(
        id=sub.id,
        plan_id=sub.plan_id,
        plan_slug=sub.plan_slug,
        status=sub.status.value,
        current_period_start=sub.current_period_start,
        current_period_end=sub.current_period_end,
        trial_ends_at=sub.trial_ends_at,
        cancel_at_period_end=sub.cancel_at_period_end,
        canceled_at=sub.canceled_at,
        ended_at=sub.ended_at,
    )


def _intent_out(intent: Any) -> PaymentIntentOut:
    return PaymentIntentOut(
        id=intent.id,
        idempotency_key=intent.idempotency_key,
        amount=intent.amount,
        currency=intent.currency,
        status=intent.status.value,
        failure_reason=intent.failure_reason,
    )


def _raise(exc: BillingError) -> None:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": str(exc)},
    ) from exc


# --- Routes: public catalog -----------------------------------------------


@router.get("/plans", response_model=PlansOut)
async def list_plans(
    db: SessionDep,
    pricing_zone: Annotated[str | None, Query(min_length=2, max_length=32)] = None,
) -> PlansOut:
    pairs = await _service(db).list_plans(pricing_zone_slug=pricing_zone)
    items = [
        PlanOut(
            id=plan.id,
            slug=plan.slug,
            product_slug=plan.product_slug,
            name=plan.name,
            billing_period=plan.billing_period,
            trial_days=plan.trial_days,
            is_default=plan.is_default,
            price=(
                PriceOut(
                    pricing_zone_slug=price.pricing_zone_slug,
                    currency=price.currency,
                    amount=price.amount,
                    effective_from=price.effective_from,
                )
                if price is not None
                else None
            ),
        )
        for plan, price in pairs
    ]
    return PlansOut(items=items, pricing_zone=pricing_zone or "cis")


# --- Routes: authenticated -------------------------------------------------


@router.get("/me/subscription", response_model=SubscriptionOut | None)
async def get_my_subscription(ctx: CurrentUserDep, db: SessionDep) -> SubscriptionOut | None:
    sub = await _service(db).get_current_subscription(
        user_id=ctx.user_id, residency_region=ctx.residency_region.value
    )
    return _sub_out(sub) if sub else None


@router.post(
    "/subscriptions",
    response_model=StartSubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_subscription(
    payload: StartSubscriptionRequest,
    ctx: CurrentUserDep,
    db: SessionDep,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=128)],
) -> StartSubscriptionResponse:
    try:
        result = await _service(db).start_subscription(
            user_id=ctx.user_id,
            tenant_id=ctx.tenant_id,
            residency_region=ctx.residency_region.value,
            plan_slug=payload.plan_slug,
            payment_method_token=payload.payment_method_token,
            pricing_zone_slug=payload.pricing_zone_slug,
            idempotency_key=idempotency_key,
        )
    except BillingError as exc:
        _raise(exc)
        raise  # unreachable; placates type-checker
    return StartSubscriptionResponse(
        subscription=_sub_out(result.subscription),
        payment_intent=_intent_out(result.payment_intent) if result.payment_intent else None,
    )


@router.post("/subscriptions/cancel", response_model=SubscriptionOut)
async def cancel_subscription(
    ctx: CurrentUserDep,
    db: SessionDep,
    payload: Annotated[
        CancelSubscriptionRequest,
        Body(default_factory=CancelSubscriptionRequest),
    ],
) -> SubscriptionOut:
    try:
        sub = await _service(db).cancel_subscription(
            user_id=ctx.user_id,
            residency_region=ctx.residency_region.value,
            at_period_end=payload.at_period_end,
        )
    except BillingError as exc:
        _raise(exc)
        raise
    return _sub_out(sub)


@router.post("/subscriptions/resume", response_model=SubscriptionOut)
async def resume_subscription(ctx: CurrentUserDep, db: SessionDep) -> SubscriptionOut:
    try:
        sub = await _service(db).resume_subscription(
            user_id=ctx.user_id, residency_region=ctx.residency_region.value
        )
    except BillingError as exc:
        _raise(exc)
        raise
    return _sub_out(sub)


@router.get("/me/invoices", response_model=InvoicesOut)
async def list_my_invoices(
    ctx: CurrentUserDep,
    db: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> InvoicesOut:
    items, total = await _service(db).list_invoices(
        user_id=ctx.user_id,
        residency_region=ctx.residency_region.value,
        limit=limit,
        offset=offset,
    )
    return InvoicesOut(
        items=[
            InvoiceOut(
                id=inv.id,
                number=inv.number,
                total=inv.total,
                currency=inv.currency,
                status=inv.status.value,
                issued_at=inv.issued_at,
                paid_at=inv.paid_at,
            )
            for inv in items
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/me/entitlements", response_model=EntitlementsOut)
async def list_my_entitlements(ctx: CurrentUserDep, db: SessionDep) -> EntitlementsOut:
    repo = SqlEntitlementRepository(db)
    items = await repo.list_for_user(ctx.user_id, ctx.residency_region.value)
    return EntitlementsOut(
        items=[
            EntitlementOut(
                feature_key=e.feature_key,
                granted=e.granted,
                limit_value=e.limit_value,
                source=e.source,
            )
            for e in items
        ]
    )


# --- Routes: webhooks ------------------------------------------------------


@router.post("/webhooks/{provider}", response_model=WebhookResult)
async def receive_webhook(
    provider: str,
    request: Request,
    db: SessionDep,
) -> WebhookResult:
    """Provider webhook ingress.

    Signature verification lands in FAZA 4 (per-provider). For now we accept
    the body, derive a synthetic `provider_event_id` from headers/body if the
    provider didn't supply one, and store the row idempotently.
    """
    body_bytes = await request.body()
    import json

    try:
        payload = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "billing.webhook_invalid_json", "message": str(exc)},
        ) from exc

    provider_event_id = (
        request.headers.get("X-Provider-Event-Id")
        or payload.get("id")
        or payload.get("event_id")
        or f"evt_{request.headers.get('X-Request-Id', 'unknown')}"
    )
    event_type = payload.get("type") or payload.get("event") or "unknown"

    try:
        stored = await _service(db).record_webhook(
            provider=provider,
            provider_event_id=str(provider_event_id),
            event_type=str(event_type),
            payload=payload if isinstance(payload, dict) else {"raw": payload},
        )
    except BillingError as exc:
        _raise(exc)
        raise
    return WebhookResult(received=True, duplicate=not stored)
