"""Public search endpoint.

Routes:
    GET /v1/search?q=...&lang=uz&country=UZ&kind=madrasa&limit=20

Backed by Elasticsearch (per Agent 7 §9). The implementation:

  1. Normalises the query (NFC + lowercase) and routes to the per-language
     tier-1 index (or the shared tier-2 intl index for unsupported langs).
  2. Builds a ``multi_match`` query across ``name``, ``summary_md`` and the
     nested ``aliases.alias`` field with field boosts per §9.1.
  3. Applies filter clauses for kind_slug / country_code.
  4. On zero hits, upserts ``search_zero_results`` for gap analysis.
  5. Always appends an anonymous row to ``search_query_log`` (Daily-partitioned
     by ``occurred_at``).

The handler is resilient to ES being offline — it returns an empty page
instead of a 500. This keeps the public API surface available during
degraded operations (the admin alerts via the bulk_reindex job error count).
"""

from __future__ import annotations

import unicodedata
import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.logging import get_logger
from src.infrastructure.search.es_client import (
    ElasticsearchClient,
    ElasticsearchUnavailable,
    get_es_client,
)
from src.infrastructure.search.mappings import INTL_INDEX, resolve_index

router = APIRouter(prefix="/v1/search", tags=["search"])
log = get_logger("silklens.search.router")

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _es_dependency() -> ElasticsearchClient:
    return get_es_client()


EsDep = Annotated[ElasticsearchClient, Depends(_es_dependency)]


def _normalise(query: str) -> str:
    return unicodedata.normalize("NFC", query).strip().lower()


# --- Schemas --------------------------------------------------------------


class SearchHit(BaseModel):
    heritage_id: str
    pub_id: str
    name: str
    summary_md: str = ""
    kind_slug: str | None = None
    country_code: str | None = None
    lat: float | None = None
    lng: float | None = None
    score: float
    confidence_score: int | None = None


class SuggestionEntry(BaseModel):
    text: str
    score: float


class SearchResponse(BaseModel):
    query: str
    language_tag: str
    total: int
    hits: list[SearchHit]
    suggestions: list[SuggestionEntry] = Field(default_factory=list)


# --- Implementation -------------------------------------------------------


def _build_query(
    *,
    query: str,
    kind_slug: str | None,
    country_code: str | None,
    limit: int,
) -> dict[str, Any]:
    must: list[dict[str, Any]] = [
        {
            "bool": {
                "should": [
                    {
                        "multi_match": {
                            "query": query,
                            "fields": [
                                "name^4",
                                "summary_md^1",
                                "description_md^0.5",
                            ],
                            "type": "best_fields",
                            "fuzziness": "AUTO",
                        }
                    },
                    {
                        "nested": {
                            "path": "aliases",
                            "query": {"match": {"aliases.alias": {"query": query}}},
                            "score_mode": "max",
                        }
                    },
                ],
                "minimum_should_match": 1,
            }
        }
    ]
    filters: list[dict[str, Any]] = []
    if kind_slug:
        filters.append({"term": {"kind_slug": kind_slug}})
    if country_code:
        filters.append({"term": {"country_code": country_code.upper()}})
    body: dict[str, Any] = {
        "size": limit,
        "query": {"bool": {"must": must, "filter": filters}},
        "suggest": {
            "did_you_mean": {
                "text": query,
                "term": {"field": "name", "suggest_mode": "popular"},
            }
        },
    }
    return body


def _to_hit(raw: dict[str, Any]) -> SearchHit:
    src = raw.get("_source", {})
    return SearchHit(
        heritage_id=str(src.get("heritage_id", raw.get("_id", ""))),
        pub_id=str(src.get("pub_id", "")),
        name=str(src.get("name", "")),
        summary_md=str(src.get("summary_md", "")),
        kind_slug=src.get("kind_slug"),
        country_code=src.get("country_code"),
        lat=src.get("lat"),
        lng=src.get("lng"),
        score=float(raw.get("_score", 0.0)),
        confidence_score=src.get("confidence_score"),
    )


def _extract_suggestions(es_response: dict[str, Any]) -> list[SuggestionEntry]:
    suggest_block = es_response.get("suggest", {}).get("did_you_mean", [])
    entries: list[SuggestionEntry] = []
    for item in suggest_block:
        for option in item.get("options", []):
            entries.append(
                SuggestionEntry(text=str(option["text"]), score=float(option.get("score", 0.0)))
            )
    return entries


async def _log_query(
    db: AsyncSession,
    *,
    query: str,
    language_tag: str,
    result_count: int,
    session_id: uuid.UUID,
) -> None:
    try:
        await db.execute(
            text(
                """
                INSERT INTO search_query_log
                    (query_text, language_tag, result_count, session_id, occurred_at)
                VALUES (:q, :lang, :count, :sid, :ts)
                """
            ),
            {
                "q": query[:1024],
                "lang": language_tag,
                "count": result_count,
                "sid": session_id,
                "ts": datetime.now(),
            },
        )
    except Exception as exc:
        # The daily partition may not exist for "today + N" outside our seeded
        # window. Tolerate that — telemetry is best-effort.
        log.debug("search.query_log_failed", error=str(exc))
        await db.rollback()
        return

    if result_count == 0:
        normalised = _normalise(query)[:512]
        if normalised:
            await db.execute(
                text(
                    """
                    INSERT INTO search_zero_results
                        (query_normalized, language_tag, occurrences, last_seen_at)
                    VALUES (:q, :lang, 1, now())
                    ON CONFLICT (query_normalized, language_tag) DO UPDATE
                    SET occurrences = search_zero_results.occurrences + 1,
                        last_seen_at = now()
                    """
                ),
                {"q": normalised, "lang": language_tag},
            )
    await db.commit()


# --- Route ---------------------------------------------------------------


@router.get("", response_model=SearchResponse)
async def search(
    db: SessionDep,
    es: EsDep,
    q: Annotated[str, Query(min_length=1, max_length=256, alias="q")],
    lang: Annotated[str, Query(min_length=2, max_length=16)] = "en",
    country: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
    kind: Annotated[str | None, Query(min_length=1, max_length=64)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> SearchResponse:
    primary = lang.split("-")[0].lower()
    index_name = resolve_index(primary)
    query_str = _normalise(q)

    body = _build_query(query=query_str, kind_slug=kind, country_code=country, limit=limit)
    if index_name == INTL_INDEX:
        # Filter by locale on the shared intl index so users on `fa` don't
        # see hits from `ja` etc.
        body["query"]["bool"]["filter"].append({"term": {"locale": primary}})

    try:
        es_response = await es.search(index=index_name, body=body)
    except ElasticsearchUnavailable as exc:
        log.warning("search.es_unavailable", error=str(exc))
        es_response = {"hits": {"total": {"value": 0}, "hits": []}, "suggest": {}}

    raw_hits = es_response.get("hits", {}).get("hits", [])
    total_block = es_response.get("hits", {}).get("total", {})
    total = int(total_block.get("value", 0)) if isinstance(total_block, dict) else int(total_block)

    hits = [_to_hit(h) for h in raw_hits]
    suggestions = _extract_suggestions(es_response) if total == 0 else []

    # Anonymous session id — we never persist user identity here.
    await _log_query(
        db,
        query=q,
        language_tag=primary,
        result_count=total,
        session_id=uuid.uuid4(),
    )

    return SearchResponse(
        query=q,
        language_tag=primary,
        total=total,
        hits=hits,
        suggestions=suggestions,
    )
