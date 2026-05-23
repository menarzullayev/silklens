"""SQL implementation of the AR gamification repository."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.domain.ar.entities import (
    ArChallenge,
    ArChallengeDraft,
    ArChallengeKind,
    ArCompletion,
    ArDifficulty,
    ArOverlay,
    ArOverlayKind,
    ArSession,
    ArSessionKind,
)
from src.infrastructure._events import emit_event_if_registered, jdump

log = get_logger("silklens.ar.repository")


def _to_challenge(row: Any) -> ArChallenge:
    m = row._mapping
    return ArChallenge(
        id=m["id"],
        heritage_id=m["heritage_id"],
        tenant_id=m["tenant_id"],
        slug=m["slug"],
        title=dict(m["title"]) if m["title"] else {},
        description_md=dict(m["description_md"]) if m["description_md"] else {},
        kind=ArChallengeKind(m["kind"]),
        difficulty=ArDifficulty(m["difficulty"]),
        reward_xp=int(m["reward_xp"]),
        time_limit_seconds=m["time_limit_seconds"],
        ar_anchor_lat=float(m["ar_anchor_lat"]),
        ar_anchor_lng=float(m["ar_anchor_lng"]),
        ar_anchor_altitude_m=(
            float(m["ar_anchor_altitude_m"]) if m["ar_anchor_altitude_m"] is not None else None
        ),
        trigger_radius_m=float(m["trigger_radius_m"]),
        clue_text_md=dict(m["clue_text_md"]) if m["clue_text_md"] else {},
        correct_answer=dict(m["correct_answer"]) if m["correct_answer"] else {},
        hint_text_md=dict(m["hint_text_md"]) if m["hint_text_md"] else None,
        is_active=bool(m["is_active"]),
        completion_count=int(m["completion_count"]),
        created_at=m["created_at"],
        updated_at=m["updated_at"],
    )


def _to_completion(row: Any) -> ArCompletion:
    m = row._mapping
    return ArCompletion(
        id=m["id"],
        challenge_id=m["challenge_id"],
        user_id=m["user_id"],
        residency_region=m["residency_region"],
        completed_at=m["completed_at"],
        time_taken_seconds=int(m["time_taken_seconds"]),
        score=int(m["score"]),
        hint_used=bool(m["hint_used"]),
        photo_media_id=m["photo_media_id"],
        xp_awarded=int(m["xp_awarded"]),
    )


def _to_session(row: Any) -> ArSession:
    m = row._mapping
    return ArSession(
        id=m["id"],
        user_id=m["user_id"],
        residency_region=m["residency_region"],
        heritage_id=m["heritage_id"],
        session_kind=ArSessionKind(m["session_kind"]),
        started_at=m["started_at"],
        ended_at=m["ended_at"],
        max_participants=int(m["max_participants"]),
        session_code=m["session_code"],
        created_at=m["created_at"],
    )


def _to_overlay(row: Any) -> ArOverlay:
    m = row._mapping
    return ArOverlay(
        id=m["id"],
        heritage_id=m["heritage_id"],
        tenant_id=m["tenant_id"],
        overlay_kind=ArOverlayKind(m["overlay_kind"]),
        position_data=dict(m["position_data"]) if m["position_data"] else {},
        content_md=dict(m["content_md"]) if m["content_md"] else {},
        media_asset_id=m["media_asset_id"],
        is_active=bool(m["is_active"]),
        display_from_date=str(m["display_from_date"]) if m["display_from_date"] else None,
        display_until_date=str(m["display_until_date"]) if m["display_until_date"] else None,
        created_at=m["created_at"],
    )


class ArRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Challenges
    # ------------------------------------------------------------------

    async def list_challenges(
        self,
        *,
        heritage_pub_id: str | None,
        kind: ArChallengeKind | None,
        limit: int,
    ) -> list[ArChallenge]:
        filters = ["ac.is_active"]
        params: dict[str, Any] = {"limit": limit}

        if heritage_pub_id is not None:
            filters.append("ho.pub_id = :heritage_pub_id")
            params["heritage_pub_id"] = heritage_pub_id
        if kind is not None:
            filters.append("ac.kind = :kind")
            params["kind"] = kind.value

        where = " AND ".join(filters)
        # `where` is built from a fixed allowlist — not user-controlled input.
        _sql = (
            "SELECT ac.* FROM ar_challenges ac"  # noqa: S608
            " JOIN heritage_objects ho ON ho.id = ac.heritage_id"
            " WHERE " + where + " ORDER BY ac.completion_count DESC, ac.created_at DESC"
            " LIMIT :limit"
        )
        rows = await self._db.execute(text(_sql), params)
        return [_to_challenge(r) for r in rows]

    async def get_challenge_by_slug(self, slug: str) -> ArChallenge | None:
        row = (
            await self._db.execute(
                text("SELECT * FROM ar_challenges WHERE slug = :slug AND is_active"),
                {"slug": slug},
            )
        ).one_or_none()
        return _to_challenge(row) if row else None

    async def get_challenge_by_id(self, challenge_id: UUID) -> ArChallenge | None:
        row = (
            await self._db.execute(
                text("SELECT * FROM ar_challenges WHERE id = :id"),
                {"id": challenge_id},
            )
        ).one_or_none()
        return _to_challenge(row) if row else None

    async def create_challenge(self, draft: ArChallengeDraft) -> ArChallenge:
        row = (
            await self._db.execute(
                text(
                    """
                    INSERT INTO ar_challenges (
                        heritage_id, tenant_id, slug, title, description_md,
                        kind, difficulty, reward_xp, time_limit_seconds,
                        ar_anchor_lat, ar_anchor_lng, ar_anchor_altitude_m,
                        trigger_radius_m, clue_text_md, correct_answer, hint_text_md
                    ) VALUES (
                        :heritage_id, :tenant_id, :slug, CAST(:title AS jsonb),
                        CAST(:description_md AS jsonb), :kind, :difficulty,
                        :reward_xp, :time_limit_seconds,
                        :ar_anchor_lat, :ar_anchor_lng, :ar_anchor_altitude_m,
                        :trigger_radius_m, CAST(:clue_text_md AS jsonb),
                        CAST(:correct_answer AS jsonb), CAST(:hint_text_md AS jsonb)
                    )
                    RETURNING *
                    """
                ),
                {
                    "heritage_id": draft.heritage_id,
                    "tenant_id": draft.tenant_id,
                    "slug": draft.slug,
                    "title": jdump(draft.title),
                    "description_md": jdump(draft.description_md),
                    "kind": draft.kind.value,
                    "difficulty": draft.difficulty.value,
                    "reward_xp": draft.reward_xp,
                    "time_limit_seconds": draft.time_limit_seconds,
                    "ar_anchor_lat": draft.ar_anchor_lat,
                    "ar_anchor_lng": draft.ar_anchor_lng,
                    "ar_anchor_altitude_m": draft.ar_anchor_altitude_m,
                    "trigger_radius_m": draft.trigger_radius_m,
                    "clue_text_md": jdump(draft.clue_text_md),
                    "correct_answer": jdump(draft.correct_answer),
                    "hint_text_md": jdump(draft.hint_text_md) if draft.hint_text_md else None,
                },
            )
        ).one()
        return _to_challenge(row)

    # ------------------------------------------------------------------
    # Completions
    # ------------------------------------------------------------------

    async def get_completion(self, *, challenge_id: UUID, user_id: UUID) -> ArCompletion | None:
        row = (
            await self._db.execute(
                text(
                    """
                    SELECT * FROM ar_challenge_completions
                    WHERE  challenge_id = :challenge_id AND user_id = :user_id
                    """
                ),
                {"challenge_id": challenge_id, "user_id": user_id},
            )
        ).one_or_none()
        return _to_completion(row) if row else None

    async def record_completion(
        self,
        *,
        challenge_id: UUID,
        user_id: UUID,
        residency: str,
        tenant_id: UUID,
        time_taken_seconds: int,
        score: int,
        hint_used: bool,
        photo_media_id: UUID | None,
        xp_awarded: int,
    ) -> tuple[ArCompletion, bool]:
        """Insert a completion row. Returns (completion, badge_unlocked).

        badge_unlocked is True when the ar_explorer threshold is first crossed.
        """
        row = (
            await self._db.execute(
                text(
                    """
                    INSERT INTO ar_challenge_completions (
                        challenge_id, user_id, residency_region,
                        time_taken_seconds, score, hint_used,
                        photo_media_id, xp_awarded
                    ) VALUES (
                        :challenge_id, :user_id, :residency,
                        :time_taken_seconds, :score, :hint_used,
                        :photo_media_id, :xp_awarded
                    )
                    RETURNING *
                    """
                ),
                {
                    "challenge_id": challenge_id,
                    "user_id": user_id,
                    "residency": residency,
                    "time_taken_seconds": time_taken_seconds,
                    "score": score,
                    "hint_used": hint_used,
                    "photo_media_id": photo_media_id,
                    "xp_awarded": xp_awarded,
                },
            )
        ).one()
        completion = _to_completion(row)

        # Award XP via gamification ledger (best-effort — not fatal if it fails)
        if xp_awarded > 0:
            try:
                await self._db.execute(
                    text(
                        """
                        INSERT INTO xp_events (
                            user_id, residency_region, source_kind,
                            source_id, delta, idempotency_key, context
                        ) VALUES (
                            :user_id, :residency, 'visit',
                            :source_id, :delta,
                            :idempotency_key, CAST(:context AS jsonb)
                        )
                        ON CONFLICT (user_id, idempotency_key, created_at) DO NOTHING
                        """
                    ),
                    {
                        "user_id": user_id,
                        "residency": residency,
                        "source_id": completion.id,
                        "delta": xp_awarded,
                        "idempotency_key": f"ar_challenge:{challenge_id}:{user_id}",
                        "context": json.dumps({"challenge_id": str(challenge_id)}),
                    },
                )
                # Upsert balance
                await self._db.execute(
                    text(
                        """
                        INSERT INTO xp_balances (user_id, residency_region, current_xp, lifetime_xp)
                        VALUES (:user_id, :residency, :delta, :delta)
                        ON CONFLICT (user_id) DO UPDATE
                            SET current_xp  = xp_balances.current_xp + EXCLUDED.current_xp,
                                lifetime_xp = xp_balances.lifetime_xp + EXCLUDED.lifetime_xp,
                                refreshed_at = now()
                        """
                    ),
                    {"user_id": user_id, "residency": residency, "delta": xp_awarded},
                )
            except Exception:  # broad catch intentional — XP is best-effort
                log.debug("ar.xp_award_failed", challenge_id=str(challenge_id))

        # Check ar_explorer badge threshold (5 completions)
        badge_unlocked = await self._check_ar_explorer_badge(
            user_id=user_id, residency=residency, tenant_id=tenant_id
        )

        # Emit event
        await emit_event_if_registered(
            self._db,
            tenant_id=tenant_id,
            event_name="ar.challenge.completed.v1",
            aggregate_type="ar_challenge_completion",
            aggregate_id=completion.id,
            payload={
                "challenge_id": str(challenge_id),
                "user_id": str(user_id),
                "score": score,
                "xp_awarded": xp_awarded,
                "badge_unlocked": badge_unlocked,
            },
        )

        return completion, badge_unlocked

    async def _check_ar_explorer_badge(
        self, *, user_id: UUID, residency: str, tenant_id: UUID
    ) -> bool:
        """Award ar_explorer badge if the user has exactly 5 completions."""
        count_row = (
            await self._db.execute(
                text("SELECT COUNT(*) FROM ar_challenge_completions WHERE user_id = :u"),
                {"u": user_id},
            )
        ).scalar_one()
        if int(count_row) != 5:
            return False

        # Check badge_types exists
        badge_row = (
            await self._db.execute(text("SELECT id FROM badge_types WHERE slug = 'ar_explorer'"))
        ).scalar_one_or_none()
        if badge_row is None:
            return False

        result = await self._db.execute(
            text(
                """
                INSERT INTO user_badges (user_id, residency_region, badge_type_id)
                VALUES (:user_id, :residency, :badge_id)
                ON CONFLICT (user_id, badge_type_id) DO NOTHING
                RETURNING badge_type_id
                """
            ),
            {"user_id": user_id, "residency": residency, "badge_id": badge_row},
        )
        newly_awarded = result.scalar_one_or_none() is not None

        if newly_awarded:
            await emit_event_if_registered(
                self._db,
                tenant_id=tenant_id,
                event_name="badge.unlocked.v1",
                aggregate_type="user_badge",
                aggregate_id=user_id,
                payload={
                    "user_id": str(user_id),
                    "badge_slug": "ar_explorer",
                    "xp_reward": 500,
                },
            )

        return newly_awarded

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    async def session_code_exists(self, code: str) -> bool:
        row = (
            await self._db.execute(
                text("SELECT 1 FROM ar_sessions WHERE session_code = :code LIMIT 1"),
                {"code": code},
            )
        ).scalar_one_or_none()
        return row is not None

    async def create_session(
        self,
        *,
        user_id: UUID,
        residency: str,
        heritage_id: UUID | None,
        session_kind: ArSessionKind,
        max_participants: int,
        session_code: str | None,
    ) -> ArSession:
        row = (
            await self._db.execute(
                text(
                    """
                    INSERT INTO ar_sessions (
                        user_id, residency_region, heritage_id,
                        session_kind, max_participants, session_code
                    ) VALUES (
                        :user_id, :residency, :heritage_id,
                        :session_kind, :max_participants, :session_code
                    )
                    RETURNING *
                    """
                ),
                {
                    "user_id": user_id,
                    "residency": residency,
                    "heritage_id": heritage_id,
                    "session_kind": session_kind.value,
                    "max_participants": max_participants,
                    "session_code": session_code,
                },
            )
        ).one()
        return _to_session(row)

    async def get_session_by_code(self, code: str) -> ArSession | None:
        row = (
            await self._db.execute(
                text(
                    """
                    SELECT * FROM ar_sessions
                    WHERE session_code = :code AND ended_at IS NULL
                    LIMIT 1
                    """
                ),
                {"code": code},
            )
        ).one_or_none()
        return _to_session(row) if row else None

    async def count_participants(self, session_id: UUID) -> int:
        """Count active (not left) participants in a session."""
        count = (
            await self._db.execute(
                text(
                    """
                    SELECT COUNT(*) FROM ar_session_participants
                    WHERE session_id = :sid AND left_at IS NULL
                    """
                ),
                {"sid": session_id},
            )
        ).scalar_one()
        return int(count)

    async def add_participant(self, *, session_id: UUID, user_id: UUID, residency: str) -> None:
        await self._db.execute(
            text(
                """
                INSERT INTO ar_session_participants (session_id, user_id, residency_region)
                VALUES (:session_id, :user_id, :residency)
                ON CONFLICT (session_id, user_id) DO NOTHING
                """
            ),
            {"session_id": session_id, "user_id": user_id, "residency": residency},
        )

    # ------------------------------------------------------------------
    # Overlays
    # ------------------------------------------------------------------

    async def list_overlays(
        self,
        *,
        heritage_pub_id: str,
        reference_date: str | None,
    ) -> list[ArOverlay]:
        date_filter = ""
        params: dict[str, Any] = {"pub_id": heritage_pub_id}

        if reference_date:
            # asyncpg requires a datetime.date instance for date columns —
            # a raw ISO string fails with `'str' object has no attribute 'toordinal'`.
            # Parse to date here (router validates the input as date type).
            from datetime import date as _date_type

            try:
                parsed = _date_type.fromisoformat(reference_date)
            except (TypeError, ValueError):
                parsed = None
            date_filter = (
                "AND (ao.display_from_date IS NULL"
                " OR ao.display_from_date <= :ref_date)\n"
                "AND (ao.display_until_date IS NULL"
                " OR ao.display_until_date >= :ref_date)"
            )
            params["ref_date"] = parsed
        else:
            date_filter = (
                "AND (ao.display_from_date IS NULL"
                " OR ao.display_from_date <= CURRENT_DATE)\n"
                "AND (ao.display_until_date IS NULL"
                " OR ao.display_until_date >= CURRENT_DATE)"
            )

        # date_filter is built from fixed string constants — not user-controlled input.
        _sql = (
            "SELECT ao.* FROM ar_overlays ao"  # noqa: S608
            " JOIN heritage_objects ho ON ho.id = ao.heritage_id"
            " WHERE ho.pub_id = :pub_id AND ao.is_active "
            + date_filter
            + " ORDER BY ao.created_at ASC"
        )
        rows = await self._db.execute(text(_sql), params)
        return [_to_overlay(r) for r in rows]
