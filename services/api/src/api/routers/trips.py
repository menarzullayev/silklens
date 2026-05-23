"""AI-powered trip planning endpoints. SILK-0061.

POST /v1/trips              — create AI-generated multi-city itinerary (auth required)
GET  /v1/trips              — list user's trips (auth required)
GET  /v1/trips/{trip_id}    — get trip with stops (auth required)
POST /v1/trips/quick-plan   — quick itinerary for limited time (public)
"""

from __future__ import annotations

import json
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, StrictFloat
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.settings import get_settings
from src.middleware.auth import CurrentUserDep
from src.middleware.ratelimit import rate_limit

router = APIRouter(prefix="/v1/trips", tags=["trips"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


# --- Request / Response Models ---


class TripCreate(BaseModel):
    title: str | None = Field(None, max_length=200)
    cities: list[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="List of city names, e.g. ['samarkand', 'bukhara', 'khiva']",
    )
    start_date: str | None = Field(None, description="ISO date YYYY-MM-DD")
    end_date: str | None = Field(None, description="ISO date YYYY-MM-DD")
    budget_usd: float | None = Field(None, gt=0, le=100_000)
    interests: list[str] = Field(
        default_factory=list,
        description="history|food|shopping|nature|art|architecture",
    )
    language: str = Field("en", min_length=2, max_length=10)


class TripOut(BaseModel):
    id: str
    title: str | None
    status: str
    cities: list[str]
    start_date: str | None
    end_date: str | None
    budget_usd: float | None
    created_at: str
    ai_plan: dict[str, Any] | None = None


class TripListOut(BaseModel):
    items: list[dict[str, Any]]
    total: int


class TripDetailOut(BaseModel):
    id: str
    title: str | None
    status: str
    cities: list[str]
    start_date: str | None
    end_date: str | None
    budget_usd: float | None
    interests: list[str]
    ai_plan_json: dict[str, Any] | None
    created_at: str
    stops: list[dict[str, Any]]


class QuickPlanRequest(BaseModel):
    available_hours: float = Field(2.0, gt=0, le=24)
    # ``StrictFloat`` so ``"lng": false`` / ``"lng": 0`` (int) are rejected
    # before they reach the planner — vanilla ``float`` coerces booleans
    # to ``0.0`` / ``1.0`` and produces nonsensical coordinates.
    lat: StrictFloat | None = None
    lng: StrictFloat | None = None
    city: str | None = Field(None, max_length=100)
    interests: list[str] = Field(default_factory=list)
    language: str = Field("en", min_length=2, max_length=10)


class QuickPlanOut(BaseModel):
    available_hours: float
    recommended_stops: list[dict[str, Any]]
    total_time_min: int
    total_stops: int
    city: str | None


# --- AI Planning Helper ---


async def _generate_ai_itinerary(
    cities: list[str],
    days: int | None,
    budget_usd: float | None,
    interests: list[str],
    language: str,
    heritage_list: list[dict[str, Any]],
) -> dict[str, Any]:
    """Call LLM to generate a structured itinerary JSON."""
    settings = get_settings()

    # anthropic_api_key is not in Settings; use the standard env var via the
    # anthropic SDK (it reads ANTHROPIC_API_KEY automatically). We gate on
    # ai_use_mock_providers to keep dev/test fully offline.
    use_mock = settings.ai_use_mock_providers

    city_str = " → ".join(cities)
    heritage_summary = "\n".join(
        "- {} ({}, {})".format(
            h.get("name", ""),
            h.get("city", h.get("country_code", "")),
            h.get("kind_slug", ""),
        )
        for h in heritage_list[:20]
    )
    interests_str = ", ".join(interests) if interests else "general sightseeing"
    days_str = f"{days} days" if days else "flexible duration"
    budget_str = f"${budget_usd:.0f} USD total" if budget_usd else "no specific budget"

    prompt = f"""Create a detailed travel itinerary for this Silk Road trip:

Route: {city_str}
Duration: {days_str}
Budget: {budget_str}
Interests: {interests_str}
Language for the response: {language}

Available heritage sites:
{heritage_summary}

Return a JSON object with this exact structure:
{{
  "title": "Trip title in {language}",
  "summary": "Brief trip overview in {language}",
  "days": [
    {{
      "day": 1,
      "city": "city name",
      "theme": "day theme",
      "stops": [
        {{
          "name": "heritage site name",
          "kind": "heritage|restaurant|hotel|transport",
          "duration_min": 90,
          "estimated_cost_usd": 5.0,
          "transport_from_prev": "walk|taxi|bus|train",
          "travel_time_min": 10,
          "tip": "brief visit tip in {language}"
        }}
      ],
      "estimated_total_cost_usd": 50.0
    }}
  ],
  "total_cost_estimate_usd": 150.0,
  "tips": ["general travel tip in {language}"]
}}

Return only valid JSON, no markdown."""

    if use_mock:
        return _stub_itinerary(cities, days or len(cities))

    try:
        import anthropic

        client = anthropic.AsyncAnthropic()  # reads ANTHROPIC_API_KEY from env
        response = await client.messages.create(
            model=settings.anthropic_model_default,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        block = response.content[0]
        if not hasattr(block, "text"):
            return _stub_itinerary(cities, days or len(cities))
        raw: str = block.text.strip()
        # Strip markdown code fences if the model wrapped the JSON
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed: dict[str, Any] = json.loads(raw)
        return parsed
    except Exception:
        return _stub_itinerary(cities, days or len(cities))


def _stub_itinerary(cities: list[str], days: int) -> dict[str, Any]:
    """Deterministic stub itinerary returned in dev / when ai_use_mock_providers=true.

    Tips are English-only; the real LLM path honours the language parameter.
    """
    day_plans = []
    for i, city in enumerate(cities[:days]):
        day_plans.append(
            {
                "day": i + 1,
                "city": city.title(),
                "theme": f"Explore {city.title()}",
                "stops": [
                    {
                        "name": f"{city.title()} Historic Center",
                        "kind": "heritage",
                        "duration_min": 120,
                        "estimated_cost_usd": 5.0,
                        "transport_from_prev": "walk",
                        "travel_time_min": 10,
                        "tip": "Start early to avoid crowds",
                    },
                    {
                        "name": f"{city.title()} Local Restaurant",
                        "kind": "restaurant",
                        "duration_min": 60,
                        "estimated_cost_usd": 8.0,
                        "transport_from_prev": "walk",
                        "travel_time_min": 5,
                        "tip": "Try local plov",
                    },
                ],
                "estimated_total_cost_usd": 30.0,
            }
        )
    return {
        "title": "Silk Road: {}".format(" → ".join(c.title() for c in cities)),
        "summary": f"A {days}-day journey through Uzbekistan's historic cities.",
        "days": day_plans,
        "total_cost_estimate_usd": 30.0 * days,
        "tips": ["Carry local currency (UZS)", "Dress modestly for mosques"],
    }


# --- Endpoints ---


@router.post(
    "",
    response_model=TripOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("5/minute", per="user", scope="trips:create"))],
)
async def create_trip(
    body: TripCreate,
    ctx: CurrentUserDep,
    db: SessionDep,
) -> TripOut:
    """Create an AI-generated multi-city trip itinerary. SILK-0061.

    Fetches relevant heritage sites for the requested cities, calls the LLM to
    produce a day-by-day itinerary, saves the trip + stop rows in one
    transaction, and returns the AI plan inline.
    """
    lang = body.language.split("-")[0].lower()

    # Fetch relevant heritage sites for the requested cities
    heritage_list: list[dict[str, Any]] = []
    for city in body.cities[:5]:
        city_pat = f"%{city.lower()}%"
        rows = await db.execute(
            text("""
                SELECT pub_id, name, kind_slug, country_code,
                       latitude AS lat, longitude AS lng
                FROM heritage_objects
                WHERE status = 'published'
                  AND deleted_at IS NULL
                  AND (
                      LOWER(admin_path) LIKE :city
                      OR LOWER(country_code) = 'uz'
                  )
                ORDER BY confidence_score DESC
                LIMIT 10
            """),
            {"city": city_pat},
        )
        for r in rows.mappings().fetchall():
            raw_name = r["name"]
            if isinstance(raw_name, dict):
                display_name: str = raw_name.get(lang) or raw_name.get("en") or str(raw_name)
            else:
                display_name = str(raw_name) if raw_name else ""
            heritage_list.append(
                {
                    "name": display_name,
                    "pub_id": str(r["pub_id"]),
                    "kind_slug": r["kind_slug"],
                    "country_code": r["country_code"],
                    "city": city,
                    "lat": r["lat"],
                    "lng": r["lng"],
                }
            )

    # Calculate trip duration
    days: int
    if body.start_date and body.end_date:
        from datetime import date

        try:
            d1 = date.fromisoformat(body.start_date)
            d2 = date.fromisoformat(body.end_date)
            days = max(1, (d2 - d1).days + 1)
        except ValueError:
            days = len(body.cities)
    else:
        days = len(body.cities)

    # Generate AI itinerary
    ai_plan = await _generate_ai_itinerary(
        body.cities, days, body.budget_usd, body.interests, lang, heritage_list
    )

    resolved_title: str = (
        ai_plan.get("title") or body.title or "Trip to {}".format(", ".join(body.cities))
    )

    # Persist trip row
    trip_row = await db.execute(
        text("""
            INSERT INTO trips
                (user_id, residency_region, title, cities, start_date, end_date,
                 budget_usd, interests, ai_plan_json)
            VALUES (:uid, :region, :title, :cities, :start, :end,
                    :budget, :interests, :plan::jsonb)
            RETURNING id, title, status, cities, start_date, end_date,
                      budget_usd, created_at
        """),
        {
            "uid": ctx.user_id,
            "region": ctx.residency_region.value,
            "title": resolved_title,
            "cities": body.cities,
            "start": body.start_date,
            "end": body.end_date,
            "budget": body.budget_usd,
            "interests": body.interests,
            "plan": json.dumps(ai_plan),
        },
    )
    trip = dict(trip_row.mappings().fetchone())  # type: ignore[arg-type]
    trip_id = trip["id"]

    # Persist trip stops produced by the AI plan
    for day_plan in ai_plan.get("days", []):
        day_num: int = day_plan.get("day", 1)
        for idx, stop in enumerate(day_plan.get("stops", [])):
            await db.execute(
                text("""
                    INSERT INTO trip_stops
                        (trip_id, day_number, order_in_day, stop_name, stop_kind,
                         visit_duration_min, estimated_cost_usd,
                         transport_to_next, travel_time_min, notes)
                    VALUES (:tid, :day, :order, :name, :kind,
                            :duration, :cost, :transport, :travel, :tip)
                """),
                {
                    "tid": str(trip_id),
                    "day": day_num,
                    "order": idx,
                    "name": stop.get("name", "")[:200],
                    "kind": stop.get("kind", "heritage")[:30],
                    "duration": stop.get("duration_min", 60),
                    "cost": stop.get("estimated_cost_usd"),
                    "transport": (stop.get("transport_from_prev") or "")[:30] or None,
                    "travel": stop.get("travel_time_min"),
                    "tip": stop.get("tip"),
                },
            )

    await db.commit()

    return TripOut(
        id=str(trip_id),
        title=trip["title"],
        status=trip["status"],
        cities=trip["cities"],
        start_date=trip["start_date"].isoformat() if trip["start_date"] else None,
        end_date=trip["end_date"].isoformat() if trip["end_date"] else None,
        budget_usd=float(trip["budget_usd"]) if trip["budget_usd"] is not None else None,
        created_at=trip["created_at"].isoformat(),
        ai_plan=ai_plan,
    )


@router.get(
    "",
    response_model=TripListOut,
    dependencies=[Depends(rate_limit("60/minute", per="user", scope="trips:list"))],
)
async def list_trips(
    ctx: CurrentUserDep,
    db: SessionDep,
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0, le=10_000_000),
) -> TripListOut:
    """List the authenticated user's trips, newest first."""
    rows = await db.execute(
        text("""
            SELECT id, title, status, cities, start_date, end_date,
                   budget_usd, created_at
            FROM trips
            WHERE user_id = :uid
              AND residency_region = :region
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """),
        {
            "uid": ctx.user_id,
            "region": ctx.residency_region.value,
            "limit": limit,
            "offset": offset,
        },
    )
    items = []
    for r in rows.mappings().fetchall():
        row = dict(r)
        row["id"] = str(row["id"])
        if row.get("start_date"):
            row["start_date"] = row["start_date"].isoformat()
        if row.get("end_date"):
            row["end_date"] = row["end_date"].isoformat()
        if row.get("budget_usd") is not None:
            row["budget_usd"] = float(row["budget_usd"])
        if row.get("created_at"):
            row["created_at"] = row["created_at"].isoformat()
        items.append(row)

    return TripListOut(items=items, total=len(items))


