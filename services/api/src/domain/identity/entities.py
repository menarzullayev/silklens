"""Identity domain entities — pure Python, framework-agnostic.

Per ADR-0003 these are dataclasses with no ORM / FastAPI / external SDK
dependencies. The infrastructure layer maps them to SQLAlchemy rows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Self
from uuid import UUID


class ResidencyRegion(StrEnum):
    UZ = "uz"
    EU = "eu"
    US = "us"
    GLOBAL = "global"


class UserStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"
    BANNED = "banned"
    DELETED = "deleted"


class TrustTier(StrEnum):
    NEW = "new"
    REGULAR = "regular"
    TRUSTED = "trusted"
    CONTRIBUTOR = "contributor"
    STAFF = "staff"
    ADMIN = "admin"


@dataclass(slots=True, frozen=True)
class User:
    """Identity aggregate root — the durable representation of a user."""

    id: UUID
    tenant_id: UUID
    residency_region: ResidencyRegion
    pub_id: str
    status: UserStatus
    is_guest: bool
    trust_tier: TrustTier
    trust_score: int
    preferred_locale: str
    preferred_timezone: str
    created_at: datetime
    updated_at: datetime
    email_verified_at: datetime | None = None
    phone_verified_at: datetime | None = None
    mfa_enabled: bool = False
    last_login_at: datetime | None = None
    last_active_at: datetime | None = None
    deleted_at: datetime | None = None
    anonymized_at: datetime | None = None

    @property
    def is_active(self) -> bool:
        return (
            self.status == UserStatus.ACTIVE
            and self.deleted_at is None
            and self.anonymized_at is None
        )

    @property
    def is_verified(self) -> bool:
        return self.email_verified_at is not None or self.phone_verified_at is not None

    def with_login(self, *, when: datetime | None = None) -> Self:
        """Return a copy reflecting a successful login."""
        return self.__class__(
            **{
                **self.__dict__,
                "last_login_at": when or datetime.now(UTC),
                "last_active_at": when or datetime.now(UTC),
            }
        )


@dataclass(slots=True, frozen=True)
class UserEmail:
    """Email address bound to a user."""

    id: UUID
    user_id: UUID
    residency_region: ResidencyRegion
    tenant_id: UUID
    email: str
    is_primary: bool
    is_forwarded: bool
    verified_at: datetime | None
    created_at: datetime


@dataclass(slots=True, frozen=True)
class Session:
    """Active session bound to a user + device."""

    id: UUID
    user_id: UUID
    residency_region: ResidencyRegion
    tenant_id: UUID
    issued_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    device_fingerprint_id: UUID | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    revoked_at: datetime | None = None
    revoke_reason: str | None = None

    @property
    def is_active(self) -> bool:
        now = datetime.now(UTC)
        return self.revoked_at is None and self.expires_at > now


@dataclass(slots=True, frozen=True)
class AuthenticatedSession:
    """The bundle a successful authentication returns to the API layer."""

    user: User
    session: Session
    access_token: str
    refresh_token: str
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime


@dataclass(slots=True, frozen=True)
class Credentials:
    """Login input — exactly one of (email, phone) must be set."""

    password: str
    email: str | None = None
    phone_e164: str | None = None

    def __post_init__(self) -> None:
        provided = sum(1 for v in (self.email, self.phone_e164) if v)
        if provided != 1:
            raise ValueError("Credentials require exactly one of email or phone_e164")


@dataclass(slots=True, frozen=True)
class RegistrationRequest:
    """All the inputs required to register a new user."""

    tenant_id: UUID
    residency_region: ResidencyRegion
    email: str
    password: str
    display_name: str | None = None
    preferred_locale: str = "en"
    preferred_timezone: str = "UTC"
    accepted_legal_versions: tuple[str, ...] = field(default_factory=tuple)
