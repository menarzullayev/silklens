"""Kids Mode — simplified heritage content for children. SILK-0068."""

from __future__ import annotations

from typing import Annotated, TypedDict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.settings import get_settings
from src.middleware.auth import CurrentUserDep
from src.middleware.ratelimit import rate_limit

router = APIRouter(tags=["kids"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


# --- Internal types --------------------------------------------------------


class _QuizEntry(TypedDict):
    question: dict[str, str]
    options: dict[str, list[str]]
    correct_index: int
    fun_fact: dict[str, str]


# --- Response models -------------------------------------------------------


class KidsModeStatusResponse(BaseModel):
    kids_mode: bool
    message: str | None = None


class HeritageKidsStoryResponse(BaseModel):
    heritage_pub_id: str
    language: str
    story: str
    reading_level: str
    source: str


class KidsQuizResponse(BaseModel):
    language: str
    question: str
    options: list[str]
    correct_index: int
    fun_fact: str


# --- Routes ----------------------------------------------------------------


@router.post(
    "/v1/me/kids-mode/enable",
    response_model=KidsModeStatusResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(rate_limit("30/minute", per="user", scope="kids:toggle")),
    ],
)
async def enable_kids_mode(
    ctx: CurrentUserDep,
    session: SessionDep,
) -> KidsModeStatusResponse:
    """Enable kids mode on the authenticated user's profile.

    Sets ``user_profiles.kids_mode = true``, which causes content
    endpoints to return age-appropriate simplified material.
    """
    await session.execute(
        text("""
            UPDATE user_profiles
            SET kids_mode = true, updated_at = now()
            WHERE user_id = :uid
              AND residency_region = :region
        """),
        {"uid": ctx.user_id, "region": ctx.residency_region.value},
    )
    await session.commit()
    return KidsModeStatusResponse(
        kids_mode=True,
        message="Kids mode enabled. Content will be simplified for children.",
    )


@router.post(
    "/v1/me/kids-mode/disable",
    response_model=KidsModeStatusResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(rate_limit("30/minute", per="user", scope="kids:toggle")),
    ],
)
async def disable_kids_mode(
    ctx: CurrentUserDep,
    session: SessionDep,
) -> KidsModeStatusResponse:
    """Disable kids mode on the authenticated user's profile."""
    await session.execute(
        text("""
            UPDATE user_profiles
            SET kids_mode = false, updated_at = now()
            WHERE user_id = :uid
              AND residency_region = :region
        """),
        {"uid": ctx.user_id, "region": ctx.residency_region.value},
    )
    await session.commit()
    return KidsModeStatusResponse(kids_mode=False)


