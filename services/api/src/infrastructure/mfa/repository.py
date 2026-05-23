"""SqlAlchemy-backed MFA repository (asyncpg via SQLAlchemy AsyncSession).

Schema is migration ``0084_mfa``. We use ``text()``-based SQL like the
identity repository because the migrations are the canonical source of
truth at this stage.
"""

from __future__ import annotations

from datetime import datetime
from typing import Final
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.settings import get_settings
from src.domain.mfa.entities import (
    BackupCode,
    MfaChallenge,
    MfaMethod,
    MfaMethodKind,
    MfaMethodStatus,
    MfaUserContext,
    WebAuthnCredential,
)

_METHOD_COLUMNS: Final = (
    "id, user_id, residency_region, tenant_id, method, label, status, "
    "enrolled_at, last_used_at, metadata, created_at, updated_at"
)


def _method_from_row(row: object) -> MfaMethod:
    m = row._mapping
    metadata = m["metadata"] or {}
    if isinstance(metadata, str):
        import json

        metadata = json.loads(metadata)
    return MfaMethod(
        id=m["id"],
        user_id=m["user_id"],
        residency_region=str(m["residency_region"]),
        tenant_id=m["tenant_id"],
        method=MfaMethodKind(m["method"]),
        label=m["label"] or "",
        status=MfaMethodStatus(m["status"]),
        enrolled_at=m["enrolled_at"],
        last_used_at=m["last_used_at"],
        metadata=metadata,
        created_at=m["created_at"],
        updated_at=m["updated_at"],
    )


