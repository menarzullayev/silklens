"""Partnership & SLA API endpoints.

Public routes:
  GET  /v1/partnerships              — active partner list (name, kind, badge)
  GET  /v1/partnerships/uptime       — current service uptime status

Admin routes (permission-gated):
  GET  /v1/admin/partnerships                         — reseller:read
  POST /v1/admin/partnerships                         — reseller:approve
  GET  /v1/admin/partnerships/{id}/sla-report         — reseller:read
  POST /v1/admin/partnerships/{id}/badges             — reseller:approve
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.domain.partnership.entities import (
    AgreementStatus,
    BadgeKind,
    PartnerKind,
    PartnershipAgreement,
)
from src.domain.partnership.errors import (
    AgreementNotFound,
    BadgeAlreadyIssued,
    InvalidMouUrl,
    TierNotFound,
)
from src.domain.partnership.service import AgreementDraft, PartnershipService
from src.middleware.auth import AuthContext, require_permission

router = APIRouter(tags=["partnerships"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


# ------------------------------------------------------------------ #
#  Pydantic schemas                                                   #
# ------------------------------------------------------------------ #


class PartnerOut(BaseModel):
    id: UUID
    partner_name: str
    partner_kind: str
    status: str
    tier_slug: str | None
    tier_name: dict[str, str] | None
    signed_at: datetime | None
    expires_at: datetime | None

    model_config = {"from_attributes": True}


class AgreementOut(BaseModel):
    id: UUID
    tenant_id: UUID
    partner_name: str
    partner_kind: str
    tier_id: UUID
    tier_slug: str | None
    tier_name: dict[str, str] | None
    tier_sla_uptime_pct: Decimal | None
    status: str
    signed_at: datetime | None
    expires_at: datetime | None
    auto_renew: bool
    annual_value_usd: Decimal | None
    contact_name: str | None
    contact_email: str | None
    contact_phone: str | None
    notes_md: str | None
    mou_url: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgreementCreate(BaseModel):
    partner_name: str = Field(min_length=2, max_length=256)
    partner_kind: PartnerKind
    tier_slug: str = Field(min_length=2, max_length=64)
    contact_name: str | None = Field(default=None, max_length=200)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, max_length=32)
    annual_value_usd: Decimal | None = Field(default=None, ge=0)
    notes_md: str | None = Field(default=None, max_length=20_000)
    mou_url: str | None = Field(default=None, max_length=512)
    auto_renew: bool = False
    expires_at: datetime | None = None

    @field_validator("mou_url")
    @classmethod
    def validate_mou_url(cls, v: str | None) -> str | None:
        if v is not None and not v.startswith("https://"):
            raise ValueError("mou_url must start with https://")
        return v


class SlaReportOut(BaseModel):
    id: UUID
    agreement_id: UUID
    period_start: date
    period_end: date
    measured_uptime_pct: Decimal
    incidents_count: int
    incidents_resolved_in_sla: int
    api_calls_total: int
    data_exports_count: int
    generated_at: datetime
    created_at: datetime
    report_url: str | None


class UptimeOut(BaseModel):
    uptime_pct: Decimal
    total_windows: int
    open_incidents: int
    last_incident_at: datetime | None
    service_status: str
    computed_at: datetime
    recent_windows: list[dict[str, Any]]


class BadgeCreate(BaseModel):
    badge_kind: BadgeKind


class BadgeOut(BaseModel):
    id: UUID
    agreement_id: UUID
    badge_kind: str
    issued_at: datetime
    expires_at: datetime | None
    is_active: bool
    display_on_heritage: list[str]


# ------------------------------------------------------------------ #
#  Helpers                                                            #
# ------------------------------------------------------------------ #


def _service(session: AsyncSession) -> PartnershipService:
    return PartnershipService(session)


def _agreement_out(a: PartnershipAgreement) -> AgreementOut:
    return AgreementOut(
        id=a.id,
        tenant_id=a.tenant_id,
        partner_name=a.partner_name,
        partner_kind=a.partner_kind.value,
        tier_id=a.tier_id,
        tier_slug=a.tier_slug,
        tier_name=a.tier_name,
        tier_sla_uptime_pct=a.tier_sla_uptime_pct,
        status=a.status.value,
        signed_at=a.signed_at,
        expires_at=a.expires_at,
        auto_renew=a.auto_renew,
        annual_value_usd=a.annual_value_usd,
        contact_name=a.contact_name,
        contact_email=a.contact_email,
        contact_phone=a.contact_phone,
        notes_md=a.notes_md,
        mou_url=a.mou_url,
        created_at=a.created_at,
        updated_at=a.updated_at,
    )


# ------------------------------------------------------------------ #
#  Public endpoints                                                   #
# ------------------------------------------------------------------ #


@router.get(
    "/v1/partnerships",
    response_model=list[PartnerOut],
    summary="List active partners (public)",
)
async def list_public_partners(session: SessionDep) -> list[PartnerOut]:
    """Returns all active partnership agreements suitable for public display."""
    svc = _service(session)
    agreements = await svc.list_public_partners()
    return [
        PartnerOut(
            id=a.id,
            partner_name=a.partner_name,
            partner_kind=a.partner_kind.value,
            status=a.status.value,
            tier_slug=a.tier_slug,
            tier_name=a.tier_name,
            signed_at=a.signed_at,
            expires_at=a.expires_at,
        )
        for a in agreements
    ]


@router.get(
    "/v1/partnerships/uptime",
    response_model=UptimeOut,
    summary="Current service uptime status (public)",
)
async def uptime_status(session: SessionDep) -> UptimeOut:
    """Returns aggregated uptime status for the last 30 days."""
    svc = _service(session)
    status_obj = await svc.current_uptime_status()
    return UptimeOut(
        uptime_pct=status_obj.uptime_pct,
        total_windows=status_obj.total_windows,
        open_incidents=status_obj.open_incidents,
        last_incident_at=status_obj.last_incident_at,
        service_status=status_obj.service_status,
        computed_at=status_obj.computed_at,
        recent_windows=status_obj.recent_windows,
    )


# ------------------------------------------------------------------ #
#  Admin endpoints                                                    #
# ------------------------------------------------------------------ #


@router.get(
    "/v1/admin/partnerships",
    response_model=list[AgreementOut],
    summary="List all partnership agreements (admin)",
)
async def admin_list_agreements(
    session: SessionDep,
    auth: Annotated[AuthContext, Depends(require_permission("reseller:read"))],
    status_filter: str | None = Query(default=None, alias="status"),
    kind_filter: str | None = Query(default=None, alias="kind"),
) -> list[AgreementOut]:
    svc = _service(session)
    status_enum = AgreementStatus(status_filter) if status_filter else None
    kind_enum = PartnerKind(kind_filter) if kind_filter else None
    agreements = await svc.list_agreements(status=status_enum, kind=kind_enum)
    return [_agreement_out(a) for a in agreements]


@router.post(
    "/v1/admin/partnerships",
    response_model=AgreementOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create partnership agreement (admin)",
)
async def admin_create_agreement(
    body: AgreementCreate,
    session: SessionDep,
    auth: Annotated[AuthContext, Depends(require_permission("reseller:approve"))],
) -> AgreementOut:
    svc = _service(session)
    draft = AgreementDraft(
        partner_name=body.partner_name,
        partner_kind=body.partner_kind,
        tier_slug=body.tier_slug,
        tenant_id=auth.tenant_id,
        contact_name=body.contact_name,
        contact_email=body.contact_email,
        contact_phone=body.contact_phone,
        annual_value_usd=body.annual_value_usd,
        notes_md=body.notes_md,
        mou_url=body.mou_url,
        auto_renew=body.auto_renew,
        expires_at=body.expires_at,
    )
    try:
        agreement = await svc.create_agreement(draft, actor=auth.user_id)
    except TierNotFound as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))  # noqa: B904
    except InvalidMouUrl as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))  # noqa: B904
    return _agreement_out(agreement)


@router.get(
    "/v1/admin/partnerships/{agreement_id}/sla-report",
    response_model=SlaReportOut,
    summary="Generate SLA report for an agreement (admin)",
)
async def admin_get_sla_report(
    agreement_id: UUID,
    session: SessionDep,
    auth: Annotated[AuthContext, Depends(require_permission("reseller:read"))],
    period_start: date = Query(..., description="Report period start date (YYYY-MM-DD)"),  # noqa: B008
    period_end: date = Query(..., description="Report period end date (YYYY-MM-DD)"),  # noqa: B008
) -> SlaReportOut:
    if period_end <= period_start:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="period_end must be after period_start",
        )
    svc = _service(session)
    try:
        report = await svc.generate_sla_report(agreement_id, period_start, period_end)
    except AgreementNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))  # noqa: B904
    return SlaReportOut(
        id=report.id,
        agreement_id=report.agreement_id,
        period_start=report.period_start,
        period_end=report.period_end,
        measured_uptime_pct=report.measured_uptime_pct,
        incidents_count=report.incidents_count,
        incidents_resolved_in_sla=report.incidents_resolved_in_sla,
        api_calls_total=report.api_calls_total,
        data_exports_count=report.data_exports_count,
        generated_at=report.generated_at,
        created_at=report.created_at,
        report_url=report.report_url,
    )


@router.post(
    "/v1/admin/partnerships/{agreement_id}/badges",
    response_model=BadgeOut,
    status_code=status.HTTP_201_CREATED,
    summary="Issue a partner badge (admin)",
)
async def admin_issue_badge(
    agreement_id: UUID,
    body: BadgeCreate,
    session: SessionDep,
    auth: Annotated[AuthContext, Depends(require_permission("reseller:approve"))],
) -> BadgeOut:
    svc = _service(session)
    try:
        badge = await svc.issue_badge(agreement_id, body.badge_kind, actor=auth.user_id)
    except AgreementNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))  # noqa: B904
    except BadgeAlreadyIssued as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))  # noqa: B904
    return BadgeOut(
        id=badge.id,
        agreement_id=badge.agreement_id,
        badge_kind=badge.badge_kind.value,
        issued_at=badge.issued_at,
        expires_at=badge.expires_at,
        is_active=badge.is_active,
        display_on_heritage=badge.display_on_heritage,
    )
