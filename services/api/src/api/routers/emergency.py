"""Emergency contacts — public safety directory.

SILK-0057: Country-keyed, multilingual emergency contacts.
No authentication required — these endpoints are intentionally public so
distressed travellers with no account can still reach them.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session

router = APIRouter(tags=["emergency"])

SessionDep = Annotated[AsyncSession, __import__("fastapi").Depends(get_session)]


# --- Response schemas ---------------------------------------------------------


class EmergencyContactOut(BaseModel):
    id: str
    country_code: str
    kind: str
    name: str | None
    phone: str | None
    phone_alt: str | None
    address: str | None
    latitude: float | None
    longitude: float | None
    languages_spoken: list[str]
    is_24h: bool


class NearestContactOut(BaseModel):
    id: str
    kind: str
    name: str | None
    phone: str | None
    address: str | None
    latitude: float | None
    longitude: float | None
    is_24h: bool
    distance_km: float | None


# --- Routes -------------------------------------------------------------------


@router.get(
    "/v1/emergency",
    response_model=list[EmergencyContactOut],
    summary="List emergency contacts by country",
)
async def list_emergency_contacts(
    session: SessionDep,
    country_code: str = Query(
        "UZ",
        min_length=2,
        max_length=2,
        description="ISO 3166-1 alpha-2 country code",
    ),
    language: str = Query("en", min_length=2, max_length=10),
    kind: str | None = Query(
        None,
        description="Filter by kind: ambulance|police|fire|hospital|embassy|tourist_police",
    ),
) -> list[EmergencyContactOut]:
    """Public emergency contacts directory. No auth required.

    Returns active emergency contacts for the given country, ordered by
    sort_order then kind. The ``name`` and ``address`` fields are resolved
    to the requested language with English as fallback.
    """
    country = country_code.upper()
    lang = language.split("-")[0].lower()

    params: dict[str, Any] = {"country": country, "lang": lang}
    kind_clause = ""
    if kind is not None:
        kind_clause = "AND kind = :kind"
        params["kind"] = kind

    result = await session.execute(
        text(
            f"""
            SELECT
                id::text,
                country_code,
                kind,
                COALESCE(name ->> :lang, name ->> 'en') AS name,
                phone,
                phone_alt,
                COALESCE(address ->> :lang, address ->> 'en') AS address,
                latitude::float,
                longitude::float,
                languages_spoken,
                is_24h
            FROM emergency_contacts
            WHERE country_code = :country
              AND is_active = true
              {kind_clause}
            ORDER BY sort_order, kind
            """  # noqa: S608 — no user input in the f-string; kind_clause is a fixed string literal
        ),
        params,
    )
    rows = result.mappings().fetchall()
    return [
        EmergencyContactOut(
            id=r["id"],
            country_code=r["country_code"],
            kind=r["kind"],
            name=r["name"],
            phone=r["phone"],
            phone_alt=r["phone_alt"],
            address=r["address"],
            latitude=r["latitude"],
            longitude=r["longitude"],
            languages_spoken=list(r["languages_spoken"] or []),
            is_24h=bool(r["is_24h"]),
        )
        for r in rows
    ]


@router.get(
    "/v1/emergency/nearest",
    response_model=list[NearestContactOut],
    summary="Find nearest emergency contacts by coordinates",
)
async def nearest_emergency(
    session: SessionDep,
    lat: float = Query(..., description="Current latitude (WGS-84)"),
    lng: float = Query(..., description="Current longitude (WGS-84)"),
    kind: str = Query(
        "hospital",
        min_length=2,
        max_length=30,
        description="Contact kind: ambulance|police|fire|hospital",
    ),
    language: str = Query("en", min_length=2, max_length=10),
    limit: int = Query(3, ge=1, le=10),
) -> list[NearestContactOut]:
    """Find nearest emergency contacts by GPS coordinates. No auth required.

    Uses the PostgreSQL ``<@>`` earth-distance operator (degrees) converted to
    kilometres. Contacts without coordinates are sorted last.
    """
    lang = language.split("-")[0].lower()

    result = await session.execute(
        text(
            """
            SELECT
                id::text,
                kind,
                COALESCE(name ->> :lang, name ->> 'en') AS name,
                phone,
                COALESCE(address ->> :lang, address ->> 'en') AS address,
                latitude::float,
                longitude::float,
                is_24h,
                CASE
                    WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN
                        round(
                            (
                                point(:lng, :lat) <@>
                                point(longitude::float8, latitude::float8)
                            )::numeric * 1.60934,
                            2
                        )
                    ELSE NULL
                END AS distance_km
            FROM emergency_contacts
            WHERE is_active = true
              AND kind = :kind
            ORDER BY
                CASE
                    WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN
                        point(:lng, :lat) <@> point(longitude::float8, latitude::float8)
                    ELSE 999999
                END
            LIMIT :limit
            """
        ),
        {"lat": lat, "lng": lng, "kind": kind, "lang": lang, "limit": limit},
    )
    rows = result.mappings().fetchall()
    return [
        NearestContactOut(
            id=r["id"],
            kind=r["kind"],
            name=r["name"],
            phone=r["phone"],
            address=r["address"],
            latitude=r["latitude"],
            longitude=r["longitude"],
            is_24h=bool(r["is_24h"]),
            distance_km=float(r["distance_km"]) if r["distance_km"] is not None else None,
        )
        for r in rows
    ]
