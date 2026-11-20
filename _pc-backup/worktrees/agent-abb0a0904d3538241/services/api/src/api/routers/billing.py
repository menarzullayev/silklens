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
from src.infrastructure.billing.factory import (
    build_billing_service,
    build_click_provider_from_settings,
    build_payme_provider_from_settings,
    build_paypal_provider_from_settings,
    build_stripe_provider_from_settings,
    is_real_stripe_active,
)
from src.infrastructure.billing.repository import SqlEntitlementRepository
from src.middleware.auth import CurrentUserDep

router = APIRouter(prefix="/v1/billing", tags=["billing"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _service(db: AsyncSession) -> BillingService:
    return build_billing_service(db)


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


_VALID_WEBHOOK_PROVIDERS: frozenset[str] = frozenset(
    {"stripe", "payme", "click", "apple_iap", "google_iap"}
)


@router.post("/webhooks/{provider}", response_model=WebhookResult)
async def receive_webhook(
    provider: str,
    request: Request,
    db: SessionDep,
) -> WebhookResult:
    """Provider webhook ingress with per-provider signature verification.

    Verification paths (selected by ``provider`` path-param):

    * **stripe** — ``Stripe-Signature`` header verified via SDK.
    * **payme**  — ``Authorization: Basic <base64(merchant_id:secret)>``.
    * **click**  — form-encoded body, MD5 sign-string over fixed field list.
    * **paypal** — five ``PayPal-*`` headers + SDK ``verify-webhook-signature``.
    * **shared-secret fallback** — dev / staging / non-configured providers
      keep the ``X-Silklens-Webhook-Secret`` HMAC-compare gate.

    Idempotency is enforced by ``payment_webhook_events.UNIQUE(provider,
    provider_event_id)``; replays return ``{"duplicate": true}``.
    """
    import hmac as _hmac
    import json
    from decimal import Decimal as _Decimal

    from src.core.settings import get_settings
    from src.domain.billing.errors import InvalidWebhookSignature

    settings = get_settings()

    # Provider allow-list — any other value would let an attacker create
    # rows for synthetic providers we'll never reconcile against.
    if provider not in _VALID_WEBHOOK_PROVIDERS:
        raise HTTPException(
            status_code=404,
            detail={"code": "billing.webhook_unknown_provider", "message": "unknown provider"},
        )

    body_bytes = await request.body()
    stripe_event: dict[str, Any] | None = None
    payme_event: Any | None = None
    click_event: Any | None = None
    paypal_event: Any | None = None
    verified = False

    # --- 1. Stripe signature verification path ---
    if provider == "stripe" and is_real_stripe_active(settings):
        stripe_provider = build_stripe_provider_from_settings(settings)
        sig_header = request.headers.get("Stripe-Signature", "")
        if stripe_provider is not None and sig_header:
            try:
                stripe_event = stripe_provider.verify_webhook(
                    payload=body_bytes, signature=sig_header
                )
                verified = True
            except InvalidWebhookSignature as exc:
                raise HTTPException(
                    status_code=401,
                    detail={
                        "code": "billing.webhook_invalid_signature",
                        "message": "stripe-signature verification failed",
                    },
                ) from exc

    # --- 2. Payme JSON-RPC + Basic-auth verification path ---
    if provider == "payme":
        payme_provider = build_payme_provider_from_settings(settings)
        if payme_provider is not None:
            try:
                body_json = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
            except Exception as exc:
                raise HTTPException(
                    status_code=400,
                    detail={"code": "billing.webhook_invalid_json", "message": str(exc)},
                ) from exc
            try:
                payme_event = payme_provider.verify_webhook(
                    headers=dict(request.headers), body=body_json
                )
                verified = True
            except InvalidWebhookSignature as exc:
                raise HTTPException(
                    status_code=401,
                    detail={
                        "code": "billing.webhook_invalid_signature",
                        "message": f"payme verification failed: {exc}",
                    },
                ) from exc

    # --- 3. Click form-encoded + MD5 sign-string verification path ---
    if provider == "click":
        click_provider = build_click_provider_from_settings(settings)
        if click_provider is not None:
            try:
                form = await request.form()
                form_data = {k: str(v) for k, v in form.items()}
            except Exception as exc:
                raise HTTPException(
                    status_code=400,
                    detail={"code": "billing.webhook_invalid_form", "message": str(exc)},
                ) from exc
            try:
                click_event = click_provider.verify_webhook(form_data)
                verified = True
            except InvalidWebhookSignature as exc:
                raise HTTPException(
                    status_code=401,
                    detail={
                        "code": "billing.webhook_invalid_signature",
                        "message": f"click verification failed: {exc}",
                    },
                ) from exc

    # --- 4. PayPal signed-webhook verification path ---
    if provider == "paypal":
        paypal_provider = build_paypal_provider_from_settings(settings)
        if paypal_provider is not None:
            try:
                body_json = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
            except Exception as exc:
                raise HTTPException(
                    status_code=400,
                    detail={"code": "billing.webhook_invalid_json", "message": str(exc)},
                ) from exc
            try:
                paypal_event = paypal_provider.verify_webhook(
                    headers=dict(request.headers), body=body_json
                )
                verified = True
            except InvalidWebhookSignature as exc:
                raise HTTPException(
                    status_code=401,
                    detail={
                        "code": "billing.webhook_invalid_signature",
                        "message": f"paypal verification failed: {exc}",
                    },
                ) from exc

    # --- 5. Shared-secret gate for the non-verified path. ---
    if not verified:
        presented = request.headers.get("X-Silklens-Webhook-Secret", "")
        expected = settings.webhook_shared_secret.get_secret_value()
        if not expected or not _hmac.compare_digest(presented, expected):
            raise HTTPException(
                status_code=401,
                detail={
                    "code": "billing.webhook_unauthorized",
                    "message": "shared secret missing or invalid",
                },
            )

    # --- 6. Normalise the payload for the persisted webhook row. ---
    payload: dict[str, Any]
    provider_event_id: str
    event_type: str
    if stripe_event is not None:
        payload = stripe_event
        provider_event_id = str(payload.get("id") or "")
        event_type = str(payload.get("type") or "unknown")
    elif payme_event is not None:
        payload = {"method": payme_event.method, "params": payme_event.params}
        provider_event_id = payme_event.provider_event_id
        event_type = payme_event.event_type
    elif click_event is not None:
        payload = dict(click_event.raw)
        provider_event_id = click_event.provider_event_id
        event_type = click_event.event_type
    elif paypal_event is not None:
        payload = dict(paypal_event.raw)
        provider_event_id = paypal_event.provider_event_id
        event_type = paypal_event.event_type
    else:
        try:
            payload = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail={"code": "billing.webhook_invalid_json", "message": str(exc)},
            ) from exc
        provider_event_id = str(
            payload.get("id")
            or request.headers.get("X-Provider-Event-Id")
            or payload.get("event_id")
            or f"evt_{request.headers.get('X-Request-Id', 'unknown')}"
        )
        event_type = str(payload.get("type") or payload.get("event") or "unknown")

    service = _service(db)
    try:
        stored = await service.record_webhook(
            provider=provider,
            provider_event_id=provider_event_id,
            event_type=event_type,
            payload=payload if isinstance(payload, dict) else {"raw": payload},
        )
    except BillingError as exc:
        _raise(exc)
        raise

    # --- 7. Route verified Stripe events to typed service handlers. ---
    if stored and stripe_event is not None:
        await _dispatch_stripe_event(service, event_type, stripe_event, _Decimal)

    return WebhookResult(received=True, duplicate=not stored)


async def _dispatch_stripe_event(
    service: BillingService,
    event_type: str,
    event: dict[str, Any],
    decimal_cls: Any,
) -> None:
    """Route a verified Stripe event to the right ``BillingService`` handler.

    Errors here are swallowed-then-logged on purpose: the webhook row is
    already persisted, so a later reconciliation job can retry.
    """
    from src.core.logging import get_logger

    log = get_logger("silklens.billing.webhook.stripe")
    data_obj = (event.get("data") or {}).get("object") or {}
    try:
        if event_type == "payment_intent.succeeded":
            amount_minor = int(data_obj.get("amount_received") or data_obj.get("amount") or 0)
            currency = str(data_obj.get("currency") or "usd").upper()
            metadata = data_obj.get("metadata") or {}
            charge_id = str(data_obj.get("id") or "")
            await service.handle_payment_succeeded(
                provider="stripe",
                provider_charge_id=charge_id,
                amount=decimal_cls(amount_minor) / decimal_cls(100),
                currency=currency,
                metadata=dict(metadata),
            )
        elif event_type == "payment_intent.payment_failed":
            last_error = data_obj.get("last_payment_error") or {}
            failure_code = str(last_error.get("code") or "payment_failed")
            metadata = data_obj.get("metadata") or {}
            await service.mark_payment_failed(
                provider_charge_id=str(data_obj.get("id") or ""),
                failure_code=failure_code,
                metadata=dict(metadata),
            )
        elif event_type == "customer.subscription.deleted":
            await service.mark_subscription_canceled_external(
                provider_subscription_id=str(data_obj.get("id") or ""),
            )
        elif event_type in {"invoice.payment_succeeded", "invoice.payment_failed"}:
            await service.handle_invoice_event(
                provider_invoice_id=str(data_obj.get("id") or ""),
                succeeded=event_type == "invoice.payment_succeeded",
            )
    except Exception as exc:  # webhook stays idempotent on retry
        log.warning(
            "billing.webhook.stripe.dispatch_failed",
            event_type=event_type,
            error=str(exc),
        )
