"""Cultural tips and etiquette guidelines. SILK-0069.

Public read-only endpoints that serve admin-managed cultural etiquette cards
to the mobile app. No authentication required.

Endpoints:
  GET /v1/cultural-tips              — list tips for a country + optional context/kind filter
  GET /v1/heritage/{pub_id}/cultural-tips — tips relevant to a specific heritage site
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session

router = APIRouter(tags=["cultural"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


# --- Response schema ---------------------------------------------------------


class CulturalTipOut(BaseModel):
    id: UUID
    country_code: str
    context: str
    kind: str
    severity: str
    title: str
    body_md: str


class HeritageCulturalTipOut(BaseModel):
    id: UUID
    context: str
    kind: str
    severity: str
    title: str
    body_md: str


# --- Routes ------------------------------------------------------------------


@router.get(
    "/v1/cultural-tips",
    response_model=list[CulturalTipOut],
    summary="List cultural etiquette tips",
)
async def list_cultural_tips(
    session: SessionDep,
    country_code: Annotated[
        str,
        Query(min_length=2, max_length=2, description="ISO-3166-1 alpha-2 country code"),
    ] = "UZ",
    language: Annotated[
        str,
        Query(min_length=2, max_length=10, description="BCP-47 language tag, e.g. en, uz, ru"),
    ] = "en",
    context: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=50,
            description=(
                "mosque | bazaar | restaurant | home_visit | "
                "general | dress_code | archaeological_site"
            ),
        ),
    ] = None,
    kind: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=30,
            description="dress_code | behavior | prohibited | recommended | greeting",
        ),
    ] = None,
) -> list[CulturalTipOut]:
    """Public cultural etiquette tips for a country and optional context/kind.

    No authentication required. Results are ordered by sort_order then context
    then kind. JSONB title/body_md fall back to English when the requested
    language key is absent.
    """
    country = country_code.upper()
    lang = language.split("-")[0].lower()

    rows = await session.execute(
        text(
            """
            SELECT
                id,
                country_code,
                context,
                kind,
                severity,
                COALESCE(title   ->> :lang, title   ->>'en') AS title,
                COALESCE(body_md ->> :lang, body_md ->>'en') AS body_md
            FROM cultural_tips
            WHERE country_code = :country
              AND is_active = true
              AND (:context IS NULL OR context = :context)
              AND (:kind IS NULL OR kind = :kind)
            ORDER BY sort_order, context, kind
            """
        ),
        {"country": country, "lang": lang, "context": context, "kind": kind},
    )
    return [
        CulturalTipOut(
            id=r._mapping["id"],
            country_code=r._mapping["country_code"],
            context=r._mapping["context"],
            kind=r._mapping["kind"],
            severity=r._mapping["severity"],
            title=r._mapping["title"] or "",
            body_md=r._mapping["body_md"] or "",
        )
        for r in rows.all()
    ]


@router.get(
    "/v1/heritage/{pub_id}/cultural-tips",
    response_model=list[HeritageCulturalTipOut],
    summary="Cultural tips for a heritage site",
)
async def heritage_cultural_tips(
    pub_id: str,
    session: SessionDep,
    language: Annotated[
        str,
        Query(min_length=2, max_length=10, description="BCP-47 language tag"),
    ] = "en",
) -> list[HeritageCulturalTipOut]:
    """Cultural tips relevant to a specific heritage object.

    Returns tips that are either directly pinned to the heritage object via
    heritage_pub_id, or that match the object's country_code + a context
    derived from the object's kind_slug (mosque/mausoleum → mosque,
    bazaar → bazaar, everything else → general). Capped at 10 rows.
    No authentication required.
    """
    lang = language.split("-")[0].lower()

    rows = await session.execute(
        text(
            """
            SELECT
                ct.id,
                ct.context,
                ct.kind,
                ct.severity,
                COALESCE(ct.title   ->> :lang, ct.title   ->>'en') AS title,
                COALESCE(ct.body_md ->> :lang, ct.body_md ->>'en') AS body_md
            FROM cultural_tips ct
            JOIN heritage_objects ho
              ON ho.pub_id = :pub_id
            WHERE ct.is_active = true
              AND (
                  ct.heritage_pub_id = ho.id
                  OR (
                      ct.heritage_pub_id IS NULL
                      AND ct.country_code = ho.country_code
                      AND ct.context = CASE ho.kind_slug
                          WHEN 'mosque'     THEN 'mosque'
                          WHEN 'mausoleum'  THEN 'mosque'
                          WHEN 'bazaar'     THEN 'bazaar'
                          ELSE 'general'
                      END
                  )
              )
            ORDER BY ct.sort_order
            LIMIT 10
            """
        ),
        {"pub_id": pub_id, "lang": lang},
    )
    return [
        HeritageCulturalTipOut(
            id=r._mapping["id"],
            context=r._mapping["context"],
            kind=r._mapping["kind"],
            severity=r._mapping["severity"],
            title=r._mapping["title"] or "",
            body_md=r._mapping["body_md"] or "",
        )
        for r in rows.all()
    ]
