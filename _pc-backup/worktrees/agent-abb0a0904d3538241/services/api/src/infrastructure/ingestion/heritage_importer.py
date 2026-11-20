"""Wikidata + Wikipedia → SilkLens heritage importer.

Translates a stream of ``WikidataHeritage`` items into rows in:

  - ``heritage_objects``    (with denormalized winning columns + ``wikidata_qid``)
  - ``heritage_aliases``    (one row per non-canonical label/alias)
  - ``heritage_facts``      (one row per atomic claim with confidence)
  - ``fact_provenance``     (linking each fact to the Wikidata source row)

Idempotency is achieved via the ``wikidata_qid`` unique index added in
migration 0072: ``import_one`` returns the existing heritage_id when the
QID is already present rather than inserting a duplicate. Subsequent calls
upsert facts so confidence + winning values converge as upstream changes.
"""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.infrastructure.ingestion.wikidata import WikidataClient, WikidataHeritage
from src.infrastructure.ingestion.wikipedia import WikipediaClient

log = get_logger("silklens.ingestion.importer")


# Wikidata P31 (instance_of) → our controlled-vocabulary kind_slug.
# When multiple matches exist we take the most specific (first match in the
# ordered tuple wins).
_INSTANCE_OF_TO_KIND: tuple[tuple[str, str], ...] = (
    ("Q2393314", "madrasa"),
    ("Q32815", "mosque"),
    ("Q35112127", "caravanserai"),
    ("Q381885", "mausoleum"),
    ("Q381885", "mausoleum"),
    ("Q839954", "archaeological_site"),
    ("Q33506", "museum"),
    ("Q570116", "monument"),
    ("Q41176", "monument"),
    ("Q1364", "palace"),
    ("Q44539", "monument"),
    ("Q23413", "palace"),
    ("Q1424516", "monument"),
    ("Q11303", "monument"),
    ("Q16970", "monument"),
    ("Q9259", "monument"),
)

# Confidence assigned per source rank. Wikidata's own rank metadata is sparse
# in the basic SPARQL response, so we use a fixed mapping per predicate.
_BASE_CONFIDENCE = {
    "name": 80,
    "description": 70,
    "country": 90,
    "coordinates": 85,
    "inception_year": 70,
    "image": 60,
}


def _generate_pub_id() -> str:
    return secrets.token_urlsafe(8)[:10]


def _kind_from_instance_of(qids: tuple[str, ...]) -> str:
    qid_set = set(qids)
    for wd_q, kind in _INSTANCE_OF_TO_KIND:
        if wd_q in qid_set:
            return kind
    return "monument"


def _json_dump(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)


@dataclass(slots=True, frozen=True)
class ImportResult:
    """Outcome of one import_one() call."""

    heritage_id: UUID
    pub_id: str
    qid: str
    created: bool
    facts_written: int = 0
    aliases_written: int = 0


@dataclass(slots=True)
class ImportBatchResult:
    discovered: int = 0
    created: int = 0
    skipped: int = 0
    failed: int = 0
    items: list[ImportResult] = field(default_factory=list)


