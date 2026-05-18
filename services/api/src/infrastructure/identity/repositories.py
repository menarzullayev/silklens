"""SQLAlchemy implementations of the identity-domain repository protocols.

We use ``text()``-based SQL rather than ORM mapping for now: migrations 0004-0009
already define the canonical schema, and writing ORM models on top adds friction
without much value at this stage. ORM models land alongside the heritage domain
in a later FAZA when we need polymorphic loading.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Final
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.identity.entities import (
    ResidencyRegion,
    Session,
    TrustTier,
    User,
    UserEmail,
    UserStatus,
)

_SELECT_USER_COLUMNS: Final = """
    id, tenant_id, residency_region, pub_id, status, is_guest,
    trust_tier, trust_score, preferred_locale, preferred_timezone,
    email_verified_at, phone_verified_at, mfa_enabled,
    last_login_at, last_active_at,
    created_at, updated_at, deleted_at, anonymized_at
"""


def _user_from_row(row: object) -> User:
    """Map a SQLAlchemy Row to the domain ``User`` entity."""
    r = row._mapping  # type: ignore[attr-defined]
    return User(
        id=r["id"],
        tenant_id=r["tenant_id"],
        residency_region=ResidencyRegion(r["residency_region"]),
        pub_id=r["pub_id"],
        status=UserStatus(r["status"]),
        is_guest=r["is_guest"],
        trust_tier=TrustTier(r["trust_tier"]),
        trust_score=r["trust_score"],
        preferred_locale=r["preferred_locale"],
        preferred_timezone=r["preferred_timezone"],
        email_verified_at=r["email_verified_at"],
        phone_verified_at=r["phone_verified_at"],
        mfa_enabled=r["mfa_enabled"],
        last_login_at=r["last_login_at"],
        last_active_at=r["last_active_at"],
        created_at=r["created_at"],
        updated_at=r["updated_at"],
        deleted_at=r["deleted_at"],
        anonymized_at=r["anonymized_at"],
    )


def _email_from_row(row: object) -> UserEmail:
    r = row._mapping  # type: ignore[attr-defined]
    return UserEmail(
        id=r["id"],
        user_id=r["user_id"],
        residency_region=ResidencyRegion(r["residency_region"]),
        tenant_id=r["tenant_id"],
        email=r["email"],
        is_primary=r["is_primary"],
        is_forwarded=r["is_forwarded"],
        verified_at=r["verified_at"],
        created_at=r["created_at"],
    )


class SqlUserRepository:
    """SQLAlchemy-backed implementation of ``UserRepository``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(
        self,
        user_id: UUID,
        residency_region: ResidencyRegion,
    ) -> User | None:
        # _SELECT_USER_COLUMNS is a module-level constant, never user input.
        result = await self._session.execute(
            text(
                f"""
                SELECT {_SELECT_USER_COLUMNS}
                FROM users
                WHERE id = :id AND residency_region = :region
                """  # noqa: S608
            ),
            {"id": user_id, "region": residency_region.value},
        )
        row = result.one_or_none()
        return _user_from_row(row) if row else None

    async def get_by_pub_id(self, pub_id: str) -> User | None:
        result = await self._session.execute(
            text(
                f"""
                SELECT {_SELECT_USER_COLUMNS}
                FROM users
                WHERE pub_id = :pub_id AND deleted_at IS NULL
                LIMIT 1
                """  # noqa: S608
            ),
            {"pub_id": pub_id},
        )
        row = result.one_or_none()
        return _user_from_row(row) if row else None

    async def find_by_email(
        self,
        email: str,
        *,
        tenant_id: UUID,
    ) -> tuple[User, UserEmail] | None:
        result = await self._session.execute(
            text(
                """
                SELECT
                    u.id, u.tenant_id, u.residency_region, u.pub_id, u.status, u.is_guest,
                    u.trust_tier, u.trust_score, u.preferred_locale, u.preferred_timezone,
                    u.email_verified_at, u.phone_verified_at, u.mfa_enabled,
                    u.last_login_at, u.last_active_at,
                    u.created_at, u.updated_at, u.deleted_at, u.anonymized_at,
                    e.id AS email_id, e.user_id AS email_user_id,
                    e.residency_region AS email_residency, e.tenant_id AS email_tenant_id,
                    e.email, e.is_primary, e.is_forwarded, e.verified_at AS email_verified_at_real,
                    e.created_at AS email_created_at
                FROM user_emails e
                JOIN users u
                  ON u.id = e.user_id AND u.residency_region = e.residency_region
                WHERE e.email = :email AND e.tenant_id = :tenant_id
                  AND u.deleted_at IS NULL
                LIMIT 1
                """
            ),
            {"email": email, "tenant_id": tenant_id},
        )
        row = result.one_or_none()
        if row is None:
            return None
        m = row._mapping  # type: ignore[attr-defined]
        user = User(
            id=m["id"],
            tenant_id=m["tenant_id"],
            residency_region=ResidencyRegion(m["residency_region"]),
            pub_id=m["pub_id"],
            status=UserStatus(m["status"]),
            is_guest=m["is_guest"],
            trust_tier=TrustTier(m["trust_tier"]),
            trust_score=m["trust_score"],
            preferred_locale=m["preferred_locale"],
            preferred_timezone=m["preferred_timezone"],
            email_verified_at=m["email_verified_at"],
            phone_verified_at=m["phone_verified_at"],
            mfa_enabled=m["mfa_enabled"],
            last_login_at=m["last_login_at"],
            last_active_at=m["last_active_at"],
            created_at=m["created_at"],
            updated_at=m["updated_at"],
            deleted_at=m["deleted_at"],
            anonymized_at=m["anonymized_at"],
        )
        email_row = UserEmail(
            id=m["email_id"],
            user_id=m["email_user_id"],
            residency_region=ResidencyRegion(m["email_residency"]),
            tenant_id=m["email_tenant_id"],
            email=m["email"],
            is_primary=m["is_primary"],
            is_forwarded=m["is_forwarded"],
            verified_at=m["email_verified_at_real"],
            created_at=m["email_created_at"],
        )
        return user, email_row

    async def email_exists(self, email: str, *, tenant_id: UUID) -> bool:
        result = await self._session.execute(
            text(
                """
                SELECT 1 FROM user_emails
                WHERE email = :email AND tenant_id = :tenant_id
                LIMIT 1
                """
            ),
            {"email": email, "tenant_id": tenant_id},
        )
        return result.one_or_none() is not None

    async def create_with_email(
        self,
        *,
        user: User,
        email: str,
        password_hash: str,
        password_algorithm: str,
    ) -> tuple[User, UserEmail]:
        await self._session.execute(
            text(
                """
                INSERT INTO users (
                    id, tenant_id, residency_region, pub_id,
                    password_hash, password_algorithm,
                    status, is_guest, trust_tier, trust_score,
                    preferred_locale, preferred_timezone,
                    created_at, updated_at
                ) VALUES (
                    :id, :tenant_id, :residency_region, :pub_id,
                    :password_hash, :password_algorithm,
                    :status, :is_guest, :trust_tier, :trust_score,
                    :preferred_locale, :preferred_timezone,
                    :created_at, :updated_at
                )
                """
            ),
            {
                "id": user.id,
                "tenant_id": user.tenant_id,
                "residency_region": user.residency_region.value,
                "pub_id": user.pub_id,
                "password_hash": password_hash,
                "password_algorithm": password_algorithm,
                "status": user.status.value,
                "is_guest": user.is_guest,
                "trust_tier": user.trust_tier.value,
                "trust_score": user.trust_score,
                "preferred_locale": user.preferred_locale,
                "preferred_timezone": user.preferred_timezone,
                "created_at": user.created_at,
                "updated_at": user.updated_at,
            },
        )
        await self._session.execute(
            text(
                """
                INSERT INTO user_profiles (
                    user_id, residency_region, tenant_id, display_name
                ) VALUES (
                    :user_id, :residency_region, :tenant_id, :display_name
                )
                """
            ),
            {
                "user_id": user.id,
                "residency_region": user.residency_region.value,
                "tenant_id": user.tenant_id,
                "display_name": user.pub_id,
            },
        )
        email_id = uuid4()
        await self._session.execute(
            text(
                """
                INSERT INTO user_emails (
                    id, user_id, residency_region, tenant_id,
                    email, is_primary, is_forwarded
                ) VALUES (
                    :id, :user_id, :residency_region, :tenant_id,
                    :email, true, false
                )
                """
            ),
            {
                "id": email_id,
                "user_id": user.id,
                "residency_region": user.residency_region.value,
                "tenant_id": user.tenant_id,
                "email": email,
            },
        )
        await self._session.commit()
        email_row = UserEmail(
            id=email_id,
            user_id=user.id,
            residency_region=user.residency_region,
            tenant_id=user.tenant_id,
            email=email,
            is_primary=True,
            is_forwarded=False,
            verified_at=None,
            created_at=user.created_at,
        )
        return user, email_row

    async def update_last_login(
        self,
        user_id: UUID,
        residency_region: ResidencyRegion,
    ) -> None:
        await self._session.execute(
            text(
                """
                UPDATE users
                SET last_login_at = now(),
                    last_active_at = now(),
                    login_count = login_count + 1
                WHERE id = :id AND residency_region = :region
                """
            ),
            {"id": user_id, "region": residency_region.value},
        )
        await self._session.commit()

    async def get_password_hash(
        self,
        user_id: UUID,
        residency_region: ResidencyRegion,
    ) -> tuple[str, str] | None:
        result = await self._session.execute(
            text(
                """
                SELECT password_hash, password_algorithm
                FROM users
                WHERE id = :id AND residency_region = :region
                """
            ),
            {"id": user_id, "region": residency_region.value},
        )
        row = result.one_or_none()
        if row is None:
            return None
        h, a = row[0], row[1]
        if h is None:
            return None
        return h, a


