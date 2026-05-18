"""MFA application service — orchestrates enrollment + verification.

Framework-free; the API layer wraps it with FastAPI routers.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID, uuid4

from src.domain.mfa.entities import (
    BackupCode,
    MfaChallenge,
    MfaMethod,
    MfaMethodKind,
    MfaMethodStatus,
    MfaUserContext,
    TotpEnrollment,
)
from src.domain.mfa.errors import (
    MfaAlreadyEnrolled,
    MfaChallengeExpired,
    MfaChallengeNotFound,
    MfaInvalidCode,
    MfaNotEnrolled,
)
from src.domain.mfa.repositories import MfaRepository, TotpAdapter, WebAuthnAdapter

# 12-char backup codes (RFC-4226 §7.6 style): hex of 6 bytes = 12 chars.
_BACKUP_CODE_BYTES = 6
_BACKUP_CODE_COUNT = 10


class BackupCodeHasher(Protocol):
    """Same shape as the Argon2 hasher used elsewhere — single-arg verify."""

    def hash(self, code: str) -> bytes: ...
    def verify_any(self, code: str, hashes: list[bytes]) -> int | None:
        """Return the index of the matching hash, or None."""


@dataclass(slots=True, frozen=True)
class MfaVerificationResult:
    """Outcome of a verify call, used to decide whether to mint elevated tokens."""

    user_id: UUID
    residency_region: str
    method: MfaMethodKind
    challenge_id: UUID
    verified_at: datetime


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class MfaService:
    """Orchestrates TOTP / WebAuthn / backup-code enrollment + verification."""

    def __init__(
        self,
        *,
        repo: MfaRepository,
        totp: TotpAdapter,
        webauthn: WebAuthnAdapter,
        backup_hasher: BackupCodeHasher,
        clock: Clock | None = None,
        challenge_ttl_seconds: int = 300,
        rp_name: str = "SilkLens",
        rp_id: str = "localhost",
    ) -> None:
        self._repo = repo
        self._totp = totp
        self._webauthn = webauthn
        self._backup_hasher = backup_hasher
        self._clock = clock or SystemClock()
        self._challenge_ttl_seconds = challenge_ttl_seconds
        self._rp_name = rp_name
        self._rp_id = rp_id

    # --- introspection --------------------------------------------------
    async def list_methods(self, user_ctx: MfaUserContext) -> list[MfaMethod]:
        return await self._repo.list_methods(
            user_ctx.user_id,
            user_ctx.residency_region,
            include_disabled=False,
        )

    async def user_has_active_mfa(self, user_ctx: MfaUserContext) -> bool:
        methods = await self.list_methods(user_ctx)
        return any(m.is_active for m in methods)

    # --- TOTP -----------------------------------------------------------
    async def enroll_totp(self, user_ctx: MfaUserContext, *, label: str) -> TotpEnrollment:
        existing = await self._repo.list_methods(
            user_ctx.user_id, user_ctx.residency_region, include_disabled=False
        )
        if any(m.method == MfaMethodKind.TOTP and m.is_active for m in existing):
            raise MfaAlreadyEnrolled("a TOTP method is already active for this user")

        method = await self._repo.create_method(
            user_ctx=user_ctx,
            method=MfaMethodKind.TOTP,
            label=label,
            metadata={},
        )
        secret = self._totp.generate_secret()
        await self._repo.store_totp_secret(
            mfa_id=method.id,
            residency_region=method.residency_region,
            secret_plaintext=secret,
            period=30,
            digits=6,
            algorithm="sha1",
        )
        account_name = user_ctx.email or user_ctx.pub_id or str(user_ctx.user_id)
        uri = self._totp.provisioning_uri(
            secret_base32=secret,
            account_name=account_name,
            issuer=self._rp_name,
        )
        return TotpEnrollment(
            mfa_id=method.id,
            secret_base32=secret,
            provisioning_uri=uri,
        )

    async def verify_totp_enrollment(
        self,
        user_ctx: MfaUserContext,
        *,
        mfa_id: UUID,
        code: str,
    ) -> MfaMethod:
        method = await self._repo.get_method(mfa_id, user_ctx.residency_region)
        if method is None or method.user_id != user_ctx.user_id:
            raise MfaNotEnrolled("TOTP enrollment not found")
        if method.method != MfaMethodKind.TOTP:
            raise MfaNotEnrolled("method is not TOTP")
        secret = await self._repo.fetch_totp_secret(mfa_id, user_ctx.residency_region)
        if secret is None:
            raise MfaNotEnrolled("TOTP secret missing")
        if not self._totp.verify(secret_base32=secret, code=code):
            raise MfaInvalidCode("TOTP code did not match")
        now = self._clock.now()
        await self._repo.activate_method(mfa_id, user_ctx.residency_region, at=now)
        await self._repo.mark_user_mfa_satisfied(
            user_ctx.user_id, user_ctx.residency_region, at=now
        )
        refreshed = await self._repo.get_method(mfa_id, user_ctx.residency_region)
        assert refreshed is not None
        return refreshed

    async def verify_totp(
        self,
        user_ctx: MfaUserContext,
        *,
        challenge_id: UUID,
        code: str,
    ) -> MfaVerificationResult:
        challenge = await self._fetch_live_challenge(challenge_id, user_ctx)
        if challenge.method != MfaMethodKind.TOTP:
            raise MfaInvalidCode("challenge was not initiated for TOTP")
        methods = await self._repo.list_methods(
            user_ctx.user_id, user_ctx.residency_region, include_disabled=False
        )
        active_totp = [m for m in methods if m.method == MfaMethodKind.TOTP and m.is_active]
        if not active_totp:
            raise MfaNotEnrolled("no active TOTP method")
        for method in active_totp:
            secret = await self._repo.fetch_totp_secret(method.id, method.residency_region)
            if secret is None:
                continue
            if self._totp.verify(secret_base32=secret, code=code):
                now = self._clock.now()
                await self._repo.touch_method_last_used(method.id, method.residency_region, at=now)
                await self._repo.complete_challenge(challenge.id, at=now)
                await self._repo.mark_user_mfa_satisfied(
                    user_ctx.user_id, user_ctx.residency_region, at=now
                )
                return MfaVerificationResult(
                    user_id=user_ctx.user_id,
                    residency_region=user_ctx.residency_region,
                    method=MfaMethodKind.TOTP,
                    challenge_id=challenge.id,
                    verified_at=now,
                )
        raise MfaInvalidCode("TOTP code did not match any active secret")

    # --- WebAuthn -------------------------------------------------------
    async def enroll_webauthn_begin(
        self,
        user_ctx: MfaUserContext,
        *,
        label: str,
    ) -> tuple[UUID, dict[str, object]]:
        """Returns (challenge_id, PublicKeyCredentialCreationOptions JSON)."""
        method = await self._repo.create_method(
            user_ctx=user_ctx,
            method=MfaMethodKind.WEBAUTHN,
            label=label,
            metadata={},
        )
        existing = await self._repo.list_methods(
            user_ctx.user_id, user_ctx.residency_region, include_disabled=False
        )
        existing_ids: list[bytes] = []
        for m in existing:
            if m.method != MfaMethodKind.WEBAUTHN:
                continue
            cred = await self._repo.fetch_webauthn_credential(m.id, m.residency_region)
            if cred is not None:
                existing_ids.append(cred.credential_id)

        options = self._webauthn.generate_registration_options(
            user_id=str(user_ctx.user_id).encode("utf-8"),
            user_name=user_ctx.email or str(user_ctx.user_id),
            user_display_name=user_ctx.pub_id or user_ctx.email or str(user_ctx.user_id),
            existing_credential_ids=existing_ids,
        )

        challenge_bytes_b64 = options.get("challenge")
        challenge_bytes = (
            challenge_bytes_b64.encode("utf-8") if isinstance(challenge_bytes_b64, str) else b""
        )
        now = self._clock.now()
        challenge = MfaChallenge(
            id=uuid4(),
            user_id=user_ctx.user_id,
            residency_region=user_ctx.residency_region,
            method=MfaMethodKind.WEBAUTHN,
            challenge_bytes=challenge_bytes,
            metadata={"mfa_id": str(method.id), "purpose": "registration"},
            expires_at=now + timedelta(seconds=self._challenge_ttl_seconds),
            completed_at=None,
            created_at=now,
        )
        await self._repo.create_challenge(challenge)
        return challenge.id, options

    async def enroll_webauthn_complete(
        self,
        user_ctx: MfaUserContext,
        *,
        challenge_id: UUID,
        attestation: dict[str, object],
    ) -> MfaMethod:
        challenge = await self._fetch_live_challenge(challenge_id, user_ctx)
        if challenge.method != MfaMethodKind.WEBAUTHN:
            raise MfaInvalidCode("challenge is not a WebAuthn registration")
        mfa_id_raw = challenge.metadata.get("mfa_id")
        if not isinstance(mfa_id_raw, str):
            raise MfaInvalidCode("challenge missing pending mfa id")
        mfa_id = UUID(mfa_id_raw)
        result = self._webauthn.verify_registration_response(
            attestation=attestation,
            expected_challenge=challenge.challenge_bytes or b"",
        )
        from src.domain.mfa.entities import WebAuthnCredential as _Cred

        cred = _Cred(
            mfa_id=mfa_id,
            residency_region=user_ctx.residency_region,
            credential_id=bytes(result["credential_id"]),  # type: ignore[arg-type]
            public_key_bytes=bytes(result["public_key"]),  # type: ignore[arg-type]
            sign_count=int(result.get("sign_count", 0) or 0),
            transports=tuple(result.get("transports") or ()),  # type: ignore[arg-type]
            attestation_format=str(result["attestation_format"])
            if result.get("attestation_format")
            else None,
            aaguid=UUID(str(result["aaguid"])) if result.get("aaguid") else None,
        )
        await self._repo.store_webauthn_credential(cred)
        now = self._clock.now()
        await self._repo.activate_method(mfa_id, user_ctx.residency_region, at=now)
        await self._repo.complete_challenge(challenge.id, at=now)
        await self._repo.mark_user_mfa_satisfied(
            user_ctx.user_id, user_ctx.residency_region, at=now
        )
        refreshed = await self._repo.get_method(mfa_id, user_ctx.residency_region)
        assert refreshed is not None
        return refreshed

    async def verify_webauthn(
        self,
        user_ctx: MfaUserContext,
        *,
        challenge_id: UUID,
        assertion: dict[str, object],
    ) -> MfaVerificationResult:
        challenge = await self._fetch_live_challenge(challenge_id, user_ctx)
        if challenge.method != MfaMethodKind.WEBAUTHN:
            raise MfaInvalidCode("challenge is not WebAuthn")
        credential_id_raw = assertion.get("credential_id") or assertion.get("rawId") or b""
        if isinstance(credential_id_raw, bytes):
            credential_id = credential_id_raw
        else:
            credential_id = str(credential_id_raw).encode()
        methods = await self._repo.list_methods(
            user_ctx.user_id, user_ctx.residency_region, include_disabled=False
        )
        for method in methods:
            if method.method != MfaMethodKind.WEBAUTHN or not method.is_active:
                continue
            cred = await self._repo.fetch_webauthn_credential(method.id, method.residency_region)
            if cred is None or cred.credential_id != credential_id:
                continue
            result = self._webauthn.verify_authentication_response(
                assertion=assertion,
                expected_challenge=challenge.challenge_bytes or b"",
                stored_public_key=cred.public_key_bytes,
                stored_sign_count=cred.sign_count,
                credential_id=cred.credential_id,
            )
            new_count = int(result.get("new_sign_count", cred.sign_count + 1))
            await self._repo.update_webauthn_sign_count(
                method.id, method.residency_region, new_sign_count=new_count
            )
            now = self._clock.now()
            await self._repo.touch_method_last_used(method.id, method.residency_region, at=now)
            await self._repo.complete_challenge(challenge.id, at=now)
            await self._repo.mark_user_mfa_satisfied(
                user_ctx.user_id, user_ctx.residency_region, at=now
            )
            return MfaVerificationResult(
                user_id=user_ctx.user_id,
                residency_region=user_ctx.residency_region,
                method=MfaMethodKind.WEBAUTHN,
                challenge_id=challenge.id,
                verified_at=now,
            )
        raise MfaInvalidCode("WebAuthn assertion did not match any registered credential")

    # --- backup codes ---------------------------------------------------
    async def generate_backup_codes(self, user_ctx: MfaUserContext) -> list[str]:
        """Wipe & regenerate the 10-code set. Plaintext returned to caller ONCE."""
        codes = [secrets.token_hex(_BACKUP_CODE_BYTES) for _ in range(_BACKUP_CODE_COUNT)]
        hashes = [self._backup_hasher.hash(c) for c in codes]
        await self._repo.replace_backup_codes(user_ctx=user_ctx, code_hashes=hashes)
        existing = await self._repo.list_methods(
            user_ctx.user_id, user_ctx.residency_region, include_disabled=False
        )
        has_method = any(m.method == MfaMethodKind.BACKUP_CODES and m.is_active for m in existing)
        if not has_method:
            method = await self._repo.create_method(
                user_ctx=user_ctx,
                method=MfaMethodKind.BACKUP_CODES,
                label="recovery",
                metadata={},
            )
            await self._repo.activate_method(
                method.id, method.residency_region, at=self._clock.now()
            )
        return codes

    async def verify_backup_code(
        self,
        user_ctx: MfaUserContext,
        *,
        challenge_id: UUID,
        code: str,
    ) -> MfaVerificationResult:
        challenge = await self._fetch_live_challenge(challenge_id, user_ctx)
        if challenge.method != MfaMethodKind.BACKUP_CODES:
            raise MfaInvalidCode("challenge is not a backup-code challenge")
        live = await self._repo.list_backup_codes(
            user_ctx.user_id, user_ctx.residency_region, only_unused=True
        )
        if not live:
            raise MfaNotEnrolled("no active backup codes")
        idx = self._backup_hasher.verify_any(code, [bc.code_hash for bc in live])
        if idx is None:
            raise MfaInvalidCode("backup code did not match")
        target: BackupCode = live[idx]
        now = self._clock.now()
        consumed = await self._repo.consume_backup_code(
            user_id=user_ctx.user_id,
            residency_region=user_ctx.residency_region,
            code_hash=target.code_hash,
            at=now,
        )
        if not consumed:
            raise MfaInvalidCode("backup code already used")
        await self._repo.complete_challenge(challenge.id, at=now)
        await self._repo.mark_user_mfa_satisfied(
            user_ctx.user_id, user_ctx.residency_region, at=now
        )
        return MfaVerificationResult(
            user_id=user_ctx.user_id,
            residency_region=user_ctx.residency_region,
            method=MfaMethodKind.BACKUP_CODES,
            challenge_id=challenge.id,
            verified_at=now,
        )

    # --- challenges -----------------------------------------------------
    async def initiate_challenge(
        self,
        user_ctx: MfaUserContext,
        *,
        method: MfaMethodKind,
    ) -> MfaChallenge:
        """Create a short-lived challenge the client completes via /verify."""
        now = self._clock.now()
        challenge_bytes = secrets.token_bytes(32)
        challenge = MfaChallenge(
            id=uuid4(),
            user_id=user_ctx.user_id,
            residency_region=user_ctx.residency_region,
            method=method,
            challenge_bytes=challenge_bytes,
            metadata={"purpose": "step_up_or_login"},
            expires_at=now + timedelta(seconds=self._challenge_ttl_seconds),
            completed_at=None,
            created_at=now,
        )
        return await self._repo.create_challenge(challenge)

    # --- disable --------------------------------------------------------
    async def disable_method(
        self,
        user_ctx: MfaUserContext,
        *,
        mfa_id: UUID,
    ) -> None:
        method = await self._repo.get_method(mfa_id, user_ctx.residency_region)
        if method is None or method.user_id != user_ctx.user_id:
            raise MfaNotEnrolled("MFA method not found")
        if method.status != MfaMethodStatus.ACTIVE:
            return
        await self._repo.disable_method(mfa_id, user_ctx.residency_region)

    # --- step-up helper -------------------------------------------------
    async def is_step_up_fresh(
        self,
        user_ctx: MfaUserContext,
        *,
        within_seconds: int,
    ) -> bool:
        ts = await self._repo.get_user_last_mfa_at(user_ctx.user_id, user_ctx.residency_region)
        if ts is None:
            return False
        now = self._clock.now()
        return (now - ts).total_seconds() <= within_seconds

    # --- internals ------------------------------------------------------
    async def _fetch_live_challenge(
        self,
        challenge_id: UUID,
        user_ctx: MfaUserContext,
    ) -> MfaChallenge:
        challenge = await self._repo.get_challenge(challenge_id)
        if (
            challenge is None
            or challenge.user_id != user_ctx.user_id
            or challenge.residency_region != user_ctx.residency_region
        ):
            raise MfaChallengeNotFound("challenge not found")
        if challenge.is_completed:
            raise MfaInvalidCode("challenge already completed")
        if challenge.is_expired:
            raise MfaChallengeExpired("challenge expired")
        return challenge


# --- helpers ------------------------------------------------------------


def fingerprint_backup_code(code: str) -> bytes:
    """Pure-SHA fingerprint used by tests / non-crypto identity lookups."""
    return hashlib.sha256(code.encode("utf-8")).digest()
