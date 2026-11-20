"""Heritage check-in and crowd-prediction endpoints. SILK-0075.

POST /v1/me/check-in                      — record a visit (anonymous or authenticated)
GET  /v1/heritage/{pub_id}/crowd-forecast — predicted + live crowd level (public)
"""

from __future__ import annotations

import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.middleware.auth import OptionalUserDep
from src.middleware.ratelimit import rate_limit

router = APIRouter(tags=["crowd"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


# --- DTOs --------------------------------------------------------------------


class CheckInRequest(BaseModel):
    heritage_pub_id: UUID


class CheckInResponse(BaseModel):
    checked_in: bool
    heritage_pub_id: UUID


class BestTimeSlot(BaseModel):
    day_of_week: int
    hour_of_day: int
    expected_crowd: str


class CrowdForecastResponse(BaseModel):
    heritage_pub_id: UUID
    current_crowd: str
    live_check_ins_2h: int
    predicted_crowd: str
    best_times: list[BestTimeSlot]
    data_source: str


# --- Routes ------------------------------------------------------------------


@router.post(
    "/v1/me/check-in",
    response_model=CheckInResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(rate_limit("10/minute", per="ip", scope="crowd:checkin")),
    ],
)
async def check_in(
    payload: CheckInRequest,
    ctx: OptionalUserDep,
    session: SessionDep,
) -> CheckInResponse:
    """Record a visit/check-in to a heritage site.

    Accepts anonymous (no bearer) and authenticated requests. The time-part
    columns (day_of_week, hour_of_day, month_of_year) are filled by a
    BEFORE-INSERT trigger so the INSERT only needs heritage_pub_id + user_id.
    No PII is logged; user_id is stored for deduplication only.
    """
    user_id = ctx.user_id if ctx else None

    await session.execute(
        text(
            """
            INSERT INTO heritage_check_ins (heritage_pub_id, user_id)
            VALUES (:pub_id, :user_id)
            """
        ),
        {
            "pub_id": str(payload.heritage_pub_id),
            "user_id": str(user_id) if user_id else None,
        },
    )
    await session.commit()

    return CheckInResponse(checked_in=True, heritage_pub_id=payload.heritage_pub_id)


@router.get(
    "/v1/heritage/{pub_id}/crowd-forecast",
    response_model=CrowdForecastResponse,
)
async def crowd_forecast(
    pub_id: UUID,
    session: SessionDep,
) -> CrowdForecastResponse:
    """Return crowd forecast for a heritage site. Public — no auth required.

    Combines:
    - A statistical prediction from crowd_predictions (populated offline by a
      background job aggregating check-in history).
    - A live indicator derived from check-ins recorded in the last 2 hours.

    When live check-ins are available they override the prediction label so the
    response reflects real-time busyness.
    """
    now = datetime.datetime.now(datetime.UTC)
    # Python weekday(): 0=Mon … 6=Sun.  Postgres DOW: 0=Sun … 6=Sat.
    # Convert: Python weekday → Postgres DOW
    current_dow = (now.weekday() + 1) % 7
    current_hour = now.hour
    current_month = now.month

    # --- Statistical prediction for this hour ---
    pred_row = await session.execute(
        text(
            """
            SELECT expected_crowd, sample_size
            FROM crowd_predictions
            WHERE heritage_pub_id = :pub_id
              AND day_of_week   = :dow
              AND hour_of_day   = :hour
              AND month_of_year = :month
            """
        ),
        {
            "pub_id": str(pub_id),
            "dow": current_dow,
            "hour": current_hour,
            "month": current_month,
        },
    )
    pred = pred_row.mappings().fetchone()
    predicted_crowd = pred["expected_crowd"] if pred else "unknown"

    # --- Best low-crowd slots this month ---
    best_rows = await session.execute(
        text(
            """
            SELECT day_of_week, hour_of_day, expected_crowd
            FROM crowd_predictions
            WHERE heritage_pub_id = :pub_id
              AND month_of_year   = :month
              AND expected_crowd  IN ('low', 'unknown')
            ORDER BY
                CASE expected_crowd WHEN 'low' THEN 0 ELSE 1 END,
                day_of_week,
                hour_of_day
            LIMIT 5
            """
        ),
        {"pub_id": str(pub_id), "month": current_month},
    )
    best_times = [
        BestTimeSlot(
            day_of_week=r["day_of_week"],
            hour_of_day=r["hour_of_day"],
            expected_crowd=r["expected_crowd"],
        )
        for r in best_rows.mappings().fetchall()
    ]

    # --- Live indicator: check-ins in the last 2 hours ---
    live_row = await session.execute(
        text(
            """
            SELECT COUNT(*) AS recent_count
            FROM heritage_check_ins
            WHERE heritage_pub_id = :pub_id
              AND checked_in_at > now() - interval '2 hours'
            """
        ),
        {"pub_id": str(pub_id)},
    )
    recent_count: int = live_row.scalar() or 0

    # Derive live crowd label from recent check-in volume
    if recent_count >= 20:
        live_label = "very_high"
    elif recent_count >= 10:
        live_label = "high"
    elif recent_count >= 3:
        live_label = "medium"
    elif recent_count >= 1:
        live_label = "low"
    else:
        live_label = predicted_crowd  # fall back to statistical prediction

    data_source = "live" if recent_count > 0 else "prediction"

    return CrowdForecastResponse(
        heritage_pub_id=pub_id,
        current_crowd=live_label,
        live_check_ins_2h=recent_count,
        predicted_crowd=predicted_crowd,
        best_times=best_times,
        data_source=data_source,
    )
