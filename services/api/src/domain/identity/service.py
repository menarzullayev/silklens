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
    OAuthProfile,
    RegistrationRequest,
    ResidencyRegion,
    TrustTier,
    User,
    UserStatus,
)
from src.domain.identity.errors import (
    AccountInactive,
    AccountLocked,
    EmailAlreadyRegistered,
    InvalidCredentials,
    RefreshTokenReused,
    WeakPassword,
)
from src.domain.identity.repositories import (
    LoginAttemptRepository,
    SessionRepository,
    UserRepository,
)


class PasswordHasher(Protocol):
    """Domain-side protocol; concrete argon2id impl in infrastructure."""

    def hash(self, password: str) -> str: ...
    def verify(self, hashed: str, password: str) -> bool: ...
    @property
    def algorithm(self) -> str: ...


class TokenIssuer(Protocol):
    """JWT issuer + opaque-refresh hashing — implementation in infrastructure."""

    def issue_access(
        self,
        *,
        user: User,
        session_id: UUID,
        mfa: bool = False,
    ) -> tuple[str, datetime]: ...
    def issue_refresh(self) -> tuple[str, bytes, datetime]:
        """Return (plaintext, hashed, expires_at). Plaintext returned ONCE to caller."""

    def hash_refresh(self, plaintext: str) -> bytes:
        """Used during refresh: hash incoming token to compare with stored hash."""


