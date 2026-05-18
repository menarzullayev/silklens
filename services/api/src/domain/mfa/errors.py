"""MFA-domain errors. Pure Python; the API layer maps to HTTP.

Names describe the condition rather than the ``...Error`` suffix because
the codes ``identity.mfa_*`` are user-facing.
"""
# ruff: noqa: N818

from __future__ import annotations


class MfaError(Exception):
    """Base class for MFA-domain errors."""

    code: str = "identity.mfa_unknown"
    status_code: int = 400


class MfaNotEnrolled(MfaError):
    code = "identity.mfa_not_enrolled"
    status_code = 404


class MfaInvalidCode(MfaError):
    code = "identity.mfa_invalid_code"
    status_code = 422


class MfaChallengeExpired(MfaError):
    code = "identity.mfa_challenge_expired"
    status_code = 410


class MfaChallengeNotFound(MfaError):
    code = "identity.mfa_challenge_not_found"
    status_code = 404


class MfaAlreadyEnrolled(MfaError):
    code = "identity.mfa_already_enrolled"
    status_code = 409


class MfaStepUpRequired(MfaError):
    """Raised when a high-stakes action lacks a recent MFA proof."""

    code = "identity.mfa_step_up_required"
    status_code = 403


class MfaRequired(MfaError):
    """Raised by ``AuthService.login`` when the account has MFA enrolled.

    The login response carries the ``challenge_id`` the client must complete
    via ``/v1/auth/mfa/verify`` before tokens are minted.
    """

    code = "identity.mfa_required"
    status_code = 401

    def __init__(self, challenge_id: str, *, available_methods: list[str] | None = None) -> None:
        super().__init__("MFA challenge required to complete login")
        self.challenge_id = challenge_id
        self.available_methods = available_methods or []
