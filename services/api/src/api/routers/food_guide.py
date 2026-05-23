"""Smart Food Guide — AI-powered food recommendations. SILK-0070."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.settings import get_settings
from src.middleware.ratelimit import rate_limit

SessionDep = Annotated[AsyncSession, Depends(get_session)]

router = APIRouter(tags=["food"])


class FoodQuery(BaseModel):
    message: str = Field(
        ...,
        max_length=500,
        description="e.g. 'I am vegetarian, recommend a good restaurant near Registon'",
    )
    lat: float | None = None
    lng: float | None = None
    language: str = Field("en", min_length=2, max_length=10)
    dietary_preferences: list[str] = Field(
        default_factory=list,
        description="halal|vegetarian|vegan|gluten_free",
    )


_DIETARY_TIPS: dict[str, dict[str, str]] = {
    "halal": {
        "en": "All traditional Uzbek restaurants are halal by default. Look for 'Halol' signs.",
        "uz": "Barcha an'anaviy o'zbek restoranlari halol. 'Halol' belgilarini qidiring.",
        "ru": "Vse traditsionnye uzbekskie restorany po umolchaniyu khalyalnye.",  # transliterated
    },
    "vegetarian": {
        "en": (
            "Ask for 'sabzavotli taomlar' (vegetable dishes)."
            " Lagman and samsa can be made without meat."
        ),
        "uz": ("Sabzavotli taomlarni so'rang. Lag'mon va samsa go'shtsiz ham tayyorlanadi."),
        "ru": "Poprosite sabzavotli taomlar. Lagman i samsa byvayut bez myasa.",  # transliterated
    },
    "vegan": {
        "en": (
            "Vegan options are limited. Stick to markets for fresh fruits, nuts and dried fruits."
        ),
        "uz": (
            "Vegan variantlari cheklangan. Bozorlardan yangi meva, yong'oq va quritilgan mevalar."
        ),
        "ru": "Veganskikh variantov malo. Rynki: frukty, orekhami.",  # transliterated
    },
}

_MUST_TRY = {
    "en": [
        "Plov (rice pilaf)",
        "Shashlik (grilled meat)",
        "Samsa (baked pastry)",
        "Lagman (noodle soup)",
        "Manti (steamed dumplings)",
    ],
    "uz": ["Palov", "Shashlik", "Somsa", "Lag'mon", "Manti"],
    "ru": ["Плов", "Шашлык", "Самса", "Лагман", "Манты"],
}


@router.post("/v1/ai/food-assistant")
async def food_assistant(
    body: FoodQuery,
    session: SessionDep,
    _rl: None = Depends(rate_limit("20/minute", per="ip", scope="food:assistant")),
) -> dict[str, Any]:
    """AI food recommendation assistant. No auth required."""
    lang = body.language.split("-")[0].lower()
    settings = get_settings()

    # Find nearby restaurants from b2b_listings
    params: dict[str, Any] = {
        "lang": lang,
        "limit": 5,
        "lat_f": body.lat or 39.65,
        "lng_f": body.lng or 66.97,
    }
    dietary_filter = ""
    if body.dietary_preferences:
        pref = body.dietary_preferences[0]
        if pref in {"halal", "vegetarian", "vegan", "gluten_free"}:
            dietary_filter = "AND :dietary = ANY(bl.dietary_tags)"
            params["dietary"] = pref

    _dist = (
        "round((point(:lng_f,:lat_f)<@>point(bl.lng::float8,bl.lat::float8))::numeric*1.60934,1)"
        " AS distance_km"
    )
    _sql = (
        "SELECT COALESCE(bl.name->>:lang,bl.name->>'en') AS name,"  # noqa: S608 # noqa: S608
        " bl.contact_phone, bl.website, bl.price_range,"
        f" {_dist}"
        f" FROM b2b_listings bl WHERE bl.category_slug='restaurant' AND bl.status='active'"
        f" {dietary_filter}"
        " ORDER BY (point(:lng_f,:lat_f)<@>point(bl.lng::float8,bl.lat::float8)) LIMIT :limit"
    )
    rows = await session.execute(text(_sql), params)
    restaurants = [dict(r) for r in rows.mappings().fetchall()]

    # AI-generated reply
    if not settings.ai_use_mock_providers:
        try:
            import anthropic

            client = anthropic.AsyncAnthropic()
            context = f"Nearby restaurants: {[r.get('name') for r in restaurants[:3]]}"
            resp = await client.messages.create(
                model=settings.anthropic_model_default,
                max_tokens=300,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"User query: {body.message}\n{context}\n"
                            f"Language: {lang}\n"
                            "Provide a helpful food recommendation in 2-3 sentences."
                        ),
                    }
                ],
            )
            from anthropic.types import TextBlock  # local import — optional dep

            first = resp.content[0]
            ai_reply = first.text.strip() if isinstance(first, TextBlock) else ""
        except Exception:
            ai_reply = (
                f"Here are some great restaurants near you! "
                f"{_MUST_TRY.get(lang, _MUST_TRY['en'])[0]} is a must-try dish in Uzbekistan."
            )
    else:
        ai_reply = (
            f"Great choice! Uzbek cuisine is famous for its rich flavors. "
            f"Try {_MUST_TRY.get(lang, _MUST_TRY['en'])[0]} — a local favourite!"
        )

    # Dietary tips
    diet_tips = []
    for pref in body.dietary_preferences:
        if pref in _DIETARY_TIPS:
            tip_data = _DIETARY_TIPS[pref]
            diet_tips.append(tip_data.get(lang) or tip_data["en"])

    return {
        "language": lang,
        "reply": ai_reply,
        "restaurant_recommendations": restaurants,
        "dietary_tips": diet_tips,
        "must_try_dishes": _MUST_TRY.get(lang, _MUST_TRY["en"])[:3],
    }
