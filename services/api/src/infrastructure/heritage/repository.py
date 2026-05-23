"""SQLAlchemy-backed implementation of ``HeritageRepository``.

Hand-written SQL again (per the identity infrastructure rationale): migration
0010 owns the canonical schema; ORM models on top would duplicate truth.
"""

from __future__ import annotations

import json
from typing import Any, Final
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.heritage.entities import (
    AliasKind,
    HeritageAlias,
    HeritageAliasDraft,
    HeritageDraft,
    HeritageFilters,
    HeritageObject,
    HeritagePage,
    HeritageRevision,
    HeritageRevisionPage,
    HeritageStatus,
    HeritageUpdate,
)
from src.domain.heritage.errors import DuplicateAlias, HeritageNotFound

_SELECT_COLUMNS: Final = """
    id, tenant_id, pub_id, kind_slug,
    name, summary_md, description_md, tags,
    country_code, admin_path::text AS admin_path,
    latitude, longitude, elevation_m,
    period_start_year, period_end_year, unesco_inscription_year,
    status, hero_media_id, confidence_score, revision,
    created_at, updated_at, deleted_at, created_by, updated_by
"""


def _row_to_entity(row: Any) -> HeritageObject:
    m = row._mapping
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


def _row_to_revision(row: Any) -> HeritageRevision:
    m = row._mapping
    return HeritageRevision(
        id=m["id"],
        heritage_id=m["heritage_id"],
        revision=m["revision"],
        action=m["action"],
        actor_user_id=m["actor_user_id"],
        before=dict(m["before"]) if m["before"] else None,
        after=dict(m["after"]) if m["after"] else {},
        diff=dict(m["diff"]) if m["diff"] else None,
        comment=m["comment"],
        valid_from=m["valid_from"],
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
                WHERE pub_id = :pub_id AND deleted_at IS NULL
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
                WHERE id = :id AND deleted_at IS NULL
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

    async def update(
        self,
        *,
        existing: HeritageObject,
        update: HeritageUpdate,
        updated_by: UUID,
    ) -> HeritageObject:
        # Partial update — we only emit SET clauses for fields the caller
        # explicitly provided. For jsonb merge columns we use the ``||``
        # operator so callers can patch individual locales without losing
        # the rest of the i18n map.
        sets: list[str] = ["updated_by = :updated_by"]
        params: dict[str, object] = {"hid": existing.id, "updated_by": updated_by}

        if update.has("name") and update.name is not None:
            sets.append("name = name || CAST(:name AS jsonb)")
            params["name"] = _json(update.name)
        if update.has("summary_md") and update.summary_md is not None:
            sets.append("summary_md = summary_md || CAST(:summary AS jsonb)")
            params["summary"] = _json(update.summary_md)
        if update.has("description_md") and update.description_md is not None:
            sets.append("description_md = description_md || CAST(:description AS jsonb)")
            params["description"] = _json(update.description_md)
        if update.has("tags"):
            sets.append("tags = :tags")
            params["tags"] = list(update.tags) if update.tags else []
        if update.has("country_code"):
            sets.append("country_code = :country_code")
            params["country_code"] = update.country_code
        if update.has("latitude"):
            sets.append("latitude = :latitude")
            params["latitude"] = update.latitude
        if update.has("longitude"):
            sets.append("longitude = :longitude")
            params["longitude"] = update.longitude
        if update.has("period_start_year"):
            sets.append("period_start_year = :period_start")
            params["period_start"] = update.period_start_year
        if update.has("period_end_year"):
            sets.append("period_end_year = :period_end")
            params["period_end"] = update.period_end_year
        if update.has("unesco_inscription_year"):
            sets.append("unesco_inscription_year = :unesco_year")
            params["unesco_year"] = update.unesco_inscription_year
        if update.has("hero_media_id"):
            sets.append("hero_media_id = :hero_media_id")
            params["hero_media_id"] = update.hero_media_id
        if update.has("status") and update.status is not None:
            sets.append("status = :status")
            params["status"] = update.status.value

        set_clause = ", ".join(sets)
        result = await self._session.execute(
            text(
                f"""
                UPDATE heritage_objects
                SET {set_clause}
                WHERE id = :hid AND deleted_at IS NULL
                RETURNING {_SELECT_COLUMNS}
                """  # noqa: S608
            ),
            params,
        )
        row = result.one()
        entity = _row_to_entity(row)

        await self._session.execute(
            text(
                """
                SELECT app.emit_event(
                    :tenant, 'heritage.updated.v1', 'heritage', :hid,
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
                        "updated_by": str(updated_by),
                        "revision": entity.revision,
                        "changed_fields": sorted(update.set_fields),
                    }
                ),
            },
        )
        await self._session.commit()
        return entity

    async def soft_delete(
        self,
        *,
        existing: HeritageObject,
        deleted_by: UUID,
    ) -> HeritageObject:
        result = await self._session.execute(
            text(
                f"""
                UPDATE heritage_objects
                SET deleted_at = now(), updated_by = :deleted_by
                WHERE id = :hid AND deleted_at IS NULL
                RETURNING {_SELECT_COLUMNS}
                """  # noqa: S608
            ),
            {"hid": existing.id, "deleted_by": deleted_by},
        )
        row = result.one()
        entity = _row_to_entity(row)

        # `heritage.deleted.v1` is seeded by migration 0062 — emit_event now
        # accepts it directly. The previous runtime ``_ensure_event_type``
        # bridge has been removed (MED-H1).
        await self._session.execute(
            text(
                """
                SELECT app.emit_event(
                    :tenant, 'heritage.deleted.v1', 'heritage', :hid,
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
                        "deleted_by": str(deleted_by),
                        "revision": entity.revision,
                    }
                ),
            },
        )
        await self._session.commit()
        return entity

    async def add_alias(
        self,
        *,
        heritage_id: UUID,
        tenant_id: UUID,
        draft: HeritageAliasDraft,
        actor: UUID,
    ) -> HeritageAlias:
        try:
            result = await self._session.execute(
                text(
                    """
                    INSERT INTO heritage_aliases (
                        heritage_id, alias, language_tag, script, kind, source, confidence
                    )
                    VALUES (:hid, :alias, :lang, :script, :kind, :source, :conf)
                    RETURNING id, heritage_id, alias, language_tag, script, kind,
                              source, confidence, created_at
                    """
                ),
                {
                    "hid": heritage_id,
                    "alias": draft.alias,
                    "lang": draft.language_tag,
                    "script": draft.script,
                    "kind": draft.kind.value,
                    "source": draft.source,
                    "conf": draft.confidence,
                },
            )
        except IntegrityError as exc:
            await self._session.rollback()
            # IntegrityError catches both the alias uniqueness clash and the
            # heritage_id FK violation (parent soft-deleted between the
            # service-layer fetch and the insert). Disambiguate via the
            # SQLSTATE code: 23503 = foreign_key_violation,
            # 23505 = unique_violation. SQLAlchemy exposes it as ``pgcode``
            # on the wrapped asyncpg error.
            pgcode = getattr(exc.orig, "pgcode", "") or getattr(exc.orig, "sqlstate", "") or ""
            if pgcode == "23503":
                raise HeritageNotFound(f"heritage_id={heritage_id} not found") from exc
            raise DuplicateAlias(
                f"alias '{draft.alias}@{draft.language_tag}' already exists"
            ) from exc

        raw = result.one_or_none()
        if raw is None:
            # Defensive: the INSERT … RETURNING contract returns the row on
            # success, so reaching here means another writer raced us out.
            raise HeritageNotFound(f"heritage_id={heritage_id} not found")
        row = raw._mapping
        alias_entity = HeritageAlias(
            id=row["id"],
            heritage_id=row["heritage_id"],
            alias=row["alias"],
            language_tag=row["language_tag"],
            script=row["script"],
            kind=AliasKind(row["kind"]),
            source=row["source"],
            confidence=row["confidence"],
            created_at=row["created_at"],
        )

        # The alias touches the aggregate — emit the standard updated.v1.
        await self._session.execute(
            text(
                """
                SELECT app.emit_event(
                    :tenant, 'heritage.updated.v1', 'heritage', :hid,
                    CAST(:payload AS jsonb)
                )
                """
            ),
            {
                "tenant": tenant_id,
                "hid": heritage_id,
                "payload": _json(
                    {
                        "alias_added": draft.alias,
                        "language_tag": draft.language_tag,
                        "kind": draft.kind.value,
                        "actor": str(actor),
                    }
                ),
            },
        )
        await self._session.commit()
        return alias_entity

    async def list_revisions(
        self,
        *,
        heritage_id: UUID,
        limit: int,
        offset: int,
    ) -> HeritageRevisionPage:
        total_row = await self._session.execute(
            text("SELECT count(*) FROM heritage_revisions WHERE heritage_id = :hid"),
            {"hid": heritage_id},
        )
        total = int(total_row.scalar_one())
        result = await self._session.execute(
            text(
                """
                SELECT id, heritage_id, revision, action, actor_user_id,
                       before, after, diff, comment, valid_from
                FROM heritage_revisions
                WHERE heritage_id = :hid
                ORDER BY revision DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            {"hid": heritage_id, "limit": limit, "offset": offset},
        )
        items = tuple(_row_to_revision(r) for r in result.all())
        return HeritageRevisionPage(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    async def transition_status(
        self,
        *,
        existing: HeritageObject,
        new_status: str,
        actor: UUID,
    ) -> HeritageObject:
        result = await self._session.execute(
            text(
                f"""
                UPDATE heritage_objects
                SET status = :status, updated_by = :actor
                WHERE id = :hid AND deleted_at IS NULL
                RETURNING {_SELECT_COLUMNS}
                """  # noqa: S608
            ),
            {"hid": existing.id, "status": new_status, "actor": actor},
        )
        row = result.one_or_none()
        if row is None:
            # Heritage was soft-deleted between the service-layer fetch and the
            # status update. Surface a typed 404 instead of a bare NoResultFound.
            raise HeritageNotFound(f"heritage_id={existing.id} not found")
        entity = _row_to_entity(row)

        await self._session.execute(
            text(
                """
                SELECT app.emit_event(
                    :tenant, 'heritage.updated.v1', 'heritage', :hid,
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
                        "status_from": existing.status.value,
                        "status_to": new_status,
                        "actor": str(actor),
                        "revision": entity.revision,
                    }
                ),
            },
        )
        await self._session.commit()
        return entity


def _json(payload: object) -> str:
    """Serialize a Python value as a JSON string for jsonb casting."""
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
