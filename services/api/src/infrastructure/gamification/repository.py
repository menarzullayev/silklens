"""SQL implementation of the gamification repository.

Ledger-style XP table: every award/clawback is one row, idempotent on
``(user_id, idempotency_key, created_at)``. We surface a stable "was it
newly created vs duplicate?" signal so the service can avoid double-counting.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from datetime import date as date_cls
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.gamification.entities import (
    Badge,
    Leaderboard,
    LeaderboardEntry,
    LeaderboardPeriod,
    LeaderboardScope,
    Level,
    Streak,
    UserBadge,
    XpBalance,
    XpEvent,
    XpSource,
)
from src.infrastructure._events import emit_event_if_registered, jdump


def _to_event(row: Any) -> XpEvent:
    m = row._mapping
    return XpEvent(
        id=m["id"],
        user_id=m["user_id"],
        residency_region=m["residency_region"],
        source_kind=XpSource(m["source_kind"]),
        source_id=m["source_id"],
        delta=m["delta"],
        idempotency_key=m["idempotency_key"],
        context=dict(m["context"]) if m["context"] else {},
        created_at=m["created_at"],
    )


def _to_balance(row: Any) -> XpBalance:
    m = row._mapping
    return XpBalance(
        user_id=m["user_id"],
        residency_region=m["residency_region"],
        current_xp=int(m["current_xp"]),
        lifetime_xp=int(m["lifetime_xp"]),
        weekly_xp=int(m["weekly_xp"]),
        monthly_xp=int(m["monthly_xp"]),
        yearly_xp=int(m["yearly_xp"]),
        refreshed_at=m["refreshed_at"],
        last_event_at=m["last_event_at"],
        last_event_id=m["last_event_id"],
    )


def _to_level(row: Any) -> Level:
    m = row._mapping
    return Level(
        number=int(m["number"]),
        slug=m["slug"],
        name=dict(m["name"]) if m["name"] else {},
        xp_required=int(m["xp_required"]),
        perks=dict(m["perks"]) if m["perks"] else {},
    )


def _to_leaderboard(row: Any) -> Leaderboard:
    m = row._mapping
    return Leaderboard(
        id=m["id"],
        slug=m["slug"],
        name=dict(m["name"]) if m["name"] else {},
        scope=LeaderboardScope(m["scope"]),
        period=LeaderboardPeriod(m["period"]),
        metric=m["metric"],
        scope_ref=m["scope_ref"],
        is_active=m["is_active"],
    )


def _period_floor(period: LeaderboardPeriod) -> datetime | None:
    """Lower bound for live-period queries; ``None`` for all-time."""
    now = datetime.now(UTC)
    if period == LeaderboardPeriod.DAILY:
        return datetime(now.year, now.month, now.day, tzinfo=UTC)
    if period == LeaderboardPeriod.WEEKLY:
        return now - timedelta(days=7)
    if period == LeaderboardPeriod.MONTHLY:
        return datetime(now.year, now.month, 1, tzinfo=UTC)
    if period == LeaderboardPeriod.YEARLY:
        return datetime(now.year, 1, 1, tzinfo=UTC)
    return None


class SqlGamificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # --- XP ledger -------------------------------------------------------

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
        # The unique index covers (user_id, idempotency_key, created_at).
        # Cross-partition uniqueness is enforced by the application putting
        # the date in the key itself (Agent 5 §5.1 — "visit:USER:HER:2026-05-18").
        # We try to upsert by guarding on (user_id, idempotency_key) in the
        # current partition window; if a row already exists we return it.
        existing = await self._session.execute(
            text(
                """
                SELECT id, user_id, residency_region, source_kind, source_id,
                       delta, idempotency_key, context, created_at
                FROM xp_events
                WHERE user_id = :u AND idempotency_key = :k
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"u": user_id, "k": idempotency_key},
        )
        existing_row = existing.one_or_none()
        if existing_row is not None:
            return _to_event(existing_row), False

        inserted = await self._session.execute(
            text(
                """
                INSERT INTO xp_events (
                    user_id, residency_region, source_kind, source_id,
                    delta, idempotency_key, context
                )
                VALUES (:u, :r, :src, :sid, :d, :k, CAST(:ctx AS jsonb))
                RETURNING id, user_id, residency_region, source_kind, source_id,
                          delta, idempotency_key, context, created_at
                """
            ),
            {
                "u": user_id,
                "r": residency,
                "src": source_kind.value,
                "sid": source_id,
                "d": delta,
                "k": idempotency_key,
                "ctx": jdump(context),
            },
        )
        event = _to_event(inserted.one())

        await emit_event_if_registered(
            self._session,
            tenant_id=tenant_id,
            event_name="xp.awarded.v1",
            aggregate_type="user",
            aggregate_id=user_id,
            payload={
                "delta": delta,
                "source_kind": source_kind.value,
                "idempotency_key": idempotency_key,
            },
        )
        return event, True

    async def get_balance(self, user_id: UUID) -> XpBalance | None:
        row = await self._session.execute(
            text(
                """
                SELECT user_id, residency_region, current_xp, lifetime_xp,
                       weekly_xp, monthly_xp, yearly_xp,
                       last_event_at, last_event_id, refreshed_at
                FROM xp_balances WHERE user_id = :u
                """
            ),
            {"u": user_id},
        )
        r = row.one_or_none()
        return _to_balance(r) if r else None

    async def upsert_balance_from_event(
        self, *, user_id: UUID, residency: str, delta: int, event_id: UUID
    ) -> XpBalance:
        await self._session.execute(
            text(
                """
                INSERT INTO xp_balances (
                    user_id, residency_region,
                    current_xp, lifetime_xp, weekly_xp, monthly_xp, yearly_xp,
                    last_event_at, last_event_id, refreshed_at
                )
                VALUES (
                    :u, :r,
                    GREATEST(0, :d), GREATEST(0, :d),
                    GREATEST(0, :d), GREATEST(0, :d), GREATEST(0, :d),
                    now(), :eid, now()
                )
                ON CONFLICT (user_id) DO UPDATE
                    SET current_xp = GREATEST(0, xp_balances.current_xp + EXCLUDED.current_xp),
                        lifetime_xp = xp_balances.lifetime_xp
                                      + GREATEST(0, EXCLUDED.lifetime_xp),
                        weekly_xp = GREATEST(0, xp_balances.weekly_xp + EXCLUDED.weekly_xp),
                        monthly_xp = GREATEST(0, xp_balances.monthly_xp + EXCLUDED.monthly_xp),
                        yearly_xp      = GREATEST(0, xp_balances.yearly_xp + EXCLUDED.yearly_xp),
                        last_event_at  = now(),
                        last_event_id  = EXCLUDED.last_event_id,
                        refreshed_at   = now()
                """
            ),
            {"u": user_id, "r": residency, "d": delta, "eid": event_id},
        )
        # The ON CONFLICT clause uses GREATEST(0, current + delta) which is correct
        # only when delta is positive (delta is added via EXCLUDED.current_xp which
        # is GREATEST(0, :d) — i.e. clamped to >= 0). For clawbacks we apply the
        # negative delta directly here so balances reflect reality.
        if delta < 0:
            await self._session.execute(
                text(
                    """
                    UPDATE xp_balances
                    SET current_xp = GREATEST(0, current_xp + :d),
                        weekly_xp  = GREATEST(0, weekly_xp + :d),
                        monthly_xp = GREATEST(0, monthly_xp + :d),
                        yearly_xp  = GREATEST(0, yearly_xp + :d),
                        refreshed_at = now()
                    WHERE user_id = :u
                    """
                ),
                {"u": user_id, "d": delta},
            )
        balance = await self.get_balance(user_id)
        assert balance is not None
        return balance

    # --- Levels ----------------------------------------------------------

    async def list_levels(self) -> tuple[Level, ...]:
        rows = await self._session.execute(
            text(
                """
                SELECT number, slug, name, xp_required, perks
                FROM levels
                WHERE is_active
                ORDER BY number ASC
                """
            )
        )
        return tuple(_to_level(r) for r in rows.all())

    # --- Badges ----------------------------------------------------------

    async def list_user_badges(self, user_id: UUID) -> tuple[UserBadge, ...]:
        rows = await self._session.execute(
            text(
                """
                SELECT ub.user_id, ub.awarded_at, ub.progress,
                       bt.id, bt.slug, bt.category, bt.name, bt.description,
                       bt.criterion_kind, bt.criterion_params, bt.rarity, bt.xp_reward
                FROM user_badges ub
                JOIN badge_types bt ON bt.id = ub.badge_type_id
                WHERE ub.user_id = :u AND ub.revoked_at IS NULL
                ORDER BY ub.awarded_at DESC
                """
            ),
            {"u": user_id},
        )
        return tuple(
            UserBadge(
                user_id=r._mapping["user_id"],
                awarded_at=r._mapping["awarded_at"],
                progress=dict(r._mapping["progress"]) if r._mapping["progress"] else {},
                badge=Badge(
                    id=r._mapping["id"],
                    slug=r._mapping["slug"],
                    category=r._mapping["category"],
                    name=dict(r._mapping["name"]) if r._mapping["name"] else {},
                    description=dict(r._mapping["description"])
                    if r._mapping["description"]
                    else {},
                    criterion_kind=r._mapping["criterion_kind"],
                    criterion_params=dict(r._mapping["criterion_params"])
                    if r._mapping["criterion_params"]
                    else {},
                    rarity=r._mapping["rarity"],
                    xp_reward=r._mapping["xp_reward"],
                ),
            )
            for r in rows.all()
        )

    # --- Streaks ---------------------------------------------------------

    async def get_streak(self, user_id: UUID) -> Streak | None:
        row = await self._session.execute(
            text(
                """
                SELECT user_id, residency_region, current_streak, longest_streak,
                       last_active_date, timezone_anchor, freeze_credits,
                       broken_at, updated_at
                FROM streaks WHERE user_id = :u
                """
            ),
            {"u": user_id},
        )
        r = row.one_or_none()
        if r is None:
            return None
        m = r._mapping
        return Streak(
            user_id=m["user_id"],
            residency_region=m["residency_region"],
            current_streak=int(m["current_streak"]),
            longest_streak=int(m["longest_streak"]),
            timezone_anchor=m["timezone_anchor"],
            freeze_credits=int(m["freeze_credits"]),
            updated_at=m["updated_at"],
            last_active_date=m["last_active_date"],
            broken_at=m["broken_at"],
        )

    async def tick_streak(self, *, user_id: UUID, residency: str, today: str) -> Streak:
        """Idempotent per (user, date). Reads + recomputes from streak_events.

        ``today`` is either an ISO date string (``"2026-05-18"``) or empty —
        empty means "use the database's CURRENT_DATE so it follows the
        connection's clock". We resolve that once in Python to keep the SQL
        simple and avoid asyncpg's strict COALESCE type unification.
        """
        # First insert today's heartbeat (PK collision = same-day no-op).
        # asyncpg expects a real date object for date columns — parse the ISO
        # string here once and use a plain bind variable.
        today_clause = ":today" if today else "CURRENT_DATE"
        params: dict[str, Any] = {"u": user_id, "r": residency}
        if today:
            params["today"] = date_cls.fromisoformat(today)

        await self._session.execute(
            text(
                f"""
                INSERT INTO streak_events (user_id, residency_region, event_date, source)
                VALUES (:u, :r, {today_clause}, 'open')
                ON CONFLICT (user_id, event_date) DO NOTHING
                """  # noqa: S608 — today_clause is a literal SQL fragment
            ),
            params,
        )

        # Compute the consecutive-day streak ending at ``today``. Classic
        # gaps-and-islands: ``event_date - row_number()`` is constant across a
        # run when rows are ordered ascending. We then keep only the island
        # whose final date is today (or earlier-with-today-included).
        current_row = await self._session.execute(
            text(
                f"""
                WITH dates AS (
                    SELECT event_date FROM streak_events
                    WHERE user_id = :u AND event_date <= {today_clause}
                ),
                runs AS (
                    SELECT
                        event_date,
                        (event_date
                          - (row_number() OVER (ORDER BY event_date ASC)
                             * INTERVAL '1 day')
                        )::date AS run_key
                    FROM dates
                ),
                last_run AS (
                    SELECT run_key FROM runs
                    ORDER BY event_date DESC LIMIT 1
                )
                SELECT count(*)::int FROM runs
                WHERE run_key = (SELECT run_key FROM last_run)
                  AND EXISTS (
                      SELECT 1 FROM runs r2
                      WHERE r2.event_date = {today_clause}
                  )
                """  # noqa: S608
            ),
            params,
        )
        new_current = int(current_row.scalar_one() or 0)

        upsert_params = {**params, "cur": new_current}
        await self._session.execute(
            text(
                f"""
                INSERT INTO streaks (
                    user_id, residency_region,
                    current_streak, longest_streak, last_active_date
                )
                VALUES (:u, :r, :cur, :cur, {today_clause})
                ON CONFLICT (user_id) DO UPDATE
                    SET current_streak  = EXCLUDED.current_streak,
                        longest_streak  = GREATEST(
                            streaks.longest_streak, EXCLUDED.current_streak
                        ),
                        last_active_date = EXCLUDED.last_active_date,
                        updated_at = now()
                """  # noqa: S608
            ),
            upsert_params,
        )
        streak = await self.get_streak(user_id)
        assert streak is not None
        return streak

    # --- Leaderboards ----------------------------------------------------

    async def list_leaderboards(self) -> tuple[Leaderboard, ...]:
        rows = await self._session.execute(
            text(
                """
                SELECT id, slug, name, scope, scope_ref, period, metric, is_active
                FROM leaderboards
                WHERE is_active
                ORDER BY slug ASC
                """
            )
        )
        return tuple(_to_leaderboard(r) for r in rows.all())

    async def get_leaderboard_by_slug(self, slug: str) -> Leaderboard | None:
        row = await self._session.execute(
            text(
                """
                SELECT id, slug, name, scope, scope_ref, period, metric, is_active
                FROM leaderboards
                WHERE slug = :s
                LIMIT 1
                """
            ),
            {"s": slug},
        )
        r = row.one_or_none()
        return _to_leaderboard(r) if r else None

    async def live_leaderboard_page(
        self,
        *,
        leaderboard: Leaderboard,
        period: LeaderboardPeriod,
        limit: int,
    ) -> tuple[LeaderboardEntry, ...]:
        floor = _period_floor(period)
        params: dict[str, Any] = {"limit": limit}
        floor_clause = ""
        if floor is not None:
            floor_clause = " AND x.created_at >= :floor"
            params["floor"] = floor

        # Currently only metric=xp is supported live (others fall back to all-time
        # SUM with the same query — metric_value semantics are still XP-derived
        # until the dedicated counter columns ship in a later FAZA).
        rows = await self._session.execute(
            text(
                f"""
                SELECT
                    u.id AS user_id,
                    u.pub_id AS user_pub_id,
                    coalesce(sum(x.delta), 0)::bigint AS metric_value
                FROM xp_events x
                JOIN users u
                  ON u.id = x.user_id AND u.residency_region = x.residency_region
                WHERE u.deleted_at IS NULL {floor_clause}
                GROUP BY u.id, u.pub_id
                HAVING coalesce(sum(x.delta), 0) > 0
                ORDER BY metric_value DESC
                LIMIT :limit
                """  # noqa: S608 — floor_clause is a literal SQL fragment
            ),
            params,
        )
        out: list[LeaderboardEntry] = []
        for idx, r in enumerate(rows.all(), start=1):
            m = r._mapping
            out.append(
                LeaderboardEntry(
                    rank=idx,
                    user_id=m["user_id"],
                    user_pub_id=m["user_pub_id"],
                    metric_value=int(m["metric_value"]),
                )
            )
        # `leaderboard` reserved for future scope-based filtering (country/friends).
        _ = leaderboard
        return tuple(out)
