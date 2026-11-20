"""AI Photo Guide — angle suggestions, historical overlays, before/after. SILK-0067."""

from __future__ import annotations

import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.settings import get_settings
from src.middleware.ratelimit import rate_limit

router = APIRouter(tags=["photo-guide"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


# --- DTOs ------------------------------------------------------------------


class PhotoGuideRequest(BaseModel):
    heritage_pub_id: UUID
    mode: str = Field("angle", description="angle | overlay | compare")
    current_photo_media_id: UUID | None = None
    language: str = Field("en", min_length=2, max_length=10)


class HistoricalPhotoOut(BaseModel):
    url: str
    year: int
    photographer: str | None
    description: str


class AngleOut(BaseModel):
    mode: str
    heritage_pub_id: str
    heritage_name: str
    suggested_azimuth_deg: int
    suggested_elevation_deg: int
    best_time: str
    tip: str
    compass_direction: str


class OverlayOut(BaseModel):
    mode: str
    heritage_pub_id: str
    heritage_name: str
    historical_photo: HistoricalPhotoOut | None
    overlay_available: bool
    tip: str


# Union-discriminated response keeps OpenAPI tidy while staying typed.
PhotoGuideOut = AngleOut | OverlayOut


# --- Pre-curated angle presets (public domain reference data) --------------
#
# These are read-only reference defaults.  Site-specific overrides must be
# managed via the admin panel (system_settings / heritage_facts) — never edit
# this file for per-site customisation in production.

_ANGLE_DB: dict[str, dict] = {
    "registan": {
        "azimuth_deg": 315,
        "elevation_deg": 12,
        "tip_en": (
            "Stand 80m back at northwest to capture all three madrasas."
            " Golden hour (06:30-08:00) gives the best light."
        ),
        "tip_uz": "Barcha uch madrasani suratga olish uchun shimoli-g'arbda 80m orqaga turing.",
        "tip_ru": "Встаньте в 80м с северо-запада, чтобы захватить все три медресе.",  # noqa: RUF001
        "best_time": "06:30-08:00",
    },
    "shah-i-zinda": {
        "azimuth_deg": 180,
        "elevation_deg": 8,
        "tip_en": "Shoot from the entrance looking north for the blue tile corridor effect.",
        "tip_uz": "Kirish joyidan shimolga qarab moviy kafel ko'rinishini suratga oling.",
        "tip_ru": "Снимайте со входа на север для эффекта синего плиточного коридора.",  # noqa: RUF001
        "best_time": "09:00-11:00",
    },
    "bibi-khanym": {
        "azimuth_deg": 45,
        "elevation_deg": 10,
        "tip_en": "Shoot from the southeast corner to capture the full portal with the minaret.",
        "tip_uz": "Janubi-sharq burchagidan to'liq portalini suratga oling.",
        "tip_ru": "Снимайте с юго-восточного угла для полного портала с минаретом.",  # noqa: RUF001
        "best_time": "07:00-09:00",
    },
    "ark fortress": {
        "azimuth_deg": 0,
        "elevation_deg": 5,
        "tip_en": (
            "Stand at the base of the Zindon gate looking straight up for a dramatic perspective."
        ),
        "tip_uz": "Zindon darvozasi tagida turib to'g'ri yuqoriga qarang.",
        "tip_ru": "Встаньте у основания ворот Зиндан, смотря прямо вверх.",  # noqa: RUF001
        "best_time": "16:00-18:00",
    },
    "lyabi hauz": {
        "azimuth_deg": 90,
        "elevation_deg": 3,
        "tip_en": "Shoot from the pool reflection side at dawn for perfect symmetry.",
        "tip_uz": "Tong paytida havuzdan aks etgan tasvirni oling.",
        "tip_ru": "Снимайте с отражением в бассейне на рассвете.",  # noqa: RUF001
        "best_time": "05:30-07:00",
    },
}

# Historical photos — public domain / CC0 only.
_HISTORICAL_PHOTOS: dict[str, dict] = {
    "registan": {
        "photo_url": (
            "https://upload.wikimedia.org/wikipedia/commons/thumb"
            "/a/af/Registan_1890s.jpg/800px-Registan_1890s.jpg"
        ),
        "year": 1890,
        "photographer": "Unknown, public domain",
        "description_en": "Registan square in the 1890s before Soviet restoration",
    },
    "ark fortress": {
        "photo_url": (
            "https://upload.wikimedia.org/wikipedia/commons/thumb"
            "/9/99/Ark_1913.jpg/800px-Ark_1913.jpg"
        ),
        "year": 1913,
        "photographer": "Unknown, public domain",
        "description_en": "Ark Fortress in Bukhara circa 1913",
    },
}


# --- Helpers ---------------------------------------------------------------


def _azimuth_to_direction(azimuth: float) -> str:
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = round(azimuth / 45) % 8
    return directions[idx]


async def _ai_angle_suggestion(
    heritage_name: str,
    lat: float | None,
    lng: float | None,
    lang: str,
    settings,
) -> dict:
    """Return an AI-generated photo angle suggestion when no preset exists.

    Falls back gracefully to a safe default on any provider failure so the
    public endpoint never surfaces a 5xx from an upstream AI call.
    """
    if settings.ai_use_mock_providers:
        return {
            "azimuth_deg": 315,
            "elevation_deg": 10,
            "tip": (
                f"For the best photo of {heritage_name}, position yourself"
                " to capture the main facade in morning light."
            ),
            "best_time": "07:00-09:00",
        }
    try:
        import anthropic

        client = anthropic.AsyncAnthropic()
        json_schema = (
            '{"tip": "...", "best_time": "HH:MM-HH:MM",'
            ' "azimuth_deg": 0-360, "elevation_deg": 0-45}'
        )
        prompt = (
            f"Give a brief photography tip for {heritage_name} in {lang}. "
            f"Include optimal camera angle, time of day, and distance. "
            f"Keep it under 50 words. Return JSON: {json_schema}"
        )
        resp = await client.messages.create(
            model=settings.anthropic_model_default,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        return {
            "azimuth_deg": int(data.get("azimuth_deg", 315)),
            "elevation_deg": int(data.get("elevation_deg", 10)),
            "tip": str(data.get("tip", "")),
            "best_time": str(data.get("best_time", "07:00-10:00")),
        }
    except Exception:  # AI provider failures must not 5xx a public endpoint
        return {
            "azimuth_deg": 315,
            "elevation_deg": 10,
            "tip": (f"Photograph {heritage_name} in the morning light from the main entrance."),
            "best_time": "07:00-09:00",
        }


# --- Route -----------------------------------------------------------------


@router.post(
    "/v1/ai/photo-guide",
    response_model=PhotoGuideOut,
    dependencies=[
        Depends(rate_limit("20/minute", per="ip", scope="ai:photo_guide")),
    ],
)
async def photo_guide(
    body: PhotoGuideRequest,
    session: SessionDep,
) -> AngleOut | OverlayOut:
    """AI photo composition guide: angles, overlays, historical comparisons.

    Public endpoint — no auth required.  Rate-limited to 20 req/min per IP.
    Premium users receive richer AI-generated tips when the Anthropic provider
    is active (``ai_use_mock_providers = false``).

    Modes:
    - ``angle``   — suggested azimuth, elevation, best time of day, compass direction.
    - ``overlay`` — historical photo URL + metadata for before/after compositing.
    - ``compare`` — alias for ``overlay``; identical response shape.
    """
    lang = body.language.split("-")[0].lower()
    settings = get_settings()

    row = await session.execute(
        text("""
            SELECT
                COALESCE(name->>:lang, name->>'en') AS name,
                kind_slug,
                lat,
                lng
            FROM heritage_objects
            WHERE pub_id   = :pub_id
              AND status   = 'published'
              AND deleted_at IS NULL
        """),
        {"pub_id": str(body.heritage_pub_id), "lang": lang},
    )
    heritage = row.mappings().fetchone()
    if heritage is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "heritage.not_found", "message": "Heritage site not found"},
        )

    site_name: str = heritage.get("name") or ""
    site_name_lower = site_name.lower()

    # Locate a preset by substring match against the normalised site name.
    angle_preset: dict | None = next(
        (data for key, data in _ANGLE_DB.items() if key in site_name_lower),
        None,
    )
    hist_preset: dict | None = next(
        (data for key, data in _HISTORICAL_PHOTOS.items() if key in site_name_lower),
        None,
    )

    if body.mode == "angle":
        if angle_preset is None:
            angle_data = await _ai_angle_suggestion(
                site_name,
                heritage.get("lat"),
                heritage.get("lng"),
                lang,
                settings,
            )
            tip = str(angle_data.get("tip", ""))
        else:
            angle_data = angle_preset
            tip = str(angle_preset.get(f"tip_{lang}") or angle_preset.get("tip_en", ""))

        return AngleOut(
            mode="angle",
            heritage_pub_id=str(body.heritage_pub_id),
            heritage_name=site_name,
            suggested_azimuth_deg=int(angle_data.get("azimuth_deg", 315)),
            suggested_elevation_deg=int(angle_data.get("elevation_deg", 10)),
            best_time=str(angle_data.get("best_time", "07:00-09:00")),
            tip=tip,
            compass_direction=_azimuth_to_direction(float(angle_data.get("azimuth_deg", 315))),
        )

    if body.mode in ("overlay", "compare"):
        hist_photo: HistoricalPhotoOut | None = None
        if hist_preset is not None:
            desc_key = f"description_{lang}"
            desc = str(hist_preset.get(desc_key) or hist_preset.get("description_en", ""))
            hist_photo = HistoricalPhotoOut(
                url=str(hist_preset["photo_url"]),
                year=int(hist_preset["year"]),
                photographer=hist_preset.get("photographer"),
                description=desc,
            )

        overlay_tip = (
            f"Compare today's {site_name} with historical photos"
            " to see how it has changed over time."
            if hist_photo is not None
            else "No historical photo available for this site yet."
        )

        return OverlayOut(
            mode=body.mode,
            heritage_pub_id=str(body.heritage_pub_id),
            heritage_name=site_name,
            historical_photo=hist_photo,
            overlay_available=hist_photo is not None,
            tip=overlay_tip,
        )

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "code": "photo_guide.invalid_mode",
            "message": "mode must be 'angle', 'overlay', or 'compare'",
        },
    )
