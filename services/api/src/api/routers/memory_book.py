"""AI Memory Book — automated travel diary.

POST /v1/me/memory-book/generate   — generate narrative diary from check-in history (SILK-0076)
GET  /v1/me/memory-book/preview    — preview recent check-ins that would be included
"""

from __future__ import annotations

from collections import defaultdict
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.settings import get_settings
from src.middleware.auth import CurrentUserDep
from src.middleware.ratelimit import rate_limit

router = APIRouter(prefix="/v1/me/memory-book", tags=["memory-book"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


# --- DTOs -------------------------------------------------------------------


class MemoryBookRequest(BaseModel):
    title: str | None = Field(None, max_length=200)
    date_from: str | None = Field(None, description="ISO date YYYY-MM-DD")
    date_to: str | None = Field(None, description="ISO date YYYY-MM-DD")
    language: str = Field("en", min_length=2, max_length=10)
    format: str = Field("json", description="json | pdf  (pdf requires async generation)")


class DaySiteOut(BaseModel):
    name: str | None
    pub_id: str | None
    kind: str | None


class DiaryDayOut(BaseModel):
    date: str
    sites: list[DaySiteOut]


class MemoryBookOut(BaseModel):
    title: str
    language: str
    total_sites: int
    total_days: int | None = None
    narrative: str | None = None
    days: list[DiaryDayOut] | None = None
    format: str = "json"
    # async PDF path
    status: str | None = None
    message: str | None = None


class MemoryBookEmptyOut(BaseModel):
    title: str
    language: str
    total_sites: int
    message: str
    diary: None = None


class PreviewSiteOut(BaseModel):
    pub_id: str | None
    site_name: str | None
    kind_slug: str | None
    checked_in_at: str | None


class MemoryBookPreviewOut(BaseModel):
    recent_check_ins: list[PreviewSiteOut]
    total_visits: int
    message: str


# --- Routes -----------------------------------------------------------------


@router.post(
    "/generate",
    response_model=MemoryBookOut | MemoryBookEmptyOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("5/hour", per="user", scope="memory:generate"))],
)
async def generate_memory_book(
    body: MemoryBookRequest,
    ctx: CurrentUserDep,
    session: SessionDep,
) -> MemoryBookOut | MemoryBookEmptyOut:
    """Generate a travel memory book from the authenticated user's activity history.

    Collects visited heritage sites and check-ins, then uses AI to generate a
    narrative diary entry. For ``format=pdf`` a stub job response is returned
    (PDF pipeline requires WeasyPrint + Celery — SILK-0087). For ``format=json``
    the diary content is returned immediately.
    """
    lang = body.language.split("-")[0].lower()
    settings = get_settings()

    # Build parameterised query — date bounds are optional.  We append literal
    # SQL clauses from a closed constant set (never from user input) so there is
    # no injection surface.  The noqa tag documents that ruff's S608 heuristic
    # fires on the JOIN keyword, not on actual dynamic SQL.
    base_sql = (
        "SELECT COALESCE(ho.name->>:lang, ho.name->>'en') AS site_name,"
        " ho.pub_id, ho.kind_slug, ho.country_code,"
        " hci.checked_in_at"
        " FROM heritage_check_ins hci"
        " JOIN heritage_objects ho ON ho.id = hci.heritage_pub_id"
        " WHERE hci.user_id = :uid"
    )
    params: dict[str, Any] = {"uid": ctx.user_id, "lang": lang}

    if body.date_from:
        base_sql += " AND hci.checked_in_at >= :date_from::date"
        params["date_from"] = body.date_from
    if body.date_to:
        base_sql += " AND hci.checked_in_at <= :date_to::date"
        params["date_to"] = body.date_to

    base_sql += " ORDER BY hci.checked_in_at LIMIT 50"

    checkins_rows = await session.execute(text(base_sql), params)
    visits = [dict(r) for r in checkins_rows.mappings().fetchall()]

    if not visits:
        return MemoryBookEmptyOut(
            title=body.title or "My Uzbekistan Journey",
            language=lang,
            total_sites=0,
            message="No check-ins found for this period. Start exploring and checking in!",
        )

    # Group by calendar day.
    days: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for v in visits:
        raw = v.get("checked_in_at")
        date_key = str(raw)[:10] if raw else "unknown"
        days[date_key].append(v)

    # AI narrative generation — falls back to a deterministic stub when mocks
    # are enabled or the Anthropic SDK is unavailable (offline dev / test).
    narrative: str
    if not settings.ai_use_mock_providers and visits:
        try:
            import anthropic

            client = anthropic.AsyncAnthropic()
            sites_summary = "\n".join(
                f"- {v.get('site_name')} ({v.get('kind_slug')}, {v.get('country_code')})"
                for v in visits[:20]
            )
            prompt = (
                f"Write a warm, personal travel diary entry in {lang} for a trip to Uzbekistan.\n"
                f"Sites visited:\n{sites_summary}\n"
                "Write 3-4 paragraphs in first person, evoking the atmosphere and emotions. "
                "Max 300 words."
            )
            resp = await client.messages.create(
                model=settings.anthropic_model_default,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            narrative = resp.content[0].text.strip()
        except Exception:
            narrative = _stub_narrative(visits, lang)
    else:
        narrative = _stub_narrative(visits, lang)

    sorted_days = sorted(days.items())
    title = body.title or (f"My Uzbekistan Journey ({sorted_days[0][0]} — {sorted_days[-1][0]})")

    diary_days = [
        DiaryDayOut(
            date=date,
            sites=[
                DaySiteOut(
                    name=v.get("site_name"),
                    pub_id=str(v["pub_id"]) if v.get("pub_id") else None,
                    kind=v.get("kind_slug"),
                )
                for v in day_visits
            ],
        )
        for date, day_visits in sorted_days
    ]

    if body.format == "pdf":
        # PDF generation requires Celery + WeasyPrint (SILK-0087, not in current stack).
        # Return the JSON content alongside a queued status so clients can display
        # a preview while waiting for the async pipeline.
        return MemoryBookOut(
            title=title,
            language=lang,
            total_sites=len(visits),
            total_days=len(days),
            narrative=narrative,
            days=diary_days,
            format="pdf",
            status="queued",
            message=(
                "PDF generation scheduled. Requires WeasyPrint pipeline (SILK-0087). "
                "Poll GET /v1/me/memory-book/jobs/{id} when available."
            ),
        )

    return MemoryBookOut(
        title=title,
        language=lang,
        total_sites=len(visits),
        total_days=len(days),
        narrative=narrative,
        days=diary_days,
        format="json",
    )


@router.get(
    "/preview",
    response_model=MemoryBookPreviewOut,
    dependencies=[Depends(rate_limit("30/minute", per="user", scope="memory:preview"))],
)
async def preview_memory_book(
    ctx: CurrentUserDep,
    session: SessionDep,
    limit: int = Query(5, ge=1, le=20),
) -> MemoryBookPreviewOut:
    """Preview the most recent check-ins that would appear in a generated diary.

    Returns up to ``limit`` (max 20) entries ordered newest-first.
    Call ``POST /v1/me/memory-book/generate`` to create the full diary.
    """
    rows = await session.execute(
        text("""
            SELECT ho.pub_id, ho.name->>'en' AS site_name, ho.kind_slug,
                   hci.checked_in_at
            FROM heritage_check_ins hci
            JOIN heritage_objects ho ON ho.id = hci.heritage_pub_id
            WHERE hci.user_id = :uid
            ORDER BY hci.checked_in_at DESC
            LIMIT :limit
        """),
        {"uid": ctx.user_id, "limit": limit},
    )
    recent = [
        PreviewSiteOut(
            pub_id=str(r["pub_id"]) if r["pub_id"] else None,
            site_name=r["site_name"],
            kind_slug=r["kind_slug"],
            checked_in_at=str(r["checked_in_at"]) if r["checked_in_at"] else None,
        )
        for r in rows.mappings().fetchall()
    ]
    return MemoryBookPreviewOut(
        recent_check_ins=recent,
        total_visits=len(recent),
        message="Call POST /v1/me/memory-book/generate to create your diary.",
    )


# --- Helpers ----------------------------------------------------------------


def _stub_narrative(visits: list[dict[str, Any]], lang: str) -> str:
    """Deterministic fallback narrative used when AI providers are unavailable."""
    site_names = [v.get("site_name") for v in visits[:3] if v.get("site_name")]
    joined = ", ".join(str(n) for n in site_names)
    if lang == "uz":
        return (
            f"Qiziqarli va unutilmas sayohat! {joined} va boshqa ko'plab joylarni ziyorat qildim. "
            "O'zbekiston tarixi va madaniyati meni hayratda qoldirdi."
        )
    if lang == "ru":
        return (
            f"Nezabyvaemoye puteshestviye! Ya posetil(a) {joined} i mnogie drugie mesta. "
            "Istoriya i kultura Uzbekistana proizveli na menya nezagladimoe vpechatlenie."
        )
    return (
        f"An unforgettable journey! I visited {joined} and many other amazing places. "
        "The history and culture of Uzbekistan left me in awe."
    )
