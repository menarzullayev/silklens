"""Carbon footprint tracker for eco-aware travel. SILK-0085."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.middleware.ratelimit import rate_limit

router = APIRouter(tags=["sustainability"])

# CO2 emissions in kg per km per person (IPCC / EEA data)
_EMISSION_FACTORS: dict[str, float] = {
    "flight_domestic": 0.255,
    "flight_international": 0.195,
    "car_petrol": 0.171,
    "car_diesel": 0.152,
    "car_electric": 0.047,
    "car_hybrid": 0.110,
    "bus": 0.089,
    "train": 0.041,
    "tram": 0.029,
    "metro": 0.031,
    "bicycle": 0.0,
    "walk": 0.0,
    "taxi": 0.171,
    "shared_taxi": 0.060,
}

_ECO_ALTERNATIVES = {
    "car_petrol": "train",
    "car_diesel": "train",
    "taxi": "shared_taxi",
    "flight_domestic": "train",
}


class JourneyLeg(BaseModel):
    transport_type: str = Field(
        ...,
        description="flight_domestic|car_petrol|bus|train|bicycle|walk|taxi",
    )
    distance_km: float = Field(..., gt=0, le=20000)


class CarbonRequest(BaseModel):
    journey_legs: list[JourneyLeg] = Field(..., min_length=1, max_length=20)
    language: str = Field("en", min_length=2, max_length=10)


@router.post("/v1/me/carbon-footprint")
async def calculate_carbon(
    body: CarbonRequest,
    _rl: None = Depends(rate_limit("30/minute", per="ip", scope="carbon:calculate")),
) -> dict:
    """Calculate carbon footprint for a journey. No auth required."""
    lang = body.language.split("-")[0].lower()

    total_co2_kg = 0.0
    legs_result = []
    eco_savings = 0.0

    for leg in body.journey_legs:
        transport = leg.transport_type.lower()
        factor = _EMISSION_FACTORS.get(transport, 0.171)
        co2_kg = round(leg.distance_km * factor, 2)
        total_co2_kg += co2_kg

        alt = _ECO_ALTERNATIVES.get(transport)
        alt_factor = _EMISSION_FACTORS.get(alt, factor) if alt else factor
        leg_saving = round(leg.distance_km * (factor - alt_factor), 2)
        eco_savings += leg_saving

        legs_result.append(
            {
                "transport_type": transport,
                "distance_km": leg.distance_km,
                "co2_kg": co2_kg,
                "is_eco_friendly": factor <= 0.05,
                "eco_alternative": alt,
                "potential_saving_kg": leg_saving if alt else 0,
            }
        )

    total_co2_kg = round(total_co2_kg, 2)
    eco_savings = round(eco_savings, 2)

    # Carbon offset equivalents
    trees_equivalent = round(total_co2_kg / 21.77, 1)  # avg tree absorbs 21.77 kg CO2/yr

    grade = (
        "A"
        if total_co2_kg < 10
        else ("B" if total_co2_kg < 50 else ("C" if total_co2_kg < 150 else "D"))
    )

    tip_map = {
        "A": {
            "en": "Excellent! Your journey has a minimal carbon footprint.",
            "uz": "A'lo! Sayohatingiz minimal karbon iziga ega.",
            "ru": "Отлично! Ваше путешествие имеет минимальный углеродный след.",
        },
        "B": {
            "en": "Good job! Consider trains for longer legs to reduce your footprint.",
            "uz": "Yaxshi! Uzoq masofalarda poyezddan foydalaning.",
            "ru": "Хорошо! Рассмотрите поезда для длинных отрезков пути.",
        },
        "C": {
            "en": "Moderate footprint. Offsetting with a tree donation would help!",
            "uz": "O'rtacha iz. Daraxt o'tqazish bilan kompensatsiya qiling!",
            "ru": "Умеренный след. Компенсируйте посадкой деревьев!",
        },
        "D": {
            "en": "High impact journey. Consider eco-alternatives where possible.",
            "uz": "Yuqori ta'sir. Iloji boricha ekologik muqobillarni ko'rib chiqing.",
            "ru": "Большое воздействие. Рассмотрите экологические альтернативы.",
        },
    }
    tip = tip_map[grade].get(lang) or tip_map[grade]["en"]

    return {
        "language": lang,
        "total_co2_kg": total_co2_kg,
        "grade": grade,
        "tip": tip,
        "trees_to_offset": trees_equivalent,
        "potential_eco_savings_kg": eco_savings,
        "legs": legs_result,
    }


@router.get("/v1/ai/eco-alternatives")
async def eco_alternatives(
    transport: str,
    language: str = "en",
    # Reserved for future distance-aware recommendations; accepted but not yet used.
    _from_city: str | None = None,
    _to_city: str | None = None,
    _rl: None = Depends(rate_limit("30/minute", per="ip", scope="carbon:eco")),
) -> dict:
    """Get eco-friendly travel alternatives. No auth required."""
    lang = language.split("-")[0].lower()
    alt = _ECO_ALTERNATIVES.get(transport.lower())
    original_factor = _EMISSION_FACTORS.get(transport.lower(), 0.171)
    alt_factor = _EMISSION_FACTORS.get(alt, original_factor) if alt else original_factor

    return {
        "language": lang,
        "transport": transport,
        "co2_kg_per_km": original_factor,
        "eco_alternative": alt,
        "alternative_co2_kg_per_km": alt_factor,
        "saving_pct": (
            round((1 - alt_factor / original_factor) * 100, 1) if original_factor > 0 and alt else 0
        ),
        "recommendation": (
            f"Switch from {transport} to {alt} to reduce emissions by "
            f"{round((1 - alt_factor / original_factor) * 100)}%"
            if alt and original_factor > 0
            else "Already an eco-friendly choice!"
        ),
    }