class MfaGate(Protocol):
    """Optional hook called by ``AuthService.login`` after password verification.

    If the user has any active MFA method, the gate creates a challenge and
    raises :class:`MfaRequired`. The API layer maps this to a 401 carrying
    ``challenge_id`` so the client can complete MFA via /v1/auth/mfa/verify.
    """

    async def require_if_enrolled(self, *, user: User) -> None: ...


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
        login_attempts: LoginAttemptRepository | None = None,
        lockout_max_failures: int = 5,
        lockout_window_seconds: int = 600,
        lockout_duration_seconds: int = 900,
        mfa_gate: MfaGate | None = None,
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._hasher = hasher
        self._tokens = tokens
        self._clock = clock or SystemClock()
        self._login_attempts = login_attempts
        self._lockout_max_failures = lockout_max_failures
        self._lockout_window_seconds = lockout_window_seconds
        self._lockout_duration_seconds = lockout_duration_seconds
        self._mfa_gate = mfa_gate

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
        # Business metric: count *successful* signups only — failed validation
        # / duplicate email never reaches this point so the counter mirrors
        # the user.registered.v1 emission downstream.
        try:
            from src.core.metrics import business_signups_total

            business_signups_total.inc()
        except Exception:  # noqa: S110  # nosec B110
            # Observability is best-effort — never break a real signup.
            pass
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

        normalized_email = credentials.email.strip().lower()

        # Brute-force gate (Agent 2 §4 / SEC-005). Check first so a locked
        # account never burns Argon2 CPU on subsequent attempts.
        await self._enforce_lockout(identifier=normalized_email, ip_address=ip_address)

        async def _fail(reason: str) -> None:
            await self._record_attempt(
                identifier=normalized_email,
                succeeded=False,
                ip_address=ip_address,
                user_agent=user_agent,
                failure_reason=reason,
            )
            # Re-check immediately: this failure may have crossed the
            # threshold. We promote to 423 so the next call from the same
            # ``(identifier, ip)`` short-circuits before Argon2 work.
            await self._enforce_lockout(identifier=normalized_email, ip_address=ip_address)

        found = await self._users.find_by_email(normalized_email, tenant_id=tenant_id)
        if found is None:
            await _fail("unknown_email")
            raise InvalidCredentials("email or password is incorrect")
        user, _email_row = found

        if not user.is_active:
            await _fail("account_inactive")
            raise AccountInactive(user.status.value)

        password_record = await self._users.get_password_hash(user.id, user.residency_region)
        if password_record is None:
            await _fail("no_password_set")
            raise InvalidCredentials("no password set for this account")
        password_hash, _algorithm = password_record
        if not self._hasher.verify(password_hash, credentials.password):
            await _fail("invalid_password")
            raise InvalidCredentials("email or password is incorrect")

        await self._record_attempt(
            identifier=normalized_email,
            succeeded=True,
            ip_address=ip_address,
            user_agent=user_agent,
            failure_reason=None,
        )
        # MFA gate: if the user has any active MFA factor, the gate raises
        # ``MfaRequired`` carrying a challenge_id. The API layer maps that to
        # a 401 so the client can complete MFA via /v1/auth/mfa/verify and
        # then exchange the verification for elevated tokens.
        if self._mfa_gate is not None:
            await self._mfa_gate.require_if_enrolled(user=user)
        return await self._issue_session(user, ip_address=ip_address, user_agent=user_agent)

    # --- oauth login ----------------------------------------------------

    async def login_with_oauth(
        self,
        *,
        provider_id: UUID,
        profile: OAuthProfile,
        tenant_id: UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
        preferred_locale: str = "en",
        preferred_timezone: str = "UTC",
        residency_region: ResidencyRegion = ResidencyRegion.GLOBAL,
    ) -> AuthenticatedSession:
        """Sign in or register a user via an OAuth provider.

        Lookup order:
          1. user_identities (provider_id + subject) — returning user
          2. user_emails (email) — existing account, first OAuth link
          3. create new account with identity linked

        No password is set; the provider's email_verified flag drives
        immediate email verification.
        """
        # 1. Known OAuth identity?
        found = await self._users.find_by_oauth_identity(
            provider_id=provider_id, subject=profile.provider_subject
        )

        # 2. Known email from a different sign-in method?
        if found is None:
            found = await self._users.find_by_email(profile.email, tenant_id=tenant_id)

        if found is not None:
            user, _ = found
            if not user.is_active:
                raise AccountInactive(user.status.value)
            await self._users.upsert_oauth_identity(
                user=user, provider_id=provider_id, profile=profile
            )
            return await self._issue_session(user, ip_address=ip_address, user_agent=user_agent)

        # 3. New user — create without password, identity linked in same txn.
        now = self._clock.now()
        user = User(
            id=uuid4(),
            tenant_id=tenant_id,
            residency_region=residency_region,
            pub_id=_generate_pub_id(),
            status=UserStatus.ACTIVE,
            is_guest=False,
            trust_tier=TrustTier.NEW,
            trust_score=0,
            preferred_locale=preferred_locale,
            preferred_timezone=preferred_timezone,
            created_at=now,
            updated_at=now,
            email_verified_at=now if profile.email_verified else None,
        )
        user, _ = await self._users.create_oauth_user(
            user=user,
            email=profile.email,
            email_verified=profile.email_verified,
            provider_id=provider_id,
            profile=profile,
        )
        try:
            from src.core.metrics import business_signups_total

            business_signups_total.inc()
        except Exception:  # noqa: S110  # nosec B110
            pass
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

    # --- brute-force defence --------------------------------------------

    async def _record_attempt(
        self,
        *,
        identifier: str,
        succeeded: bool,
        ip_address: str | None,
        user_agent: str | None,
        failure_reason: str | None,
    ) -> None:
        if self._login_attempts is None:
            return
        await self._login_attempts.record_attempt(
            identifier=identifier,
            succeeded=succeeded,
            ip_address=ip_address,
            user_agent=user_agent,
            failure_reason=failure_reason,
        )

    async def _enforce_lockout(self, *, identifier: str, ip_address: str | None) -> None:
        """Raise :class:`AccountLocked` when the identifier has accumulated
        ``lockout_max_failures`` failures inside ``lockout_window_seconds``.

        Per Agent 2 §4 the canonical key is the identifier (normalized email
        or phone). ``ip_address`` is recorded for forensics but does NOT
        narrow the lockout query — that would let an IP-rotating attacker
        keep guessing forever. The lockout lasts
        ``lockout_duration_seconds`` (surfaced via ``Retry-After`` at the
        API layer).
        """
        del ip_address  # logged on the row; not used for the threshold check
        if self._login_attempts is None:
            return
        failures = await self._login_attempts.count_recent_failures(
            identifier=identifier,
            ip_address=None,
            within_seconds=self._lockout_window_seconds,
        )
        if failures >= self._lockout_max_failures:
            raise AccountLocked(self._lockout_duration_seconds)
