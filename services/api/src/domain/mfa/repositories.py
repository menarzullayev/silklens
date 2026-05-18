"""MFA repository + adapter protocols.

Domain stays infrastructure-free: the concrete SQL repo + pyotp/webauthn
adapters live in ``src/infrastructure/mfa/``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.domain.mfa.entities import (
    BackupCode,
    MfaChallenge,
    MfaMethod,
    MfaMethodKind,
    MfaUserContext,
    WebAuthnCredential,
)


class MfaRepository(Protocol):
    """SQL persistence for every MFA entity."""

    # --- methods --------------------------------------------------------
    async def create_method(
        self,
        *,
        user_ctx: MfaUserContext,
        method: MfaMethodKind,
        label: str,
        metadata: dict[str, object] | None = None,
    ) -> MfaMethod: ...

    async def get_method(
        self,
        mfa_id: UUID,
        residency_region: str,
    ) -> MfaMethod | None: ...

    async def list_methods(
        self,
        user_id: UUID,
        residency_region: str,
        *,
        include_disabled: bool = False,
    ) -> list[MfaMethod]: ...

    async def activate_method(
        self,
        mfa_id: UUID,
        residency_region: str,
        *,
        at: datetime,
    ) -> None: ...

    async def disable_method(
        self,
        mfa_id: UUID,
        residency_region: str,
    ) -> None: ...

    async def touch_method_last_used(
        self,
        mfa_id: UUID,
        residency_region: str,
        *,
        at: datetime,
    ) -> None: ...

    # --- TOTP secrets --------------------------------------------------
    async def store_totp_secret(
        self,
        *,
        mfa_id: UUID,
        residency_region: str,
        secret_plaintext: str,
        period: int,
        digits: int,
        algorithm: str,
    ) -> None: ...

    async def fetch_totp_secret(
        self,
        mfa_id: UUID,
        residency_region: str,
    ) -> str | None:
        """Return the decrypted base32 secret or None if absent."""

    # --- WebAuthn credentials ------------------------------------------
    async def store_webauthn_credential(self, cred: WebAuthnCredential) -> None: ...

    async def fetch_webauthn_credential(
        self,
        mfa_id: UUID,
        residency_region: str,
    ) -> WebAuthnCredential | None: ...

    async def update_webauthn_sign_count(
        self,
        mfa_id: UUID,
        residency_region: str,
        *,
        new_sign_count: int,
    ) -> None: ...

    # --- backup codes ---------------------------------------------------
    async def replace_backup_codes(
        self,
        *,
        user_ctx: MfaUserContext,
        code_hashes: list[bytes],
    ) -> int:
        """Wipe & insert; returns count inserted."""

    async def consume_backup_code(
        self,
        *,
        user_id: UUID,
        residency_region: str,
        code_hash: bytes,
        at: datetime,
    ) -> bool:
        """Mark a single backup code used. Returns True on success."""

    async def list_backup_codes(
        self,
        user_id: UUID,
        residency_region: str,
        *,
        only_unused: bool = True,
    ) -> list[BackupCode]: ...

    # --- challenges -----------------------------------------------------
    async def create_challenge(self, challenge: MfaChallenge) -> MfaChallenge: ...

    async def get_challenge(self, challenge_id: UUID) -> MfaChallenge | None: ...

    async def complete_challenge(self, challenge_id: UUID, *, at: datetime) -> None: ...

    # --- user step-up clock --------------------------------------------
    async def mark_user_mfa_satisfied(
        self,
        user_id: UUID,
        residency_region: str,
        *,
        at: datetime,
    ) -> None: ...

    async def get_user_last_mfa_at(
        self,
        user_id: UUID,
        residency_region: str,
    ) -> datetime | None: ...


class TotpAdapter(Protocol):
    """RFC-6238 TOTP — pure crypto, library-backed (pyotp in prod)."""

    def generate_secret(self) -> str:
        """Return a base32-encoded secret (the bytes the client + server share)."""

    def provisioning_uri(
        self,
        *,
        secret_base32: str,
        account_name: str,
        issuer: str,
    ) -> str:
        """``otpauth://totp/...`` URI consumable by Authy/Google Authenticator."""

    def verify(self, *, secret_base32: str, code: str, window: int = 1) -> bool:
        """Validate an offered TOTP code against the secret."""


class WebAuthnAdapter(Protocol):
    """FIDO2 / WebAuthn flow."""

    def generate_registration_options(
        self,
        *,
        user_id: bytes,
        user_name: str,
        user_display_name: str,
        existing_credential_ids: list[bytes],
    ) -> dict[str, object]:
        """Return a JSON-serializable PublicKeyCredentialCreationOptions."""

    def verify_registration_response(
        self,
        *,
        attestation: dict[str, object],
        expected_challenge: bytes,
    ) -> dict[str, object]:
        """Return a dict with ``credential_id``, ``public_key``, ``sign_count``,
        ``transports``, ``attestation_format``, ``aaguid``."""

    def generate_authentication_options(
        self,
        *,
        allow_credential_ids: list[bytes],
    ) -> dict[str, object]: ...

    def verify_authentication_response(
        self,
        *,
        assertion: dict[str, object],
        expected_challenge: bytes,
        stored_public_key: bytes,
        stored_sign_count: int,
        credential_id: bytes,
    ) -> dict[str, object]:
        """Return a dict with at minimum ``new_sign_count``."""
