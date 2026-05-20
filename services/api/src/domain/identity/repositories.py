"""Repository protocols for the identity domain.

Protocols (not ABCs) keep the domain layer dependency-free while letting
the infrastructure layer satisfy them structurally.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.domain.identity.entities import (
    OAuthProfile,
    ResidencyRegion,
    Session,
    User,
    UserEmail,
)


class UserRepository(Protocol):
    """Read + write access to users and their email rows."""

    async def get_by_id(
        self,
        user_id: UUID,
        residency_region: ResidencyRegion,
    ) -> User | None: ...

    async def get_by_pub_id(self, pub_id: str) -> User | None: ...

    async def find_by_email(
        self,
        email: str,
        *,
        tenant_id: UUID,
    ) -> tuple[User, UserEmail] | None: ...

    async def email_exists(self, email: str, *, tenant_id: UUID) -> bool: ...

    async def create_with_email(
        self,
        *,
        user: User,
        email: str,
        password_hash: str,
        password_algorithm: str,
    ) -> tuple[User, UserEmail]: ...

    async def update_last_login(self, user_id: UUID, residency_region: ResidencyRegion) -> None: ...

    async def get_password_hash(
        self,
        user_id: UUID,
        residency_region: ResidencyRegion,
    ) -> tuple[str, str] | None:
        """Return (password_hash, password_algorithm) or None if not set."""

    async def find_by_oauth_identity(
        self,
        *,
        provider_id: UUID,
        subject: str,
    ) -> tuple[User, UserEmail] | None:
        """Look up a user by their stable OAuth provider subject ('sub').

        Returns the user + their primary email row, or None if no identity
        link exists for this (provider, subject) pair.
        """

    async def create_oauth_user(
        self,
        *,
        user: User,
        email: str,
        email_verified: bool,
        provider_id: UUID,
        profile: OAuthProfile,
    ) -> tuple[User, UserEmail]:
        """Create a new user originating from an OAuth provider.

        Unlike create_with_email there is no password. The email is marked
        verified immediately when the provider reports email_verified=True.
        The user_identities link is inserted in the same transaction.
        """

    async def upsert_oauth_identity(
        self,
        *,
        user: User,
        provider_id: UUID,
        profile: OAuthProfile,
    ) -> None:
        """Insert or update the user_identities row for an existing user.

        Also marks the primary email as verified and updates user_profiles
        (display_name, avatar_url) from the provider's authoritative data.
        """

    async def verify_email(self, user_id: UUID, residency_region: ResidencyRegion) -> None:
        """Mark the user's primary email and the user row as verified."""


class SessionRepository(Protocol):
    """Active sessions + refresh tokens."""

    async def create_session(
        self,
        *,
        user: User,
        ip_address: str | None,
        user_agent: str | None,
        access_token_expires_at: datetime,
        refresh_token_hash: bytes,
        refresh_token_expires_at: datetime,
        family_id: UUID,
    ) -> Session: ...

    async def get_session(
        self, session_id: UUID, residency_region: ResidencyRegion
    ) -> Session | None: ...

    async def revoke_session(
        self,
        session_id: UUID,
        residency_region: ResidencyRegion,
        *,
        reason: str,
    ) -> None: ...

    async def rotate_refresh_token(
        self,
        *,
        old_token_hash: bytes,
        new_token_hash: bytes,
        new_expires_at: datetime,
    ) -> Session | None:
        """Mark the old token used, issue a new one in the same family.

        Returns None if the old token is unknown or already used (caller MUST
        treat None as ``RefreshTokenReused`` and revoke the family).
        """


class LoginAttemptRepository(Protocol):
    """Append-only brute-force ledger backing the lockout window.

    Per Agent 2 §4: every login attempt — success or failure — is recorded
    so the auth service can ask, on the next call from the same
    ``(identifier, ip)``, "how many failures in the last N minutes?".
    """

    async def record_attempt(
        self,
        *,
        identifier: str,
        succeeded: bool,
        ip_address: str | None,
        user_agent: str | None,
        failure_reason: str | None,
    ) -> None: ...

    async def count_recent_failures(
        self,
        *,
        identifier: str,
        ip_address: str | None,
        within_seconds: int,
    ) -> int:
        """Return the number of failed attempts in the last ``within_seconds``
        window for this identifier (and IP, when present)."""