@router.get(
    "/v1/heritage/{pub_id}/kids-story",
    response_model=HeritageKidsStoryResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(rate_limit("30/minute", per="ip", scope="kids:story")),
    ],
)
async def heritage_kids_story(
    pub_id: str,
    session: SessionDep,
    language: str = "en",
) -> HeritageKidsStoryResponse:
    """Get a child-friendly simplified story for a heritage site.

    First checks ``heritage_facts`` for predicate ``kids_story``. If not
    found, generates a simplified version via AI (or returns a friendly stub).
    Public endpoint — no auth required.
    """
    lang = language.split("-")[0].lower()
    settings = get_settings()

    # 1. Check for pre-generated kids story in heritage_facts
    stored = await session.execute(
        text("""
            SELECT COALESCE(
                hf.object_value->>:lang,
                hf.object_value->>'en',
                hf.object_text
            ) AS story
            FROM heritage_facts hf
            JOIN heritage_objects ho ON ho.id = hf.heritage_id
            WHERE ho.pub_id = :pub_id
              AND ho.deleted_at IS NULL
              AND hf.predicate = 'kids_story'
            LIMIT 1
        """),
        {"pub_id": pub_id, "lang": lang},
    )
    row = stored.mappings().fetchone()
    if row and row.get("story"):
        return HeritageKidsStoryResponse(
            heritage_pub_id=pub_id,
            language=lang,
            story=row["story"],
            reading_level="kids",
            source="curated",
        )

    # 2. Fetch heritage name + description for AI simplification
    heritage_row = await session.execute(
        text("""
            SELECT
                COALESCE(name->>:lang, name->>'en') AS name,
                COALESCE(summary_md->>:lang, summary_md->>'en') AS summary,
                kind_slug, country_code
            FROM heritage_objects
            WHERE pub_id = :pub_id AND deleted_at IS NULL AND status = 'published'
        """),
        {"pub_id": pub_id, "lang": lang},
    )
    heritage = heritage_row.mappings().fetchone()
    if not heritage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "heritage.not_found", "message": "Heritage site not found"},
        )

    # 3. Generate kids story — curated stub or AI-generated
    site_name: str = heritage.get("name") or "this amazing place"
    summary: str = heritage.get("summary") or ""

    if settings.ai_use_mock_providers:
        story = (
            f"Hello, little explorer! Today we visit **{site_name}**!\n\n"
            f"This magical place was built a very long time ago by clever people who "
            f"wanted to create something beautiful for everyone to enjoy. "
            f"Can you imagine what it was like to live here hundreds of years ago?\n\n"
            f"Fun fact: People from all over the world still come to see it today!"
        )
    else:
        try:
            import anthropic

            client = anthropic.AsyncAnthropic()
            prompt = (
                f"Write a fun, engaging story about '{site_name}' for children aged 7-12. "
                f"Background: {summary[:300]}\n"
                f"Language: {lang}\n"
                f"Requirements:\n"
                f"- Use simple words, short sentences\n"
                f"- Add 2-3 emoji\n"
                f"- Include 1 interesting fun fact\n"
                f"- Max 150 words\n"
                f"- Exciting and encouraging tone"
            )
            from anthropic.types import TextBlock as _TextBlock

            resp = await client.messages.create(
                model=settings.anthropic_model_default,
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
            text_blocks = [b for b in resp.content if isinstance(b, _TextBlock)]
            if not text_blocks:
                raise ValueError("no text block in response")
            story = text_blocks[0].text.strip()
        except Exception:
            story = (
                f"Welcome to {site_name}! This amazing place has a wonderful history "
                f"waiting to be discovered. Ask a grown-up to tell you more!"
            )

    return HeritageKidsStoryResponse(
        heritage_pub_id=pub_id,
        language=lang,
        story=story,
        reading_level="kids",
        source="ai_generated",
    )


@router.get(
    "/v1/kids/quiz",
    response_model=KidsQuizResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(rate_limit("30/minute", per="ip", scope="kids:quiz")),
    ],
)
async def kids_quiz(
    language: str = "en",
) -> KidsQuizResponse:
    """Return a random fun quiz question about heritage sites for kids.

    Public endpoint — no auth required.
    """
    import random

    lang = language.split("-")[0].lower()

    quiz_bank: list[_QuizEntry] = [
        {
            "question": {
                "en": "What does UNESCO stand for?",
                "uz": "UNESCO nima?",
                "ru": "Что значит ЮНЕСКО?",
            },
            "options": {
                "en": [
                    "United Nations Educational, Scientific and Cultural Organization",
                    "United Nations Emergency Safety Council Operation",
                    "Universal National Education Standard Council Organization",
                ],
                "uz": [
                    "BMT Ta'lim, Fan va Madaniyat Tashkiloti",
                    "Qo'shilgan Millatlar Xavfsizlik Operatsiyasi",
                    "Universal Milliy Ta'lim Standart Kengashi",
                ],
                "ru": [
                    "Организация ООН по вопросам образования, науки и культуры",  # noqa: RUF001
                    "Чрезвычайная операция по безопасности ООН",  # noqa: RUF001
                    "Универсальный совет национальных образовательных стандартов",
                ],
            },
            "correct_index": 0,
            "fun_fact": {
                "en": "UNESCO protects over 1,100 World Heritage Sites worldwide!",
                "uz": "UNESCO dunyo bo'ylab 1100 dan ortiq meros joylarini himoya qiladi!",
                "ru": "ЮНЕСКО охраняет более 1100 объектов Всемирного наследия!",
            },
        },
        {
            "question": {
                "en": "The Registan in Samarkand has how many madrasas?",
                "uz": "Samarqand Registonida nechta madrasa bor?",
                "ru": "Сколько медресе на Регистане в Самарканде?",
            },
            "options": {
                "en": ["2", "3", "4", "5"],
                "uz": ["2", "3", "4", "5"],
                "ru": ["2", "3", "4", "5"],
            },
            "correct_index": 1,
            "fun_fact": {
                "en": "The three madrasas are Ulugbek, Tilya-Kori and Sher-Dor!",
                "uz": "Uch madrasa: Ulug'bek, Tillaqori va Sherdor!",
                "ru": "Три медресе: Улугбек, Тилля-Кари и Шер-Дор!",
            },
        },
    ]

    question = random.choice(quiz_bank)  # noqa: S311  # nosec B311
    return KidsQuizResponse(
        language=lang,
        question=question["question"].get(lang) or question["question"]["en"],
        options=question["options"].get(lang) or question["options"]["en"],
        correct_index=question["correct_index"],
        fun_fact=question["fun_fact"].get(lang) or question["fun_fact"]["en"],
    )
