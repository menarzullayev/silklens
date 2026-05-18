"""Gamification integration tests — XP idempotency, levels, streak, leaderboards."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.gamification.entities import XpSource
from src.domain.gamification.service import GamificationService
from src.infrastructure.gamification.repository import SqlGamificationRepository

pytestmark = pytest.mark.integration


def _email() -> str:
    return f"xp-{uuid.uuid4().hex[:10]}@silklens-test.com"


async def _register(http: AsyncClient) -> dict[str, Any]:
    response = await http.post(
        "/v1/auth/register",
        json={"email": _email(), "password": "GamerDemoPass12345"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _h(auth: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {auth['tokens']['access_token']}"}


async def _user_uuid(db_session: AsyncSession, pub_id: str) -> tuple[str, str, str]:
    row = (
        await db_session.execute(
            text(
                """
                SELECT id::text, residency_region, tenant_id::text
                FROM users WHERE pub_id = :p
                """
            ),
            {"p": pub_id},
        )
    ).one()
    return row[0], row[1], row[2]


@pytest.mark.asyncio
async def test_award_xp_idempotent(http: AsyncClient, db_session: AsyncSession) -> None:
    auth = await _register(http)
    user_id, residency, tenant_id = await _user_uuid(db_session, auth["user"]["pub_id"])
    service = GamificationService(repository=SqlGamificationRepository(db_session))

    event1, balance1 = await service.award_xp(
        user_id=uuid.UUID(user_id),
        residency=residency,
        tenant_id=uuid.UUID(tenant_id),
        source_kind=XpSource.VISIT,
        source_id=None,
        delta=100,
        idempotency_key=f"visit:{user_id}:heritage1:2026-05-18",
    )
    await db_session.commit()
    assert balance1.current_xp == 100

    # Same key replays — must return the same event and not bump the balance.
    event2, balance2 = await service.award_xp(
        user_id=uuid.UUID(user_id),
        residency=residency,
        tenant_id=uuid.UUID(tenant_id),
        source_kind=XpSource.VISIT,
        source_id=None,
        delta=100,
        idempotency_key=f"visit:{user_id}:heritage1:2026-05-18",
    )
    await db_session.commit()
    assert event2.id == event1.id
    assert balance2.current_xp == 100


@pytest.mark.asyncio
async def test_level_progression(http: AsyncClient, db_session: AsyncSession) -> None:
    auth = await _register(http)
    user_id, residency, tenant_id = await _user_uuid(db_session, auth["user"]["pub_id"])
    service = GamificationService(repository=SqlGamificationRepository(db_session))

    # Award 600 XP — crosses the "explorer" boundary (500 xp_required).
    await service.award_xp(
        user_id=uuid.UUID(user_id),
        residency=residency,
        tenant_id=uuid.UUID(tenant_id),
        source_kind=XpSource.VISIT,
        source_id=None,
        delta=600,
        idempotency_key=f"visit:{user_id}:heritage:bigger",
    )
    await db_session.commit()

    response = await http.get("/v1/me/xp", headers=_h(auth))
    assert response.status_code == 200
    body = response.json()
    assert body["current_xp"] == 600
    assert body["level"]["slug"] == "kashfiyotchi"
    assert body["next_level"]["slug"] == "meros_qoriqchi"
    assert body["xp_to_next_level"] == 2000 - 600


@pytest.mark.asyncio
async def test_streak_tick_idempotent_per_day(http: AsyncClient, db_session: AsyncSession) -> None:
    auth = await _register(http)

    first = await http.post("/v1/me/streak/tick", headers=_h(auth))
    assert first.status_code == 200
    assert first.json()["current_streak"] == 1

    # Second tick same day must not bump the counter.
    second = await http.post("/v1/me/streak/tick", headers=_h(auth))
    assert second.status_code == 200
    assert second.json()["current_streak"] == 1


@pytest.mark.asyncio
async def test_streak_extends_on_consecutive_days(
    http: AsyncClient, db_session: AsyncSession
) -> None:
    auth = await _register(http)
    user_id_str, residency, _ = await _user_uuid(db_session, auth["user"]["pub_id"])
    user_id = uuid.UUID(user_id_str)

    # Insert backfilled heartbeats for yesterday + today directly to simulate
    # a multi-day streak. Then read /v1/me/streak.
    today = date.today()
    yesterday = today - timedelta(days=1)
    for d in (yesterday, today):
        await db_session.execute(
            text(
                """
                INSERT INTO streak_events (user_id, residency_region, event_date, source)
                VALUES (:u, :r, :d, 'open')
                ON CONFLICT DO NOTHING
                """
            ),
            {"u": user_id, "r": residency, "d": d},
        )
    await db_session.commit()

    # Tick the streak with explicit "today" so the repo recomputes.
    service = GamificationService(repository=SqlGamificationRepository(db_session))
    streak = await service.tick_streak(user_id=user_id, residency=residency, today=today)
    await db_session.commit()
    assert streak.current_streak >= 2


@pytest.mark.asyncio
async def test_leaderboard_lists_and_page(http: AsyncClient, db_session: AsyncSession) -> None:
    listing = await http.get("/v1/leaderboards")
    assert listing.status_code == 200
    boards = listing.json()["items"]
    slugs = {b["slug"] for b in boards}
    assert "global_xp_alltime" in slugs

    page = await http.get("/v1/leaderboards/global_xp_alltime?limit=5")
    assert page.status_code == 200
    body = page.json()
    assert body["slug"] == "global_xp_alltime"
    assert isinstance(body["entries"], list)


@pytest.mark.asyncio
async def test_leaderboard_unknown_slug(http: AsyncClient) -> None:
    response = await http.get("/v1/leaderboards/does_not_exist")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "gamification.leaderboard_not_found"


@pytest.mark.asyncio
async def test_me_badges_empty_for_new_user(http: AsyncClient) -> None:
    auth = await _register(http)
    response = await http.get("/v1/me/badges", headers=_h(auth))
    assert response.status_code == 200
    assert response.json() == {"items": []}