class SqlSessionRepository:
    """SQLAlchemy-backed sessions + refresh tokens."""

    def __init__(self, db_session: AsyncSession) -> None:
        self._db = db_session

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
    ) -> Session:
        session_id = uuid4()
        now = datetime.now(UTC)
        await self._db.execute(
            text(
                """
                INSERT INTO sessions (
                    id, user_id, residency_region, tenant_id,
                    ip_address, user_agent,
                    issued_at, last_seen_at, expires_at
                ) VALUES (
                    :id, :user_id, :residency_region, :tenant_id,
                    :ip_address, :user_agent,
                    :issued, :last_seen, :expires
                )
                """
            ),
            {
                "id": session_id,
                "user_id": user.id,
                "residency_region": user.residency_region.value,
                "tenant_id": user.tenant_id,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "issued": now,
                "last_seen": now,
                "expires": refresh_token_expires_at,
            },
        )
        await self._db.execute(
            text(
                """
                INSERT INTO refresh_tokens (
                    session_id, session_residency,
                    user_id, residency_region, tenant_id,
                    token_hash, family_id, expires_at
                ) VALUES (
                    :session_id, :session_residency,
                    :user_id, :residency_region, :tenant_id,
                    :token_hash, :family_id, :expires_at
                )
                """
            ),
            {
                "session_id": session_id,
                "session_residency": user.residency_region.value,
                "user_id": user.id,
                "residency_region": user.residency_region.value,
                "tenant_id": user.tenant_id,
                "token_hash": refresh_token_hash,
                "family_id": family_id,
                "expires_at": refresh_token_expires_at,
            },
        )
        await self._db.commit()
        return Session(
            id=session_id,
            user_id=user.id,
            residency_region=user.residency_region,
            tenant_id=user.tenant_id,
            issued_at=now,
            last_seen_at=now,
            expires_at=refresh_token_expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def get_session(
        self,
        session_id: UUID,
        residency_region: ResidencyRegion,
    ) -> Session | None:
        result = await self._db.execute(
            text(
                """
                SELECT id, user_id, residency_region, tenant_id,
                       ip_address, user_agent,
                       issued_at, last_seen_at, expires_at,
                       revoked_at, revoke_reason
                FROM sessions
                WHERE id = :id AND residency_region = :region
                """
            ),
            {"id": session_id, "region": residency_region.value},
        )
        row = result.one_or_none()
        if row is None:
            return None
        m = row._mapping  # type: ignore[attr-defined]
        return Session(
            id=m["id"],
            user_id=m["user_id"],
            residency_region=ResidencyRegion(m["residency_region"]),
            tenant_id=m["tenant_id"],
            issued_at=m["issued_at"],
            last_seen_at=m["last_seen_at"],
            expires_at=m["expires_at"],
            ip_address=str(m["ip_address"]) if m["ip_address"] else None,
            user_agent=m["user_agent"],
            revoked_at=m["revoked_at"],
            revoke_reason=m["revoke_reason"],
        )

    async def revoke_session(
        self,
        session_id: UUID,
        residency_region: ResidencyRegion,
        *,
        reason: str,
    ) -> None:
        await self._db.execute(
            text(
                """
                UPDATE sessions
                SET revoked_at = now(), revoke_reason = :reason
                WHERE id = :id AND residency_region = :region AND revoked_at IS NULL
                """
            ),
            {"id": session_id, "region": residency_region.value, "reason": reason},
        )
        await self._db.execute(
            text(
                """
                UPDATE refresh_tokens
                SET revoked_at = now(), revoke_reason = 'session_revoked'
                WHERE session_id = :id AND residency_region = :region AND revoked_at IS NULL
                """
            ),
            {"id": session_id, "region": residency_region.value},
        )
        await self._db.commit()

    async def rotate_refresh_token(
        self,
        *,
        old_token_hash: bytes,
        new_token_hash: bytes,
        new_expires_at: datetime,
    ) -> Session | None:
        # Look up the old refresh token; if already used → replay → revoke family
        result = await self._db.execute(
            text(
                """
                SELECT id, session_id, session_residency, user_id, residency_region,
                       tenant_id, family_id, used_at, revoked_at
                FROM refresh_tokens
                WHERE token_hash = :hash
                LIMIT 1
                """
            ),
            {"hash": old_token_hash},
        )
        row = result.one_or_none()
        if row is None:
            return None
        m = row._mapping  # type: ignore[attr-defined]
        if m["used_at"] is not None or m["revoked_at"] is not None:
            # Replay attempt: revoke the entire family.
            await self._db.execute(
                text(
                    """
                    UPDATE refresh_tokens
                    SET revoked_at = now(),
                        revoke_reason = 'token_replay'
                    WHERE family_id = :fam AND revoked_at IS NULL
                    """
                ),
                {"fam": m["family_id"]},
            )
            await self._db.execute(
                text(
                    """
                    UPDATE sessions
                    SET revoked_at = now(), revoke_reason = 'token_replay'
                    WHERE id = :sid AND residency_region = :region
                      AND revoked_at IS NULL
                    """
                ),
                {"sid": m["session_id"], "region": m["session_residency"]},
            )
            await self._db.commit()
            return None

        new_id = uuid4()
        # Mark old used + insert new in same transaction
        await self._db.execute(
            text(
                """
                UPDATE refresh_tokens
                SET used_at = now(), replaced_by_id = :new_id
                WHERE id = :old_id AND residency_region = :region
                """
            ),
            {
                "new_id": new_id,
                "old_id": m["id"],
                "region": m["residency_region"],
            },
        )
        await self._db.execute(
            text(
                """
                INSERT INTO refresh_tokens (
                    id, session_id, session_residency,
                    user_id, residency_region, tenant_id,
                    token_hash, family_id, expires_at
                ) VALUES (
                    :id, :session_id, :session_residency,
                    :user_id, :residency_region, :tenant_id,
                    :token_hash, :family_id, :expires_at
                )
                """
            ),
            {
                "id": new_id,
                "session_id": m["session_id"],
                "session_residency": m["session_residency"],
                "user_id": m["user_id"],
                "residency_region": m["residency_region"],
                "tenant_id": m["tenant_id"],
                "token_hash": new_token_hash,
                "family_id": m["family_id"],
                "expires_at": new_expires_at,
            },
        )
        await self._db.execute(
            text(
                """
                UPDATE sessions
                SET last_seen_at = now(), expires_at = :new_exp
                WHERE id = :sid AND residency_region = :region
                """
            ),
            {
                "new_exp": new_expires_at,
                "sid": m["session_id"],
                "region": m["session_residency"],
            },
        )
        await self._db.commit()
        return await self.get_session(m["session_id"], ResidencyRegion(m["session_residency"]))
