"""Gamification endpoints — XP / badges / levels / streaks / leaderboards."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.domain.gamification.entities import LeaderboardPeriod, LeaderboardScope
from src.domain.gamification.errors import GamificationError
from src.domain.gamification.service import GamificationService
from src.infrastructure.gamification.repository import SqlGamificationRepository
from src.middleware.auth import CurrentUserDep

router = APIRouter(tags=["gamification"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _service(db: AsyncSession) -> GamificationService:
    return GamificationService(repository=SqlGamificationRepository(db))


def _raise(exc: GamificationError) -> None:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": str(exc)},
    ) from exc


# --- Schemas ---------------------------------------------------------------


class XpStatusOut(BaseModel):
    current_xp: int
    lifetime_xp: int
    weekly_xp: int
    monthly_xp: int
    level: dict | None
    next_level: dict | None
    xp_to_next_level: int | None
    progress_pct: float | None


class BadgeOut(BaseModel):
    slug: str
    category: str
    name: dict
    description: dict
    rarity: str
    awarded_at: datetime
    progress: dict


class BadgesOut(BaseModel):
    items: list[BadgeOut]


class LeaderboardSummary(BaseModel):
    slug: str
    name: dict
    scope: str
    period: str
    metric: str


class LeaderboardListOut(BaseModel):
    items: list[LeaderboardSummary]


class LeaderboardEntryOut(BaseModel):
    rank: int
    user_pub_id: str
    metric_value: int


class LeaderboardPageOut(BaseModel):
    slug: str
    name: dict
    scope: str
    period: str
    entries: list[LeaderboardEntryOut]


class StreakOut(BaseModel):
    current_streak: int
    longest_streak: int
    last_active_date: date | None
    freeze_credits: int


# --- Endpoints -------------------------------------------------------------


@router.get("/v1/me/xp", response_model=XpStatusOut)
async def me_xp(db: SessionDep, ctx: CurrentUserDep) -> XpStatusOut:
    service = _service(db)
    current_level, next_level, balance = await service.current_level(user_id=ctx.user_id)

    current_xp = balance.current_xp if balance else 0
    xp_to_next: int | None = None
    progress: float | None = None
    if next_level is not None:
        floor = current_level.xp_required if current_level else 0
        span = max(1, next_level.xp_required - floor)
        xp_to_next = max(0, next_level.xp_required - current_xp)
        progress = round(min(1.0, max(0.0, (current_xp - floor) / span)) * 100, 2)

    return XpStatusOut(
        current_xp=current_xp,
        lifetime_xp=balance.lifetime_xp if balance else 0,
        weekly_xp=balance.weekly_xp if balance else 0,
        monthly_xp=balance.monthly_xp if balance else 0,
        level=_level_to_dict(current_level) if current_level else None,
        next_level=_level_to_dict(next_level) if next_level else None,
        xp_to_next_level=xp_to_next,
        progress_pct=progress,
    )


def _level_to_dict(level: Any) -> dict:
    return {
        "number": level.number,
        "slug": level.slug,
        "name": level.name,
        "xp_required": level.xp_required,
        "perks": level.perks,
    }


@router.get("/v1/me/badges", response_model=BadgesOut)
async def me_badges(db: SessionDep, ctx: CurrentUserDep) -> BadgesOut:
    badges = await _service(db).list_user_badges(user_id=ctx.user_id)
    return BadgesOut(
        items=[
            BadgeOut(
                slug=ub.badge.slug,
                category=ub.badge.category,
                name=ub.badge.name,
                description=ub.badge.description,
                rarity=ub.badge.rarity,
                awarded_at=ub.awarded_at,
                progress=ub.progress,
            )
            for ub in badges
        ]
    )


@router.get("/v1/me/streak", response_model=StreakOut)
async def me_streak(db: SessionDep, ctx: CurrentUserDep) -> StreakOut:
    streak = await _service(db).get_streak(user_id=ctx.user_id)
    if streak is None:
        return StreakOut(
            current_streak=0,
            longest_streak=0,
            last_active_date=None,
            freeze_credits=0,
        )
    return StreakOut(
        current_streak=streak.current_streak,
        longest_streak=streak.longest_streak,
        last_active_date=streak.last_active_date,
        freeze_credits=streak.freeze_credits,
    )


@router.post("/v1/me/streak/tick", response_model=StreakOut, status_code=status.HTTP_200_OK)
async def me_streak_tick(db: SessionDep, ctx: CurrentUserDep) -> StreakOut:
    streak = await _service(db).tick_streak(
        user_id=ctx.user_id, residency=ctx.residency_region.value
    )
    await db.commit()
    return StreakOut(
        current_streak=streak.current_streak,
        longest_streak=streak.longest_streak,
        last_active_date=streak.last_active_date,
        freeze_credits=streak.freeze_credits,
    )


@router.get("/v1/leaderboards", response_model=LeaderboardListOut)
async def list_leaderboards(db: SessionDep) -> LeaderboardListOut:
    boards = await _service(db).list_leaderboards()
    return LeaderboardListOut(
        items=[
            LeaderboardSummary(
                slug=b.slug,
                name=b.name,
                scope=b.scope.value,
                period=b.period.value,
                metric=b.metric,
            )
            for b in boards
        ]
    )


@router.get("/v1/leaderboards/{slug}", response_model=LeaderboardPageOut)
async def get_leaderboard(
    slug: str,
    db: SessionDep,
    period: Annotated[LeaderboardPeriod | None, Query()] = None,
    scope: Annotated[LeaderboardScope | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> LeaderboardPageOut:
    try:
        board, entries = await _service(db).leaderboard_page(slug=slug, period=period, limit=limit)
    except GamificationError as exc:
        _raise(exc)
    # `scope` is forwarded for future per-friends/per-country filtering — the
    # underlying SUM query is global today.
    _ = scope
    return LeaderboardPageOut(
        slug=board.slug,
        name=board.name,
        scope=board.scope.value,
        period=(period or board.period).value,
        entries=[
            LeaderboardEntryOut(rank=e.rank, user_pub_id=e.user_pub_id, metric_value=e.metric_value)
            for e in entries
        ],
    )
