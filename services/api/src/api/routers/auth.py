"""Auth endpoints: register, login, refresh.

OAuth start/callback and phone-OTP land in a follow-up migration once
provider secrets are wired (per [[reference-ai-providers]]).
"""

from __future__ import annotations

import asyncio
from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.settings import get_settings
from src.domain.identity.entities import (
    Credentials,
    OAuthProfile,
    RegistrationRequest,
    ResidencyRegion,
)
from src.domain.identity.errors import AccountLocked, IdentityError
from src.domain.identity.service import AuthService
from src.domain.mfa.errors import MfaRequired
from src.infrastructure.identity.repositories import (
    SqlLoginAttemptRepository,
    SqlSessionRepository,
    SqlUserRepository,
)
from src.infrastructure.security import Argon2PasswordHasher, JwtTokenIssuer
from src.infrastructure.notifications import otp_service
from src.infrastructure.notifications.email_client import get_email_client
from src.middleware.auth import CurrentUserDep
from src.middleware.ratelimit import rate_limit

router = APIRouter(prefix="/v1/auth", tags=["auth"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


# --- DTOs --------------------------------------------------------------------


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=200)
    display_name: str | None = Field(default=None, min_length=2, max_length=64)
    preferred_locale: str = Field(default="en", min_length=2, max_length=12)
    preferred_timezone: str = Field(default="UTC", min_length=2, max_length=64)
    tenant_id: UUID | None = None
    residency_region: ResidencyRegion = ResidencyRegion.GLOBAL


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)
    tenant_id: UUID | None = None


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=8, max_length=512)


class UserOut(BaseModel):
    id: UUID
    pub_id: str
    tenant_id: UUID
    residency_region: ResidencyRegion
    trust_tier: str
    preferred_locale: str
    preferred_timezone: str
    is_verified: bool


class TokenBundle(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int  # seconds


class LoginResponse(BaseModel):
    user: UserOut
    tokens: TokenBundle


# --- Wiring ------------------------------------------------------------------


def _service(session: AsyncSession) -> AuthService:
    settings = get_settings()
    # Local import to keep AuthService' domain layer free of API dependencies
    # at definition time — the gate adapter sits in the API router file.
    from src.api.routers.mfa import MfaGateAdapter

    return AuthService(
        users=SqlUserRepository(session),
        sessions=SqlSessionRepository(session),
        hasher=Argon2PasswordHasher(),
        tokens=JwtTokenIssuer(),
        login_attempts=SqlLoginAttemptRepository(session),
        lockout_max_failures=settings.login_lockout_max_failures,
        lockout_window_seconds=settings.login_lockout_window_seconds,
        lockout_duration_seconds=settings.login_lockout_duration_seconds,
        mfa_gate=MfaGateAdapter(session),
    )


def _user_out(user: object) -> UserOut:  # use object to avoid circular ORM types
    return UserOut(
        id=user.id,
        pub_id=user.pub_id,
        tenant_id=user.tenant_id,
        residency_region=user.residency_region,
        trust_tier=user.trust_tier.value,
        preferred_locale=user.preferred_locale,
        preferred_timezone=user.preferred_timezone,
        is_verified=user.is_verified,
    )


def _token_bundle(auth: object, *, ttl: int) -> TokenBundle:
    return TokenBundle(
        access_token=auth.access_token,
        refresh_token=auth.refresh_token,
        expires_in=ttl,
    )


def _raise_identity_error(exc: IdentityError) -> NoReturn:
    """Translate domain errors → HTTPException; attach ``Retry-After`` on 423."""
    headers: dict[str, str] | None = None
    if isinstance(exc, AccountLocked):
        headers = {"Retry-After": str(exc.retry_after_seconds)}
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": str(exc)},
        headers=headers,
    ) from exc


# --- Email templates ---------------------------------------------------------

# Plain-text only on purpose: mail.ru (and a few other strict consumer ISPs)
# silently drop HTML emails from shared Resend senders, while accepting the
# same content in plain text. Once silklens.app is verified on Resend we can
# re-introduce branded HTML — until then text/plain is the deliverable form.


def _otp_text(code: str) -> str:
    return (
        f"SilkLens kirish kodi: {code}\n"
        f"\n"
        f"Kodni ilovaga kiriting. 10 daqiqada amal qiladi.\n"
    )


# --- Routes ------------------------------------------------------------------

