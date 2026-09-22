"""AR gamification application service."""

from __future__ import annotations

import random
import string
from typing import Any
from uuid import UUID

from src.core.logging import get_logger
from src.domain.ar.entities import (
    ArChallenge,
    ArChallengeDraft,
    ArChallengeKind,
    ArCompletion,
    ArOverlay,
    ArSession,
    ArSessionKind,
)
from src.domain.ar.errors import (
    AlreadyCompleted,
    ChallengeNotFound,
    InsufficientPermission,
    SessionFull,
    SessionNotFound,
)
from src.infrastructure.ar.repository import ArRepository

log = get_logger("silklens.ar")

_CODE_CHARS = string.ascii_uppercase + string.digits


def _generate_session_code() -> str:
    """6-character random alphanumeric session code (group AR sessions)."""
    return "".join(random.choices(_CODE_CHARS, k=6))  # noqa: S311  # nosec B311 — not crypto


class ArService:
    def __init__(self, *, repository: ArRepository) -> None:
        self._repo = repository

    # ------------------------------------------------------------------
    # Challenges
    # ------------------------------------------------------------------

    async def list_challenges(
        self,
        *,
        heritage_pub_id: str | None = None,
        kind: ArChallengeKind | None = None,
        limit: int = 20,
    ) -> list[ArChallenge]:
        return await self._repo.list_challenges(
            heritage_pub_id=heritage_pub_id,
            kind=kind,
            limit=limit,
        )

    async def get_challenge(self, slug: str) -> ArChallenge:
        challenge = await self._repo.get_challenge_by_slug(slug)
        if challenge is None:
            raise ChallengeNotFound(f"AR challenge '{slug}' not found")
        return challenge

    async def get_hint(self, slug: str) -> dict[str, Any]:
        """Return the hint_text_md for the challenge.

        The caller (router) decides whether to deduct XP for the hint.
        """
        challenge = await self.get_challenge(slug)
        return challenge.hint_text_md or {}

    async def submit_completion(
        self,
        *,
        user_id: UUID,
        residency: str,
        tenant_id: UUID,
        challenge_id: UUID,
        answer: dict[str, Any],
        time_taken_seconds: int,
        hint_used: bool = False,
        photo_media_id: UUID | None = None,
    ) -> tuple[ArCompletion, int, bool]:
        """Score the answer and record the completion.

        Returns
        -------
        (completion, xp_delta, badge_unlocked)

        Raises
        ------
        AlreadyCompleted  — if the user already completed this challenge.
        """
        # Idempotency guard first
        existing = await self._repo.get_completion(challenge_id=challenge_id, user_id=user_id)
        if existing is not None:
            raise AlreadyCompleted(f"Challenge {challenge_id} already completed by user {user_id}")

        challenge = await self._repo.get_challenge_by_id(challenge_id)
        if challenge is None:
            raise ChallengeNotFound(f"Challenge {challenge_id} not found")

        score = self._score_answer(challenge, answer, time_taken_seconds)
        xp_awarded = self._compute_xp(challenge, score, hint_used)

        completion, badge_unlocked = await self._repo.record_completion(
            challenge_id=challenge_id,
            user_id=user_id,
            residency=residency,
            tenant_id=tenant_id,
            time_taken_seconds=time_taken_seconds,
            score=score,
            hint_used=hint_used,
            photo_media_id=photo_media_id,
            xp_awarded=xp_awarded,
        )
        log.info(
            "ar.challenge.completed",
            challenge_id=str(challenge_id),
            user_id=str(user_id),
            score=score,
            xp=xp_awarded,
            badge_unlocked=badge_unlocked,
        )
        return completion, xp_awarded, badge_unlocked

    def _score_answer(
        self,
        challenge: ArChallenge,
        answer: dict[str, Any],
        time_taken: int,
    ) -> int:
        """Compute 0-100 score.

        Rules per kind:
        - historical_riddle / time_period_guess: text match → 100 if correct else 0.
        - object_hunt / photo_spot:              presence of required keywords → proportional.
        - reconstruction_quiz:                   range-check accepted_min/accepted_max.
        Time bonus: arriving under 50 % of time_limit adds up to +10 points (capped at 100).
        """
        correct = challenge.correct_answer
        base = 0

        try:
            if challenge.kind in (
                ArChallengeKind.HISTORICAL_RIDDLE,
                ArChallengeKind.TIME_PERIOD_GUESS,
            ):
                user_text = str(answer.get("text", "")).lower().strip()
                accepted: list[str] = [
                    a.lower() for a in correct.get("accepted", [correct.get("text", "")])
                ]
                base = 100 if any(user_text == a for a in accepted) else 0

            elif challenge.kind == ArChallengeKind.RECONSTRUCTION_QUIZ:
                user_val = float(answer.get("value", 0))
                lo = float(correct.get("accepted_min", 0))
                hi = float(correct.get("accepted_max", 0))
                if lo <= user_val <= hi:
                    # Full credit in the centre, partial at the edges
                    mid = (lo + hi) / 2.0
                    spread = max(1.0, (hi - lo) / 2.0)
                    dist = abs(user_val - mid) / spread  # 0 → 1
                    base = max(0, int(100 - dist * 30))
                else:
                    base = 0

            elif challenge.kind in (
                ArChallengeKind.OBJECT_HUNT,
                ArChallengeKind.PHOTO_SPOT,
            ):
                required = [k.lower() for k in correct.get("required_elements", [])]
                found = [k.lower() for k in answer.get("elements", [])]
                if required:
                    hits = sum(1 for r in required if r in found)
                    base = int(100 * hits / len(required))
                else:
                    base = 100

        except (TypeError, ValueError, KeyError):
            base = 0

        # Time bonus: only when the answer is at least partially correct
        # (base > 0) and completed in under 50 % of the time limit.
        if (
            base > 0
            and challenge.time_limit_seconds
            and time_taken < challenge.time_limit_seconds * 0.5
        ):
            bonus = int(10 * (1 - time_taken / (challenge.time_limit_seconds * 0.5)))
            base = min(100, base + bonus)

        return base

    def _compute_xp(self, challenge: ArChallenge, score: int, hint_used: bool) -> int:
        """Award XP proportional to score; 50 % penalty if hint used."""
        xp = int(challenge.reward_xp * score / 100)
        if hint_used:
            xp = xp // 2
        return max(0, xp)

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    async def start_session(
        self,
        *,
        user_id: UUID,
        residency: str,
        heritage_id: UUID | None,
        kind: ArSessionKind,
        max_participants: int = 1,
    ) -> ArSession:
        session_code: str | None = None
        if kind == ArSessionKind.GROUP:
            # Generate a unique 6-char code; retry on (unlikely) collision
            for _ in range(5):
                candidate = _generate_session_code()
                if not await self._repo.session_code_exists(candidate):
                    session_code = candidate
                    break
            if session_code is None:
                session_code = _generate_session_code()  # last-resort

        return await self._repo.create_session(
            user_id=user_id,
            residency=residency,
            heritage_id=heritage_id,
            session_kind=kind,
            max_participants=max(1, max_participants) if kind == ArSessionKind.GROUP else 1,
            session_code=session_code,
        )

    async def join_session(
        self,
        *,
        user_id: UUID,
        residency: str,
        session_code: str,
    ) -> ArSession:
        session = await self._repo.get_session_by_code(session_code)
        if session is None:
            raise SessionNotFound(f"No active group session with code '{session_code}'")

        # Count current participants
        participant_count = await self._repo.count_participants(session.id)
        if participant_count >= session.max_participants:
            raise SessionFull(f"Session '{session_code}' is full ({session.max_participants} max)")

        await self._repo.add_participant(
            session_id=session.id,
            user_id=user_id,
            residency=residency,
        )
        return session

    # ------------------------------------------------------------------
    # Overlays
    # ------------------------------------------------------------------

    async def list_overlays(
        self,
        *,
        heritage_pub_id: str,
        reference_date: str | None = None,
    ) -> list[ArOverlay]:
        return await self._repo.list_overlays(
            heritage_pub_id=heritage_pub_id,
            reference_date=reference_date,
        )

    # ------------------------------------------------------------------
    # Admin: create challenge
    # ------------------------------------------------------------------

    async def create_challenge(
        self, draft: ArChallengeDraft, *, actor_permissions: list[str]
    ) -> ArChallenge:
        if "heritage:create" not in actor_permissions:
            raise InsufficientPermission(
                "heritage:create permission required to create AR challenges"
            )
        return await self._repo.create_challenge(draft)
