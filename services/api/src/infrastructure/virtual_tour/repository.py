"""SQLAlchemy-backed implementation of VirtualTourRepository.

Hand-written SQL — migration 0087 owns the canonical schema.
asyncpg-safe: all JSON values cast via ::jsonb, arrays explicit.
"""

from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.virtual_tour.entities import (
    TourDraft,
    TourKind,
    TourPage,
    TourProgress,
    TourScene,
    TourStatus,
    TourUpdate,
    VirtualTour,
    VirtualTourCollection,
)
from src.domain.virtual_tour.errors import DuplicateTourSlug

_TOUR_COLS = """
    vt.id, vt.tenant_id, vt.heritage_id, vt.slug,
    vt.title, vt.description_md, vt.kind, vt.status,
    vt.thumbnail_media_id, vt.tour_duration_seconds,
    vt.viewer_url, vt.embed_code, vt.view_count,
    vt.created_at, vt.updated_at, vt.deleted_at
"""

_SCENE_COLS = """
    id, tour_id, scene_order,
    title, description_md,
    panorama_media_id, model_3d_asset_id,
    hotspot_data, audio_guide_media_id,
    created_at, updated_at
"""


def _row_to_tour(row: object, scenes: tuple[TourScene, ...] = ()) -> VirtualTour:
    m = row._mapping  # type: ignore[attr-defined]
    return VirtualTour(
        id=m["id"],
        tenant_id=m["tenant_id"],
        heritage_id=m["heritage_id"],
        slug=m["slug"],
        title=dict(m["title"]) if m["title"] else {},
        description_md=dict(m["description_md"]) if m["description_md"] else {},
        kind=TourKind(m["kind"]),
        status=TourStatus(m["status"]),
        thumbnail_media_id=m["thumbnail_media_id"],
        tour_duration_seconds=m["tour_duration_seconds"],
        viewer_url=m["viewer_url"],
        embed_code=m["embed_code"],
        view_count=m["view_count"] or 0,
        created_at=m["created_at"],
        updated_at=m["updated_at"],
        deleted_at=m["deleted_at"],
        scenes=scenes,
    )


def _row_to_scene(row: object) -> TourScene:
    m = row._mapping  # type: ignore[attr-defined]
    hotspots = m["hotspot_data"]
    if isinstance(hotspots, str):
        hotspots = json.loads(hotspots)
    return TourScene(
        id=m["id"],
        tour_id=m["tour_id"],
        scene_order=m["scene_order"],
        title=dict(m["title"]) if m["title"] else {},
        description_md=dict(m["description_md"]) if m["description_md"] else {},
        panorama_media_id=m["panorama_media_id"],
        model_3d_asset_id=m["model_3d_asset_id"],
        hotspot_data=list(hotspots) if hotspots else [],
        audio_guide_media_id=m["audio_guide_media_id"],
        created_at=m["created_at"],
        updated_at=m["updated_at"],
    )


def _row_to_progress(row: object) -> TourProgress:
    m = row._mapping  # type: ignore[attr-defined]
    return TourProgress(
        user_id=m["user_id"],
        residency_region=m["residency_region"],
        tour_id=m["tour_id"],
        last_scene_order=m["last_scene_order"],
        completed=m["completed"],
        started_at=m["started_at"],
        updated_at=m["updated_at"],
    )


def _row_to_collection(row: object) -> VirtualTourCollection:
    m = row._mapping  # type: ignore[attr-defined]
    return VirtualTourCollection(
        id=m["id"],
        tenant_id=m["tenant_id"],
        slug=m["slug"],
        title=dict(m["title"]) if m["title"] else {},
        description_md=dict(m["description_md"]) if m["description_md"] else {},
        is_featured=m["is_featured"],
        sort_order=m["sort_order"],
        created_at=m["created_at"],
    )


class SqlVirtualTourRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def list_tours(
        self,
        *,
        heritage_id: UUID | None,
        collection_slug: str | None,
        kind: str | None,
        limit: int,
        offset: int,
    ) -> TourPage:
        filters: list[str] = ["vt.deleted_at IS NULL", "vt.status = 'published'"]
        params: dict[str, object] = {"limit": limit, "offset": offset}

        if heritage_id is not None:
            filters.append("vt.heritage_id = :heritage_id")
            params["heritage_id"] = heritage_id

        if kind is not None:
            filters.append("vt.kind = :kind")
            params["kind"] = kind

        join_clause = ""
        if collection_slug is not None:
            join_clause = """
                JOIN virtual_tour_collection_items vtci ON vtci.tour_id = vt.id
                JOIN virtual_tour_collections vtc ON vtc.id = vtci.collection_id
                    AND vtc.slug = :collection_slug
            """
            params["collection_slug"] = collection_slug

        where_clause = " AND ".join(filters)

        count_sql = f"SELECT COUNT(*) FROM virtual_tours vt {join_clause} WHERE {where_clause}"  # noqa: S608
        select_sql = (
            f"SELECT {_TOUR_COLS} FROM virtual_tours vt"  # noqa: S608
            f" {join_clause} WHERE {where_clause}"
            " ORDER BY vt.created_at DESC LIMIT :limit OFFSET :offset"
        )

        total_row = await self._db.execute(text(count_sql), params)
        total = total_row.scalar_one()

        rows = await self._db.execute(text(select_sql), params)
        items = tuple(_row_to_tour(r) for r in rows)
        return TourPage(items=items, total=total, limit=limit, offset=offset)

    async def get_by_slug(self, slug: str) -> VirtualTour | None:
        sql = f"SELECT {_TOUR_COLS} FROM virtual_tours vt WHERE vt.slug = :slug"  # noqa: S608
        row = await self._db.execute(text(sql), {"slug": slug})
        tour_row = row.first()
        if tour_row is None:
            return None

        # Load scenes
        scene_sql = (
            f"SELECT {_SCENE_COLS} FROM virtual_tour_scenes"  # noqa: S608
            " WHERE tour_id = :tour_id ORDER BY scene_order"
        )
        scene_rows = await self._db.execute(text(scene_sql), {"tour_id": tour_row._mapping["id"]})
        scenes = tuple(_row_to_scene(r) for r in scene_rows)
        return _row_to_tour(tour_row, scenes)

    async def create(self, draft: TourDraft) -> VirtualTour:
        sql = """
            INSERT INTO virtual_tours (
                tenant_id, heritage_id, slug, title, description_md,
                kind, status, thumbnail_media_id, tour_duration_seconds,
                viewer_url, embed_code
            ) VALUES (
                :tenant_id, :heritage_id, :slug,
                CAST(:title AS jsonb), CAST(:description_md AS jsonb),
                :kind, :status, :thumbnail_media_id,
                :tour_duration_seconds, :viewer_url, :embed_code
            )
            RETURNING id, tenant_id, heritage_id, slug,
                title, description_md, kind, status,
                thumbnail_media_id, tour_duration_seconds,
                viewer_url, embed_code, view_count,
                created_at, updated_at, deleted_at
        """
        try:
            row = await self._db.execute(
                text(sql),
                {
                    "tenant_id": draft.tenant_id,
                    "heritage_id": draft.heritage_id,
                    "slug": draft.slug,
                    "title": json.dumps(draft.title),
                    "description_md": json.dumps(draft.description_md),
                    "kind": draft.kind.value,
                    "status": draft.status.value,
                    "thumbnail_media_id": draft.thumbnail_media_id,
                    "tour_duration_seconds": draft.tour_duration_seconds,
                    "viewer_url": draft.viewer_url,
                    "embed_code": draft.embed_code,
                },
            )
            await self._db.commit()
        except IntegrityError as exc:
            await self._db.rollback()
            if "unique" in str(exc).lower():
                raise DuplicateTourSlug(draft.slug) from exc
            raise
        return _row_to_tour(row.first())

    async def update(self, slug: str, update: TourUpdate) -> VirtualTour | None:
        sets: list[str] = []
        params: dict[str, object] = {"slug": slug}

        if update.has("title") and update.title is not None:
            sets.append("title = CAST(:title AS jsonb)")
            params["title"] = json.dumps(update.title)
        if update.has("description_md") and update.description_md is not None:
            sets.append("description_md = CAST(:description_md AS jsonb)")
            params["description_md"] = json.dumps(update.description_md)
        if update.has("kind") and update.kind is not None:
            sets.append("kind = :kind")
            params["kind"] = update.kind.value
        if update.has("tour_duration_seconds"):
            sets.append("tour_duration_seconds = :tour_duration_seconds")
            params["tour_duration_seconds"] = update.tour_duration_seconds
        if update.has("viewer_url"):
            sets.append("viewer_url = :viewer_url")
            params["viewer_url"] = update.viewer_url
        if update.has("embed_code"):
            sets.append("embed_code = :embed_code")
            params["embed_code"] = update.embed_code
        if update.has("thumbnail_media_id"):
            sets.append("thumbnail_media_id = :thumbnail_media_id")
            params["thumbnail_media_id"] = update.thumbnail_media_id

        if not sets:
            return await self.get_by_slug(slug)

        cols_ret = _TOUR_COLS.replace("vt.", "")
        sql = (
            f"UPDATE virtual_tours SET {', '.join(sets)}"  # noqa: S608
            f" WHERE slug = :slug AND deleted_at IS NULL RETURNING {cols_ret}"
        )
        row = await self._db.execute(text(sql), params)
        await self._db.commit()
        result = row.first()
        return _row_to_tour(result) if result else None

    async def set_status(self, slug: str, status: str) -> VirtualTour | None:
        cols_ret = _TOUR_COLS.replace("vt.", "")
        sql = (
            f"UPDATE virtual_tours SET status = :status"  # noqa: S608
            f" WHERE slug = :slug AND deleted_at IS NULL RETURNING {cols_ret}"
        )
        row = await self._db.execute(text(sql), {"slug": slug, "status": status})
        await self._db.commit()
        result = row.first()
        return _row_to_tour(result) if result else None

    async def upsert_progress(
        self,
        user_id: UUID,
        residency_region: str,
        tour_id: UUID,
        last_scene_order: int,
        completed: bool,
    ) -> TourProgress:
        sql = """
            INSERT INTO virtual_tour_progress
                (user_id, residency_region, tour_id, last_scene_order, completed)
            VALUES (:user_id, :residency_region, :tour_id, :last_scene_order, :completed)
            ON CONFLICT (user_id, residency_region, tour_id) DO UPDATE
                SET last_scene_order = EXCLUDED.last_scene_order,
                    completed        = EXCLUDED.completed,
                    updated_at       = now()
            RETURNING
                user_id, residency_region, tour_id,
                last_scene_order, completed, started_at, updated_at
        """
        row = await self._db.execute(
            text(sql),
            {
                "user_id": user_id,
                "residency_region": residency_region,
                "tour_id": tour_id,
                "last_scene_order": last_scene_order,
                "completed": completed,
            },
        )
        await self._db.commit()
        return _row_to_progress(row.first())

    async def get_progress(
        self,
        user_id: UUID,
        residency_region: str,
        tour_id: UUID,
    ) -> TourProgress | None:
        sql = """
            SELECT user_id, residency_region, tour_id,
                   last_scene_order, completed, started_at, updated_at
            FROM virtual_tour_progress
            WHERE user_id = :user_id
              AND residency_region = :residency_region
              AND tour_id = :tour_id
        """
        row = await self._db.execute(
            text(sql),
            {"user_id": user_id, "residency_region": residency_region, "tour_id": tour_id},
        )
        result = row.first()
        return _row_to_progress(result) if result else None

    async def list_collections(self) -> list[VirtualTourCollection]:
        sql = """
            SELECT id, tenant_id, slug, title, description_md,
                   is_featured, sort_order, created_at
            FROM virtual_tour_collections
            ORDER BY sort_order, created_at
        """
        rows = await self._db.execute(text(sql))
        return [_row_to_collection(r) for r in rows]

    async def increment_view_count(self, tour_id: UUID) -> None:
        sql = "UPDATE virtual_tours SET view_count = view_count + 1 WHERE id = :id"
        await self._db.execute(text(sql), {"id": tour_id})
        await self._db.commit()
