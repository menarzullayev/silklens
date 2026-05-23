"""Heritage CRUD endpoints.

GET    /v1/heritage                      — list + filter + paginate (public)
GET    /v1/heritage/{pub_id}              — fetch one (public)
POST   /v1/heritage                       — create (requires heritage:create)
PATCH  /v1/heritage/{pub_id}              — partial update (requires heritage:update)
DELETE /v1/heritage/{pub_id}              — soft delete (requires heritage:delete)
POST   /v1/heritage/{pub_id}/aliases      — add alias (requires heritage:update)
GET    /v1/heritage/{pub_id}/revisions    — list revisions (requires heritage:read)
POST   /v1/heritage/{pub_id}/transitions  — moderation state machine
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.domain.heritage.entities import (
    AliasKind,
    HeritageAliasDraft,
    HeritageDraft,
    HeritageFilters,
    HeritageObject,
    HeritageStatus,
    HeritageUpdate,
    StatusTransitionAction,
)
from src.domain.heritage.errors import HeritageError
from src.domain.heritage.service import HeritageService, required_permission
from src.infrastructure.heritage.repository import SqlHeritageRepository
from src.middleware.auth import AuthContext, require_permission, require_user

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


class HeritagePatch(BaseModel):
    """Partial-update payload. Every field is optional; we use
    ``model_fields_set`` to distinguish "not provided" from "explicit null"
    so the service can perform a true PATCH semantic on jsonb columns.
    """

    name: dict[str, str] | None = None
    summary_md: dict[str, str] | None = None
    description_md: dict[str, str] | None = None
    tags: list[str] | None = None
    country_code: str | None = Field(default=None, max_length=2)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)
    period_start_year: int | None = Field(default=None, ge=-10000, le=2200)
    period_end_year: int | None = Field(default=None, ge=-10000, le=2200)
    unesco_inscription_year: int | None = Field(default=None, ge=1972, le=2200)
    hero_media_id: UUID | None = None
    status: HeritageStatus | None = None

    @field_validator("country_code")
    @classmethod
    def _upper_country(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if len(v) != 2:
            raise ValueError("country_code must be 2 chars")
        return v.upper()

    @model_validator(mode="after")
    def _at_least_one_field(self) -> HeritagePatch:
        if not self.model_fields_set:
            raise ValueError("at least one field must be provided")
        return self


class HeritageAliasIn(BaseModel):
    alias: str = Field(min_length=1, max_length=512)
    language_tag: str = Field(min_length=2, max_length=32)
    kind: AliasKind = AliasKind.HISTORICAL
    confidence: int = Field(default=80, ge=0, le=100)
    script: str | None = Field(default=None, max_length=32)
    source: str | None = Field(default=None, max_length=256)


class HeritageAliasOut(BaseModel):
    id: UUID
    heritage_id: UUID
    alias: str
    language_tag: str
    kind: AliasKind
    confidence: int
    script: str | None
    source: str | None
    created_at: datetime | None


class RevisionOut(BaseModel):
    id: UUID
    revision: int
    action: str
    actor_user_id: UUID | None
    comment: str | None
    valid_from: datetime
    before: dict[str, Any] | None
    after: dict[str, Any]


class RevisionPageOut(BaseModel):
    items: list[RevisionOut]
    total: int
    limit: int
    offset: int


class TransitionIn(BaseModel):
    action: StatusTransitionAction
    comment: str | None = Field(default=None, max_length=1024)


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


def _raise_heritage_error(exc: HeritageError) -> None:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": str(exc)},
    ) from exc


# --- Routes ------------------------------------------------------------------


KindQ = Annotated[str | None, Query(description="Filter by kind slug")]
CountryQ = Annotated[str | None, Query(min_length=2, max_length=2)]
StatusQ = Annotated[HeritageStatus | None, Query(alias="status")]
SearchQ = Annotated[str | None, Query(max_length=128)]
LimitQ = Annotated[int, Query(ge=1, le=100)]
OffsetQ = Annotated[int, Query(ge=0, le=10_000_000)]


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
        _raise_heritage_error(exc)
    # Business metric: count detail views by country so the Grafana
    # `silklens-business` dashboard can pivot on geography. Use a literal
    # fallback when the heritage object has no country code yet.
    try:
        from src.core.metrics import business_heritage_views_total

        country = (getattr(entity, "country_code", None) or "unknown").lower()
        business_heritage_views_total.labels(country=country).inc()
    except Exception:  # noqa: S110
        # Observability — never break the actual response on a metric miss.
        pass
    return _to_out(entity)


@router.post(
    "",
    response_model=HeritageOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_heritage(
    payload: HeritageCreate,
    db: SessionDep,
    ctx: Annotated[
        AuthContext,
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
        _raise_heritage_error(exc)
    return _to_out(entity)


@router.patch("/{pub_id}", response_model=HeritageOut)
async def update_heritage(
    pub_id: str,
    payload: HeritagePatch,
    db: SessionDep,
    ctx: Annotated[
        AuthContext,
        Depends(require_permission("heritage:update")),
    ],
) -> HeritageOut:
    # SEC-016: ``status`` is a moderation FSM field. ``heritage:update`` covers
    # content edits; only ``heritage:moderate`` may advance the workflow state.
    # Reject the request outright so callers don't get a silent no-op on a
    # field they thought was applied.
    if "status" in payload.model_fields_set and payload.status is not None:
        granted = await _check_permission(db, ctx, "heritage:moderate")
        if not granted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "identity.permission_denied",
                    "message": "status field requires heritage:moderate",
                    "permission": "heritage:moderate",
                },
            )

    update = HeritageUpdate(
        name=payload.name,
        summary_md=payload.summary_md,
        description_md=payload.description_md,
        tags=tuple(payload.tags) if payload.tags is not None else None,
        country_code=payload.country_code,
        latitude=payload.latitude,
        longitude=payload.longitude,
        period_start_year=payload.period_start_year,
        period_end_year=payload.period_end_year,
        unesco_inscription_year=payload.unesco_inscription_year,
        hero_media_id=payload.hero_media_id,
        status=payload.status,
        set_fields=frozenset(payload.model_fields_set),
    )
    try:
        entity = await _service(db).update(pub_id=pub_id, update=update, updated_by=ctx.user_id)
    except HeritageError as exc:
        _raise_heritage_error(exc)
    return _to_out(entity)


@router.delete("/{pub_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_heritage(
    pub_id: str,
    db: SessionDep,
    ctx: Annotated[
        AuthContext,
        Depends(require_permission("heritage:delete")),
    ],
) -> Response:
    try:
        await _service(db).soft_delete(pub_id=pub_id, deleted_by=ctx.user_id)
    except HeritageError as exc:
        _raise_heritage_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{pub_id}/aliases",
    response_model=HeritageAliasOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_alias(
    pub_id: str,
    payload: HeritageAliasIn,
    db: SessionDep,
    ctx: Annotated[
        AuthContext,
        Depends(require_permission("heritage:update")),
    ],
) -> HeritageAliasOut:
    draft = HeritageAliasDraft(
        alias=payload.alias,
        language_tag=payload.language_tag,
        kind=payload.kind,
        confidence=payload.confidence,
        script=payload.script,
        source=payload.source,
    )
    try:
        alias = await _service(db).add_alias(pub_id=pub_id, draft=draft, actor=ctx.user_id)
    except HeritageError as exc:
        _raise_heritage_error(exc)
    return HeritageAliasOut(
        id=alias.id,
        heritage_id=alias.heritage_id,
        alias=alias.alias,
        language_tag=alias.language_tag,
        kind=alias.kind,
        confidence=alias.confidence,
        script=alias.script,
        source=alias.source,
        created_at=alias.created_at,
    )


@router.get("/{pub_id}/revisions", response_model=RevisionPageOut)
async def list_revisions(
    pub_id: str,
    db: SessionDep,
    _ctx: Annotated[
        AuthContext,
        Depends(require_permission("heritage:read")),
    ],
    limit: LimitQ = 20,
    offset: OffsetQ = 0,
) -> RevisionPageOut:
    try:
        page = await _service(db).list_revisions(pub_id=pub_id, limit=limit, offset=offset)
    except HeritageError as exc:
        _raise_heritage_error(exc)
    return RevisionPageOut(
        items=[
            RevisionOut(
                id=r.id,
                revision=r.revision,
                action=r.action,
                actor_user_id=r.actor_user_id,
                comment=r.comment,
                valid_from=r.valid_from,
                before=r.before,
                after=r.after,
            )
            for r in page.items
        ],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@router.post("/{pub_id}/transitions", response_model=HeritageOut)
async def transition_heritage(
    pub_id: str,
    payload: TransitionIn,
    db: SessionDep,
    ctx: Annotated[AuthContext, Depends(require_user)],
) -> HeritageOut:
    # Each action requires a different permission — we resolve at call time
    # via the same has_permission SQL function the dependency factory uses.
    perm = required_permission(payload.action)
    granted = await _check_permission(db, ctx, perm)
    if not granted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "identity.permission_denied",
                "message": f"missing permission '{perm}'",
                "permission": perm,
            },
        )
    try:
        entity = await _service(db).transition_status(
            pub_id=pub_id, action=payload.action, actor=ctx.user_id
        )
    except HeritageError as exc:
        _raise_heritage_error(exc)
    return _to_out(entity)


async def _check_permission(db: AsyncSession, ctx: AuthContext, perm: str) -> bool:
    row = await db.execute(
        text("SELECT app.has_permission(:uid, :residency, :perm, :tenant)"),
        {
            "uid": ctx.user_id,
            "residency": ctx.residency_region.value,
            "perm": perm,
            "tenant": ctx.tenant_id,
        },
    )
    return bool(row.scalar_one())
