"""Gamification-domain errors."""
# ruff: noqa: N818

from __future__ import annotations


class GamificationError(Exception):
    code: str = "gamification.unknown"
    status_code: int = 400


class LeaderboardNotFound(GamificationError):
    code = "gamification.leaderboard_not_found"
    status_code = 404


class InvalidXpDelta(GamificationError):
    code = "gamification.invalid_delta"
    status_code = 422