@router.get(
    "/{trip_id:uuid}",
    response_model=TripDetailOut,
    dependencies=[Depends(rate_limit("60/minute", per="user", scope="trips:read"))],
)
async def get_trip(
    trip_id: UUID,
    ctx: CurrentUserDep,
    db: SessionDep,
) -> TripDetailOut:
    """Get a trip with its day-by-day stops. Tenant-isolated by user_id + residency."""
    row = await db.execute(
        text("""
            SELECT id, title, status, cities, start_date, end_date,
                   budget_usd, interests, ai_plan_json, created_at
            FROM trips
            WHERE id = :tid
              AND user_id = :uid
              AND residency_region = :region
        """),
        {
            "tid": str(trip_id),
            "uid": ctx.user_id,
            "region": ctx.residency_region.value,
        },
    )
    trip = row.mappings().fetchone()
    if trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "trips.not_found", "message": "Trip not found"},
        )

    stops_rows = await db.execute(
        text("""
            SELECT id, day_number, order_in_day, stop_name, stop_kind,
                   heritage_pub_id, visit_duration_min, estimated_cost_usd,
                   transport_to_next, travel_time_min, notes, lat, lng
            FROM trip_stops
            WHERE trip_id = :tid
            ORDER BY day_number, order_in_day
        """),
        {"tid": str(trip_id)},
    )
    stops = []
    for s in stops_rows.mappings().fetchall():
        stop = dict(s)
        stop["id"] = str(stop["id"])
        if stop.get("heritage_pub_id"):
            stop["heritage_pub_id"] = str(stop["heritage_pub_id"])
        if stop.get("estimated_cost_usd") is not None:
            stop["estimated_cost_usd"] = float(stop["estimated_cost_usd"])
        stops.append(stop)

    t = dict(trip)
    return TripDetailOut(
        id=str(t["id"]),
        title=t["title"],
        status=t["status"],
        cities=t["cities"] or [],
        start_date=t["start_date"].isoformat() if t["start_date"] else None,
        end_date=t["end_date"].isoformat() if t["end_date"] else None,
        budget_usd=float(t["budget_usd"]) if t["budget_usd"] is not None else None,
        interests=t["interests"] or [],
        ai_plan_json=t["ai_plan_json"],
        created_at=t["created_at"].isoformat(),
        stops=stops,
    )