class SqlMfaRepository:
    """All MFA reads/writes funnel through here."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # --- methods --------------------------------------------------------
    async def create_method(
        self,
        *,
        user_ctx: MfaUserContext,
        method: MfaMethodKind,
        label: str,
        metadata: dict[str, object] | None = None,
    ) -> MfaMethod:
        import json

        new_id = uuid4()
        await self._session.execute(
            text(
                f"""
                INSERT INTO mfa_methods (
                    id, user_id, residency_region, tenant_id, method, label,
                    status, metadata
                ) VALUES (
                    :id, :user_id, :region, :tenant_id, :method, :label,
                    'pending', CAST(:metadata AS jsonb)
                )
                RETURNING {_METHOD_COLUMNS}
                """  # noqa: S608
            ),
            {
                "id": new_id,
                "user_id": user_ctx.user_id,
                "region": user_ctx.residency_region,
                "tenant_id": user_ctx.tenant_id,
                "method": method.value,
                "label": label,
                "metadata": json.dumps(metadata or {}),
            },
        )
        await self._session.commit()
        return await self._fetch_method_or_raise(new_id, user_ctx.residency_region)

    async def get_method(
        self,
        mfa_id: UUID,
        residency_region: str,
    ) -> MfaMethod | None:
        result = await self._session.execute(
            text(
                f"""
                SELECT {_METHOD_COLUMNS}
                FROM mfa_methods
                WHERE id = :id AND residency_region = :region
                """  # noqa: S608
            ),
            {"id": mfa_id, "region": residency_region},
        )
        row = result.one_or_none()
        return _method_from_row(row) if row else None

    async def list_methods(
        self,
        user_id: UUID,
        residency_region: str,
        *,
        include_disabled: bool = False,
    ) -> list[MfaMethod]:
        if include_disabled:
            query = text(
                f"""
                SELECT {_METHOD_COLUMNS}
                FROM mfa_methods
                WHERE user_id = :user_id AND residency_region = :region
                ORDER BY created_at ASC
                """  # noqa: S608
            )
        else:
            query = text(
                f"""
                SELECT {_METHOD_COLUMNS}
                FROM mfa_methods
                WHERE user_id = :user_id AND residency_region = :region
                  AND status <> 'disabled'
                ORDER BY created_at ASC
                """  # noqa: S608
            )
        result = await self._session.execute(
            query,
            {"user_id": user_id, "region": residency_region},
        )
        return [_method_from_row(row) for row in result.all()]

    async def activate_method(
        self,
        mfa_id: UUID,
        residency_region: str,
        *,
        at: datetime,
    ) -> None:
        await self._session.execute(
            text(
                """
                UPDATE mfa_methods
                SET status = 'active',
                    enrolled_at = COALESCE(enrolled_at, :at),
                    updated_at = now()
                WHERE id = :id AND residency_region = :region
                """
            ),
            {"id": mfa_id, "region": residency_region, "at": at},
        )
        await self._session.commit()

    async def disable_method(
        self,
        mfa_id: UUID,
        residency_region: str,
    ) -> None:
        await self._session.execute(
            text(
                """
                UPDATE mfa_methods
                SET status = 'disabled', updated_at = now()
                WHERE id = :id AND residency_region = :region
                """
            ),
            {"id": mfa_id, "region": residency_region},
        )
        await self._session.commit()

    async def touch_method_last_used(
        self,
        mfa_id: UUID,
        residency_region: str,
        *,
        at: datetime,
    ) -> None:
        await self._session.execute(
            text(
                """
                UPDATE mfa_methods
                SET last_used_at = :at, updated_at = now()
                WHERE id = :id AND residency_region = :region
                """
            ),
            {"id": mfa_id, "region": residency_region, "at": at},
        )
        await self._session.commit()

    # --- TOTP secrets ---------------------------------------------------
    async def store_totp_secret(
        self,
        *,
        mfa_id: UUID,
        residency_region: str,
        secret_plaintext: str,
        period: int,
        digits: int,
        algorithm: str,
    ) -> None:
        key = get_settings().mfa_at_rest_key.get_secret_value()
        await self._session.execute(
            text(
                """
                INSERT INTO mfa_totp_secrets (
                    mfa_id, residency_region, secret_bytes, period, digits, algorithm
                ) VALUES (
                    :id, :region, pgp_sym_encrypt(:plaintext, :key), :period, :digits, :alg
                )
                ON CONFLICT (mfa_id, residency_region) DO UPDATE
                SET secret_bytes = EXCLUDED.secret_bytes,
                    period = EXCLUDED.period,
                    digits = EXCLUDED.digits,
                    algorithm = EXCLUDED.algorithm
                """
            ),
            {
                "id": mfa_id,
                "region": residency_region,
                "plaintext": secret_plaintext,
                "key": key,
                "period": period,
                "digits": digits,
                "alg": algorithm,
            },
        )
        await self._session.commit()

    async def fetch_totp_secret(
        self,
        mfa_id: UUID,
        residency_region: str,
    ) -> str | None:
        key = get_settings().mfa_at_rest_key.get_secret_value()
        result = await self._session.execute(
            text(
                """
                SELECT pgp_sym_decrypt(secret_bytes, :key) AS plaintext
                FROM mfa_totp_secrets
                WHERE mfa_id = :id AND residency_region = :region
                """
            ),
            {"id": mfa_id, "region": residency_region, "key": key},
        )
        row = result.one_or_none()
        if row is None:
            return None
        return str(row[0]) if row[0] is not None else None

    # --- WebAuthn credentials ------------------------------------------
    async def store_webauthn_credential(self, cred: WebAuthnCredential) -> None:
        await self._session.execute(
            text(
                """
                INSERT INTO mfa_webauthn_credentials (
                    mfa_id, residency_region, credential_id, public_key_bytes,
                    sign_count, transports, attestation_format, aaguid
                ) VALUES (
                    :id, :region, :cred_id, :pk,
                    :sign_count, :transports, :att_fmt, :aaguid
                )
                ON CONFLICT (mfa_id, residency_region) DO UPDATE
                SET credential_id = EXCLUDED.credential_id,
                    public_key_bytes = EXCLUDED.public_key_bytes,
                    sign_count = EXCLUDED.sign_count,
                    transports = EXCLUDED.transports,
                    attestation_format = EXCLUDED.attestation_format,
                    aaguid = EXCLUDED.aaguid
                """
            ),
            {
                "id": cred.mfa_id,
                "region": cred.residency_region,
                "cred_id": cred.credential_id,
                "pk": cred.public_key_bytes,
                "sign_count": cred.sign_count,
                "transports": list(cred.transports),
                "att_fmt": cred.attestation_format,
                "aaguid": cred.aaguid,
            },
        )
        await self._session.commit()

    async def fetch_webauthn_credential(
        self,
        mfa_id: UUID,
        residency_region: str,
    ) -> WebAuthnCredential | None:
        result = await self._session.execute(
            text(
                """
                SELECT mfa_id, residency_region, credential_id, public_key_bytes,
                       sign_count, transports, attestation_format, aaguid
                FROM mfa_webauthn_credentials
                WHERE mfa_id = :id AND residency_region = :region
                """
            ),
            {"id": mfa_id, "region": residency_region},
        )
        row = result.one_or_none()
        if row is None:
            return None
        m = row._mapping
        return WebAuthnCredential(
            mfa_id=m["mfa_id"],
            residency_region=str(m["residency_region"]),
            credential_id=bytes(m["credential_id"]),
            public_key_bytes=bytes(m["public_key_bytes"]),
            sign_count=int(m["sign_count"]),
            transports=tuple(m["transports"] or ()),
            attestation_format=m["attestation_format"],
            aaguid=m["aaguid"],
        )

    async def update_webauthn_sign_count(
        self,
        mfa_id: UUID,
        residency_region: str,
        *,
        new_sign_count: int,
    ) -> None:
        await self._session.execute(
            text(
                """
                UPDATE mfa_webauthn_credentials
                SET sign_count = :n
                WHERE mfa_id = :id AND residency_region = :region
                """
            ),
            {"id": mfa_id, "region": residency_region, "n": new_sign_count},
        )
        await self._session.commit()

    # --- backup codes ---------------------------------------------------
    async def replace_backup_codes(
        self,
        *,
        user_ctx: MfaUserContext,
        code_hashes: list[bytes],
    ) -> int:
        await self._session.execute(
            text(
                """
                DELETE FROM mfa_backup_codes
                WHERE user_id = :uid AND residency_region = :region
                """
            ),
            {"uid": user_ctx.user_id, "region": user_ctx.residency_region},
        )
        for code_hash in code_hashes:
            await self._session.execute(
                text(
                    """
                    INSERT INTO mfa_backup_codes (
                        user_id, residency_region, tenant_id, code_hash
                    ) VALUES (
                        :uid, :region, :tid, :code_hash
                    )
                    """
                ),
                {
                    "uid": user_ctx.user_id,
                    "region": user_ctx.residency_region,
                    "tid": user_ctx.tenant_id,
                    "code_hash": code_hash,
                },
            )
        await self._session.commit()
        return len(code_hashes)

    async def consume_backup_code(
        self,
        *,
        user_id: UUID,
        residency_region: str,
        code_hash: bytes,
        at: datetime,
    ) -> bool:
        result = await self._session.execute(
            text(
                """
                UPDATE mfa_backup_codes
                SET used_at = :at
                WHERE user_id = :uid AND residency_region = :region
                  AND code_hash = :code_hash AND used_at IS NULL
                RETURNING id
                """
            ),
            {
                "uid": user_id,
                "region": residency_region,
                "code_hash": code_hash,
                "at": at,
            },
        )
        await self._session.commit()
        return result.one_or_none() is not None

    async def list_backup_codes(
        self,
        user_id: UUID,
        residency_region: str,
        *,
        only_unused: bool = True,
    ) -> list[BackupCode]:
        if only_unused:
            query = text(
                """
                SELECT id, user_id, residency_region, code_hash, used_at, created_at
                FROM mfa_backup_codes
                WHERE user_id = :uid AND residency_region = :region
                  AND used_at IS NULL
                ORDER BY created_at ASC
                """
            )
        else:
            query = text(
                """
                SELECT id, user_id, residency_region, code_hash, used_at, created_at
                FROM mfa_backup_codes
                WHERE user_id = :uid AND residency_region = :region
                ORDER BY created_at ASC
                """
            )
        result = await self._session.execute(
            query,
            {"uid": user_id, "region": residency_region},
        )
        out: list[BackupCode] = []
        for row in result.all():
            m = row._mapping
            out.append(
                BackupCode(
                    id=m["id"],
                    user_id=m["user_id"],
                    residency_region=str(m["residency_region"]),
                    code_hash=bytes(m["code_hash"]),
                    used_at=m["used_at"],
                    created_at=m["created_at"],
                )
            )
        return out

    # --- challenges -----------------------------------------------------
    async def create_challenge(self, challenge: MfaChallenge) -> MfaChallenge:
        import json

        await self._session.execute(
            text(
                """
                INSERT INTO mfa_challenges (
                    id, user_id, residency_region, method, challenge_bytes,
                    metadata, expires_at, created_at
                ) VALUES (
                    :id, :uid, :region, :method, :cb,
                    CAST(:metadata AS jsonb), :exp, :created
                )
                """
            ),
            {
                "id": challenge.id,
                "uid": challenge.user_id,
                "region": challenge.residency_region,
                "method": challenge.method.value,
                "cb": challenge.challenge_bytes,
                "metadata": json.dumps(challenge.metadata or {}),
                "exp": challenge.expires_at,
                "created": challenge.created_at,
            },
        )
        await self._session.commit()
        return challenge

    async def get_challenge(self, challenge_id: UUID) -> MfaChallenge | None:
        result = await self._session.execute(
            text(
                """
                SELECT id, user_id, residency_region, method, challenge_bytes,
                       metadata, expires_at, completed_at, created_at
                FROM mfa_challenges
                WHERE id = :id
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"id": challenge_id},
        )
        row = result.one_or_none()
        if row is None:
            return None
        m = row._mapping
        metadata = m["metadata"] or {}
        if isinstance(metadata, str):
            import json

            metadata = json.loads(metadata)
        cb = m["challenge_bytes"]
        return MfaChallenge(
            id=m["id"],
            user_id=m["user_id"],
            residency_region=str(m["residency_region"]),
            method=MfaMethodKind(m["method"]),
            challenge_bytes=bytes(cb) if cb is not None else None,
            metadata=metadata,
            expires_at=m["expires_at"],
            completed_at=m["completed_at"],
            created_at=m["created_at"],
        )

    async def complete_challenge(self, challenge_id: UUID, *, at: datetime) -> None:
        await self._session.execute(
            text(
                """
                UPDATE mfa_challenges
                SET completed_at = :at
                WHERE id = :id AND completed_at IS NULL
                """
            ),
            {"id": challenge_id, "at": at},
        )
        await self._session.commit()

    # --- user step-up clock --------------------------------------------
    async def mark_user_mfa_satisfied(
        self,
        user_id: UUID,
        residency_region: str,
        *,
        at: datetime,
    ) -> None:
        await self._session.execute(
            text(
                """
                UPDATE users
                SET last_mfa_at = :at,
                    mfa_enabled = true
                WHERE id = :id AND residency_region = :region
                """
            ),
            {"id": user_id, "region": residency_region, "at": at},
        )
        await self._session.commit()

    async def get_user_last_mfa_at(
        self,
        user_id: UUID,
        residency_region: str,
    ) -> datetime | None:
        result = await self._session.execute(
            text(
                """
                SELECT last_mfa_at FROM users
                WHERE id = :id AND residency_region = :region
                """
            ),
            {"id": user_id, "region": residency_region},
        )
        row = result.one_or_none()
        return row[0] if row else None

    # --- internals ------------------------------------------------------
    async def _fetch_method_or_raise(self, mfa_id: UUID, region: str) -> MfaMethod:
        method = await self.get_method(mfa_id, region)
        if method is None:  # pragma: no cover — INSERT just succeeded
            raise RuntimeError(f"mfa method {mfa_id} disappeared after insert")
        return method
