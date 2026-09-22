"""AI utility tools — bargaining assistant, scam detection, lost & found. SILK-0080.

POST /v1/ai/fair-price   — check if a market price is fair (public)
POST /v1/ai/scam-check   — analyse a service offer for scam indicators (public)
GET  /v1/ai/lost-found   — find nearest help centres for a lost item (public)
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.middleware.ratelimit import rate_limit

router = APIRouter(tags=["ai-utilities"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


# --- Bargaining Assistant --------------------------------------------------


class FairPriceQuery(BaseModel):
    item: str = Field(
        ..., min_length=1, max_length=200, description="Item name, e.g. 'silk carpet 2x3m'"
    )
    market: str = Field(
        ..., min_length=1, max_length=100, description="Market name, e.g. 'chorsu bazaar'"
    )
    currency: str = Field("USD", min_length=3, max_length=3)
    language: str = Field("en", min_length=2, max_length=10)


class FairPriceResponse(BaseModel):
    item: str
    market: str
    currency: str
    typical_price_usd: float | None
    price_range: dict[str, Any] | None
    negotiation_tip: str
    recommended_offer_pct: int | None
    confidence: str


# Approximate fair-price guide (USD) for common Uzbek bazaar items.
_PRICE_GUIDE: dict[str, dict[str, Any]] = {
    "silk carpet": {
        "min": 50,
        "max": 500,
        "typical": 150,
        "tip": "Start at 40% of asking price",
    },
    "suzane": {
        "min": 20,
        "max": 200,
        "typical": 60,
        "tip": "Hand-embroidered ones cost more",
    },
    "ceramic plate": {
        "min": 5,
        "max": 30,
        "typical": 12,
        "tip": "Bargain respectfully, expect 20-30% off",
    },
    "knife": {
        "min": 10,
        "max": 80,
        "typical": 25,
        "tip": "Yusupov knives are authentic and quality",
    },
    "miniature painting": {
        "min": 15,
        "max": 300,
        "typical": 50,
        "tip": "Signed works are more valuable",
    },
    "hat": {
        "min": 3,
        "max": 20,
        "typical": 8,
        "tip": "Tubeteika hats are traditional and affordable",
    },
    "spices": {
        "min": 2,
        "max": 15,
        "typical": 5,
        "tip": "Buy by weight, not pre-packaged",
    },
}


@router.post(
    "/v1/ai/fair-price",
    response_model=FairPriceResponse,
    status_code=200,
    dependencies=[
        Depends(rate_limit("20/minute", per="ip", scope="ai:fair_price")),
    ],
)
async def fair_price_check(
    body: FairPriceQuery,
) -> FairPriceResponse:
    """Check if a price is fair for a market item. No auth required."""
    item_lower = body.item.lower()
    price_info: dict[str, Any] | None = None
    for key, prices in _PRICE_GUIDE.items():
        if key in item_lower or any(word in item_lower for word in key.split()):
            price_info = prices
            break

    if not price_info:
        return FairPriceResponse(
            item=body.item,
            market=body.market,
            currency=body.currency,
            typical_price_usd=None,
            price_range=None,
            negotiation_tip="Research local prices before bargaining. Ask multiple vendors.",
            recommended_offer_pct=None,
            confidence="low",
        )

    return FairPriceResponse(
        item=body.item,
        market=body.market,
        currency=body.currency,
        typical_price_usd=float(price_info["typical"]),
        price_range={"min": price_info["min"], "max": price_info["max"]},
        negotiation_tip=price_info["tip"],
        recommended_offer_pct=50,
        confidence="medium",
    )


# --- Scam Detector ---------------------------------------------------------


class ScamCheckRequest(BaseModel):
    venue_name: str = Field(..., min_length=1, max_length=200)
    service_description: str = Field(..., min_length=1, max_length=500)
    quoted_price_usd: float = Field(..., gt=0)
    language: str = Field("en", min_length=2, max_length=10)


class ScamCheckResponse(BaseModel):
    venue_name: str
    risk_score: float
    verdict: str
    flags: list[str]
    advice: str
    tourist_police: str


_SCAM_SIGNALS: list[dict[str, Any]] = [
    {"pattern": "taxi airport", "flag": "airport_taxi_overcharge"},
    {"pattern": "carpet shop tour", "flag": "forced_carpet_tour"},
    {"pattern": "special price friend", "flag": "friendship_scam"},
    {"pattern": "money exchange street", "flag": "street_money_exchange"},
    {"pattern": "entry fee unofficial", "flag": "fake_entry_fee"},
]

_ADVICE: dict[str, dict[str, str]] = {
    "safe": {
        "en": "Looks reasonable. Verify reviews before paying.",
        "uz": "Ma'qul ko'rinadi. To'lovdan oldin sharhlarni tekshiring.",
        "ru": "Выглядит приемлемо. Проверьте отзывы перед оплатой.",
    },
    "suspicious": {
        "en": "Exercise caution. Ask for a written receipt and verify prices with other vendors.",
        "uz": "Ehtiyot bo'ling. Yozma chek so'rang.",
        "ru": "Будьте осторожны. Попросите письменный чек.",
    },
    "likely_scam": {
        "en": "High risk! Walk away and report this to tourist police (+998712444444).",
        "uz": "Yuqori xavf! Sayyohlik politsiyasiga xabar bering.",
        "ru": "Высокий риск! Сообщите туристической полиции.",
    },
}


@router.post(
    "/v1/ai/scam-check",
    response_model=ScamCheckResponse,
    status_code=200,
    dependencies=[
        Depends(rate_limit("15/minute", per="ip", scope="ai:scam_check")),
    ],
)
async def scam_check(
    body: ScamCheckRequest,
) -> ScamCheckResponse:
    """Analyse a service offer for potential scam indicators. No auth required."""
    lang = body.language.split("-")[0].lower()
    combined = f"{body.venue_name} {body.service_description}".lower()

    flags: list[str] = []
    risk_score = 0.0

    for signal in _SCAM_SIGNALS:
        pattern_words = signal["pattern"].split()
        matches = sum(1 for w in pattern_words if w in combined)
        if matches >= len(pattern_words) // 2 + 1:
            flags.append(signal["flag"])
            risk_score += 0.4

    if body.quoted_price_usd > 200 and "carpet" not in combined:
        risk_score += 0.2
        flags.append("unusually_high_price")

    risk_score = min(1.0, risk_score)
    if risk_score < 0.3:
        verdict = "safe"
    elif risk_score < 0.7:
        verdict = "suspicious"
    else:
        verdict = "likely_scam"

    advice_map = _ADVICE[verdict]
    advice = advice_map.get(lang) or advice_map["en"]

    return ScamCheckResponse(
        venue_name=body.venue_name,
        risk_score=round(risk_score, 2),
        verdict=verdict,
        flags=flags,
        advice=advice,
        tourist_police="+998712444444",
    )


# --- Lost & Found Assistant -----------------------------------------------


class LostFoundContact(BaseModel):
    name: str | None
    phone: str | None
    address: str | None
    kind: str | None
    distance_km: float | None


class LostFoundResponse(BaseModel):
    item_type: str
    steps: list[str]
    nearest_help: list[LostFoundContact]
    emergency_number: str
    tourist_police: str


_LOST_STEPS: dict[str, dict[str, list[str]]] = {
    "passport": {
        "en": [
            "1. Contact your embassy immediately (see contacts below)",
            "2. Report to police and get a report number",
            "3. Apply for emergency travel document at embassy",
        ],
        "uz": [
            "1. Elchixonangizga murojaat qiling",
            "2. Politsiyaga xabar bering",
            "3. Vaqtinchalik hujjat oling",
        ],
        "ru": [
            "1. Немедленно свяжитесь с посольством",  # noqa: RUF001
            "2. Сообщите в полицию и получите номер дела",
            "3. Запросите экстренный проездной документ",
        ],
    },
    "phone": {
        "en": [
            "1. Retrace your steps",
            "2. Contact last visited venues",
            "3. Report to tourist police",
        ],
        "uz": [
            "1. O'tgan yo'lingizni takrorlang",
            "2. Politsiyaga murojaat qiling",
        ],
        "ru": [
            "1. Вернитесь по своему маршруту",
            "2. Обратитесь в туристическую полицию",
        ],
    },
}
_DEFAULT_STEPS: dict[str, list[str]] = {
    "en": ["1. Report to local police", "2. Contact tourist police: +998712444444"],
    "uz": ["1. Mahalliy politsiyaga murojaat qiling"],
    "ru": ["1. Обратитесь в местную полицию"],
}


@router.get(
    "/v1/ai/lost-found",
    response_model=LostFoundResponse,
    status_code=200,
    dependencies=[
        Depends(rate_limit("10/minute", per="ip", scope="ai:lost_found")),
    ],
)
async def lost_found_help(
    session: SessionDep,
    item_type: str = Query(..., description="passport|phone|wallet|bag|camera"),
    lat: float = Query(39.65, ge=-90, le=90),
    lng: float = Query(66.97, ge=-180, le=180),
    language: str = Query("en"),
) -> LostFoundResponse:
    """Find nearest help centres for a lost item. No auth required."""
    lang = language.split("-")[0].lower()
    contact_kind = "embassy" if item_type == "passport" else "police"

    rows = await session.execute(
        text("""
            SELECT
                COALESCE(name->>:lang, name->>'en') AS name,
                phone,
                COALESCE(address->>:lang, address->>'en') AS address,
                kind,
                CASE WHEN latitude IS NOT NULL THEN
                    round(
                        (point(:lng, :lat) <@> point(longitude::float8, latitude::float8)
                        )::numeric * 1.60934, 1
                    )
                ELSE NULL END AS distance_km
            FROM emergency_contacts
            WHERE country_code = 'UZ'
              AND is_active = true
              AND (kind LIKE :kind_pattern OR kind = 'tourist_police')
            ORDER BY distance_km NULLS LAST, sort_order
            LIMIT 5
        """),
        {"lat": lat, "lng": lng, "lang": lang, "kind_pattern": f"%{contact_kind}%"},
    )
    contacts = [
        LostFoundContact(
            name=r["name"],
            phone=r["phone"],
            address=r["address"],
            kind=r["kind"],
            distance_km=r["distance_km"],
        )
        for r in rows.mappings().fetchall()
    ]

    steps_data = _LOST_STEPS.get(item_type, _DEFAULT_STEPS)
    steps = steps_data.get(lang) or steps_data.get("en") or []

    return LostFoundResponse(
        item_type=item_type,
        steps=steps,
        nearest_help=contacts,
        emergency_number="102",
        tourist_police="+998712444444",
    )
