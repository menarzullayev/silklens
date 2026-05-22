"""Internationalization support endpoints. SILK-0079.

GET /v1/languages        — list supported languages from the registry (public)
GET /v1/languages/{tag}  — get details for a single BCP-47 language tag (public)
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session

router = APIRouter(tags=["i18n"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


# --- Response models -------------------------------------------------------


class LanguageOut(BaseModel):
    bcp47_tag: str
    endonym: str | None
    exonym_en: str | None
    is_rtl: bool
    is_active: bool
    sort_order: int | None
    nllb_code: str | None
    deepl_code: str | None
    google_code: str | None


# --- Routes ----------------------------------------------------------------


@router.get(
    "/v1/languages",
    response_model=list[LanguageOut],
    status_code=status.HTTP_200_OK,
)
async def list_supported_languages(
    session: SessionDep,
    active_only: bool = Query(default=True),
) -> list[LanguageOut]:
    """List supported languages from the languages registry. Public endpoint."""
    rows = await session.execute(
        text("""
            SELECT bcp47_tag, endonym, exonym_en, is_rtl, is_active, sort_order,
                   nllb_code, deepl_code, google_code
            FROM languages
            WHERE (:active_only = false OR is_active = true)
            ORDER BY sort_order
        """),
        {"active_only": active_only},
    )
    return [LanguageOut.model_validate(dict(r)) for r in rows.mappings().fetchall()]


@router.get(
    "/v1/languages/{tag}",
    response_model=LanguageOut,
    status_code=status.HTTP_200_OK,
)
async def get_language(
    tag: str,
    session: SessionDep,
) -> LanguageOut:
    """Get details for a specific language by BCP-47 tag. Public endpoint."""
    row = await session.execute(
        text("""
            SELECT bcp47_tag, endonym, exonym_en, is_rtl, is_active, sort_order,
                   nllb_code, deepl_code, google_code
            FROM languages
            WHERE bcp47_tag = :tag
        """),
        {"tag": tag.lower()},
    )
    data = row.mappings().fetchone()
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "language.not_found", "message": f"Language '{tag}' not found"},
        )
    return LanguageOut.model_validate(dict(data))
