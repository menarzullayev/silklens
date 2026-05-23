"""B2B listing search — hotels, restaurants, transport. SILK-0056.

GET /v1/listings                — search by category, location, dietary tags
GET /v1/listings/{listing_id}   — single listing detail

No auth required for read-only search; rate-limited per IP.

Schema notes (from migration 0053 + 0100):
  - Location columns: lat / lng  (numeric(9,6)) — NOT latitude/longitude
  - Contact phone:    contact_phone
  - Website:         website
  - Status guard:    status = 'active'  (not is_active boolean)
  - Name/description: jsonb, e.g. {"en": "...", "ru": "..."}
  - dietary_tags, transport_type, city, rating_avg, review_count, sort_order
    added by migration 0100.
"""

from __future__ import annotations

import math
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.middleware.ratelimit import rate_limit

router = APIRouter(tags=["listings"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

_VALID_CATEGORIES = frozenset(
    {"hotel", "restaurant", "transport", "tour_agency", "souvenir", "museum_partner"}
)
_VALID_DIETARY = frozenset({"halal", "vegetarian", "vegan", "gluten_free", "kosher"})

# Fixed SELECT columns — server-controlled, never user-interpolated.
_SELECT_COLS = (
    "bl.id, bl.name::text AS name_raw, bl.category_slug,"
    " bl.lat, bl.lng, bl.dietary_tags, bl.transport_type,"
    " bl.price_range, bl.contact_phone, bl.website,"
    " bl.rating_avg, bl.review_count,"
    " COALESCE(bl.name->>:lang, bl.name->>'en') AS name"
)


def _build_search_sql(distance_select: str, where_sql: str, order_by: str) -> str:
    """Assemble the search query from server-side constant fragments.

    All three arguments are composed from validated enum-checked constants.
    No user-supplied text is ever interpolated; user values travel via
    SQLAlchemy :param binds in the accompanying params dict.
    """
    return (
        "SELECT "  # noqa: S608 — parts built from server-side constants, no user input
        + _SELECT_COLS
        + ", "
        + distance_select
        + " FROM b2b_listings bl WHERE "
        + where_sql
        + " ORDER BY "
        + order_by
        + " LIMIT :limit OFFSET :offset"
    )


# --- DTOs --------------------------------------------------------------------


class ListingItem(BaseModel):
    id: UUID
    slug: str | None
    name: str | None
    category_slug: str
    lat: float | None
    lng: float | None
    dietary_tags: list[str]
    transport_type: str | None
    price_range: str | None
    contact_phone: str | None
    website: str | None
    rating_avg: float
    review_count: int
    distance_km: float | None


class ListingsResponse(BaseModel):
    items: list[ListingItem]
    total: int
    limit: int
    offset: int


class ListingDetail(BaseModel):
    id: UUID
    slug: str | None
    name: str | None
    description: str | None
    category_slug: str
    lat: float | None
    lng: float | None
    dietary_tags: list[str]
    transport_type: str | None
    price_range: str | None
    contact_phone: str | None
    website: str | None
    rating_avg: float
    review_count: int


# --- Routes ------------------------------------------------------------------


@router.get(
    "/v1/listings",
    response_model=ListingsResponse,
    dependencies=[
        Depends(rate_limit("60/minute", per="ip", scope="listings:search")),
    ],
)
async def search_listings(
    session: SessionDep,
    category: str = Query(
        ...,
        description="hotel|restaurant|transport|tour_agency|souvenir|museum_partner",
    ),
    lat: float | None = Query(None, ge=-90, le=90),
    lng: float | None = Query(None, ge=-180, le=180),
    radius_km: float = Query(10.0, gt=0, le=100),
    dietary: str | None = Query(None, description="halal|vegetarian|vegan|gluten_free|kosher"),
    city: str | None = Query(None, max_length=100),
    language: str = Query("en", min_length=2, max_length=10),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0, le=10_000_000),
) -> ListingsResponse:
    """Search active B2B listings by category, location and dietary preference.

    Geographic filtering uses a bounding-box approximation (no PostGIS needed).
    Results are ordered by distance when lat/lng are supplied, otherwise by
    sort_order (editorial) then by id.
    """
    if category not in _VALID_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "listings.invalid_category",
                "message": f"category must be one of: {', '.join(sorted(_VALID_CATEGORIES))}",
            },
        )

    lang = language.split("-")[0].lower()
    params: dict[str, Any] = {"category": category, "lang": lang, "limit": limit, "offset": offset}

    wheres: list[str] = ["bl.category_slug = :category", "bl.status = 'active'"]

    if dietary and dietary in _VALID_DIETARY:
        wheres.append(":dietary = ANY(bl.dietary_tags)")
        params["dietary"] = dietary

    if city:
        wheres.append("bl.city ILIKE :city")
        params["city"] = "%" + city + "%"

    distance_select = "NULL::float AS distance_km"
    order_by = "bl.sort_order, bl.id"

    if lat is not None and lng is not None:
        lat_delta = radius_km / 111.0
        cos_lat = max(math.cos(math.radians(lat)), 0.0001)
        lng_delta = radius_km / (111.0 * cos_lat)
        wheres.append(
            "(bl.lat BETWEEN :lat_min AND :lat_max AND bl.lng BETWEEN :lng_min AND :lng_max)"
        )
        params.update(
            {
                "lat_min": lat - lat_delta,
                "lat_max": lat + lat_delta,
                "lng_min": lng - lng_delta,
                "lng_max": lng + lng_delta,
                "lat_center": lat,
                "lng_center": lng,
            }
        )
        # Postgres earthdistance <@>: point(lng, lat); converts miles → km.
        distance_select = (
            "round((point(:lng_center, :lat_center) <@>"
            " point(bl.lng::float8, bl.lat::float8))::numeric * 1.60934, 2)"
            " AS distance_km"
        )
        order_by = "distance_km NULLS LAST, bl.sort_order"

    query_sql = _build_search_sql(distance_select, " AND ".join(wheres), order_by)
    rows = await session.execute(text(query_sql), params)
    mappings = rows.mappings().fetchall()
    items = [
        ListingItem(
            id=r["id"],
            slug=None,
            name=r["name"],
            category_slug=r["category_slug"],
            lat=float(r["lat"]) if r["lat"] is not None else None,
            lng=float(r["lng"]) if r["lng"] is not None else None,
            dietary_tags=list(r["dietary_tags"]) if r["dietary_tags"] else [],
            transport_type=r["transport_type"],
            price_range=r["price_range"],
            contact_phone=r["contact_phone"],
            website=r["website"],
            rating_avg=float(r["rating_avg"]) if r["rating_avg"] is not None else 0.0,
            review_count=int(r["review_count"]) if r["review_count"] is not None else 0,
            distance_km=float(r["distance_km"]) if r["distance_km"] is not None else None,
        )
        for r in mappings
    ]
    return ListingsResponse(items=items, total=len(items), limit=limit, offset=offset)


