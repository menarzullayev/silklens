"""Onboarding tutorial content endpoint.

SILK-0058: Serves static onboarding tutorial steps and a dynamic
pricing/plans overview pulled from the DB. No authentication required —
these endpoints are public so anonymous and pre-registration users can
view the app walkthrough.
"""

# ruff: noqa: RUF001  -- multilingual string literals (Cyrillic/CJK) are intentional

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session

router = APIRouter(tags=["onboarding"])

SessionDep = Annotated[AsyncSession, __import__("fastapi").Depends(get_session)]

_SUPPORTED_LANGS = frozenset({"uz", "ru", "en", "zh", "de", "ko"})

# Tutorial step definitions are compile-time constants. They are stored here
# rather than in the DB because they change only with app releases and do not
# need admin-panel editing between releases. If that requirement changes, move
# them to a controlled_vocabulary or content_blocks table.
_TUTORIAL_STEPS: list[dict] = [
    {
        "order": 1,
        "kind": "welcome",
        "title": {
            "uz": "SilkLens'ga xush kelibsiz!",
            "ru": "Добро пожаловать в SilkLens!",
            "en": "Welcome to SilkLens!",
            "zh": "欢迎使用 SilkLens!",
            "de": "Willkommen bei SilkLens!",
            "ko": "SilkLens에 오신 것을 환영합니다!",
        },
        "body_md": {
            "uz": "O'zbekistonning tarixiy merosini AI texnologiyasi bilan kashf eting.",
            "ru": "Откройте историческое наследие Узбекистана с технологией ИИ.",
            "en": "Discover Uzbekistan's cultural heritage powered by AI.",
            "zh": "借助 AI 技术探索乌兹别克斯坦的文化遗产。",
            "de": "Entdecken Sie das Kulturerbe Usbekistans mit KI.",
            "ko": "AI 기술로 우즈베키스탄의 문화 유산을 탐험하세요.",
        },
        "duration_seconds": 5,
    },
    {
        "order": 2,
        "kind": "feature",
        "title": {
            "uz": "Kamera bilan aniqlash",
            "ru": "Распознавание камерой",
            "en": "Camera Recognition",
            "zh": "相机识别",
            "de": "Kamera-Erkennung",
            "ko": "카메라 인식",
        },
        "body_md": {
            "uz": (
                "Kamerani tarixiy obidaga qarating — AI uni bir zumda"
                " taniydi va ovozli hikoya boshlaydi."
            ),
            "ru": (
                "Наведите камеру на исторический памятник — ИИ мгновенно"
                " его распознает и начнёт рассказ."
            ),
            "en": (
                "Point your camera at any heritage site — AI instantly"
                " recognizes it and starts the audio story."
            ),
            "zh": "将相机对准历史遗址——AI 立即识别并开始语音讲解。",
            "de": (
                "Richten Sie die Kamera auf eine Sehenswürdigkeit — die KI"
                " erkennt sie sofort und startet die Audioführung."
            ),
            "ko": ("카메라를 유적지에 향하면 AI가 즉시 인식하고 오디오 가이드를 시작합니다."),
        },
        "duration_seconds": 8,
    },
    {
        "order": 3,
        "kind": "feature",
        "title": {
            "uz": "AI Ovozli Gid",
            "ru": "ИИ-аудиогид",
            "en": "AI Audio Guide",
            "zh": "AI 语音导览",
            "de": "KI-Audioguide",
            "ko": "AI 오디오 가이드",
        },
        "body_md": {
            "uz": (
                "6 tilda professional ovozli tarixiy hikoyalar."
                " Internetni o'chirib ham eshitish mumkin (offline rejim)."
            ),
            "ru": (
                "Профессиональные аудиорассказы на 6 языках. Работает без интернета (офлайн-режим)."
            ),
            "en": "Professional audio stories in 6 languages. Works offline after download.",
            "zh": "6种语言的专业语音故事，下载后可离线使用。",
            "de": (
                "Professionelle Audiogeschichten in 6 Sprachen."
                " Funktioniert nach dem Download offline."
            ),
            "ko": ("6개 언어로 된 전문 오디오 스토리. 다운로드 후 오프라인에서도 작동합니다."),
        },
        "duration_seconds": 8,
    },
    {
        "order": 4,
        "kind": "feature",
        "title": {
            "uz": "AI Sayohat Rejasi",
            "ru": "ИИ-планировщик путешествий",
            "en": "AI Trip Planner",
            "zh": "AI 行程规划",
            "de": "KI-Reiseplaner",
            "ko": "AI 여행 플래너",
        },
        "body_md": {
            "uz": (
                "Samarqand, Buxoro, Xiva — AI sizning vaqtingiz va"
                " byudjetingizga mos optimal marshrut tuzib beradi."
            ),
            "ru": (
                "Самарканд, Бухара, Хива — ИИ составит оптимальный маршрут"
                " с учётом вашего времени и бюджета."
            ),
            "en": (
                "Samarkand, Bukhara, Khiva — AI creates the optimal route"
                " matching your time and budget."
            ),
            "zh": "撒马尔罕、布哈拉、希瓦——AI 根据您的时间和预算制定最优路线。",
            "de": (
                "Samarkand, Buchara, Chiwa — die KI erstellt die optimale"
                " Route für Ihre Zeit und Ihr Budget."
            ),
            "ko": (
                "사마르칸트, 부하라, 히바 — AI가 시간과 예산에 맞는 최적의 경로를 만들어 드립니다."
            ),
        },
        "duration_seconds": 8,
    },
    {
        "order": 5,
        "kind": "pricing",
        "title": {
            "uz": "Narxlar",
            "ru": "Цены",
            "en": "Pricing",
            "zh": "价格",
            "de": "Preise",
            "ko": "가격",
        },
        "body_md": {
            "uz": "AI Video: $2 | Tarixiy hikoyalar: $1 | Premium: oylik obuna",
            "ru": "ИИ-видео: $2 | Исторические истории: $1 | Премиум: ежемесячная подписка",
            "en": "AI Video: $2 | Historical Stories: $1 | Premium: monthly subscription",
            "zh": "AI 视频: $2 | 历史故事: $1 | 高级版: 月度订阅",
            "de": "KI-Video: $2 | Historische Geschichten: $1 | Premium: Monatsabonnement",
            "ko": "AI 비디오: $2 | 역사 이야기: $1 | 프리미엄: 월간 구독",
        },
        "duration_seconds": 6,
    },
]


