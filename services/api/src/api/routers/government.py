"""Government Smart Mode — official info, laws, holidays. SILK-0086."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.middleware.ratelimit import rate_limit

SessionDep = Annotated[AsyncSession, Depends(get_session)]

router = APIRouter(tags=["government"])


@router.get("/v1/government")
async def list_government_info(
    session: SessionDep,
    country_code: str = Query("UZ", min_length=2, max_length=2),
    language: str = Query("en", min_length=2, max_length=10),
    kind: str | None = Query(
        None,
        description="holiday|law|visa_info|emergency|announcement",
    ),
    _rl: None = Depends(rate_limit("60/minute", per="ip", scope="government:list")),
) -> list[dict[str, Any]]:
    """Official government information for travelers. No auth required."""
    country = country_code.upper()
    lang = language.split("-")[0].lower()

    rows = await session.execute(
        text("""
            SELECT
                id, country_code, kind,
                COALESCE(title->>:lang, title->>'en') AS title,
                COALESCE(body_md->>:lang, body_md->>'en') AS body_md,
                source_url, effective_date, expires_date
            FROM government_info
            WHERE country_code = :country
              AND is_active = true
              AND (:kind IS NULL OR kind = :kind)
              AND (expires_date IS NULL OR expires_date >= CURRENT_DATE)
            ORDER BY sort_order, kind, created_at DESC
        """),
        {"country": country, "lang": lang, "kind": kind},
    )
    return [dict(r) for r in rows.mappings().fetchall()]
