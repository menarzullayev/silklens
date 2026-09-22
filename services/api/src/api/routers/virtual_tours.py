"""Virtual tour endpoints.

GET    /v1/virtual-tours           — public list (filter: heritage_pub_id, collection_slug, kind)
GET    /v1/virtual-tours/{slug}    — public detail with scenes
POST   /v1/virtual-tours                        — create (requires heritage:create)
PATCH  /v1/virtual-tours/{slug}                 — update (requires heritage:update)
POST   /v1/virtual-tours/{slug}/publish         — state machine (requires heritage:moderate)
GET    /v1/virtual-tours/{slug}/embed           — embed_code (public, published only)
POST   /v1/virtual-tours/{slug}/progress        — record viewer progress (authenticated)
GET    /v1/virtual-tour-collections             — public collection list
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.domain.virtual_tour.entities import (
    TourDraft,
    TourKind,
    TourStatus,
    TourUpdate,
)
from src.domain.virtual_tour.errors import VirtualTourError
from src.domain.virtual_tour.service import VirtualTourService
from src.infrastructure.virtual_tour.repository import SqlVirtualTourRepository
from src.middleware.auth import require_permission, require_user

router = APIRouter(tags=["virtual-tours"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


# ---------------------------------------------------------------------------
# Output schemas
# ---------------------------------------------------------------------------


class TourSceneOut(BaseModel):
    id: UUID
    tour_id: UUID
    scene_order: int
    title: dict[str, str]
    description_md: dict[str, str]
    hotspot_data: list[dict[str, Any]]
    panorama_media_id: UUID | None
    model_3d_asset_id: UUID | None
    audio_guide_media_id: UUID | None
    created_at: datetime | None
    updated_at: datetime | None


class VirtualTourOut(BaseModel):
    id: UUID
    tenant_id: UUID
    heritage_id: UUID | None
    slug: str
    title: dict[str, str]
    description_md: dict[str, str]
    kind: TourKind
    status: TourStatus
    thumbnail_media_id: UUID | None
    tour_duration_seconds: int | None
    viewer_url: str | None
    embed_code: str | None
    view_count: int
    scenes: list[TourSceneOut]
    created_at: datetime
    updated_at: datetime


class TourPageOut(BaseModel):
    items: list[VirtualTourOut]
    total: int
    limit: int
    offset: int


class VirtualTourCollectionOut(BaseModel):
    id: UUID
    tenant_id: UUID
    slug: str
    title: dict[str, str]
    description_md: dict[str, str]
    is_featured: bool
    sort_order: int
    created_at: datetime


class TourProgressOut(BaseModel):
    user_id: UUID
    residency_region: str
    tour_id: UUID
    last_scene_order: int
    completed: bool
    started_at: datetime
    updated_at: datetime


class EmbedOut(BaseModel):
    slug: str
    embed_code: str | None


# ---------------------------------------------------------------------------
# Input schemas
# ---------------------------------------------------------------------------


class TourCreate(BaseModel):
    slug: str = Field(min_length=3, max_length=128)
    title: dict[str, str] = Field(min_length=1)
    kind: TourKind
    description_md: dict[str, str] = Field(default_factory=dict)
    heritage_id: UUID | None = None
    thumbnail_media_id: UUID | None = None
    tour_duration_seconds: int | None = Field(default=None, ge=1)
    viewer_url: str | None = None
    embed_code: str | None = None


class TourPatch(BaseModel):
    title: dict[str, str] | None = None
    description_md: dict[str, str] | None = None
    kind: TourKind | None = None
    tour_duration_seconds: int | None = Field(default=None, ge=1)
    viewer_url: str | None = None
    embed_code: str | None = None
    thumbnail_media_id: UUID | None = None


class ProgressIn(BaseModel):
    scene_order: int = Field(ge=0)
    completed: bool = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _service(db: AsyncSession) -> VirtualTourService:
    return VirtualTourService(repository=SqlVirtualTourRepository(db))


def _raise(exc: VirtualTourError) -> None:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": str(exc)},
    ) from exc


def _tour_out(entity: object) -> VirtualTourOut:
    from src.domain.virtual_tour.entities import VirtualTour  # local import fine

    t: VirtualTour = entity  # type: ignore[assignment]
    return VirtualTourOut(
        id=t.id,
        tenant_id=t.tenant_id,
        heritage_id=t.heritage_id,
        slug=t.slug,
        title=t.title,
        description_md=t.description_md,
        kind=t.kind,
        status=t.status,
        thumbnail_media_id=t.thumbnail_media_id,
        tour_duration_seconds=t.tour_duration_seconds,
        viewer_url=t.viewer_url,
        embed_code=t.embed_code,
        view_count=t.view_count,
        scenes=[
            TourSceneOut(
                id=s.id,
                tour_id=s.tour_id,
                scene_order=s.scene_order,
                title=s.title,
                description_md=s.description_md,
                hotspot_data=s.hotspot_data,
                panorama_media_id=s.panorama_media_id,
                model_3d_asset_id=s.model_3d_asset_id,
                audio_guide_media_id=s.audio_guide_media_id,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in t.scenes
        ],
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


LimitQ = Annotated[int, Query(ge=1, le=100)]
OffsetQ = Annotated[int, Query(ge=0, le=10_000_000)]

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/v1/virtual-tours", response_model=TourPageOut)
async def list_tours(
    db: SessionDep,
    heritage_pub_id: Annotated[str | None, Query()] = None,
    collection_slug: Annotated[str | None, Query()] = None,
    kind: Annotated[TourKind | None, Query()] = None,
    limit: LimitQ = 20,
    offset: OffsetQ = 0,
) -> TourPageOut:
    svc = _service(db)

    # Resolve heritage_pub_id → UUID if provided
    heritage_uuid: UUID | None = None
    if heritage_pub_id is not None:
        row = await db.execute(
            text("SELECT id FROM heritage_objects WHERE pub_id = :pub_id"),
            {"pub_id": heritage_pub_id},
        )
        result = row.first()
        if result is None:
            return TourPageOut(items=[], total=0, limit=limit, offset=offset)
        heritage_uuid = result._mapping["id"]

    page = await svc.list_tours(
        heritage_id=heritage_uuid,
        collection_slug=collection_slug,
        kind=kind.value if kind else None,
        limit=limit,
        offset=offset,
    )
    return TourPageOut(
        items=[_tour_out(t) for t in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/v1/virtual-tours/{slug}", response_model=VirtualTourOut)
async def get_tour(slug: str, db: SessionDep) -> VirtualTourOut:
    try:
        tour = await _service(db).get_tour(slug)
    except VirtualTourError as exc:
        _raise(exc)
    return _tour_out(tour)


@router.post(
    "/v1/virtual-tours",
    response_model=VirtualTourOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_tour(
    payload: TourCreate,
    db: SessionDep,
    ctx: Annotated[object, Depends(require_permission("heritage:create"))],
) -> VirtualTourOut:
    draft = TourDraft(
        tenant_id=ctx.tenant_id,  # type: ignore[attr-defined]
        slug=payload.slug,
        title=payload.title,
        kind=payload.kind,
        description_md=payload.description_md,
        heritage_id=payload.heritage_id,
        thumbnail_media_id=payload.thumbnail_media_id,
        tour_duration_seconds=payload.tour_duration_seconds,
        viewer_url=payload.viewer_url,
        embed_code=payload.embed_code,
    )
    try:
        tour = await _service(db).create_tour(draft, actor_user_id=ctx.user_id)  # type: ignore[attr-defined]
    except VirtualTourError as exc:
        _raise(exc)
    return _tour_out(tour)


@router.patch("/v1/virtual-tours/{slug}", response_model=VirtualTourOut)
async def update_tour(
    slug: str,
    payload: TourPatch,
    db: SessionDep,
    ctx: Annotated[object, Depends(require_permission("heritage:update"))],
) -> VirtualTourOut:
    update = TourUpdate(
        title=payload.title,
        description_md=payload.description_md,
        kind=payload.kind,
        tour_duration_seconds=payload.tour_duration_seconds,
        viewer_url=payload.viewer_url,
        embed_code=payload.embed_code,
        thumbnail_media_id=payload.thumbnail_media_id,
        set_fields=frozenset(payload.model_fields_set),
    )
    try:
        tour = await _service(db).update_tour(slug, update, actor_user_id=ctx.user_id)  # type: ignore[attr-defined]
    except VirtualTourError as exc:
        _raise(exc)
    return _tour_out(tour)


@router.post("/v1/virtual-tours/{slug}/publish", response_model=VirtualTourOut)
async def publish_tour(
    slug: str,
    db: SessionDep,
    ctx: Annotated[object, Depends(require_permission("heritage:moderate"))],
) -> VirtualTourOut:
    try:
        tour = await _service(db).publish_tour(slug, actor_user_id=ctx.user_id)  # type: ignore[attr-defined]
    except VirtualTourError as exc:
        _raise(exc)
    return _tour_out(tour)


@router.get("/v1/virtual-tours/{slug}/embed", response_model=EmbedOut)
async def get_embed(slug: str, db: SessionDep) -> EmbedOut:
    try:
        embed_code = await _service(db).get_embed(slug)
    except VirtualTourError as exc:
        _raise(exc)
    return EmbedOut(slug=slug, embed_code=embed_code)


@router.post("/v1/virtual-tours/{slug}/progress", response_model=TourProgressOut)
async def record_progress(
    slug: str,
    payload: ProgressIn,
    db: SessionDep,
    ctx: Annotated[object, Depends(require_user)],
) -> TourProgressOut:
    # Resolve slug → id
    svc = _service(db)
    try:
        tour = await svc.get_tour(slug)
    except VirtualTourError as exc:
        _raise(exc)

    progress = await svc.record_progress(
        user_id=ctx.user_id,  # type: ignore[attr-defined]
        residency_region=ctx.residency_region.value,  # type: ignore[attr-defined]
        tour_id=tour.id,
        scene_order=payload.scene_order,
        completed=payload.completed,
    )
    return TourProgressOut(
        user_id=progress.user_id,
        residency_region=progress.residency_region,
        tour_id=progress.tour_id,
        last_scene_order=progress.last_scene_order,
        completed=progress.completed,
        started_at=progress.started_at,
        updated_at=progress.updated_at,
    )


@router.get("/v1/virtual-tour-collections", response_model=list[VirtualTourCollectionOut])
async def list_collections(db: SessionDep) -> list[VirtualTourCollectionOut]:
    collections = await _service(db).list_collections()
    return [
        VirtualTourCollectionOut(
            id=c.id,
            tenant_id=c.tenant_id,
            slug=c.slug,
            title=c.title,
            description_md=c.description_md,
            is_featured=c.is_featured,
            sort_order=c.sort_order,
            created_at=c.created_at,
        )
        for c in collections
    ]
