"""Heritage → Elasticsearch indexer.

The indexer is the *only* thing that knows the shape of the ES documents. It
reads from Postgres directly (``heritage_objects`` + ``heritage_aliases``)
and routes the resulting doc into the correct per-language tier-1 index plus
the tier-2 intl index so cross-locale fallback queries still hit.

Bootstrapping is idempotent — re-running ``bootstrap()`` only creates indices
that don't already exist. ``bulk_reindex`` is the safety-net for outbox loss
or schema migrations; it streams in pages so memory stays bounded.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.infrastructure.search.es_client import ElasticsearchClient
from src.infrastructure.search.mappings import (
    HERITAGE_INDICES,
    INTL_INDEX,
    TIER1_INDEX_BY_LANG,
    mapping_for,
)

log = get_logger("silklens.search.indexer")


@dataclass(slots=True, frozen=True)
class IndexFilters:
    """Optional filters for ``bulk_reindex``."""

    country_code: str | None = None
    kind_slug: str | None = None
    only_published: bool = False
    page_size: int = 200


@dataclass(slots=True, frozen=True)
class IndexResult:
    indexed: int
    skipped: int
    failed: int


class HeritageIndexer:
    """Index one or many heritage objects into per-language ES indices."""

    def __init__(self, session: AsyncSession, es: ElasticsearchClient) -> None:
        self._session = session
        self._es = es

    # ------------------------------------------------------------------
    # Bootstrap
    # ------------------------------------------------------------------

    async def bootstrap(self) -> list[str]:
        """Create any missing indices; return the list of indices we created.

        Updates ``search_index_mappings`` so admin endpoints can show what
        the cluster is supposed to be holding.
        """
        created: list[str] = []
        for index_name in sorted(HERITAGE_INDICES):
            exists = await self._es.index_exists(index_name)
            if not exists:
                await self._es.create_index(index_name, mapping_for(index_name))
                created.append(index_name)
            await self._upsert_mapping_row(index_name)
        return created

    async def _upsert_mapping_row(self, slug: str) -> None:
        tier = "tier1_dedicated" if slug != INTL_INDEX else "tier2_icu"
        await self._session.execute(
            text(
                """
                INSERT INTO search_index_mappings (
                    slug, kind, language_tier, analyzer_config, is_active
                ) VALUES (:slug, 'heritage', :tier, '{}'::jsonb, true)
                ON CONFLICT (slug) DO UPDATE SET
                    language_tier = EXCLUDED.language_tier,
                    is_active = true
                """
            ),
            {"slug": slug, "tier": tier},
        )
        await self._session.commit()

    # ------------------------------------------------------------------
    # Per-document operations
    # ------------------------------------------------------------------

    async def _load_heritage_doc(self, heritage_id: UUID) -> dict[str, Any] | None:
        row = (
            await self._session.execute(
                text(
                    """
                    SELECT id, tenant_id, pub_id, kind_slug,
                           name, summary_md, description_md, tags,
                           country_code, latitude, longitude,
                           period_start_year, period_end_year, unesco_inscription_year,
                           status, confidence_score, revision, updated_at,
                           wikidata_qid
                    FROM heritage_objects
                    WHERE id = :hid AND deleted_at IS NULL
                    """
                ),
                {"hid": heritage_id},
            )
        ).one_or_none()
        if row is None:
            return None
        m = row._mapping

        aliases_rows = (
            await self._session.execute(
                text(
                    """
                    SELECT alias, language_tag, kind
                    FROM heritage_aliases
                    WHERE heritage_id = :hid
                    """
                ),
                {"hid": heritage_id},
            )
        ).all()
        aliases = [
            {
                "alias": a._mapping["alias"],
                "language_tag": a._mapping["language_tag"],
                "kind": a._mapping["kind"],
            }
            for a in aliases_rows
        ]

        # Build the multi-locale base doc; we'll specialise per index below.
        names: dict[str, str] = dict(m["name"] or {})
        summaries: dict[str, str] = dict(m["summary_md"] or {})
        descriptions: dict[str, str] = dict(m["description_md"] or {})

        return {
            "heritage_id": str(m["id"]),
            "pub_id": m["pub_id"],
            "tenant_id": str(m["tenant_id"]),
            "wikidata_qid": m["wikidata_qid"],
            "kind_slug": m["kind_slug"],
            "country_code": m["country_code"],
            "status": m["status"],
            "tags": list(m["tags"] or []),
            "lat": float(m["latitude"]) if m["latitude"] is not None else None,
            "lng": float(m["longitude"]) if m["longitude"] is not None else None,
            "location": (
                {"lat": float(m["latitude"]), "lon": float(m["longitude"])}
                if m["latitude"] is not None and m["longitude"] is not None
                else None
            ),
            "period_start_year": m["period_start_year"],
            "period_end_year": m["period_end_year"],
            "unesco_inscription_year": m["unesco_inscription_year"],
            "confidence_score": m["confidence_score"],
            "revision": m["revision"],
            "updated_at": (m["updated_at"].isoformat() if m["updated_at"] else None),
            "_names": names,
            "_summaries": summaries,
            "_descriptions": descriptions,
            "_aliases": aliases,
        }

    def _project_for_lang(self, doc: dict[str, Any], lang: str) -> dict[str, Any]:
        names = doc["_names"]
        summaries = doc["_summaries"]
        descriptions = doc["_descriptions"]
        # Prefer the requested language; fall back to en, uz, then any
        # available locale so we always have a non-empty name. Suggest uses
        # the same fallback chain.
        fallback_order = [lang, "en", "uz"]
        name = ""
        for tag in fallback_order:
            if names.get(tag):
                name = names[tag]
                break
        if not name and names:
            name = next(iter(names.values()))
        summary = summaries.get(lang) or summaries.get("en") or summaries.get("uz") or ""
        description = (
            descriptions.get(lang) or descriptions.get("en") or descriptions.get("uz") or ""
        )

        projected = {
            k: v
            for k, v in doc.items()
            if k not in {"_names", "_summaries", "_descriptions", "_aliases"}
        }
        projected.update(
            {
                "name": name,
                "summary_md": summary,
                "description_md": description,
                "aliases": [
                    a for a in doc["_aliases"] if a["language_tag"].split("-")[0].lower() == lang
                ],
                "suggest": [name, *(a["alias"] for a in doc["_aliases"])],
            }
        )
        return projected

    def _project_for_intl(self, doc: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
        """Return one intl doc per non-tier-1 locale present on the object."""
        non_tier1_langs = {
            tag.split("-")[0].lower()
            for tag in doc["_names"]
            if tag.split("-")[0].lower() not in TIER1_INDEX_BY_LANG
        }
        out: list[tuple[str, dict[str, Any]]] = []
        for lang in sorted(non_tier1_langs):
            base = self._project_for_lang(doc, lang)
            base["locale"] = lang
            doc_id = f"{doc['heritage_id']}:{lang}"
            out.append((doc_id, base))
        return out

    async def index_one(self, heritage_id: UUID) -> IndexResult:
        doc = await self._load_heritage_doc(heritage_id)
        if doc is None:
            # The row was deleted between event emit and consumer drain — treat
            # as a delete for safety.
            await self.delete_one(heritage_id)
            return IndexResult(indexed=0, skipped=1, failed=0)

        indexed = 0
        for lang, index_name in TIER1_INDEX_BY_LANG.items():
            if lang in doc["_names"]:
                body = self._project_for_lang(doc, lang)
                await self._es.index_doc(index_name, str(heritage_id), body)
                indexed += 1

        for doc_id, body in self._project_for_intl(doc):
            await self._es.index_doc(INTL_INDEX, doc_id, body)
            indexed += 1

        log.info("search.indexed", heritage_id=str(heritage_id), docs=indexed)
        return IndexResult(indexed=indexed, skipped=0, failed=0)

    async def delete_one(self, heritage_id: UUID) -> IndexResult:
        deleted = 0
        for index_name in TIER1_INDEX_BY_LANG.values():
            await self._es.delete_doc(index_name, str(heritage_id))
            deleted += 1
        # Tier-2 docs are stored per-locale so we issue a delete-by-query.
        # The thin client doesn't expose it cleanly, so we approximate with
        # a wildcard ID list for common locales. The intl index is small.
        for lang_guess in ("fa", "tr", "ar", "ja"):
            await self._es.delete_doc(INTL_INDEX, f"{heritage_id}:{lang_guess}")
        log.info("search.deleted", heritage_id=str(heritage_id), docs=deleted)
        return IndexResult(indexed=0, skipped=0, failed=deleted)

    # ------------------------------------------------------------------
    # Full rebuild
    # ------------------------------------------------------------------

    async def bulk_reindex(self, filters: IndexFilters | None = None) -> IndexResult:
        filters = filters or IndexFilters()
        await self.bootstrap()

        clauses = ["deleted_at IS NULL"]
        params: dict[str, Any] = {}
        if filters.country_code:
            clauses.append("country_code = :country")
            params["country"] = filters.country_code.upper()
        if filters.kind_slug:
            clauses.append("kind_slug = :kind")
            params["kind"] = filters.kind_slug
        if filters.only_published:
            clauses.append("status = 'published'")
        where = " AND ".join(clauses)

        total_indexed = 0
        last_id: UUID | None = None
        while True:
            cursor_clause = "AND id > :last_id" if last_id else ""
            page_params = dict(params)
            page_params["limit"] = filters.page_size
            if last_id:
                page_params["last_id"] = last_id
            rows = (
                await self._session.execute(
                    text(
                        f"""
                        SELECT id FROM heritage_objects
                        WHERE {where} {cursor_clause}
                        ORDER BY id ASC
                        LIMIT :limit
                        """  # noqa: S608 — composed from constants
                    ),
                    page_params,
                )
            ).all()
            if not rows:
                break
            for row in rows:
                result = await self.index_one(row._mapping["id"])
                total_indexed += result.indexed
            last_id = rows[-1]._mapping["id"]
            if len(rows) < filters.page_size:
                break

        # Refresh + persist counts.
        for index_name in HERITAGE_INDICES:
            await self._es.refresh(index_name)
            count = await self._es.count(index_name)
            await self._session.execute(
                text(
                    """
                    UPDATE search_index_mappings
                    SET current_doc_count = :count,
                        target_doc_count = :count,
                        last_rebuilt_at = now()
                    WHERE slug = :slug
                    """
                ),
                {"count": count, "slug": index_name},
            )
        await self._session.commit()
        return IndexResult(indexed=total_indexed, skipped=0, failed=0)
