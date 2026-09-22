"""Identity-domain errors. Pure Python; mapped to HTTP at the API layer.

Names intentionally describe the condition rather than the ``...Error`` suffix
ruff prefers — these are domain exceptions whose names appear in user-facing
error codes (``identity.email_already_registered`` etc.), so the noun form
reads better. We silence N818 for the file.
"""
# ruff: noqa: N818

from __future__ import annotations


class IdentityError(Exception):
    """Base for all identity-domain errors."""

    code: str = "identity.unknown"
    status_code: int = 400


class EmailAlreadyRegistered(IdentityError):
    code = "identity.email_already_registered"
    status_code = 409


class InvalidCredentials(IdentityError):
    code = "identity.invalid_credentials"
    status_code = 401


class UserNotFound(IdentityError):
    code = "identity.user_not_found"
    status_code = 404


class AccountInactive(IdentityError):
    code = "identity.account_inactive"
    status_code = 403


class SessionExpired(IdentityError):
    code = "identity.session_expired"
    status_code = 401


class RefreshTokenReused(IdentityError):
    """Token-replay defence: a refresh token used twice revokes the whole family."""

    code = "identity.refresh_token_reused"
    status_code = 401


class WeakPassword(IdentityError):
    code = "identity.weak_password"
    status_code = 422

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class AccountLocked(IdentityError):
    """Brute-force defence: too many failed logins from this identifier+IP.

    Maps to HTTP 423 LOCKED. ``retry_after_seconds`` is exposed so the API
    layer can set a ``Retry-After`` header. Per Agent 2 §4 / SEC-005.
    """

    code = "identity.account_locked"
    status_code = 423

    def __init__(self, retry_after_seconds: int, *, reason: str = "too_many_failed_logins") -> None:
        super().__init__(f"account locked: {reason} (retry after {retry_after_seconds}s)")
        self.retry_after_seconds = retry_after_seconds
        self.reason = reason