@router.get(
    "/v1/listings/{listing_id}",
    response_model=ListingDetail,
)
async def get_listing(
    listing_id: UUID,
    session: SessionDep,
    language: str = Query("en", min_length=2, max_length=10),
) -> ListingDetail:
    """Fetch a single active B2B listing by its UUID. Public — no auth required."""
    lang = language.split("-")[0].lower()

    row = await session.execute(
        text(
            """
            SELECT
                bl.id,
                bl.category_slug,
                bl.lat,
                bl.lng,
                bl.dietary_tags,
                bl.transport_type,
                bl.price_range,
                bl.contact_phone,
                bl.website,
                bl.rating_avg,
                bl.review_count,
                COALESCE(bl.name->>:lang,        bl.name->>'en')        AS name,
                COALESCE(bl.description->>:lang, bl.description->>'en') AS description
            FROM b2b_listings bl
            WHERE bl.id = :lid
              AND bl.status = 'active'
            """
        ),
        {"lid": str(listing_id), "lang": lang},
    )
    result = row.mappings().fetchone()
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "listings.not_found", "message": "listing not found"},
        )

    return ListingDetail(
        id=result["id"],
        slug=None,
        name=result["name"],
        description=result["description"],
        category_slug=result["category_slug"],
        lat=float(result["lat"]) if result["lat"] is not None else None,
        lng=float(result["lng"]) if result["lng"] is not None else None,
        dietary_tags=list(result["dietary_tags"]) if result["dietary_tags"] else [],
        transport_type=result["transport_type"],
        price_range=result["price_range"],
        contact_phone=result["contact_phone"],
        website=result["website"],
        rating_avg=float(result["rating_avg"]) if result["rating_avg"] is not None else 0.0,
        review_count=int(result["review_count"]) if result["review_count"] is not None else 0,
    )
