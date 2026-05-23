"""Reseller / white-label API endpoints.

Routes:

  POST   /v1/reseller/applications                   — public, rate-limited
  GET    /v1/reseller/applications/{id}              — redacted to applicant,
                                                       full to admins.
  GET    /v1/admin/reseller/applications             — admin list
  POST   /v1/admin/reseller/applications/{id}/approve
  POST   /v1/admin/reseller/applications/{id}/reject
  GET    /v1/admin/tenants/{slug}/revenue-share      — list rows for a child
  PUT    /v1/admin/tenants/{slug}/revenue-share      — upsert (parent/child)
  GET    /v1/me/tenant                               — caller's tenant chain

Admin endpoints are permission-gated; the public submission is anonymous +
rate-limited (3/min/IP via :func:`src.middleware.ratelimit.rate_limit`).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.domain.reseller.entities import (
    ApplicationStatus,
    PlanKind,
    ResellerApplication,
    ResellerApplicationDraft,
)
from src.domain.reseller.errors import ResellerError
from src.domain.reseller.service import ResellerService
from src.infrastructure.reseller.repository import SqlResellerRepository
from src.middleware.auth import AuthContext, current_user, require_permission, require_user
from src.middleware.ratelimit import rate_limit

router = APIRouter(tags=["reseller"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


# --- Schemas ----------------------------------------------------------------


class ResellerApplicationRequest(BaseModel):
    applicant_email: EmailStr
    applicant_name: str = Field(min_length=2, max_length=200)
    company_name: str = Field(min_length=2, max_length=200)
    plan_kind: PlanKind
    expected_users: int = Field(default=0, ge=0, le=1_000_000)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    tax_id: str | None = Field(default=None, max_length=64)
    message: str | None = Field(default=None, max_length=4000)


class ResellerApplicationPublicOut(BaseModel):
    """Redacted view returned to the applicant (no notes, no reviewer)."""

    id: UUID
    status: ApplicationStatus
    plan_kind: PlanKind
    company_name: str
    submitted_at: datetime
    reviewed_at: datetime | None = None


class ResellerApplicationAdminOut(BaseModel):
    id: UUID
    applicant_email: str
    applicant_name: str
    company_name: str
    plan_kind: PlanKind
    status: ApplicationStatus
    expected_users: int
    country_code: str | None
    tax_id: str | None
    message: str | None
    submitted_at: datetime
    reviewed_at: datetime | None
    reviewed_by: UUID | None
    notes: str | None
    tenant_id_assigned: UUID | None


class ResellerApplicationPage(BaseModel):
    items: list[ResellerApplicationAdminOut]
    total: int
    limit: int
    offset: int


class ApproveRequest(BaseModel):
    plan_kind: PlanKind
    initial_revenue_share_pct: Decimal = Field(ge=0, le=100)
    notes: str | None = Field(default=None, max_length=1024)


class ApproveResponse(BaseModel):
    application: ResellerApplicationAdminOut
    child_tenant_id: UUID
    initial_revenue_share_pct: Decimal


class RejectRequest(BaseModel):
    reason: str = Field(min_length=2, max_length=1024)


class RevenueShareOut(BaseModel):
    parent_tenant_id: UUID
    child_tenant_id: UUID
    percentage: Decimal
    effective_from: datetime
    effective_until: datetime | None
    notes: str | None


class RevenueSharePage(BaseModel):
    items: list[RevenueShareOut]


class ConfigureRevenueShareRequest(BaseModel):
    parent_tenant_slug: str = Field(min_length=2, max_length=64)
    percentage: Decimal = Field(ge=0, le=100)
    notes: str | None = Field(default=None, max_length=1024)


class TenantChainOut(BaseModel):
    tenant_id: UUID
    slug: str
    display_name: dict[str, str]
    plan_tier: str
    status: str
    parent_chain: list[UUID]


# --- Helpers ----------------------------------------------------------------


def _service(db: AsyncSession) -> ResellerService:
    return ResellerService(repository=SqlResellerRepository(db))


def _admin_out(application: ResellerApplication) -> ResellerApplicationAdminOut:
    return ResellerApplicationAdminOut(
        id=application.id,
        applicant_email=application.applicant_email,
        applicant_name=application.applicant_name,
        company_name=application.company_name,
        plan_kind=application.plan_kind,
        status=application.status,
        expected_users=application.expected_users,
        country_code=application.country_code,
        tax_id=application.tax_id,
        message=application.message,
        submitted_at=application.submitted_at,
        reviewed_at=application.reviewed_at,
        reviewed_by=application.reviewed_by,
        notes=application.notes,
        tenant_id_assigned=application.tenant_id_assigned,
    )


def _public_out(application: ResellerApplication) -> ResellerApplicationPublicOut:
    return ResellerApplicationPublicOut(
        id=application.id,
        status=application.status,
        plan_kind=application.plan_kind,
        company_name=application.company_name,
        submitted_at=application.submitted_at,
        reviewed_at=application.reviewed_at,
    )


def _raise_reseller_error(exc: ResellerError) -> None:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": str(exc)},
    ) from exc


async def _is_admin(db: AsyncSession, ctx: AuthContext) -> bool:
    """Cheap permission check used to decide redaction on the public GET."""
    granted = (
        await db.execute(
            text(
                """
                SELECT app.has_permission(:uid, :residency, :perm, :tenant)
                """
            ),
            {
                "uid": ctx.user_id,
                "residency": ctx.residency_region.value,
                "perm": "reseller:read",
                "tenant": ctx.tenant_id,
            },
        )
    ).scalar_one()
    return bool(granted)


# --- Public submission ------------------------------------------------------


@router.post(
    "/v1/reseller/applications",
    response_model=ResellerApplicationPublicOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(rate_limit("3/minute", per="ip", scope="reseller:submit")),
    ],
)
async def submit_application(
    payload: ResellerApplicationRequest,
    db: SessionDep,
) -> ResellerApplicationPublicOut:
    draft = ResellerApplicationDraft(
        applicant_email=str(payload.applicant_email),
        applicant_name=payload.applicant_name,
        company_name=payload.company_name,
        plan_kind=payload.plan_kind,
        expected_users=payload.expected_users,
        country_code=payload.country_code,
        tax_id=payload.tax_id,
        message=payload.message,
    )
    try:
        application = await _service(db).submit_application(draft)
    except ResellerError as exc:
        _raise_reseller_error(exc)
    return _public_out(application)


@router.get("/v1/reseller/applications/{application_id}")
async def get_application(
    application_id: UUID,
    db: SessionDep,
    ctx: Annotated[AuthContext | None, Depends(current_user)],
) -> dict[str, Any]:
    try:
        application = await _service(db).get_application(application_id)
    except ResellerError as exc:
        _raise_reseller_error(exc)
    if ctx is not None and await _is_admin(db, ctx):
        return _admin_out(application).model_dump(mode="json")
    return _public_out(application).model_dump(mode="json")


# --- Admin: applications ----------------------------------------------------


@router.get(
    "/v1/admin/reseller/applications",
    response_model=ResellerApplicationPage,
    dependencies=[Depends(require_permission("reseller:read"))],
)
async def admin_list_applications(
    db: SessionDep,
    status_filter: Annotated[
        ApplicationStatus | None,
        Query(alias="status"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=10_000_000)] = 0,
) -> ResellerApplicationPage:
    items, total = await _service(db).list_applications(
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )
    return ResellerApplicationPage(
        items=[_admin_out(a) for a in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/v1/admin/reseller/applications/{application_id}/approve",
    response_model=ApproveResponse,
)
async def admin_approve_application(
    application_id: UUID,
    payload: ApproveRequest,
    db: SessionDep,
    ctx: Annotated[AuthContext, Depends(require_permission("reseller:approve"))],
) -> ApproveResponse:
    try:
        application, share = await _service(db).approve_application(
            application_id=application_id,
            plan_kind=payload.plan_kind,
            admin_user=ctx.user_id,
            admin_tenant_id=ctx.tenant_id,
            initial_revenue_share_pct=payload.initial_revenue_share_pct,
            notes=payload.notes,
        )
    except ResellerError as exc:
        _raise_reseller_error(exc)
    assert application.tenant_id_assigned is not None
    return ApproveResponse(
        application=_admin_out(application),
        child_tenant_id=application.tenant_id_assigned,
        initial_revenue_share_pct=share.percentage,
    )


@router.post(
    "/v1/admin/reseller/applications/{application_id}/reject",
    response_model=ResellerApplicationAdminOut,
)
async def admin_reject_application(
    application_id: UUID,
    payload: RejectRequest,
    db: SessionDep,
    ctx: Annotated[AuthContext, Depends(require_permission("reseller:approve"))],
) -> ResellerApplicationAdminOut:
    try:
        application = await _service(db).reject_application(
            application_id=application_id,
            admin_user=ctx.user_id,
            reason=payload.reason,
        )
    except ResellerError as exc:
        _raise_reseller_error(exc)
    return _admin_out(application)


# --- Admin: revenue share ---------------------------------------------------


@router.get(
    "/v1/admin/tenants/{slug}/revenue-share",
    response_model=RevenueSharePage,
    dependencies=[Depends(require_permission("reseller:configure_revenue_share"))],
)
async def admin_list_revenue_share(
    slug: str,
    db: SessionDep,
) -> RevenueSharePage:
    try:
        items = await _service(db).list_revenue_shares_for_child_slug(slug)
    except ResellerError as exc:
        _raise_reseller_error(exc)
    return RevenueSharePage(
        items=[
            RevenueShareOut(
                parent_tenant_id=s.parent_tenant_id,
                child_tenant_id=s.child_tenant_id,
                percentage=s.percentage,
                effective_from=s.effective_from,
                effective_until=s.effective_until,
                notes=s.notes,
            )
            for s in items
        ],
    )


@router.put(
    "/v1/admin/tenants/{slug}/revenue-share",
    response_model=RevenueShareOut,
)
async def admin_put_revenue_share(
    slug: str,
    payload: ConfigureRevenueShareRequest,
    db: SessionDep,
    ctx: Annotated[
        AuthContext,
        Depends(require_permission("reseller:configure_revenue_share")),
    ],
) -> RevenueShareOut:
    _ = ctx  # ctx required for permission gate; not used in body
    try:
        share = await _service(db).configure_revenue_share(
            parent_tenant_slug=payload.parent_tenant_slug,
            child_tenant_slug=slug,
            percentage=payload.percentage,
            notes=payload.notes,
        )
    except ResellerError as exc:
        _raise_reseller_error(exc)
    return RevenueShareOut(
        parent_tenant_id=share.parent_tenant_id,
        child_tenant_id=share.child_tenant_id,
        percentage=share.percentage,
        effective_from=share.effective_from,
        effective_until=share.effective_until,
        notes=share.notes,
    )


# --- Self-service: caller's tenant chain ------------------------------------


@router.get(
    "/v1/me/tenant",
    response_model=TenantChainOut,
)
async def get_my_tenant_chain(
    db: SessionDep,
    ctx: Annotated[AuthContext, Depends(require_user)],
) -> TenantChainOut:
    """Return the caller's tenant + parent chain for reseller-aware UI.

    The endpoint reads the caller's *own* tenant from the bearer claims, so
    ``require_user`` is enough — no extra permission is needed.
    """
    try:
        chain = await _service(db).get_tenant_chain(ctx.tenant_id)
    except ResellerError as exc:
        _raise_reseller_error(exc)
    return TenantChainOut(
        tenant_id=chain.tenant_id,
        slug=chain.slug,
        display_name=chain.display_name,
        plan_tier=chain.plan_tier,
        status=chain.status,
        parent_chain=list(chain.parent_chain),
    )
