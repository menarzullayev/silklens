"""Fundraising / investor data-room API endpoints.

Public routes (no auth required):
  GET /v1/investors/traction          — curated traction metrics
  GET /v1/investors/data-room         — public_teaser documents only

Admin routes (tenant:manage permission required):
  GET    /v1/admin/fundraising/investors
  POST   /v1/admin/fundraising/investors
  PATCH  /v1/admin/fundraising/investors/{id}/status
  GET    /v1/admin/fundraising/rounds
  POST   /v1/admin/fundraising/rounds
  POST   /v1/admin/fundraising/documents/{id}/grant
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.domain.fundraising.entities import (
    InvestorKind,
    InvestorStatus,
    RoundKind,
)
from src.domain.fundraising.errors import (
    DocumentNotFound,
    InvestorNotFound,
)
from src.domain.fundraising.service import FundraisingService
from src.infrastructure.fundraising.repository import SqlFundraisingRepository
from src.middleware.auth import AuthContext, require_permission, require_user

router = APIRouter(tags=["fundraising"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

DEFAULT_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")


def _svc(session: AsyncSession, tenant_id: UUID = DEFAULT_TENANT_ID) -> FundraisingService:
    repo = SqlFundraisingRepository(session)
    return FundraisingService(repo, tenant_id)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class TractionOut(BaseModel):
    mau: int
    dau: int
    paying_users: int
    mrr_usd: str
    arr_usd: str
    heritage_count: int
    countries_count: int
    nps_score: float | None
    mom_mau_growth_pct: float | None
    yoy_growth_est_pct: float | None
    snapshot_date: str | None


class DataRoomDocumentOut(BaseModel):
    id: UUID
    name: str
    description_md: str | None
    category: str
    version: str
    doc_url: str
    access_level: str
    uploaded_at: datetime


class InvestorOut(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    firm_name: str
    kind: str
    region: str
    status: str
    thesis_md: str | None
    min_check_size_usd: Decimal | None
    max_check_size_usd: Decimal | None
    contacted_at: datetime | None
    nda_signed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CreateInvestorRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    firm_name: str = Field(min_length=1, max_length=200)
    kind: InvestorKind
    region: str = Field(default="global", max_length=100)
    thesis_md: str | None = None
    min_check_size_usd: Decimal | None = None
    max_check_size_usd: Decimal | None = None


class UpdateStatusRequest(BaseModel):
    status: InvestorStatus


class RoundOut(BaseModel):
    id: UUID
    tenant_id: UUID
    round_name: str
    target_raise_usd: Decimal
    valuation_cap_usd: Decimal | None
    discount_pct: Decimal | None
    round_kind: str
    status: str
    raised_usd: Decimal
    fill_pct: float
    remaining_usd: Decimal
    opened_at: datetime | None
    closed_at: datetime | None
    created_at: datetime


class CreateRoundRequest(BaseModel):
    round_name: str = Field(min_length=1, max_length=100)
    target_raise_usd: Decimal = Field(gt=0)
    round_kind: RoundKind = RoundKind.SAFE
    valuation_cap_usd: Decimal | None = None
    discount_pct: Decimal | None = Field(default=None, ge=0, le=100)


class GrantAccessRequest(BaseModel):
    investor_id: UUID
    days: int | None = Field(default=None, gt=0, le=3650)


class AccessGrantOut(BaseModel):
    investor_id: UUID
    document_id: UUID
    granted_by: UUID
    granted_at: datetime
    expires_at: datetime | None
    is_active: bool


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------


@router.get("/v1/investors/traction", response_model=TractionOut)
async def public_traction(session: SessionDep) -> Any:
    """Curated traction metrics for the public investor page."""
    svc = _svc(session)
    return await svc.get_traction_summary()


@router.get("/v1/investors/data-room", response_model=list[DataRoomDocumentOut])
async def public_data_room(session: SessionDep) -> Any:
    """Return only public_teaser documents — no auth required."""
    svc = _svc(session)
    docs = await svc.list_documents(access_level="public_teaser")
    return [
        DataRoomDocumentOut(
            id=d.id,
            name=d.name,
            description_md=d.description_md,
            category=d.category.value,
            version=d.version,
            doc_url=d.doc_url,
            access_level=d.access_level.value,
            uploaded_at=d.uploaded_at,
        )
        for d in docs
    ]


# ---------------------------------------------------------------------------
# Admin — investors
# ---------------------------------------------------------------------------


@router.get(
    "/v1/admin/fundraising/investors",
    response_model=list[InvestorOut],
    dependencies=[Depends(require_permission("tenant:manage"))],
)
async def admin_list_investors(
    session: SessionDep,
    auth: Annotated[AuthContext, Depends(require_user)],
    status_filter: str | None = Query(default=None, alias="status"),
) -> Any:
    svc = _svc(session, auth.tenant_id)
    status_enum = InvestorStatus(status_filter) if status_filter else None
    investors = await svc.list_investors(status=status_enum)
    return [
        InvestorOut(
            id=i.id,
            tenant_id=i.tenant_id,
            name=i.name,
            firm_name=i.firm_name,
            kind=i.kind.value,
            region=i.region,
            status=i.status.value,
            thesis_md=i.thesis_md,
            min_check_size_usd=i.min_check_size_usd,
            max_check_size_usd=i.max_check_size_usd,
            contacted_at=i.contacted_at,
            nda_signed_at=i.nda_signed_at,
            created_at=i.created_at,
            updated_at=i.updated_at,
        )
        for i in investors
    ]


@router.post(
    "/v1/admin/fundraising/investors",
    response_model=InvestorOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("tenant:manage"))],
)
async def admin_create_investor(
    body: CreateInvestorRequest,
    session: SessionDep,
    auth: Annotated[AuthContext, Depends(require_user)],
) -> Any:
    svc = _svc(session, auth.tenant_id)
    investor = await svc.create_investor(
        name=body.name,
        firm_name=body.firm_name,
        kind=body.kind.value,
        actor=auth.user_id,
        region=body.region,
        thesis_md=body.thesis_md,
        min_check_size_usd=body.min_check_size_usd,
        max_check_size_usd=body.max_check_size_usd,
    )
    await session.commit()
    return InvestorOut(
        id=investor.id,
        tenant_id=investor.tenant_id,
        name=investor.name,
        firm_name=investor.firm_name,
        kind=investor.kind.value,
        region=investor.region,
        status=investor.status.value,
        thesis_md=investor.thesis_md,
        min_check_size_usd=investor.min_check_size_usd,
        max_check_size_usd=investor.max_check_size_usd,
        contacted_at=investor.contacted_at,
        nda_signed_at=investor.nda_signed_at,
        created_at=investor.created_at,
        updated_at=investor.updated_at,
    )


@router.patch(
    "/v1/admin/fundraising/investors/{investor_id}/status",
    response_model=InvestorOut,
    dependencies=[Depends(require_permission("tenant:manage"))],
)
async def admin_update_investor_status(
    investor_id: UUID,
    body: UpdateStatusRequest,
    session: SessionDep,
    auth: Annotated[AuthContext, Depends(require_user)],
) -> Any:
    svc = _svc(session, auth.tenant_id)
    try:
        investor = await svc.update_investor_status(investor_id, body.status.value, auth.user_id)
    except InvestorNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await session.commit()
    return InvestorOut(
        id=investor.id,
        tenant_id=investor.tenant_id,
        name=investor.name,
        firm_name=investor.firm_name,
        kind=investor.kind.value,
        region=investor.region,
        status=investor.status.value,
        thesis_md=investor.thesis_md,
        min_check_size_usd=investor.min_check_size_usd,
        max_check_size_usd=investor.max_check_size_usd,
        contacted_at=investor.contacted_at,
        nda_signed_at=investor.nda_signed_at,
        created_at=investor.created_at,
        updated_at=investor.updated_at,
    )


# ---------------------------------------------------------------------------
# Admin — rounds
# ---------------------------------------------------------------------------


@router.get(
    "/v1/admin/fundraising/rounds",
    response_model=list[RoundOut],
    dependencies=[Depends(require_permission("tenant:manage"))],
)
async def admin_list_rounds(
    session: SessionDep,
    auth: Annotated[AuthContext, Depends(require_user)],
) -> Any:
    svc = _svc(session, auth.tenant_id)
    rounds = await svc.list_rounds()
    return [
        RoundOut(
            id=r.id,
            tenant_id=r.tenant_id,
            round_name=r.round_name,
            target_raise_usd=r.target_raise_usd,
            valuation_cap_usd=r.valuation_cap_usd,
            discount_pct=r.discount_pct,
            round_kind=r.round_kind.value,
            status=r.status.value,
            raised_usd=r.raised_usd,
            fill_pct=r.fill_pct,
            remaining_usd=r.remaining_usd,
            opened_at=r.opened_at,
            closed_at=r.closed_at,
            created_at=r.created_at,
        )
        for r in rounds
    ]


@router.post(
    "/v1/admin/fundraising/rounds",
    response_model=RoundOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("tenant:manage"))],
)
async def admin_create_round(
    body: CreateRoundRequest,
    session: SessionDep,
    auth: Annotated[AuthContext, Depends(require_user)],
) -> Any:
    svc = _svc(session, auth.tenant_id)
    r = await svc.create_round(
        round_name=body.round_name,
        target_raise_usd=body.target_raise_usd,
        round_kind=body.round_kind.value,
        valuation_cap_usd=body.valuation_cap_usd,
        discount_pct=body.discount_pct,
    )
    await session.commit()
    return RoundOut(
        id=r.id,
        tenant_id=r.tenant_id,
        round_name=r.round_name,
        target_raise_usd=r.target_raise_usd,
        valuation_cap_usd=r.valuation_cap_usd,
        discount_pct=r.discount_pct,
        round_kind=r.round_kind.value,
        status=r.status.value,
        raised_usd=r.raised_usd,
        fill_pct=r.fill_pct,
        remaining_usd=r.remaining_usd,
        opened_at=r.opened_at,
        closed_at=r.closed_at,
        created_at=r.created_at,
    )


# ---------------------------------------------------------------------------
# Admin — data-room access grants
# ---------------------------------------------------------------------------


@router.post(
    "/v1/admin/fundraising/documents/{document_id}/grant",
    response_model=AccessGrantOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("tenant:manage"))],
)
async def admin_grant_doc_access(
    document_id: UUID,
    body: GrantAccessRequest,
    session: SessionDep,
    auth: Annotated[AuthContext, Depends(require_user)],
) -> Any:
    svc = _svc(session, auth.tenant_id)
    try:
        grant = await svc.grant_access(
            investor_id=body.investor_id,
            document_id=document_id,
            actor=auth.user_id,
            days=body.days,
        )
    except (InvestorNotFound, DocumentNotFound) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await session.commit()
    return AccessGrantOut(
        investor_id=grant.investor_id,
        document_id=grant.document_id,
        granted_by=grant.granted_by,
        granted_at=grant.granted_at,
        expires_at=grant.expires_at,
        is_active=grant.is_active,
    )