class WikidataHeritageImporter:
    """Orchestrates Wikidata discovery + per-item import."""

    def __init__(
        self,
        session: AsyncSession,
        wikidata: WikidataClient,
        wikipedia: WikipediaClient,
        *,
        default_tenant_id: UUID,
    ) -> None:
        self._session = session
        self._wd = wikidata
        self._wp = wikipedia
        self._tenant_id = default_tenant_id

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    async def discover(self, country_code: str, limit: int = 50) -> list[WikidataHeritage]:
        return await self._wd.heritage_for_country(country_code, limit=limit)

    # ------------------------------------------------------------------
    # Wikipedia enrichment
    # ------------------------------------------------------------------

    async def _enrich_wikipedia(self, item: WikidataHeritage) -> WikidataHeritage:
        # Build a title map: prefer the language-specific Wikidata label when
        # present, fall back to the english label.
        titles_by_lang = dict(item.names)
        if "en" in titles_by_lang:
            for lang in ("uz", "ru", "zh"):
                titles_by_lang.setdefault(lang, titles_by_lang["en"])
        summaries = await self._wp.fetch_many(titles_by_lang)
        if not summaries:
            return item

        descriptions = dict(item.description)
        wikipedia_urls = dict(item.wikipedia_urls)
        for lang, summary in summaries.items():
            descriptions[lang] = summary.extract
            wikipedia_urls[lang] = summary.url
        return WikidataHeritage(
            qid=item.qid,
            names=item.names,
            aliases=item.aliases,
            description=descriptions,
            country_code=item.country_code,
            instance_of=item.instance_of,
            latitude=item.latitude,
            longitude=item.longitude,
            inception_year=item.inception_year,
            image_url=item.image_url,
            wikipedia_urls=wikipedia_urls,
        )

    # ------------------------------------------------------------------
    # SQL helpers
    # ------------------------------------------------------------------

    async def _existing_id_for_qid(self, qid: str) -> UUID | None:
        row = (
            await self._session.execute(
                text("SELECT id FROM heritage_objects WHERE wikidata_qid = :q LIMIT 1"),
                {"q": qid},
            )
        ).one_or_none()
        return row[0] if row else None

    async def _wikidata_provenance_id(self) -> UUID:
        row = (
            await self._session.execute(
                text("SELECT id FROM heritage_provenance WHERE slug = 'wikidata' LIMIT 1"),
            )
        ).one_or_none()
        if row is None:
            raise RuntimeError(
                "wikidata heritage_provenance row missing — migration 0011 seed not applied"
            )
        return row[0]

    async def _insert_heritage(
        self,
        *,
        item: WikidataHeritage,
        kind_slug: str,
        actor: UUID,
    ) -> UUID:
        pub_id = _generate_pub_id()
        # Use the same retry strategy as the heritage service to avoid pub_id
        # collisions. 5 attempts is plenty given 64-bit secrets.
        for _ in range(5):
            try:
                row = (
                    await self._session.execute(
                        text(
                            """
                            INSERT INTO heritage_objects (
                                tenant_id, pub_id, kind_slug,
                                name, summary_md, description_md, tags,
                                country_code, latitude, longitude,
                                period_start_year, status, created_by, updated_by,
                                wikidata_qid, wikipedia_url_by_lang, confidence_score
                            ) VALUES (
                                :tenant, :pub_id, :kind,
                                CAST(:name AS jsonb),
                                '{}'::jsonb,
                                CAST(:description AS jsonb),
                                ARRAY[]::text[],
                                :country, :lat, :lng,
                                :start_year, 'draft', :actor, :actor,
                                :qid, CAST(:urls AS jsonb), :confidence
                            )
                            RETURNING id
                            """
                        ),
                        {
                            "tenant": self._tenant_id,
                            "pub_id": pub_id,
                            "kind": kind_slug,
                            "name": _json_dump(item.names),
                            "description": _json_dump(item.description),
                            "country": item.country_code,
                            "lat": item.latitude,
                            "lng": item.longitude,
                            "start_year": item.inception_year,
                            "actor": actor,
                            "qid": item.qid,
                            "urls": _json_dump(item.wikipedia_urls),
                            "confidence": 60,
                        },
                    )
                ).one()
                return row[0]
            except Exception as exc:  # pragma: no cover - extremely rare
                if "pub_id" in str(exc).lower():
                    pub_id = _generate_pub_id()
                    continue
                raise
        raise RuntimeError("could not generate unique pub_id after 5 attempts")

    async def _insert_fact(
        self,
        *,
        heritage_id: UUID,
        provenance_id: UUID,
        predicate: str,
        value: Any,
        language_tag: str | None,
        confidence: int,
    ) -> None:
        # Supersede any prior winning fact from this same source for this
        # (heritage, predicate, language) tuple — Wikidata is authoritative
        # against itself, so we don't accumulate duplicates per re-import.
        await self._session.execute(
            text(
                """
                UPDATE heritage_facts
                SET is_winning = false,
                    superseded_at = now()
                WHERE heritage_id = :hid
                  AND predicate = :pred
                  AND COALESCE(language_tag, '') = COALESCE(:lang, '')
                  AND is_winning
                  AND superseded_at IS NULL
                """
            ),
            {"hid": heritage_id, "pred": predicate, "lang": language_tag},
        )
        fact_row = (
            await self._session.execute(
                text(
                    """
                    INSERT INTO heritage_facts (
                        heritage_id, predicate, object_value, language_tag,
                        confidence, is_winning, asserted_at
                    ) VALUES (
                        :hid, :pred, CAST(:value AS jsonb), :lang,
                        :conf, true, now()
                    )
                    RETURNING id
                    """
                ),
                {
                    "hid": heritage_id,
                    "pred": predicate,
                    "value": _json_dump(value),
                    "lang": language_tag,
                    "conf": confidence,
                },
            )
        ).one()
        await self._session.execute(
            text(
                """
                INSERT INTO fact_provenance (
                    fact_id, provenance_id, citation_detail, confidence
                ) VALUES (:fid, :pid, :cite, :conf)
                ON CONFLICT DO NOTHING
                """
            ),
            {
                "fid": fact_row[0],
                "pid": provenance_id,
                "cite": f"wikidata:{predicate}",
                "conf": confidence,
            },
        )

    async def _insert_aliases(
        self, *, heritage_id: UUID, item: WikidataHeritage, primary_lang: str
    ) -> int:
        written = 0
        # Treat every language label other than the chosen primary as an alias.
        for lang, label in item.names.items():
            if lang == primary_lang:
                continue
            await self._session.execute(
                text(
                    """
                    INSERT INTO heritage_aliases (
                        heritage_id, alias, language_tag, kind, confidence, source
                    ) VALUES (:hid, :alias, :lang, 'transliteration', :conf, :src)
                    ON CONFLICT DO NOTHING
                    """
                ),
                {
                    "hid": heritage_id,
                    "alias": label,
                    "lang": lang,
                    "conf": 75,
                    "src": f"wikidata:{item.qid}",
                },
            )
            written += 1
        # And any explicit ``also-known-as`` rows.
        for lang, text_value in item.aliases:
            await self._session.execute(
                text(
                    """
                    INSERT INTO heritage_aliases (
                        heritage_id, alias, language_tag, kind, confidence, source
                    ) VALUES (:hid, :alias, :lang, 'historical', :conf, :src)
                    ON CONFLICT DO NOTHING
                    """
                ),
                {
                    "hid": heritage_id,
                    "alias": text_value,
                    "lang": lang,
                    "conf": 70,
                    "src": f"wikidata:{item.qid}",
                },
            )
            written += 1
        return written

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def import_one(self, item: WikidataHeritage, *, requested_by: UUID) -> ImportResult:
        existing_id = await self._existing_id_for_qid(item.qid)
        if existing_id is not None:
            # Idempotent: we never insert a duplicate. We still refresh facts
            # so confidence and winning values stay current.
            facts = await self._refresh_facts(
                heritage_id=existing_id, item=await self._enrich_wikipedia(item)
            )
            await self._session.commit()
            return ImportResult(
                heritage_id=existing_id,
                pub_id=await self._pub_id_for(existing_id),
                qid=item.qid,
                created=False,
                facts_written=facts,
            )

        item = await self._enrich_wikipedia(item)
        kind_slug = _kind_from_instance_of(item.instance_of)
        primary_lang = "en" if "en" in item.names else next(iter(item.names), "en")
        heritage_id = await self._insert_heritage(
            item=item, kind_slug=kind_slug, actor=requested_by
        )
        facts = await self._refresh_facts(heritage_id=heritage_id, item=item)
        aliases = await self._insert_aliases(
            heritage_id=heritage_id, item=item, primary_lang=primary_lang
        )

        await self._emit_imported_event(heritage_id=heritage_id, item=item, kind_slug=kind_slug)
        await self._session.commit()

        return ImportResult(
            heritage_id=heritage_id,
            pub_id=await self._pub_id_for(heritage_id),
            qid=item.qid,
            created=True,
            facts_written=facts,
            aliases_written=aliases,
        )

    async def _pub_id_for(self, heritage_id: UUID) -> str:
        row = (
            await self._session.execute(
                text("SELECT pub_id FROM heritage_objects WHERE id = :hid"),
                {"hid": heritage_id},
            )
        ).one()
        return row[0]

    async def _refresh_facts(self, *, heritage_id: UUID, item: WikidataHeritage) -> int:
        provenance_id = await self._wikidata_provenance_id()
        written = 0
        for lang, label in item.names.items():
            await self._insert_fact(
                heritage_id=heritage_id,
                provenance_id=provenance_id,
                predicate=f"name.{lang}",
                value=label,
                language_tag=lang,
                confidence=_BASE_CONFIDENCE["name"],
            )
            written += 1
        for lang, descr in item.description.items():
            await self._insert_fact(
                heritage_id=heritage_id,
                provenance_id=provenance_id,
                predicate=f"description.{lang}",
                value=descr,
                language_tag=lang,
                confidence=_BASE_CONFIDENCE["description"],
            )
            written += 1
        if item.country_code:
            await self._insert_fact(
                heritage_id=heritage_id,
                provenance_id=provenance_id,
                predicate="country",
                value=item.country_code,
                language_tag=None,
                confidence=_BASE_CONFIDENCE["country"],
            )
            written += 1
        if item.latitude is not None and item.longitude is not None:
            await self._insert_fact(
                heritage_id=heritage_id,
                provenance_id=provenance_id,
                predicate="coordinates",
                value={"lat": item.latitude, "lng": item.longitude},
                language_tag=None,
                confidence=_BASE_CONFIDENCE["coordinates"],
            )
            written += 1
        if item.inception_year is not None:
            await self._insert_fact(
                heritage_id=heritage_id,
                provenance_id=provenance_id,
                predicate="inception_year",
                value=item.inception_year,
                language_tag=None,
                confidence=_BASE_CONFIDENCE["inception_year"],
            )
            written += 1
        if item.image_url:
            await self._insert_fact(
                heritage_id=heritage_id,
                provenance_id=provenance_id,
                predicate="image_url",
                value=item.image_url,
                language_tag=None,
                confidence=_BASE_CONFIDENCE["image"],
            )
            written += 1
        return written

    async def _emit_imported_event(
        self, *, heritage_id: UUID, item: WikidataHeritage, kind_slug: str
    ) -> None:
        # Best-effort: skip if the registry doesn't carry the event yet.
        registered = (
            await self._session.execute(
                text(
                    "SELECT 1 FROM event_types WHERE event_name = 'heritage.imported.v1' "
                    "AND NOT is_deprecated LIMIT 1"
                )
            )
        ).scalar_one_or_none()
        if registered is None:
            return
        await self._session.execute(
            text(
                """
                SELECT app.emit_event(
                    :tenant, 'heritage.imported.v1', 'heritage', :hid,
                    CAST(:payload AS jsonb)
                )
                """
            ),
            {
                "tenant": self._tenant_id,
                "hid": heritage_id,
                "payload": _json_dump(
                    {
                        "qid": item.qid,
                        "kind_slug": kind_slug,
                        "source": "wikidata",
                        "country_code": item.country_code,
                    }
                ),
            },
        )

    async def import_batch(
        self,
        *,
        country_code: str,
        limit: int = 50,
        requested_by: UUID,
    ) -> ImportBatchResult:
        discovered = await self.discover(country_code, limit=limit)
        result = ImportBatchResult(discovered=len(discovered))
        for item in discovered:
            try:
                outcome = await self.import_one(item, requested_by=requested_by)
                result.items.append(outcome)
                if outcome.created:
                    result.created += 1
                else:
                    result.skipped += 1
            except Exception as exc:
                log.warning("ingestion.import_failed", qid=item.qid, error=str(exc))
                result.failed += 1
                await self._session.rollback()
        return result
