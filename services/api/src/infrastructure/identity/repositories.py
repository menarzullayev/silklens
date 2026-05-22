"""SQLAlchemy implementations of the identity-domain repository protocols.

We use ``text()``-based SQL rather than ORM mapping for now: migrations 0004-0009
already define the canonical schema, and writing ORM models on top adds friction
without much value at this stage. ORM models land alongside the heritage domain
in a later FAZA when we need polymorphic loading.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Final
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.identity.entities import (
    OAuthProfile,
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

    async def find_by_oauth_identity(
        self,
        *,
        provider_id: UUID,
        subject: str,
    ) -> tuple[User, UserEmail] | None:
        result = await self._session.execute(
            text(
                """
                SELECT
                    u.id, u.tenant_id, u.residency_region, u.pub_id,
                    u.status, u.is_guest, u.trust_tier, u.trust_score,
                    u.preferred_locale, u.preferred_timezone,
                    u.email_verified_at, u.phone_verified_at, u.mfa_enabled,
                    u.last_login_at, u.last_active_at,
                    u.created_at, u.updated_at, u.deleted_at, u.anonymized_at,
                    e.id          AS email_id,
                    e.user_id     AS email_user_id,
                    e.residency_region AS email_residency,
                    e.tenant_id   AS email_tenant_id,
                    e.email, e.is_primary, e.is_forwarded,
                    e.verified_at AS email_verified_at_real,
                    e.created_at  AS email_created_at
                FROM user_identities ui
                JOIN users u
                  ON u.id = ui.user_id AND u.residency_region = ui.residency_region
                JOIN user_emails e
                  ON e.user_id = u.id
                 AND e.residency_region = u.residency_region
                 AND e.is_primary = true
                WHERE ui.provider_id = :provider_id
                  AND ui.provider_subject = :subject
                  AND u.deleted_at IS NULL
                LIMIT 1
                """
            ),
            {"provider_id": provider_id, "subject": subject},
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

    async def create_oauth_user(
        self,
        *,
        user: User,
        email: str,
        email_verified: bool,
        provider_id: UUID,
        profile: OAuthProfile,
    ) -> tuple[User, UserEmail]:
        """Create user+email+profile+identity in one transaction. No password set."""
        now = user.created_at
        verified_at = now if email_verified else None

        await self._session.execute(
            text(
                """
                INSERT INTO users (
                    id, tenant_id, residency_region, pub_id,
                    status, is_guest, trust_tier, trust_score,
                    preferred_locale, preferred_timezone,
                    email_verified_at,
                    created_at, updated_at
                ) VALUES (
                    :id, :tenant_id, :residency_region, :pub_id,
                    :status, :is_guest, :trust_tier, :trust_score,
                    :preferred_locale, :preferred_timezone,
                    :email_verified_at,
                    :created_at, :updated_at
                )
                """
            ),
            {
                "id": user.id,
                "tenant_id": user.tenant_id,
                "residency_region": user.residency_region.value,
                "pub_id": user.pub_id,
                "status": user.status.value,
                "is_guest": user.is_guest,
                "trust_tier": user.trust_tier.value,
                "trust_score": user.trust_score,
                "preferred_locale": user.preferred_locale,
                "preferred_timezone": user.preferred_timezone,
                "email_verified_at": verified_at,
                "created_at": now,
                "updated_at": now,
            },
        )

        email_id = uuid4()
        await self._session.execute(
            text(
                """
                INSERT INTO user_emails (
                    id, user_id, residency_region, tenant_id,
                    email, is_primary, is_forwarded, verified_at
                ) VALUES (
                    :id, :user_id, :residency_region, :tenant_id,
                    :email, true, false, :verified_at
                )
                """
            ),
            {
                "id": email_id,
                "user_id": user.id,
                "residency_region": user.residency_region.value,
                "tenant_id": user.tenant_id,
                "email": email,
                "verified_at": verified_at,
            },
        )

        await self._session.execute(
            text(
                """
                INSERT INTO user_profiles (
                    user_id, residency_region, tenant_id,
                    display_name, full_name, avatar_url
                ) VALUES (
                    :user_id, :residency_region, :tenant_id,
                    :display_name, :full_name, :avatar_url
                )
                """
            ),
            {
                "user_id": user.id,
                "residency_region": user.residency_region.value,
                "tenant_id": user.tenant_id,
                "display_name": profile.display_name or user.pub_id,
                "full_name": profile.display_name,
                "avatar_url": profile.avatar_url,
            },
        )

        await self._session.execute(
            text(
                """
                INSERT INTO user_identities (
                    id, user_id, residency_region, tenant_id,
                    provider_id, provider_subject,
                    email_at_link, display_name_at_link,
                    raw_profile, linked_at, last_used_at
                ) VALUES (
                    :id, :user_id, :residency_region, :tenant_id,
                    :provider_id, :subject,
                    :email_at_link, :display_name_at_link,
                    CAST(:raw_profile AS jsonb), now(), now()
                )
                """
            ),
            {
                "id": uuid4(),
                "user_id": user.id,
                "residency_region": user.residency_region.value,
                "tenant_id": user.tenant_id,
                "provider_id": provider_id,
                "subject": profile.provider_subject,
                "email_at_link": email,
                "display_name_at_link": profile.display_name,
                "raw_profile": json.dumps(profile.raw),
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
            verified_at=verified_at,
            created_at=now,
        )
        return user, email_row

    async def upsert_oauth_identity(
        self,
        *,
        user: User,
        provider_id: UUID,
        profile: OAuthProfile,
    ) -> None:
        """Link (or refresh) an OAuth identity for an existing user.

        On first link: inserts user_identities and patches email + profile
        with the provider's authoritative data. On subsequent logins: updates
        last_used_at and raw_profile only (preserves user-edited profile).
        Uses xmax to distinguish INSERT from UPDATE.
        """
        result = await self._session.execute(
            text(
                """
                INSERT INTO user_identities (
                    id, user_id, residency_region, tenant_id,
                    provider_id, provider_subject,
                    email_at_link, display_name_at_link,
                    raw_profile, linked_at, last_used_at
                ) VALUES (
                    :id, :user_id, :residency_region, :tenant_id,
                    :provider_id, :subject,
                    :email_at_link, :display_name_at_link,
                    CAST(:raw_profile AS jsonb), now(), now()
                )
                ON CONFLICT (provider_id, provider_subject, residency_region)
                DO UPDATE SET
                    last_used_at          = now(),
                    raw_profile           = EXCLUDED.raw_profile,
                    updated_at            = now()
                RETURNING (linked_at = last_used_at) AS was_inserted
                """
            ),
            {
                "id": uuid4(),
                "user_id": user.id,
                "residency_region": user.residency_region.value,
                "tenant_id": user.tenant_id,
                "provider_id": provider_id,
                "subject": profile.provider_subject,
                "email_at_link": profile.email,
                "display_name_at_link": profile.display_name,
                "raw_profile": json.dumps(profile.raw),
            },
        )
        row = result.one_or_none()
        was_inserted: bool = row[0] if row else False

        if profile.email_verified:
            await self._session.execute(
                text(
                    """
                    UPDATE user_emails
                    SET verified_at = now(), updated_at = now()
                    WHERE user_id = :user_id
                      AND residency_region = :region
                      AND verified_at IS NULL
                    """
                ),
                {"user_id": user.id, "region": user.residency_region.value},
            )
            await self._session.execute(
                text(
                    """
                    UPDATE users
                    SET email_verified_at = now(), updated_at = now()
                    WHERE id = :user_id
                      AND residency_region = :region
                      AND email_verified_at IS NULL
                    """
                ),
                {"user_id": user.id, "region": user.residency_region.value},
            )

        # On first link: overwrite the placeholder display_name (= pub_id) and
        # set avatar_url. On subsequent logins: don't disturb user edits.
        if was_inserted:
            await self._session.execute(
                text(
                    """
                    UPDATE user_profiles
                    SET
                        display_name = COALESCE(:display_name, display_name),
                        full_name    = COALESCE(:full_name, full_name),
                        avatar_url   = COALESCE(:avatar_url, avatar_url),
                        updated_at   = now()
                    WHERE user_id = :user_id AND residency_region = :region
                    """
                ),
                {
                    "user_id": user.id,
                    "region": user.residency_region.value,
                    "display_name": profile.display_name,
                    "full_name": profile.display_name,
                    "avatar_url": profile.avatar_url,
                },
            )

        await self._session.commit()

    async def verify_email(self, user_id: UUID, residency_region: ResidencyRegion) -> None:
        """Mark primary email + user row as verified (idempotent)."""
        await self._session.execute(
            text(
                """
                UPDATE user_emails
                SET verified_at = now(), updated_at = now()
                WHERE user_id = :user_id
                  AND residency_region = :region
                  AND verified_at IS NULL
                """
            ),
            {"user_id": user_id, "region": residency_region.value},
        )
        await self._session.execute(
            text(
                """
                UPDATE users
                SET email_verified_at = now(),
                    status = 'active',
                    updated_at = now()
                WHERE id = :user_id
                  AND residency_region = :region
                  AND email_verified_at IS NULL
                """
            ),
            {"user_id": user_id, "region": residency_region.value},
        )
        await self._session.commit()


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
        # Atomic mark-used: one UPDATE that succeeds only on the first concurrent
        # rotation attempt. Fixes CRIT-2 / SEC-012 — eliminates the TOCTOU race
        # in the previous SELECT-then-UPDATE flow.
        new_id = uuid4()
        result = await self._db.execute(
            text(
                """
                UPDATE refresh_tokens
                SET used_at = now(), replaced_by_id = :new_id
                WHERE token_hash = :hash
                  AND used_at IS NULL
                  AND revoked_at IS NULL
                RETURNING id, session_id, session_residency, user_id,
                          residency_region, tenant_id, family_id
                """
            ),
            {"hash": old_token_hash, "new_id": new_id},
        )
        row = result.one_or_none()
        if row is None:
            # Either the token is unknown OR a concurrent request already
            # consumed it — both are replay. Look up the family for revocation.
            replay_row = await self._db.execute(
                text(
                    """
                    SELECT family_id, session_id, session_residency
                    FROM refresh_tokens
                    WHERE token_hash = :hash
                    LIMIT 1
                    """
                ),
                {"hash": old_token_hash},
            )
            replay = replay_row.one_or_none()
            if replay is None:
                # Truly unknown token. Nothing to revoke.
                return None
            rm = replay._mapping  # type: ignore[attr-defined]
            await self._db.execute(
                text(
                    """
                    UPDATE refresh_tokens
                    SET revoked_at = now(), revoke_reason = 'token_replay'
                    WHERE family_id = :fam AND revoked_at IS NULL
                    """
                ),
                {"fam": rm["family_id"]},
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
                {"sid": rm["session_id"], "region": rm["session_residency"]},
            )
            await self._db.commit()
            return None

        m = row._mapping  # type: ignore[attr-defined]
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


class SqlLoginAttemptRepository:
    """SQLAlchemy-backed login_attempts ledger (migration 0070).

    The lookback query is index-covered by ``idx_login_attempts_identifier_at``
    and naturally pruned to the most recent partition because
    ``attempted_at >= now() - interval`` is a partition-pruning predicate.
    """

    def __init__(self, db_session: AsyncSession) -> None:
        self._db = db_session

    async def record_attempt(
        self,
        *,
        identifier: str,
        succeeded: bool,
        ip_address: str | None,
        user_agent: str | None,
        failure_reason: str | None,
    ) -> None:
        await self._db.execute(
            text(
                """
                INSERT INTO login_attempts (
                    identifier, succeeded, ip_address, user_agent, failure_reason
                ) VALUES (
                    :identifier, :succeeded, CAST(:ip AS inet), :ua, :reason
                )
                """
            ),
            {
                "identifier": identifier,
                "succeeded": succeeded,
                "ip": ip_address,
                "ua": user_agent,
                "reason": failure_reason,
            },
        )
        await self._db.commit()

    async def count_recent_failures(
        self,
        *,
        identifier: str,
        ip_address: str | None,
        within_seconds: int,
    ) -> int:
        # Two-clause filter: identifier always; IP optional. Same window for
        # both so the lockout follows the user across IP changes inside the
        # 10-minute pane (best-effort defence against IP rotation).
        if ip_address is None:
            result = await self._db.execute(
                text(
                    """
                    SELECT count(*) FROM login_attempts
                    WHERE identifier = :identifier
                      AND succeeded = false
                      AND attempted_at >= now() - make_interval(secs => :win)
                    """
                ),
                {"identifier": identifier, "win": within_seconds},
            )
        else:
            result = await self._db.execute(
                text(
                    """
                    SELECT count(*) FROM login_attempts
                    WHERE identifier = :identifier
                      AND ip_address = CAST(:ip AS inet)
                      AND succeeded = false
                      AND attempted_at >= now() - make_interval(secs => :win)
                    """
                ),
                {"identifier": identifier, "ip": ip_address, "win": within_seconds},
            )
        return int(result.scalar_one())
