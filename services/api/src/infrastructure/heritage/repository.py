"""SQLAlchemy-backed implementation of ``HeritageRepository``.

Hand-written SQL again (per the identity infrastructure rationale): migration
0010 owns the canonical schema; ORM models on top would duplicate truth.
"""

from __future__ import annotations

from typing import Final
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.heritage.entities import (
    HeritageDraft,
    HeritageFilters,
    HeritageObject,
    HeritagePage,
    HeritageStatus,
)

_SELECT_COLUMNS: Final = """
    id, tenant_id, pub_id, kind_slug,
    name, summary_md, description_md, tags,
    country_code, admin_path::text AS admin_path,
    latitude, longitude, elevation_m,
    period_start_year, period_end_year, unesco_inscription_year,
    status, hero_media_id, confidence_score, revision,
    created_at, updated_at, deleted_at, created_by, updated_by
"""


def _row_to_entity(row: object) -> HeritageObject:
    m = row._mapping  # type: ignore[attr-defined]
    return HeritageObject(
        id=m["id"],
        tenant_id=m["tenant_id"],
        pub_id=m["pub_id"],
        kind_slug=m["kind_slug"],
        name=dict(m["name"]) if m["name"] else {},
        summary_md=dict(m["summary_md"]) if m["summary_md"] else {},
        description_md=dict(m["description_md"]) if m["description_md"] else {},
        tags=tuple(m["tags"]) if m["tags"] else (),
        country_code=m["country_code"],
        admin_path=m["admin_path"],
        latitude=m["latitude"],
        longitude=m["longitude"],
        elevation_m=m["elevation_m"],
        period_start_year=m["period_start_year"],
        period_end_year=m["period_end_year"],
        unesco_inscription_year=m["unesco_inscription_year"],
        status=HeritageStatus(m["status"]),
        hero_media_id=m["hero_media_id"],
        confidence_score=m["confidence_score"],
        revision=m["revision"],
        created_at=m["created_at"],
        updated_at=m["updated_at"],
        deleted_at=m["deleted_at"],
        created_by=m["created_by"],
        updated_by=m["updated_by"],
    )


class SqlHeritageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_pub_id(self, pub_id: str) -> HeritageObject | None:
        result = await self._session.execute(
            text(
                f"""
                SELECT {_SELECT_COLUMNS}
                FROM heritage_objects
                WHERE pub_id = :pub_id
                LIMIT 1
                """  # noqa: S608 — _SELECT_COLUMNS is a constant, not user input
            ),
            {"pub_id": pub_id},
        )
        row = result.one_or_none()
        return _row_to_entity(row) if row else None

    async def get_by_id(self, heritage_id: UUID) -> HeritageObject | None:
        result = await self._session.execute(
            text(
                f"""
                SELECT {_SELECT_COLUMNS}
                FROM heritage_objects
                WHERE id = :id
                LIMIT 1
                """  # noqa: S608
            ),
            {"id": heritage_id},
        )
        row = result.one_or_none()
        return _row_to_entity(row) if row else None

    async def list_page(self, filters: HeritageFilters) -> HeritagePage:
        clauses = ["deleted_at IS NULL"]
        params: dict[str, object] = {}
        if filters.kind_slug:
            clauses.append("kind_slug = :kind_slug")
            params["kind_slug"] = filters.kind_slug
        if filters.country_code:
            clauses.append("country_code = :country_code")
            params["country_code"] = filters.country_code
        if filters.status is not None:
            clauses.append("status = :status")
            params["status"] = filters.status.value
        if filters.search:
            clauses.append(
                """
                (
                    name::text ILIKE '%' || :search || '%'
                    OR summary_md::text ILIKE '%' || :search || '%'
                )
                """
            )
            params["search"] = filters.search

        where = " AND ".join(clauses)

        # Count
        count_row = await self._session.execute(
            text(f"SELECT count(*) FROM heritage_objects WHERE {where}"),  # noqa: S608
            params,
        )
        total = count_row.scalar_one()

        # Page
        params["limit"] = filters.limit
        params["offset"] = filters.offset
        result = await self._session.execute(
            text(
                f"""
                SELECT {_SELECT_COLUMNS}
                FROM heritage_objects
                WHERE {where}
                ORDER BY created_at DESC, id DESC
                LIMIT :limit OFFSET :offset
                """  # noqa: S608
            ),
            params,
        )
        items = tuple(_row_to_entity(r) for r in result.all())
        return HeritagePage(
            items=items,
            total=int(total),
            limit=filters.limit,
            offset=filters.offset,
        )

    async def pub_id_exists(self, pub_id: str) -> bool:
        row = await self._session.execute(
            text("SELECT 1 FROM heritage_objects WHERE pub_id = :p LIMIT 1"),
            {"p": pub_id},
        )
        return row.one_or_none() is not None

    async def kind_exists(self, kind_slug: str) -> bool:
        row = await self._session.execute(
            text(
                """
                SELECT 1
                FROM vocabulary_terms t
                JOIN controlled_vocabularies v ON v.id = t.vocabulary_id
                WHERE v.slug = 'heritage_kinds'
                  AND t.slug = :kind_slug
                  AND t.is_active
                LIMIT 1
                """
            ),
            {"kind_slug": kind_slug},
        )
        return row.one_or_none() is not None

    async def create(
        self,
        *,
        draft: HeritageDraft,
        pub_id: str,
        created_by: UUID,
    ) -> HeritageObject:
        # Insert the row + the aliases in one transaction; commit at the end.
        result = await self._session.execute(
            text(
                f"""
                INSERT INTO heritage_objects (
                    tenant_id, pub_id, kind_slug,
                    name, summary_md, description_md, tags,
                    country_code, latitude, longitude,
                    period_start_year, period_end_year, unesco_inscription_year,
                    status, created_by, updated_by
                )
                VALUES (
                    :tenant_id, :pub_id, :kind_slug,
                    CAST(:name AS jsonb), CAST(:summary AS jsonb),
                    CAST(:description AS jsonb), :tags,
                    :country_code, :latitude, :longitude,
                    :period_start, :period_end, :unesco_year,
                    :status, :created_by, :created_by
                )
                RETURNING {_SELECT_COLUMNS}
                """  # noqa: S608
            ),
            {
                "tenant_id": draft.tenant_id,
                "pub_id": pub_id,
                "kind_slug": draft.kind_slug,
                "name": _json(draft.name),
                "summary": _json(draft.summary_md),
                "description": _json(draft.description_md),
                "tags": list(draft.tags),
                "country_code": draft.country_code,
                "latitude": draft.latitude,
                "longitude": draft.longitude,
                "period_start": draft.period_start_year,
                "period_end": draft.period_end_year,
                "unesco_year": draft.unesco_inscription_year,
                "status": draft.status.value,
                "created_by": created_by,
            },
        )
        row = result.one()
        entity = _row_to_entity(row)

        for alias in draft.aliases:
            await self._session.execute(
                text(
                    """
                    INSERT INTO heritage_aliases (
                        heritage_id, alias, language_tag, kind, confidence
                    )
                    VALUES (:hid, :alias, :lang, :kind, :conf)
                    """
                ),
                {
                    "hid": entity.id,
                    "alias": alias.alias,
                    "lang": alias.language_tag,
                    "kind": alias.kind.value,
                    "conf": alias.confidence,
                },
            )

        # Emit the event into the transactional outbox before commit
        await self._session.execute(
            text(
                """
                SELECT app.emit_event(
                    :tenant, 'heritage.created.v1', 'heritage', :hid,
                    CAST(:payload AS jsonb)
                )
                """
            ),
            {
                "tenant": entity.tenant_id,
                "hid": entity.id,
                "payload": _json(
                    {
                        "pub_id": entity.pub_id,
                        "kind_slug": entity.kind_slug,
                        "created_by": str(created_by),
                        "country_code": entity.country_code,
                    }
                ),
            },
        )

        await self._session.commit()
        return entity


def _json(payload: object) -> str:
    """Serialize a Python value as a JSON string for jsonb casting."""
    import json

    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
