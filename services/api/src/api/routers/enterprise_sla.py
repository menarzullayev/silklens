"""Enterprise SLA API router — FAZA 7 Wave-8 Agent-7.

Public:
  GET  /v1/enterprise/tiers          — SLA tier catalogue + pricing
  GET  /v1/enterprise/status         — platform uptime + open incidents
  GET  /v1/enterprise/incidents      — public incidents (public_visible=true)

Enterprise account owner:
  GET  /v1/enterprise/me/subscription
  GET  /v1/enterprise/me/usage       ?month=YYYY-MM
  GET  /v1/enterprise/me/sla-report  ?month=YYYY-MM

Admin (system:settings):
  POST  /v1/admin/enterprise/incidents
  PATCH /v1/admin/enterprise/incidents/{id}/resolve
  GET   /v1/admin/enterprise/accounts/{id}/usage
"""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.domain.enterprise.entities import (
    EnterpriseSLAStatus,
    EnterpriseSLATier,
    EnterpriseSubscription,
    SLAIncident,
)
from src.domain.enterprise.errors import (
    IncidentAlreadyResolvedError,
    IncidentNotFoundError,
)
from src.domain.enterprise.service import EnterpriseService
from src.middleware.auth import AuthContext, CurrentUserDep, require_permission

router = APIRouter(tags=["enterprise-sla"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


# ---------------------------------------------------------------------------
# Output schemas
# ---------------------------------------------------------------------------


class SLATierOut(BaseModel):
    id: UUID
    slug: str
    name: dict[str, str]
    monthly_price_usd: Decimal | None
    uptime_commitment_pct: Decimal
    support_response_hours: int
    dedicated_csm: bool
    custom_domain: bool
    max_seats: int | None
    api_rate_limit_per_min: int
    analytics_retention_days: int
    includes_white_label: bool
    white_label_subdomains: int
    created_at: datetime

    @classmethod
    def from_entity(cls, e: EnterpriseSLATier) -> SLATierOut:
        return cls(
            id=e.id,
            slug=e.slug,
            name=e.name,
            monthly_price_usd=e.monthly_price_usd,
            uptime_commitment_pct=e.uptime_commitment_pct,
            support_response_hours=e.support_response_hours,
            dedicated_csm=e.dedicated_csm,
            custom_domain=e.custom_domain,
            max_seats=e.max_seats,
            api_rate_limit_per_min=e.api_rate_limit_per_min,
            analytics_retention_days=e.analytics_retention_days,
            includes_white_label=e.includes_white_label,
            white_label_subdomains=e.white_label_subdomains,
            created_at=e.created_at,
        )


class IncidentOut(BaseModel):
    id: UUID
    enterprise_account_id: UUID | None
    title: str
    severity: str
    affected_services: list[str]
    status: str
    started_at: datetime
    resolved_at: datetime | None
    root_cause: str | None
    remediation_md: str | None
    post_mortem_url: str | None
    public_visible: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, e: SLAIncident) -> IncidentOut:
        return cls(
            id=e.id,
            enterprise_account_id=e.enterprise_account_id,
            title=e.title,
            severity=e.severity,
            affected_services=e.affected_services,
            status=e.status,
            started_at=e.started_at,
            resolved_at=e.resolved_at,
            root_cause=e.root_cause,
            remediation_md=e.remediation_md,
            post_mortem_url=e.post_mortem_url,
            public_visible=e.public_visible,
            created_at=e.created_at,
            updated_at=e.updated_at,
        )


class SubscriptionOut(BaseModel):
    id: UUID
    enterprise_account_id: UUID
    sla_tier_id: UUID
    tier_slug: str | None
    tier_name: dict[str, str]
    status: str
    billing_period: str
    started_at: datetime
    current_period_end: datetime
    trial_ends_at: datetime | None
    mrr_usd: Decimal
    contracted_annual_usd: Decimal | None
    uptime_commitment_pct: Decimal | None
    created_at: datetime | None
    updated_at: datetime | None

    @classmethod
    def from_entity(cls, e: EnterpriseSubscription) -> SubscriptionOut:
        return cls(
            id=e.id,
            enterprise_account_id=e.enterprise_account_id,
            sla_tier_id=e.sla_tier_id,
            tier_slug=e.tier_slug,
            tier_name=e.tier_name,
            status=e.status,
            billing_period=e.billing_period,
            started_at=e.started_at,
            current_period_end=e.current_period_end,
            trial_ends_at=e.trial_ends_at,
            mrr_usd=e.mrr_usd,
            contracted_annual_usd=e.contracted_annual_usd,
            uptime_commitment_pct=e.uptime_commitment_pct,
            created_at=e.created_at,
            updated_at=e.updated_at,
        )


class SLAStatusOut(BaseModel):
    uptime_pct: Decimal
    committed_pct: Decimal
    open_incidents: list[IncidentOut]
    total_api_calls_this_period: int
    active_seats: int
    sla_met: bool
    credit_owed_usd: Decimal

    @classmethod
    def from_entity(cls, e: EnterpriseSLAStatus) -> SLAStatusOut:
        return cls(
            uptime_pct=e.uptime_pct,
            committed_pct=e.committed_pct,
            open_incidents=[IncidentOut.from_entity(i) for i in e.open_incidents],
            total_api_calls_this_period=e.total_api_calls_this_period,
            active_seats=e.active_seats,
            sla_met=e.sla_met,
            credit_owed_usd=e.credit_owed_usd,
        )


# ---------------------------------------------------------------------------
# Input schemas
# ---------------------------------------------------------------------------


class CreateIncidentIn(BaseModel):
    title: str = Field(min_length=3, max_length=256)
    severity: str = Field(pattern="^(p1|p2|p3|p4)$")
    affected_services: list[str] = Field(min_length=1)
    enterprise_account_id: UUID | None = None
    public_visible: bool = False


class ResolveIncidentIn(BaseModel):
    root_cause: str = Field(min_length=10, max_length=4096)
    remediation_md: str | None = None
    post_mortem_url: str | None = Field(default=None, max_length=512)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _svc(session: AsyncSession) -> EnterpriseService:
    return EnterpriseService(session)


def _validate_month(month: str) -> str:
    if not _MONTH_RE.match(month):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "enterprise.invalid_month", "message": "month must be YYYY-MM"},
        )
    return month


