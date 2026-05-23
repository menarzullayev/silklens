"""Local legends, myths and hidden stories for heritage sites. SILK-0081.

GET /v1/heritage/{pub_id}/stories — list stories for a site (public)
GET /v1/stories/random             — random legend by country (public)

Stories live in ``heritage_facts`` rows whose ``predicate`` is one of:
  local_legend | myth | oral_tradition | hidden_fact | historical_story

The ``value_jsonb`` column holds a JSON object keyed by BCP-47 language
subtag (e.g. ``{"en": "...", "uz": "...", "ru": "..."}``); the query
falls back to ``en`` then ``value_text`` when the requested language is
absent.

Both endpoints are public (no bearer required) and rate-limited per IP.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.middleware.ratelimit import rate_limit

router = APIRouter(tags=["storyteller"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

# The closed set of predicates that represent "story" content.
_STORY_PREDICATES = ("local_legend", "myth", "oral_tradition", "hidden_fact", "historical_story")
_STORY_PREDICATE_LIST = ", ".join(f"'{p}'" for p in _STORY_PREDICATES)


# --- Schemas ------------------------------------------------------------------


class StoryOut(BaseModel):
    id: str
    kind: str
    confidence: float | None
    story_text: str | None
    created_at: str


class RandomStoryOut(BaseModel):
    heritage_pub_id: str | None = None
    heritage_name: str | None = None
    kind: str | None = None
    story_text: str | None = None
    confidence: float | None = None
    message: str | None = None


# --- Routes -------------------------------------------------------------------


@router.get(
    "/v1/heritage/{pub_id}/stories",
    response_model=list[StoryOut],
    dependencies=[Depends(rate_limit("120/minute", per="ip", scope="stories:list"))],
)
async def list_heritage_stories(
    pub_id: str,
    session: SessionDep,
    language: str = Query("en", min_length=2, max_length=10),
    kind: str | None = Query(
        None,
        description=(
            "Filter by story type: local_legend | myth | oral_tradition"
            " | hidden_fact | historical_story"
        ),
    ),
) -> list[StoryOut]:
    """Return local legends and hidden stories for a heritage site.

    Stories are heritage_facts rows with a story predicate.  Results are
    ordered by confidence descending so the best-sourced stories appear first.
    No authentication required — stories are part of the public discovery layer.
    """
    lang = language.split("-")[0].lower()

    if kind is not None and kind not in _STORY_PREDICATES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "stories.invalid_kind",
                "message": f"kind must be one of: {', '.join(_STORY_PREDICATES)}",
            },
        )

    if kind is not None:
        predicate_clause = "AND hf.predicate = :kind"
        params: dict[str, Any] = {"pub_id": pub_id, "lang": lang, "kind": kind}
    else:
        predicate_clause = f"AND hf.predicate IN ({_STORY_PREDICATE_LIST})"
        params = {"pub_id": pub_id, "lang": lang}

    rows = await session.execute(
        text(
            f"""
            SELECT
                hf.id::text                             AS id,
                hf.predicate                            AS kind,
                hf.confidence,
                COALESCE(
                    hf.object_value->>:lang,
                    hf.object_value->>'en',
                    hf.object_text
                )                                       AS story_text,
                hf.asserted_at
            FROM heritage_facts  hf
            JOIN heritage_objects ho ON ho.id = hf.heritage_id
            WHERE ho.pub_id      = :pub_id
              AND ho.deleted_at  IS NULL
              {predicate_clause}
            ORDER BY hf.confidence DESC NULLS LAST, hf.asserted_at DESC
            LIMIT 20
            """  # noqa: S608 — predicate_clause is built from a closed set above
        ),
        params,
    )
    return [
        StoryOut(
            id=r._mapping["id"],
            kind=r._mapping["kind"],
            confidence=r._mapping["confidence"],
            story_text=r._mapping["story_text"],
            created_at=r._mapping["created_at"].isoformat(),
        )
        for r in rows.fetchall()
    ]


@router.get(
    "/v1/stories/random",
    response_model=RandomStoryOut,
    dependencies=[Depends(rate_limit("30/minute", per="ip", scope="stories:random"))],
)
async def random_story(
    session: SessionDep,
    language: str = Query("en", min_length=2, max_length=10),
    country_code: str = Query("UZ", min_length=2, max_length=2),
) -> RandomStoryOut:
    """Return a random local legend from a country. Great for discovery.

    ``country_code`` is ISO 3166-1 alpha-2 (e.g. ``UZ``, ``TR``, ``IN``).
    No authentication required.
    """
    lang = language.split("-")[0].lower()

    row = await session.execute(
        text(
            f"""
            SELECT
                ho.pub_id                                           AS heritage_pub_id,
                COALESCE(ho.name->>:lang, ho.name->>'en')          AS heritage_name,
                hf.predicate                                        AS kind,
                COALESCE(
                    hf.object_value->>:lang,
                    hf.object_value->>'en',
                    hf.object_text
                )                                                   AS story_text,
                hf.confidence
            FROM heritage_facts  hf
            JOIN heritage_objects ho ON ho.id = hf.heritage_id
            WHERE ho.country_code  = :country
              AND ho.deleted_at    IS NULL
              AND ho.status        = 'published'
              AND hf.predicate     IN ({_STORY_PREDICATE_LIST})
            ORDER BY RANDOM()
            LIMIT 1
            """  # noqa: S608 — predicate list is a closed constant
        ),
        {"lang": lang, "country": country_code.upper()},
    )
    result = row.mappings().fetchone()
    if not result:
        return RandomStoryOut(message="No stories found for this region yet.")
    return RandomStoryOut(
        heritage_pub_id=result["heritage_pub_id"],
        heritage_name=result["heritage_name"],
        kind=result["kind"],
        story_text=result["story_text"],
        confidence=result["confidence"],
    )
