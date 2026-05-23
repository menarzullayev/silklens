"""Mood-based travel recommendations. SILK-0078."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, StrictFloat
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.middleware.ratelimit import rate_limit

router = APIRouter(tags=["recommendations"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

_MOOD_PROFILES: dict[str, dict[str, Any]] = {
    "tired": {
        "venue_kinds": ["museum", "gallery", "tea_house", "restaurant"],
        "max_walk_km": 0.5,
        "prefer_indoor": True,
        "message_en": "You deserve a calm, indoor experience. Museums and cosy teahouses await.",
        "message_uz": "Dam olish vaqti! Muzeylar va choyxonalar siz uchun.",
        "message_ru": "Время отдохнуть! Музеи и уютные чайхоны ждут вас.",
    },
    "adventurous": {
        "venue_kinds": ["archaeological_site", "mountain_pass", "bazaar", "city_walk"],
        "max_walk_km": 10.0,
        "prefer_indoor": False,
        "message_en": "Adventure mode! Explore bazaars, ancient ruins and AR walking tours.",
        "message_uz": "Sarguzasht rejimi! Bozorlar, qadimiy xarobalar va AR sayohat.",
        "message_ru": "Режим приключений! Базары, древние руины и AR прогулки.",
    },
    "romantic": {
        "venue_kinds": ["park", "garden", "sunset_terrace", "restaurant", "mosque"],
        "max_walk_km": 2.0,
        "prefer_indoor": False,
        "message_en": "A romantic evening — gardens, sunset terraces and candlelit dinners.",
        "message_uz": "Romantik kech — bog'lar, quyosh botishini ko'rish joylari.",
        "message_ru": "Романтический вечер — сады, закатные террасы и ужин при свечах.",
    },
    "curious": {
        "venue_kinds": ["monument", "mausoleum", "mosque", "caravanserai", "observatory"],
        "max_walk_km": 5.0,
        "prefer_indoor": False,
        "message_en": (
            "Feed your curiosity — UNESCO sites, ancient mausoleums and Silk Road stories."
        ),
        "message_uz": "Qiziquvchanlik uchun — UNESCO obidalar, qadimiy maqbaralar.",
        "message_ru": "Для любознательных — объекты ЮНЕСКО, древние мавзолеи.",
    },
    "family": {
        "venue_kinds": ["park", "museum", "monument", "bazaar"],
        "max_walk_km": 3.0,
        "prefer_indoor": False,
        "message_en": "Family-friendly sights — interactive museums and open parks for the kids.",
        "message_uz": "Oilaviy sayohat — interaktiv muzeylar va bog'lar.",
        "message_ru": "Семейные достопримечательности — интерактивные музеи и парки.",
    },
}

_VALID_MOODS = frozenset(_MOOD_PROFILES)


class MoodRequest(BaseModel):
    # ``Literal`` so the OpenAPI schema declares the exact enum the runtime
    # enforces — schemathesis's positive-data-acceptance check then knows
    # that ``""`` / ``"x"`` are schema-violating and won't flag the 422.
    mood: Literal[
        "tired", "adventurous", "romantic", "curious", "family"
    ] = Field(..., description="tired|adventurous|romantic|curious|family")
    available_hours: float = Field(2.0, gt=0, le=12)
    lat: StrictFloat | None = None
    lng: StrictFloat | None = None
    language: str = Field("en", min_length=2, max_length=10)


@router.post("/v1/ai/mood-recommendations")
async def mood_recommendations(
    body: MoodRequest,
    session: SessionDep,
    _rl: None = Depends(rate_limit("20/minute", per="ip", scope="mood:recommend")),
) -> dict[str, Any]:
    """Mood-aware heritage + listing recommendations. No auth required."""
    if body.mood not in _VALID_MOODS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "mood.invalid",
                "message": f"mood must be one of: {', '.join(sorted(_VALID_MOODS))}",
            },
        )

    lang = body.language.split("-")[0].lower()
    profile = _MOOD_PROFILES[body.mood]
    message_key = f"message_{lang}" if f"message_{lang}" in profile else "message_en"

    # Fetch nearby heritage matching mood kind preferences
    kinds = profile["venue_kinds"]
    params: dict[str, Any] = {"limit": 5, "lat_f": body.lat or 39.65, "lng_f": body.lng or 66.97}

    kind_placeholders = ", ".join(f":kind_{i}" for i in range(len(kinds)))
    for i, k in enumerate(kinds):
        params[f"kind_{i}"] = k

    rows = await session.execute(
        text(
            f"""
            SELECT pub_id,
                   COALESCE(name->>:lang, name->>'en') AS name,
                   kind_slug, latitude AS lat, longitude AS lng,
                   round(
                       (point(:lng_f, :lat_f)
                        <@> point(longitude::float8, latitude::float8)
                       )::numeric * 1.60934, 1
                   ) AS distance_km
            FROM heritage_objects
            WHERE status = 'published'
              AND deleted_at IS NULL
              AND kind_slug IN ({kind_placeholders})
              AND latitude IS NOT NULL
            ORDER BY (point(:lng_f, :lat_f) <@> point(longitude::float8, latitude::float8))
            LIMIT :limit
        """  # noqa: S608 — kind_placeholders built from validated list, no user input
        ),
        {**params, "lang": lang},
    )
    heritage = [dict(r) for r in rows.mappings().fetchall()]

    return {
        "mood": body.mood,
        "language": lang,
        "message": profile.get(message_key) or profile["message_en"],
        "available_hours": body.available_hours,
        "venue_kinds": profile["venue_kinds"],
        "recommended_heritage": heritage,
        "prefer_indoor": profile["prefer_indoor"],
        "max_walk_km": profile["max_walk_km"],
    }