# ---------------------------------------------------------------------------
# PUBLIC endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/v1/enterprise/tiers",
    response_model=list[SLATierOut],
    summary="List SLA tiers and pricing",
)
async def list_tiers(session: SessionDep) -> list[SLATierOut]:
    """Public — returns all SLA tiers ordered by uptime commitment."""
    tiers = await _svc(session).list_tiers()
    return [SLATierOut.from_entity(t) for t in tiers]


@router.get(
    "/v1/enterprise/status",
    response_model=SLAStatusOut,
    summary="Platform-wide SLA status",
)
async def platform_status(session: SessionDep) -> SLAStatusOut:
    """Public — current platform uptime % and open incidents.

    Uses a synthetic zero-UUID account_id so the query returns platform-wide
    (enterprise_account_id IS NULL) incidents only.
    """

    # Public platform status: no account_id filtering — gather platform-wide incidents
    from sqlalchemy import text

    result = await session.execute(
        text(
            """
            SELECT id, enterprise_account_id, title, severity, affected_services,
                   status, started_at, resolved_at, root_cause, remediation_md,
                   post_mortem_url, public_visible, created_at, updated_at
            FROM sla_incident_reports
            WHERE public_visible = true AND status != 'resolved'
              AND enterprise_account_id IS NULL
            ORDER BY started_at DESC
            """
        )
    )
    from src.domain.enterprise.service import _row_to_incident

    open_incidents = [_row_to_incident(r) for r in result.fetchall()]

    # Platform uptime — no specific account, return a generic status
    return SLAStatusOut(
        uptime_pct=Decimal("100.00") if not open_incidents else Decimal("99.90"),
        committed_pct=Decimal("99.90"),
        open_incidents=[IncidentOut.from_entity(i) for i in open_incidents],
        total_api_calls_this_period=0,
        active_seats=0,
        sla_met=True,
        credit_owed_usd=Decimal("0"),
    )


