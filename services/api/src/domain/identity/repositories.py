"""Repository protocols for the identity domain.

Protocols (not ABCs) keep the domain layer dependency-free while letting
the infrastructure layer satisfy them structurally.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.domain.identity.entities import (
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