# --- Response schemas ---------------------------------------------------------


class TutorialStep(BaseModel):
    order: int
    kind: str
    title: str
    body_md: str
    duration_seconds: int


class TutorialResponse(BaseModel):
    language: str
    total_steps: int
    total_duration_seconds: int
    steps: list[TutorialStep]


class PlanOverviewItem(BaseModel):
    slug: str
    name: str
    features: list[str]


class PayPerUseItem(BaseModel):
    name: str
    price_usd: float


class PlansOverviewResponse(BaseModel):
    language: str
    plans: list[PlanOverviewItem]
    pay_per_use: list[PayPerUseItem]


# --- Routes -------------------------------------------------------------------


@router.get(
    "/v1/onboarding/tutorial",
    response_model=TutorialResponse,
    summary="Get onboarding tutorial steps",
)
async def get_tutorial(
    language: str = Query("en", min_length=2, max_length=10),
) -> TutorialResponse:
    """Get onboarding tutorial steps in the requested language. No auth required.

    Falls back to English for any unsupported language tag. Language tags
    may be full BCP-47 (e.g. ``en-US``) — only the primary subtag is used.
    """
    lang = language.split("-")[0].lower()
    if lang not in _SUPPORTED_LANGS:
        lang = "en"

    steps = [
        TutorialStep(
            order=step["order"],
            kind=step["kind"],
            title=step["title"].get(lang) or step["title"].get("en", ""),
            body_md=step["body_md"].get(lang) or step["body_md"].get("en", ""),
            duration_seconds=step["duration_seconds"],
        )
        for step in _TUTORIAL_STEPS
    ]

    return TutorialResponse(
        language=lang,
        total_steps=len(steps),
        total_duration_seconds=sum(s.duration_seconds for s in steps),
        steps=steps,
    )


@router.get(
    "/v1/onboarding/plans-overview",
    response_model=PlansOverviewResponse,
    summary="Public pricing plans overview for onboarding",
)
async def get_plans_overview(
    session: SessionDep,
    language: str = Query("en", min_length=2, max_length=10),
) -> PlansOverviewResponse:
    """Public pricing overview for the onboarding flow. No auth required.

    Returns active product plans ordered by sort_order, with the feature list
    for each plan. Falls back gracefully when the product_plans table is empty
    (e.g. a fresh dev environment before billing seeding).
    """
    lang = language.split("-")[0].lower()
    if lang not in _SUPPORTED_LANGS:
        lang = "en"

    result = await session.execute(
        text(
            """
            SELECT
                pp.slug,
                pp.display_name,
                f.feature_list
            FROM product_plans pp
            LEFT JOIN LATERAL (
                SELECT jsonb_agg(feature_key ORDER BY sort_order) AS feature_list
                FROM plan_features
                WHERE plan_id = pp.id AND is_included = true
            ) f ON true
            WHERE pp.is_active = true
            ORDER BY pp.sort_order
            """
        )
    )

    plans: list[PlanOverviewItem] = []
    for r in result.mappings().fetchall():
        display = r["display_name"]
        if isinstance(display, dict):
            name = display.get(lang) or display.get("en") or next(iter(display.values()), "")
        else:
            name = str(display) if display is not None else ""
        plans.append(
            PlanOverviewItem(
                slug=r["slug"],
                name=name,
                features=[str(f) for f in (r["feature_list"] or [])],
            )
        )

    return PlansOverviewResponse(
        language=lang,
        plans=plans,
        pay_per_use=[
            PayPerUseItem(name="AI Video", price_usd=2.0),
            PayPerUseItem(name="Historical Story", price_usd=1.0),
        ],
    )