@router.get(
    "/v1/enterprise/incidents",
    response_model=list[IncidentOut],
    summary="Public incident history",
)
async def list_public_incidents(
    session: SessionDep,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[IncidentOut]:
    """Public — returns incidents with public_visible=true only."""
    incidents = await _svc(session).list_incidents(public_only=True, limit=limit)
    return [IncidentOut.from_entity(i) for i in incidents]


# ---------------------------------------------------------------------------
# AUTHENTICATED — account owner
# ---------------------------------------------------------------------------


@router.get(
    "/v1/enterprise/me/subscription",
    response_model=SubscriptionOut,
    summary="My enterprise subscription",
)
async def my_subscription(
    session: SessionDep,
    auth: CurrentUserDep,
) -> SubscriptionOut:
    """Return the authenticated user's enterprise subscription."""
    # Resolve enterprise_account_id from the auth context tenant
    from sqlalchemy import text

    result = await session.execute(
        text("SELECT id FROM enterprise_accounts WHERE tenant_id = :tid LIMIT 1"),
        {"tid": auth.tenant_id},
    )
    account_row = result.fetchone()
    if not account_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "enterprise.no_account",
                "message": "no enterprise account for this tenant",
            },
        )

    sub = await _svc(session).my_subscription(account_row.id)
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "enterprise.no_subscription",
                "message": "no active subscription found",
            },
        )
    return SubscriptionOut.from_entity(sub)


@router.get(
    "/v1/enterprise/me/usage",
    summary="My usage snapshots for a month",
)
async def my_usage(
    session: SessionDep,
    auth: CurrentUserDep,
    month: str = Query(default=None, description="YYYY-MM (default: current month)"),
) -> dict[str, Any]:
    """Return daily usage snapshots for the authenticated tenant's enterprise account."""
    from datetime import date

    from sqlalchemy import text

    if month is None:
        today = date.today()
        month = f"{today.year}-{today.month:02d}"
    _validate_month(month)

    result = await session.execute(
        text("SELECT id FROM enterprise_accounts WHERE tenant_id = :tid LIMIT 1"),
        {"tid": auth.tenant_id},
    )
    account_row = result.fetchone()
    if not account_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "enterprise.no_account", "message": "no enterprise account"},
        )

    year, month_num = int(month.split("-")[0]), int(month.split("-")[1])
    import calendar

    days_in_month = calendar.monthrange(year, month_num)[1]
    month_start = date(year, month_num, 1)
    month_end = date(year, month_num, days_in_month)

    snap_result = await session.execute(
        text(
            """
            SELECT snapshot_date, api_calls, successful_calls, error_calls,
                   avg_latency_ms, p95_latency_ms, data_exported_mb, active_seats
            FROM enterprise_usage_snapshots
            WHERE enterprise_account_id = :account_id
              AND snapshot_date >= :month_start
              AND snapshot_date <= :month_end
            ORDER BY snapshot_date ASC
            """
        ),
        {
            "account_id": account_row.id,
            "month_start": month_start,
            "month_end": month_end,
        },
    )
    rows = snap_result.fetchall()
    return {
        "account_id": str(account_row.id),
        "month": month,
        "snapshots": [
            {
                "date": str(r.snapshot_date),
                "api_calls": r.api_calls,
                "successful_calls": r.successful_calls,
                "error_calls": r.error_calls,
                "avg_latency_ms": float(r.avg_latency_ms),
                "p95_latency_ms": float(r.p95_latency_ms),
                "data_exported_mb": float(r.data_exported_mb),
                "active_seats": r.active_seats,
            }
            for r in rows
        ],
    }


