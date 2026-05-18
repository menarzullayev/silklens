"""MFA domain entities — pure-Python, framework-agnostic.

Per ADR-0003 the domain layer carries no ORM / FastAPI / SDK types. The
infrastructure adapters map these to SQL rows and external library DTOs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class MfaMethodKind(StrEnum):
    """Enrollable MFA factors. ``backup_codes`` is treated like a method so
    a user can "have" backup codes as a fallback even with no other method."""

    TOTP = "totp"
    WEBAUTHN = "webauthn"
    BACKUP_CODES = "backup_codes"
    SMS_OTP = "sms_otp"


class MfaMethodStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    PENDING = "pending"


@dataclass(slots=True, frozen=True)
class MfaMethod:
    """A per-user enrolled MFA factor row."""

    id: UUID
    user_id: UUID
    residency_region: str
    tenant_id: UUID
    method: MfaMethodKind
    label: str
    status: MfaMethodStatus
    enrolled_at: datetime | None
    last_used_at: datetime | None
    metadata: dict[str, object]
    created_at: datetime
    updated_at: datetime

    @property
    def is_active(self) -> bool:
        return self.status == MfaMethodStatus.ACTIVE


@dataclass(slots=True, frozen=True)
class TotpEnrollment:
    """Result of starting a TOTP enrollment — the secret is sent to the
    client exactly once so they can render a QR code or paste it into an
    authenticator app. The shared secret is also persisted (encrypted) by
    the repository."""

    mfa_id: UUID
    secret_base32: str
    provisioning_uri: str
    period: int = 30
    digits: int = 6
    algorithm: str = "sha1"


@dataclass(slots=True, frozen=True)
class WebAuthnCredential:
    """Persisted WebAuthn credential after a successful registration."""

    mfa_id: UUID
    residency_region: str
    credential_id: bytes
    public_key_bytes: bytes
    sign_count: int
    transports: tuple[str, ...]
    attestation_format: str | None
    aaguid: UUID | None


@dataclass(slots=True, frozen=True)
class BackupCode:
    """A single recovery code, plaintext only exists at generation time."""

    id: UUID
    user_id: UUID
    residency_region: str
    code_hash: bytes
    used_at: datetime | None
    created_at: datetime


@dataclass(slots=True, frozen=True)
class MfaChallenge:
    """Short-lived verification challenge bound to a single user."""

    id: UUID
    user_id: UUID
    residency_region: str
    method: MfaMethodKind
    challenge_bytes: bytes | None
    metadata: dict[str, object]
    expires_at: datetime
    completed_at: datetime | None
    created_at: datetime

    @property
    def is_expired(self) -> bool:
        from datetime import UTC

        return datetime.now(UTC) >= self.expires_at

    @property
    def is_completed(self) -> bool:
        return self.completed_at is not None


@dataclass(slots=True, frozen=True)
class MfaUserContext:
    """The slice of identity info MfaService needs for an enrollment / verify."""

    user_id: UUID
    residency_region: str
    tenant_id: UUID
    email: str | None = None
    pub_id: str | None = None
    extra: dict[str, object] = field(default_factory=dict)
