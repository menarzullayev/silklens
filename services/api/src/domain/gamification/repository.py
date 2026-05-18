"""Gamification repository protocol."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

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


class GamificationRepository(Protocol):
    async def record_xp_event(
        self,
        *,
        user_id: UUID,
        residency: str,
        source_kind: XpSource,
        source_id: UUID | None,
        delta: int,
        idempotency_key: str,
        context: dict,
        tenant_id: UUID,
    ) -> tuple[XpEvent, bool]:
        """Returns (event, was_created). When the idempotency key collides we
        return the *existing* event and ``was_created=False``."""

    async def get_balance(self, user_id: UUID) -> XpBalance | None: ...

    async def upsert_balance_from_event(
        self, *, user_id: UUID, residency: str, delta: int, event_id: UUID
    ) -> XpBalance: ...

    async def list_levels(self) -> tuple[Level, ...]: ...

    async def list_user_badges(self, user_id: UUID) -> tuple[UserBadge, ...]: ...

    async def get_streak(self, user_id: UUID) -> Streak | None: ...

    async def tick_streak(self, *, user_id: UUID, residency: str, today: str) -> Streak:
        """Idempotent per (user, date). Returns the updated streak row."""

    async def list_leaderboards(self) -> tuple[Leaderboard, ...]: ...

    async def get_leaderboard_by_slug(self, slug: str) -> Leaderboard | None: ...

    async def live_leaderboard_page(
        self,
        *,
        leaderboard: Leaderboard,
        period: LeaderboardPeriod,
        limit: int,
    ) -> tuple[LeaderboardEntry, ...]: ...
