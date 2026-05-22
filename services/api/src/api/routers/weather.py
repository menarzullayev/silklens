"""Weather-aware travel guide endpoints. SILK-0074."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.infrastructure.weather.openweather_client import get_weather_client
from src.infrastructure.weather.recommendations import get_recommendations
from src.middleware.ratelimit import rate_limit

router = APIRouter(tags=["weather"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


# --- DTOs -------------------------------------------------------------------


class WeatherOut(BaseModel):
    city: str
    temperature_c: float
    feels_like_c: float
    condition: str
    description: str
    humidity_pct: int
    wind_speed_ms: float
    icon_code: str
    is_daytime: bool


class NearbyHeritageItem(BaseModel):
    pub_id: str
    name: str | None
    kind_slug: str | None
    distance_km: float | None


class RecommendationsOut(BaseModel):
    condition: str
    temperature_c: float
    description: str
    recommended_venue_kinds: list[str]
    activity_tip: str
    health_tips: list[str]
    avoid_tip: str | None = None


class WeatherGuideResponse(BaseModel):
    language: str
    weather: WeatherOut
    recommendations: RecommendationsOut
    nearby_heritage: list[NearbyHeritageItem]


class HealthTipsResponse(BaseModel):
    temperature_c: float
    activity: str
    language: str
    tips: list[str]
    hydration_reminder_minutes: int


# --- Routes -----------------------------------------------------------------


@router.get(
    "/v1/ai/weather-guide",
    response_model=WeatherGuideResponse,
)
async def weather_guide(
    db: SessionDep,
    lat: float = Query(..., ge=-90, le=90, description="Current latitude"),
    lng: float = Query(..., ge=-180, le=180, description="Current longitude"),
    language: str = Query("en", min_length=2, max_length=10),
    _rl: None = Depends(rate_limit("60/minute", per="ip", scope="weather:guide")),
) -> WeatherGuideResponse:
    """Weather-aware heritage site recommendations.

    Returns current weather, recommended venue types, health tips, and nearby
    heritage objects sorted by distance. No authentication required — public endpoint.
    """
    lang = language.split("-")[0].lower()
    client = get_weather_client()
    weather = await client.current(lat, lng)
    rec_dict: dict[str, Any] = get_recommendations(weather, lang)

    # Fetch nearby published heritage objects from DB, sorted by proximity
    rows = await db.execute(
        text("""
            SELECT pub_id, name, kind_slug, lat, lng,
                CASE WHEN lat IS NOT NULL AND lng IS NOT NULL THEN
                    round(
                        (point(:lng, :lat) <@> point(lng::float8, lat::float8))::numeric * 1.60934,
                        1
                    )
                ELSE NULL END AS distance_km
            FROM heritage_objects
            WHERE status = 'published'
              AND lat IS NOT NULL
              AND deleted_at IS NULL
            ORDER BY (point(:lng, :lat) <@> point(lng::float8, lat::float8))
            LIMIT 5
        """),
        {"lat": lat, "lng": lng},
    )
    nearby: list[NearbyHeritageItem] = []
    for r in rows.mappings().fetchall():
        raw_name = r["name"]
        if isinstance(raw_name, dict):
            display_name: str | None = raw_name.get(lang) or raw_name.get("en")
        else:
            display_name = str(raw_name) if raw_name is not None else None
        nearby.append(
            NearbyHeritageItem(
                pub_id=str(r["pub_id"]),
                name=display_name,
                kind_slug=r["kind_slug"],
                distance_km=float(r["distance_km"]) if r["distance_km"] is not None else None,
            )
        )

    return WeatherGuideResponse(
        language=lang,
        weather=WeatherOut(
            city=weather.city,
            temperature_c=weather.temperature_c,
            feels_like_c=weather.feels_like_c,
            condition=weather.condition,
            description=weather.description,
            humidity_pct=weather.humidity_pct,
            wind_speed_ms=weather.wind_speed_ms,
            icon_code=weather.icon_code,
            is_daytime=weather.is_daytime,
        ),
        recommendations=RecommendationsOut(
            condition=rec_dict["condition"],
            temperature_c=rec_dict["temperature_c"],
            description=rec_dict["description"],
            recommended_venue_kinds=rec_dict["recommended_venue_kinds"],
            activity_tip=rec_dict["activity_tip"],
            health_tips=rec_dict["health_tips"],
            avoid_tip=rec_dict.get("avoid_tip"),
        ),
        nearby_heritage=nearby,
    )


@router.get(
    "/v1/ai/health-tips",
    response_model=HealthTipsResponse,
)
async def health_tips(
    temperature_c: float = Query(25.0, ge=-50, le=60),
    activity: str = Query(
        "walking",
        min_length=1,
        max_length=50,
        description="walking | cycling | museum | outdoor",
    ),
    language: str = Query("en", min_length=2, max_length=10),
    _rl: None = Depends(rate_limit("120/minute", per="ip", scope="weather:health")),
) -> HealthTipsResponse:
    """Activity + temperature based health tips. No authentication required."""
    tips: list[str] = []
    lang = language.split("-")[0].lower()

    if temperature_c >= 38:
        tips.append("Extreme heat — avoid outdoor activity, stay in air-conditioned spaces.")
        tips.append("Drink 3-4 liters of water throughout the day.")
    elif temperature_c >= 30:
        tips.append("Drink at least 500ml of water every hour during outdoor activities.")
        tips.append("Apply SPF 50+ sunscreen before going outside.")
        if activity == "walking":
            tips.append("Best walking time: before 10:00 or after 17:00.")
    elif temperature_c <= 0:
        tips.append("Dress in thermal layers — exposed skin risks frostbite.")
        tips.append("Carry warm drinks to stay hydrated.")
    elif temperature_c <= 10:
        tips.append("Wear a warm jacket and comfortable walking shoes.")

    if activity == "walking" and temperature_c >= 25:
        tips.append("Take a 10-minute shade break every 45 minutes of walking.")
    if activity == "cycling" and temperature_c >= 30:
        tips.append("Wear a helmet and sunglasses. Carry extra water.")

    if not tips:
        tips.append("Great conditions for your activity — enjoy the experience!")

    return HealthTipsResponse(
        temperature_c=temperature_c,
        activity=activity,
        language=lang,
        tips=tips,
        hydration_reminder_minutes=30 if temperature_c >= 30 else 60,
    )
