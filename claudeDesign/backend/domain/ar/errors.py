"""AR domain errors."""
# ruff: noqa: N818

from __future__ import annotations


class ArError(Exception):
    code: str = "ar.unknown"
    status_code: int = 400


class ChallengeNotFound(ArError):
    code = "ar.challenge_not_found"
    status_code = 404


class AlreadyCompleted(ArError):
    code = "ar.already_completed"
    status_code = 409


class SessionFull(ArError):
    code = "ar.session_full"
    status_code = 409


class SessionNotFound(ArError):
    code = "ar.session_not_found"
    status_code = 404


class InsufficientPermission(ArError):
    code = "ar.insufficient_permission"
    status_code = 403


class InvalidAnswer(ArError):
    code = "ar.invalid_answer"
    status_code = 422