# Per-route rate-limit dependencies. SEC-005: prevents credential-stuffing /
# enumeration and protects Argon2 CPU cost. Keys on IP because these
# endpoints are reachable without a bearer.


@router.post(
    "/register",
    response_model=LoginResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("3/minute", per="ip", scope="auth:register"))],
)
async def register(
    payload: RegisterRequest,
    request: Request,
    db: SessionDep,
) -> LoginResponse:
    settings = get_settings()
    service = _service(db)
    try:
        user = await service.register(
            RegistrationRequest(
                tenant_id=payload.tenant_id or UUID(settings.default_tenant_id),
                residency_region=payload.residency_region,
                email=str(payload.email),
                password=payload.password,
                display_name=payload.display_name,
                preferred_locale=payload.preferred_locale,
                preferred_timezone=payload.preferred_timezone,
            )
        )
    except IdentityError as exc:
        _raise_identity_error(exc)

    # Auto-login after registration so the client gets tokens immediately.
    auth = await service.login(
        Credentials(email=payload.email, password=payload.password),
        tenant_id=user.tenant_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    # Send email verification OTP — fire-and-forget; don't block the response.
    try:
        code = await otp_service.generate_and_store(payload.email)
        await get_email_client().send_email(
            to=payload.email,
            subject=f"SilkLens kirish kodi: {code}",
            html=None,
            text=_otp_text(code),
        )
    except Exception:  # noqa: BLE001
        # Email failure must never break login — OTP can be resent.
        pass

    return LoginResponse(
        user=_user_out(auth.user),
        tokens=_token_bundle(auth, ttl=settings.jwt_access_token_ttl_seconds),
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    dependencies=[Depends(rate_limit("5/minute", per="ip", scope="auth:login"))],
)
async def login(
    payload: LoginRequest,
    request: Request,
    db: SessionDep,
) -> LoginResponse:
    settings = get_settings()
    service = _service(db)
    try:
        auth = await service.login(
            Credentials(email=str(payload.email), password=payload.password),
            tenant_id=payload.tenant_id or UUID(settings.default_tenant_id),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except MfaRequired as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={
                "code": exc.code,
                "message": str(exc),
                "challenge_id": exc.challenge_id,
                "available_methods": exc.available_methods,
            },
        ) from exc
    except IdentityError as exc:
        _raise_identity_error(exc)

    return LoginResponse(
        user=_user_out(auth.user),
        tokens=_token_bundle(auth, ttl=settings.jwt_access_token_ttl_seconds),
    )


@router.post(
    "/refresh",
    response_model=LoginResponse,
    dependencies=[Depends(rate_limit("20/minute", per="ip", scope="auth:refresh"))],
)
async def refresh(payload: RefreshRequest, db: SessionDep) -> LoginResponse:
    settings = get_settings()
    service = _service(db)
    try:
        auth = await service.refresh(payload.refresh_token)
    except IdentityError as exc:
        _raise_identity_error(exc)

    return LoginResponse(
        user=_user_out(auth.user),
        tokens=_token_bundle(auth, ttl=settings.jwt_access_token_ttl_seconds),
    )


# --- Protected endpoints ----------------------------------------------------


class MeResponse(BaseModel):
    user: UserOut
    session_id: UUID
    trust_tier: str


@router.get("/me", response_model=MeResponse)
async def me(ctx: CurrentUserDep, db: SessionDep) -> MeResponse:
    """Return the currently authenticated user. Foundational protected endpoint."""
    repo = SqlUserRepository(db)
    user = await repo.get_by_id(ctx.user_id, ctx.residency_region)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "identity.user_not_found", "message": "user no longer exists"},
        )
    return MeResponse(
        user=_user_out(user),
        session_id=ctx.session_id,
        trust_tier=ctx.trust_tier.value,
    )


class GoogleTokenRequest(BaseModel):
    access_token: str


class LogoutResponse(BaseModel):
    status: str = "ok"


async def _get_provider_id(session: AsyncSession, slug: str) -> UUID:
    from sqlalchemy import text as _text

    result = await session.execute(
        _text("SELECT id FROM oauth_providers WHERE slug = :slug AND is_enabled = true"),
        {"slug": slug},
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "PROVIDER_NOT_CONFIGURED", "message": f"OAuth provider '{slug}' not configured"},
        )
    return row[0]