@router.post(
    "/quick-plan",
    response_model=QuickPlanOut,
    dependencies=[Depends(rate_limit("10/minute", per="ip", scope="trips:quick"))],
)
async def quick_plan(
    body: QuickPlanRequest,
    db: SessionDep,
) -> QuickPlanOut:
    """Quick itinerary for limited time — no auth required.

    Answers 'I have N hours, what should I see?' queries. Looks up nearby
    heritage sites (ordered by distance when lat/lng provided, otherwise by
    confidence_score) and assembles a feasible stop list within the available
    window.
    """
    lang = body.language.split("-")[0].lower()
    available_stops = max(1, int(body.available_hours / 1.5))  # ~1.5 h per heritage stop

    default_lat = body.lat if body.lat is not None else 39.65
    default_lng = body.lng if body.lng is not None else 66.97

    if body.lat is not None and body.lng is not None:
        order_clause = "(point(:lng_f, :lat_f) <@> point(longitude::float8, latitude::float8))"
    else:
        order_clause = "confidence_score DESC"

    rows = await db.execute(
        text(f"""
            SELECT pub_id,
                   COALESCE(name->>:lang, name->>'en') AS name,
                   kind_slug, latitude AS lat, longitude AS lng,
                   CASE WHEN latitude IS NOT NULL THEN
                       round(
                           (point(:lng_f, :lat_f)
                            <@> point(longitude::float8, latitude::float8)
                           )::numeric * 1.60934, 1)
                   ELSE NULL END AS distance_km
            FROM heritage_objects
            WHERE status = 'published'
              AND deleted_at IS NULL
              AND latitude IS NOT NULL
            ORDER BY {order_clause}
            LIMIT :limit
        """),  # noqa: S608 — order_clause is from a closed set above, not user input
        {
            "lang": lang,
            "lat_f": default_lat,
            "lng_f": default_lng,
            "limit": available_stops + 2,
        },
    )
    nearby = [dict(r) for r in rows.mappings().fetchall()]

    total_time = 0
    stops: list[dict[str, Any]] = []
    for site in nearby[:available_stops]:
        duration = 90 if "museum" in (site.get("kind_slug") or "") else 60
        travel = 15  # conservative travel estimate
        if total_time + duration + travel <= int(body.available_hours * 60):
            stops.append(
                {
                    "name": site.get("name"),
                    "pub_id": str(site.get("pub_id")),
                    "kind_slug": site.get("kind_slug"),
                    "distance_km": float(site["distance_km"])
                    if site.get("distance_km") is not None
                    else None,
                    "suggested_duration_min": duration,
                    "travel_to_next_min": travel,
                }
            )
            total_time += duration + travel

    return QuickPlanOut(
        available_hours=body.available_hours,
        recommended_stops=stops,
        total_time_min=total_time,
        total_stops=len(stops),
        city=body.city,
    )
