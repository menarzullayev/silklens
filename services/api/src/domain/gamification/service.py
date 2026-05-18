"""Gamification application service."""

from __future__ import annotations

from datetime import date as date_cls
from typing import Any
from uuid import UUID

from src.core.logging import get_logger
from src.domain.gamification.entities import (
    Leaderboard,
    LeaderboardEntry,
    LeaderboardPeriod,
    Level,
    Streak,
    UserBadge,
    XpBalance,
    XpEvent,
    XpSource,
)
from src.domain.gamification.errors import InvalidXpDelta, LeaderboardNotFound
from src.domain.gamification.repository import GamificationRepository

log = get_logger("silklens.gamification")


class GamificationService:
    def __init__(self, *, repository: GamificationRepository) -> None:
        self._repo = repository

    # --- XP --------------------------------------------------------------

    async def award_xp(
        self,
        *,
        user_id: UUID,
        residency: str,
        tenant_id: UUID,
        source_kind: XpSource,
        source_id: UUID | None,
        delta: int,
        idempotency_key: str,
        context: dict | None = None,
    ) -> tuple[XpEvent, XpBalance]:
        if delta == 0:
            raise InvalidXpDelta("delta must be non-zero")
        event, created = await self._repo.record_xp_event(
            user_id=user_id,
            residency=residency,
            source_kind=source_kind,
            source_id=source_id,
            delta=delta,
            idempotency_key=idempotency_key,
            context=context or {},
            tenant_id=tenant_id,
        )
        if not created:
            balance = await self._repo.get_balance(user_id)
            if balance is None:
                raise RuntimeError(
                    "xp_balances missing for an existing xp event "
                    f"(user_id={user_id}); ledger and projection out of sync"
                )
            return event, balance

        balance = await self._repo.upsert_balance_from_event(
            user_id=user_id,
            residency=residency,
            delta=delta,
            event_id=event.id,
        )
        return event, balance

    # --- Levels ----------------------------------------------------------

    async def current_level(
        self, *, user_id: UUID
    ) -> tuple[Level | None, Level | None, XpBalance | None]:
        """Returns (current_level, next_level, balance)."""
        levels = await self._repo.list_levels()
        balance = await self._repo.get_balance(user_id)
        current_xp = balance.current_xp if balance else 0
        current_level: Level | None = None
        next_level: Level | None = None
        for level in levels:
            if level.xp_required <= current_xp:
                current_level = level
            else:
                next_level = level
                break
        return current_level, next_level, balance

    # --- Badges ----------------------------------------------------------

    async def list_user_badges(self, *, user_id: UUID) -> tuple[UserBadge, ...]:
        return await self._repo.list_user_badges(user_id)

    async def check_badge_progress(
        self,
        *,
        user_id: UUID,
        action_kind: str,
        payload: dict[str, Any],
    ) -> None:
        """Evaluate criterion rules against the user's activity log.

        FAZA-1 stub: heritage_views and per-criterion materialised counters
        are not yet wired (TODO in handoff). For now we just log the intent
        so the worker can pick it up once the upstream views land.
        """
        log.info(
            "gamification.badge_check_pending",
            user_id=str(user_id),
            action_kind=action_kind,
            payload_keys=list(payload.keys()),
        )

    # --- Streak ----------------------------------------------------------

    async def tick_streak(
        self,
        *,
        user_id: UUID,
        residency: str,
        today: date_cls | None = None,
    ) -> Streak:
        # Caller usually passes None; we leave the date resolution to the
        # repository so it can honour the user's timezone_anchor.
        return await self._repo.tick_streak(
            user_id=user_id,
            residency=residency,
            today=today.isoformat() if today else "",
        )

    async def get_streak(self, *, user_id: UUID) -> Streak | None:
        return await self._repo.get_streak(user_id)

    # --- Leaderboards ----------------------------------------------------

    async def list_leaderboards(self) -> tuple[Leaderboard, ...]:
        return await self._repo.list_leaderboards()

    async def leaderboard_page(
        self,
        *,
        slug: str,
        period: LeaderboardPeriod | None = None,
        limit: int = 20,
    ) -> tuple[Leaderboard, tuple[LeaderboardEntry, ...]]:
        board = await self._repo.get_leaderboard_by_slug(slug)
        if board is None:
            raise LeaderboardNotFound()
        effective_period = period or board.period
        entries = await self._repo.live_leaderboard_page(
            leaderboard=board,
            period=effective_period,
            limit=limit,
        )
        return board, entries