@router.post(
    "/google",
    response_model=LoginResponse,
    dependencies=[Depends(rate_limit("10/minute", per="ip", scope="auth:google"))],
)
async def google_sign_in(
    payload: GoogleTokenRequest,
    request: Request,
    db: SessionDep,
) -> LoginResponse:
    """Sign in or register via Google access token.

    Verifies the token with Google's tokeninfo endpoint, then:
      1. Looks up the user by OAuth identity (provider + subject).
      2. Falls back to email lookup and links the identity.
      3. Creates a new account (no password) if neither found.
    Email is marked verified, display_name and avatar_url are saved from Google.
    """
    import httpx  # noqa: PLC0415

    # Two calls with a single client:
    #   1. tokeninfo — validates the access_token and returns sub/email/email_verified
    #   2. userinfo  — returns full profile (name, picture, locale) that tokeninfo omits
    async with httpx.AsyncClient(timeout=10) as client:
        tokeninfo_r, userinfo_r = await asyncio.gather(
            client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"access_token": payload.access_token},
            ),
            client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {payload.access_token}"},
            ),
        )

    if tokeninfo_r.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "GOOGLE_TOKEN_INVALID", "message": "Google token noto'g'ri"},
        )

    tokeninfo = tokeninfo_r.json()
    userinfo = userinfo_r.json() if userinfo_r.status_code == 200 else {}

    # Merge: tokeninfo is authoritative for security fields; userinfo for profile.
    info = {**tokeninfo, **userinfo}

    email: str = info.get("email", "")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "GOOGLE_NO_EMAIL", "message": "Google email topilmadi"},
        )

    subject: str = info.get("sub", "")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "GOOGLE_NO_SUB", "message": "Google foydalanuvchi ID topilmadi"},
        )

    profile = OAuthProfile(
        provider_subject=subject,
        email=email,
        email_verified=info.get("email_verified") in ("true", True),
        display_name=info.get("name") or email.split("@")[0],
        avatar_url=info.get("picture"),
        raw=info,
    )

    settings = get_settings()
    service = _service(db)
    provider_id = await _get_provider_id(db, "google")

    try:
        auth = await service.login_with_oauth(
            provider_id=provider_id,
            profile=profile,
            tenant_id=UUID(settings.default_tenant_id),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            preferred_locale="uz",
            preferred_timezone="UTC",
            residency_region=ResidencyRegion.GLOBAL,
        )
    except IdentityError as exc:
        _raise_identity_error(exc)

    return LoginResponse(
        user=_user_out(auth.user),
        tokens=_token_bundle(auth, ttl=settings.jwt_access_token_ttl_seconds),
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(ctx: CurrentUserDep, db: SessionDep) -> LogoutResponse:
    """Revoke the current session (and its refresh-token family)."""
    sessions = SqlSessionRepository(db)
    await sessions.revoke_session(
        ctx.session_id,
        ctx.residency_region,
        reason="user_logout",
    )
    return LogoutResponse()


# --- Email verification endpoints --------------------------------------------


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class VerifyEmailResponse(BaseModel):
    verified: bool


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ResendVerificationResponse(BaseModel):
    sent: bool


@router.post(
    "/verify-email",
    response_model=VerifyEmailResponse,
    dependencies=[Depends(rate_limit("10/minute", per="ip", scope="auth:verify_email"))],
)
async def verify_email(
    payload: VerifyEmailRequest,
    ctx: CurrentUserDep,
    db: SessionDep,
) -> VerifyEmailResponse:
    """Verify the OTP code sent to the user's email after registration."""
    ok = await otp_service.verify_and_consume(payload.email, payload.code)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "OTP_INVALID", "message": "Kod noto'g'ri yoki muddati o'tgan"},
        )

    repo = SqlUserRepository(db)
    await repo.verify_email(ctx.user_id, ctx.residency_region)
    return VerifyEmailResponse(verified=True)


@router.post(
    "/resend-verification",
    response_model=ResendVerificationResponse,
    dependencies=[Depends(rate_limit("3/minute", per="ip", scope="auth:resend_verification"))],
)
async def resend_verification(
    payload: ResendVerificationRequest,
    _ctx: CurrentUserDep,
) -> ResendVerificationResponse:
    """Resend email verification OTP to the authenticated user."""
    try:
        code = await otp_service.generate_and_store(payload.email)
        await get_email_client().send_email(
            to=payload.email,
            subject=f"SilkLens kirish kodi: {code}",
            html=None,
            text=_otp_text(code),
        )
    except Exception:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "EMAIL_SEND_FAILED", "message": "Email yuborishda xato"},
        )
    return ResendVerificationResponse(sent=True)
