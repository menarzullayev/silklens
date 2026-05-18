"""Identity domain service — pure business logic on top of repository protocols.

The service is framework-free. The API layer wraps it with FastAPI routers
and middleware; tests substitute fake repositories.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from src.domain.identity.entities import (
    AuthenticatedSession,
    Credentials,
    RegistrationRequest,
    TrustTier,
    User,
    UserStatus,
)
from src.domain.identity.errors import (
    AccountInactive,
    EmailAlreadyRegistered,
    InvalidCredentials,
    RefreshTokenReused,
    WeakPassword,
)
from src.domain.identity.repositories import SessionRepository, UserRepository


class PasswordHasher(Protocol):
    """Domain-side protocol; concrete argon2id impl in infrastructure."""

    def hash(self, password: str) -> str: ...
    def verify(self, hashed: str, password: str) -> bool: ...
    @property
    def algorithm(self) -> str: ...


class TokenIssuer(Protocol):
    """JWT issuer + opaque-refresh hashing — implementation in infrastructure."""

    def issue_access(self, *, user: User, session_id: UUID) -> tuple[str, datetime]: ...
    def issue_refresh(self) -> tuple[str, bytes, datetime]:
        """Return (plaintext, hashed, expires_at). Plaintext returned ONCE to caller."""

    def hash_refresh(self, plaintext: str) -> bytes:
        """Used during refresh: hash incoming token to compare with stored hash."""


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


def _generate_pub_id() -> str:
    """16 URL-safe characters from base62 — matches users.pub_id CHECK."""
    return secrets.token_urlsafe(12)[:16]


def _validate_password(password: str) -> None:
    """FAZA 1 minimal policy. Tighter rules land in a later ADR."""
    if len(password) < 12:
        raise WeakPassword("password must be at least 12 characters long")
    if password.lower() == password or password.upper() == password:
        raise WeakPassword("password must contain mixed case characters")
    if not any(ch.isdigit() for ch in password):
        raise WeakPassword("password must contain at least one digit")


class AuthService:
    """Application service orchestrating identity flows."""

    def __init__(
        self,
        *,
        users: UserRepository,
        sessions: SessionRepository,
        hasher: PasswordHasher,
        tokens: TokenIssuer,
        clock: Clock | None = None,
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._hasher = hasher
        self._tokens = tokens
        self._clock = clock or SystemClock()

    # --- registration ---------------------------------------------------

    async def register(self, request: RegistrationRequest) -> User:
        _validate_password(request.password)

        normalized_email = request.email.strip().lower()
        if await self._users.email_exists(normalized_email, tenant_id=request.tenant_id):
            raise EmailAlreadyRegistered(normalized_email)

        now = self._clock.now()
        user = User(
            id=uuid4(),
            tenant_id=request.tenant_id,
            residency_region=request.residency_region,
            pub_id=_generate_pub_id(),
            status=UserStatus.ACTIVE,
            is_guest=False,
            trust_tier=TrustTier.NEW,
            trust_score=0,
            preferred_locale=request.preferred_locale,
            preferred_timezone=request.preferred_timezone,
            created_at=now,
            updated_at=now,
        )

        password_hash = self._hasher.hash(request.password)
        user, _email = await self._users.create_with_email(
            user=user,
            email=normalized_email,
            password_hash=password_hash,
            password_algorithm=self._hasher.algorithm,
        )
        return user

    # --- login ----------------------------------------------------------

    async def login(
        self,
        credentials: Credentials,
        *,
        tenant_id: UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuthenticatedSession:
        if credentials.email is None:
            # Phone-OTP login goes through a different flow; not yet implemented.
            raise InvalidCredentials("phone-otp login not yet supported")

        found = await self._users.find_by_email(
            credentials.email.strip().lower(), tenant_id=tenant_id
        )
        if found is None:
            raise InvalidCredentials("email or password is incorrect")
        user, _email_row = found

        if not user.is_active:
            raise AccountInactive(user.status.value)

        password_record = await self._users.get_password_hash(user.id, user.residency_region)
        if password_record is None:
            raise InvalidCredentials("no password set for this account")
        password_hash, _algorithm = password_record
        if not self._hasher.verify(password_hash, credentials.password):
            raise InvalidCredentials("email or password is incorrect")

        return await self._issue_session(user, ip_address=ip_address, user_agent=user_agent)

    # --- refresh -------------------------------------------------------

    async def refresh(self, refresh_token: str) -> AuthenticatedSession:
        new_plain, new_hashed, new_refresh_expires = self._tokens.issue_refresh()
        old_hash = self._tokens.hash_refresh(refresh_token)
        session = await self._sessions.rotate_refresh_token(
            old_token_hash=old_hash,
            new_token_hash=new_hashed,
            new_expires_at=new_refresh_expires,
        )
        if session is None:
            # Either unknown token or replay; the repository revokes the family
            # internally on replay, but we surface the error so callers don't
            # think they got a fresh session.
            raise RefreshTokenReused("refresh token unknown or already used")

        user = await self._users.get_by_id(session.user_id, session.residency_region)
        if user is None or not user.is_active:
            raise AccountInactive("user no longer active")

        access_token, access_expires = self._tokens.issue_access(user=user, session_id=session.id)
        return AuthenticatedSession(
            user=user,
            session=session,
            access_token=access_token,
            refresh_token=new_plain,
            access_token_expires_at=access_expires,
            refresh_token_expires_at=new_refresh_expires,
        )

    # --- helpers --------------------------------------------------------

    async def _issue_session(
        self,
        user: User,
        *,
        ip_address: str | None,
        user_agent: str | None,
    ) -> AuthenticatedSession:
        family_id = uuid4()
        refresh_plain, refresh_hashed, refresh_expires = self._tokens.issue_refresh()
        # Session expiry tracks the longer-lived refresh token; access tokens
        # are JWT and stateless.
        session = await self._sessions.create_session(
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            access_token_expires_at=refresh_expires,  # session lives as long as the longest token
            refresh_token_hash=refresh_hashed,
            refresh_token_expires_at=refresh_expires,
            family_id=family_id,
        )
        access_token, access_expires = self._tokens.issue_access(user=user, session_id=session.id)
        await self._users.update_last_login(user.id, user.residency_region)
        return AuthenticatedSession(
            user=user,
            session=session,
            access_token=access_token,
            refresh_token=refresh_plain,
            access_token_expires_at=access_expires,
            refresh_token_expires_at=refresh_expires,
        )
