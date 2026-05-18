"""Heritage CRUD endpoints.

GET  /v1/heritage              — list + filter + paginate (public)
GET  /v1/heritage/{pub_id}     — fetch one (public)
POST /v1/heritage              — create (requires heritage:create permission)

Update / delete land in a follow-up migration with their own RBAC scopes.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.domain.heritage.entities import (
    HeritageDraft,
    HeritageFilters,
    HeritageObject,
    HeritageStatus,
)
from src.domain.heritage.errors import HeritageError
from src.domain.heritage.service import HeritageService
from src.infrastructure.heritage.repository import SqlHeritageRepository
from src.middleware.auth import require_permission

router = APIRouter(prefix="/v1/heritage", tags=["heritage"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


# --- Schemas -----------------------------------------------------------------


class HeritageOut(BaseModel):
    id: UUID
    pub_id: str
    kind_slug: str
    name: dict[str, str]
    summary_md: dict[str, str]
    description_md: dict[str, str]
    tags: list[str]
    status: HeritageStatus
    country_code: str | None
    admin_path: str | None
    latitude: Decimal | None
    longitude: Decimal | None
    period_start_year: int | None
    period_end_year: int | None
    unesco_inscription_year: int | None
    hero_media_id: UUID | None
    confidence_score: int
    revision: int


class HeritagePageOut(BaseModel):
    items: list[HeritageOut]
    total: int
    limit: int
    offset: int


class HeritageCreate(BaseModel):
    kind_slug: str = Field(min_length=2, max_length=64)
    name: dict[str, str] = Field(min_length=1)
    summary_md: dict[str, str] = Field(default_factory=dict)
    description_md: dict[str, str] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list, max_length=64)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)
    period_start_year: int | None = Field(default=None, ge=-10000, le=2200)
    period_end_year: int | None = Field(default=None, ge=-10000, le=2200)
    unesco_inscription_year: int | None = Field(default=None, ge=1972, le=2200)
    status: HeritageStatus = HeritageStatus.DRAFT

    @field_validator("country_code")
    @classmethod
    def _upper_country(cls, v: str | None) -> str | None:
        return v.upper() if v else v


def _to_out(entity: HeritageObject) -> HeritageOut:
    return HeritageOut(
        id=entity.id,
        pub_id=entity.pub_id,
        kind_slug=entity.kind_slug,
        name=entity.name,
        summary_md=entity.summary_md,
        description_md=entity.description_md,
        tags=list(entity.tags),
        status=entity.status,
        country_code=entity.country_code,
        admin_path=entity.admin_path,
        latitude=entity.latitude,
        longitude=entity.longitude,
        period_start_year=entity.period_start_year,
        period_end_year=entity.period_end_year,
        unesco_inscription_year=entity.unesco_inscription_year,
        hero_media_id=entity.hero_media_id,
        confidence_score=entity.confidence_score,
        revision=entity.revision,
    )


def _service(db: AsyncSession) -> HeritageService:
    return HeritageService(repository=SqlHeritageRepository(db))


# --- Routes ------------------------------------------------------------------


KindQ = Annotated[str | None, Query(description="Filter by kind slug")]
CountryQ = Annotated[str | None, Query(min_length=2, max_length=2)]
StatusQ = Annotated[HeritageStatus | None, Query(alias="status")]
SearchQ = Annotated[str | None, Query(max_length=128)]
LimitQ = Annotated[int, Query(ge=1, le=100)]
OffsetQ = Annotated[int, Query(ge=0)]


@router.get("", response_model=HeritagePageOut)
async def list_heritage(
    db: SessionDep,
    kind: KindQ = None,
    country: CountryQ = None,
    status_filter: StatusQ = None,
    search: SearchQ = None,
    limit: LimitQ = 20,
    offset: OffsetQ = 0,
) -> HeritagePageOut:
    service = _service(db)
    page = await service.list(
        HeritageFilters(
            kind_slug=kind,
            country_code=country,
            status=status_filter,
            search=search,
            limit=limit,
            offset=offset,
        )
    )
    return HeritagePageOut(
        items=[_to_out(i) for i in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/{pub_id}", response_model=HeritageOut)
async def get_heritage(pub_id: str, db: SessionDep) -> HeritageOut:
    try:
        entity = await _service(db).get(pub_id)
    except HeritageError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    return _to_out(entity)


@router.post(
    "",
    response_model=HeritageOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("heritage:create"))],
)
async def create_heritage(
    payload: HeritageCreate,
    db: SessionDep,
    ctx: Annotated[
        object,  # actually AuthContext, but typing is enforced by dependency above
        Depends(require_permission("heritage:create")),
    ],
) -> HeritageOut:
    draft = HeritageDraft(
        tenant_id=ctx.tenant_id,
        kind_slug=payload.kind_slug,
        name=payload.name,
        summary_md=payload.summary_md,
        description_md=payload.description_md,
        tags=tuple(payload.tags),
        country_code=payload.country_code,
        latitude=payload.latitude,
        longitude=payload.longitude,
        period_start_year=payload.period_start_year,
        period_end_year=payload.period_end_year,
        unesco_inscription_year=payload.unesco_inscription_year,
        status=payload.status,
    )
    try:
        entity = await _service(db).create(draft, created_by=ctx.user_id)
    except HeritageError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    return _to_out(entity)