@router.get(
    "/v1/enterprise/me/sla-report",
    summary="SLA compliance report for a month",
)
async def my_sla_report(
    session: SessionDep,
    auth: CurrentUserDep,
    month: str = Query(default=None, description="YYYY-MM (default: current month)"),
) -> dict[str, Any]:
    """Return SLA compliance report: uptime vs commitment, credits owed."""
    from datetime import date

    from sqlalchemy import text

    if month is None:
        today = date.today()
        month = f"{today.year}-{today.month:02d}"
    _validate_month(month)

    result = await session.execute(
        text("SELECT id FROM enterprise_accounts WHERE tenant_id = :tid LIMIT 1"),
        {"tid": auth.tenant_id},
    )
    account_row = result.fetchone()
    if not account_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "enterprise.no_account", "message": "no enterprise account"},
        )

    return await _svc(session).generate_sla_compliance_report(account_row.id, month)


# ---------------------------------------------------------------------------
# ADMIN endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/v1/admin/enterprise/incidents",
    response_model=IncidentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create incident report (admin)",
)
async def admin_create_incident(
    body: CreateIncidentIn,
    session: SessionDep,
    auth: Annotated[AuthContext, Depends(require_permission("system:settings"))],
) -> IncidentOut:
    """Admin - create a new SLA incident (P1-P4)."""
    incident = await _svc(session).create_incident(
        title=body.title,
        severity=body.severity,
        services=body.affected_services,
        _actor=str(auth.user_id),
        account_id=body.enterprise_account_id,
        public_visible=body.public_visible,
    )
    return IncidentOut.from_entity(incident)


@router.patch(
    "/v1/admin/enterprise/incidents/{incident_id}/resolve",
    response_model=IncidentOut,
    summary="Resolve incident (admin)",
)
async def admin_resolve_incident(
    incident_id: UUID,
    body: ResolveIncidentIn,
    session: SessionDep,
    auth: Annotated[AuthContext, Depends(require_permission("system:settings"))],
) -> IncidentOut:
    """Admin — mark incident as resolved and record root cause."""
    try:
        incident = await _svc(session).resolve_incident(
            incident_id=incident_id,
            root_cause=body.root_cause,
            _actor=str(auth.user_id),
            remediation_md=body.remediation_md,
            post_mortem_url=body.post_mortem_url,
        )
    except IncidentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "enterprise.incident_not_found", "message": str(exc)},
        ) from exc
    except IncidentAlreadyResolvedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "enterprise.already_resolved", "message": str(exc)},
        ) from exc
    return IncidentOut.from_entity(incident)


@router.get(
    "/v1/admin/enterprise/accounts/{account_id}/usage",
    summary="Account usage snapshots (admin)",
)
async def admin_account_usage(
    account_id: UUID,
    session: SessionDep,
    auth: Annotated[AuthContext, Depends(require_permission("system:settings"))],
    month: str = Query(default=None, description="YYYY-MM"),
) -> dict[str, Any]:
    """Admin — view usage snapshots for any enterprise account."""
    import calendar
    from datetime import date

    from sqlalchemy import text

    if month is None:
        today = date.today()
        month = f"{today.year}-{today.month:02d}"
    _validate_month(month)

    year, month_num = int(month.split("-")[0]), int(month.split("-")[1])
    days_in_month = calendar.monthrange(year, month_num)[1]
    month_start = date(year, month_num, 1)
    month_end = date(year, month_num, days_in_month)

    result = await session.execute(
        text(
            """
            SELECT snapshot_date, api_calls, successful_calls, error_calls,
                   avg_latency_ms, p95_latency_ms, data_exported_mb, active_seats
            FROM enterprise_usage_snapshots
            WHERE enterprise_account_id = :account_id
              AND snapshot_date >= :month_start
              AND snapshot_date <= :month_end
            ORDER BY snapshot_date ASC
            """
        ),
        {
            "account_id": account_id,
            "month_start": month_start,
            "month_end": month_end,
        },
    )
    rows = result.fetchall()
    return {
        "account_id": str(account_id),
        "month": month,
        "snapshots": [
            {
                "date": str(r.snapshot_date),
                "api_calls": r.api_calls,
                "successful_calls": r.successful_calls,
                "error_calls": r.error_calls,
                "avg_latency_ms": float(r.avg_latency_ms),
                "p95_latency_ms": float(r.p95_latency_ms),
                "data_exported_mb": float(r.data_exported_mb),
                "active_seats": r.active_seats,
            }
            for r in rows
        ],
    }
