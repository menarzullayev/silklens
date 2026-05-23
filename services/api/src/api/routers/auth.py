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
from src.infrastructure.notifications import otp_service
from src.infrastructure.notifications.email_client import get_email_client
from src.infrastructure.security import Argon2PasswordHasher, JwtTokenIssuer
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
    return f"SilkLens kirish kodi: {code}\n\nKodni ilovaga kiriting. 10 daqiqada amal qiladi.\n"


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
    except Exception:  # noqa: S110
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
    access_token: str = Field(..., min_length=10, max_length=2048)


class FacebookLoginRequest(BaseModel):
    access_token: str = Field(
        ..., min_length=10, max_length=2048, description="Facebook user access token"
    )
    tenant_id: UUID | None = None
    residency_region: ResidencyRegion = ResidencyRegion.GLOBAL


class InstagramLoginRequest(BaseModel):
    access_token: str = Field(
        ...,
        min_length=10,
        max_length=2048,
        description="Instagram Basic Display API access token",
    )
    tenant_id: UUID | None = None
    residency_region: ResidencyRegion = ResidencyRegion.GLOBAL


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
            detail={
                "code": "PROVIDER_NOT_CONFIGURED",
                "message": f"OAuth provider '{slug}' not configured",
            },
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
    import httpx  # local import keeps domain layer free of httpx at definition time

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


@router.post(
    "/facebook",
    response_model=LoginResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("10/minute", per="ip", scope="auth:facebook"))],
)
async def facebook_sign_in(
    payload: FacebookLoginRequest,
    request: Request,
    db: SessionDep,
) -> LoginResponse:
    """Sign in or register via Facebook access token.

    1. Verifies the token using Facebook's debug_token endpoint with our app
       token — prevents token-substitution attacks where a token issued to
       another app is replayed here.
    2. Confirms the token belongs to OUR app_id.
    3. Fetches minimal profile (id, email, name, picture) via Graph API.
    4. Delegates to AuthService.login_with_oauth (same path as Google).
    Note: email may be absent if the user hasn't granted the email permission —
    a synthetic placeholder is used so the domain entity constraint is satisfied.
    """
    import httpx  # local import keeps domain layer free of httpx at definition time

    settings = get_settings()

    app_id = settings.facebook_app_id
    app_secret = settings.facebook_app_secret.get_secret_value()
    if not app_id or not app_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "PROVIDER_NOT_CONFIGURED", "message": "Facebook OAuth not configured"},
        )

    async with httpx.AsyncClient(timeout=15.0) as client:
        # Step 1: verify token authenticity — prevents token substitution attacks
        app_token = f"{app_id}|{app_secret}"
        debug_resp = await client.get(
            "https://graph.facebook.com/debug_token",
            params={"input_token": payload.access_token, "access_token": app_token},
        )

    if debug_resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "FACEBOOK_TOKEN_INVALID",
                "message": "Facebook token tekshirib bo'lmadi",
            },
        )

    debug_data = debug_resp.json().get("data", {})
    if not debug_data.get("is_valid"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "FACEBOOK_TOKEN_INVALID", "message": "Facebook token yaroqsiz"},
        )

    # Security: confirm the token belongs to OUR app (not another Facebook app)
    if str(debug_data.get("app_id")) != str(app_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "FACEBOOK_TOKEN_WRONG_APP", "message": "Token boshqa ilovaga tegishli"},
        )

    # Step 2: fetch user profile — use a separate client call to avoid holding
    # the connection open while we do app-token verification above
    async with httpx.AsyncClient(timeout=15.0) as client:
        me_resp = await client.get(
            "https://graph.facebook.com/me",
            params={
                "fields": "id,email,name,picture.width(200)",
                "access_token": payload.access_token,
            },
        )

    if me_resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "FACEBOOK_PROFILE_FETCH_FAILED",
                "message": "Facebook profilni olishda xato",
            },
        )

    fb_data = me_resp.json()
    provider_user_id: str = fb_data.get("id", "")
    if not provider_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "FACEBOOK_NO_ID", "message": "Facebook foydalanuvchi ID topilmadi"},
        )

    raw_email: str | None = fb_data.get("email")
    # Synthetic placeholder for accounts where email scope was not granted.
    # The provider_subject (stable FB user ID) uniquely identifies the account;
    # the placeholder keeps OAuthProfile's non-optional email constraint happy
    # while ensuring no collision with real addresses.
    email: str = raw_email if raw_email else f"fb_{provider_user_id}@oauth.silklens.internal"
    email_verified: bool = raw_email is not None  # only verified if Facebook returned a real email

    display_name: str = fb_data.get("name") or "Facebook User"
    avatar_url: str | None = fb_data.get("picture", {}).get("data", {}).get("url")

    profile = OAuthProfile(
        provider_subject=provider_user_id,
        email=email,
        email_verified=email_verified,
        display_name=display_name,
        avatar_url=avatar_url,
        raw=fb_data,
    )

    service = _service(db)
    provider_id = await _get_provider_id(db, "facebook")

    try:
        auth = await service.login_with_oauth(
            provider_id=provider_id,
            profile=profile,
            tenant_id=payload.tenant_id or UUID(settings.default_tenant_id),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            preferred_locale="uz",
            preferred_timezone="UTC",
            residency_region=payload.residency_region,
        )
    except IdentityError as exc:
        _raise_identity_error(exc)

    return LoginResponse(
        user=_user_out(auth.user),
        tokens=_token_bundle(auth, ttl=settings.jwt_access_token_ttl_seconds),
    )


@router.post(
    "/instagram",
    response_model=LoginResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("10/minute", per="ip", scope="auth:instagram"))],
)
async def instagram_sign_in(
    payload: InstagramLoginRequest,
    request: Request,
    db: SessionDep,
) -> LoginResponse:
    """Sign in or register via Instagram Basic Display API access token.

    Instagram Basic Display API returns only id and username — no email scope.
    A synthetic internal email placeholder is used so the domain's OAuthProfile
    constraint is satisfied while keeping the account anchored on the stable
    Instagram user ID (provider_subject). The account can be linked to a real
    email later via the email-verification flow.
    """
    import httpx  # local import keeps domain layer free of httpx at definition time

    settings = get_settings()

    ig_app_id = settings.instagram_app_id
    ig_app_secret = settings.instagram_app_secret.get_secret_value()
    if not ig_app_id or not ig_app_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "PROVIDER_NOT_CONFIGURED", "message": "Instagram OAuth sozlanmagan"},
        )

    async with httpx.AsyncClient(timeout=15.0) as client:
        me_resp = await client.get(
            "https://graph.instagram.com/me",
            params={
                "fields": "id,username",
                "access_token": payload.access_token,
            },
        )

    if me_resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INSTAGRAM_TOKEN_INVALID", "message": "Instagram token yaroqsiz"},
        )

    ig_data = me_resp.json()
    provider_user_id: str = ig_data.get("id", "")
    if not provider_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INSTAGRAM_NO_ID", "message": "Instagram foydalanuvchi ID topilmadi"},
        )

    username: str = ig_data.get("username", "instagram_user")

    # Instagram Basic Display API does not expose email. Use a synthetic
    # internal placeholder anchored on the stable provider_subject.
    # email_verified=False ensures the account still needs email verification
    # unless the user links a real address later.
    synthetic_email = f"ig_{provider_user_id}@oauth.silklens.internal"

    profile = OAuthProfile(
        provider_subject=provider_user_id,
        email=synthetic_email,
        email_verified=False,  # Instagram never returns email — always unverified
        display_name=f"@{username}",
        avatar_url=None,  # Basic Display API does not expose avatar
        raw=ig_data,
    )

    service = _service(db)
    provider_id = await _get_provider_id(db, "instagram")

    try:
        auth = await service.login_with_oauth(
            provider_id=provider_id,
            profile=profile,
            tenant_id=payload.tenant_id or UUID(settings.default_tenant_id),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            preferred_locale="uz",
            preferred_timezone="UTC",
            residency_region=payload.residency_region,
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
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "EMAIL_SEND_FAILED", "message": "Email yuborishda xato"},
        ) from None
    return ResendVerificationResponse(sent=True)


# --- Password reset endpoints (SILK-0122) ------------------------------------


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    sent: bool


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")
    new_password: str = Field(..., min_length=12, max_length=200)


class ResetPasswordResponse(BaseModel):
    reset: bool


_RESET_KEY_PREFIX = "otp:password_reset:"


def _reset_otp_text(code: str) -> str:
    return (
        f"SilkLens parolni tiklash kodi: {code}\n\n"
        "Kodni ilovaga kiriting. 10 daqiqada amal qiladi.\n"
    )


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    dependencies=[Depends(rate_limit("3/minute", per="ip", scope="auth:forgot"))],
)
async def forgot_password(
    body: ForgotPasswordRequest,
    db: SessionDep,
) -> ForgotPasswordResponse:
    """Send password reset OTP.

    Always returns 200 to prevent email enumeration — the response is identical
    whether or not the email exists in the database.
    """
    from sqlalchemy import text as _text

    row = await db.execute(
        _text(
            "SELECT id FROM user_emails WHERE LOWER(email) = LOWER(:email) AND is_primary = true"
        ),
        {"email": body.email},
    )
    user_row = row.fetchone()

    if user_row is not None:
        settings = get_settings()
        code = f"{__import__('secrets').randbelow(1_000_000):06d}"
        import redis.asyncio as aioredis

        async with aioredis.from_url(settings.redis_url, decode_responses=True) as r:
            await r.setex(
                f"{_RESET_KEY_PREFIX}{body.email.lower().strip()}",
                settings.email_otp_ttl_seconds,
                code,
            )
        import contextlib

        with contextlib.suppress(Exception):
            await get_email_client().send_email(
                to=body.email,
                subject=f"SilkLens parolni tiklash kodi: {code}",
                html=None,
                text=_reset_otp_text(code),
            )

    return ForgotPasswordResponse(sent=True)


@router.post(
    "/reset-password",
    response_model=ResetPasswordResponse,
    dependencies=[Depends(rate_limit("5/minute", per="ip", scope="auth:reset"))],
)
async def reset_password(
    body: ResetPasswordRequest,
    db: SessionDep,
) -> ResetPasswordResponse:
    """Verify the password-reset OTP and set a new password."""
    import redis.asyncio as aioredis
    from sqlalchemy import text as _text

    settings = get_settings()
    redis_key = f"{_RESET_KEY_PREFIX}{body.email.lower().strip()}"

    async with aioredis.from_url(settings.redis_url, decode_responses=True) as r:
        stored = await r.get(redis_key)
        if stored is None or stored != body.code:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "identity.invalid_otp",
                    "message": "Kod noto'g'ri yoki muddati o'tgan",
                },
            )
        await r.delete(redis_key)

    hasher = Argon2PasswordHasher()
    password_hash = hasher.hash(body.new_password)

    result = await db.execute(
        _text("""
            UPDATE users
            SET password_hash = :hash, updated_at = now()
            WHERE id = (
                SELECT user_id FROM user_emails
                WHERE LOWER(email) = LOWER(:email) AND is_primary = true
            )
            RETURNING id
        """),
        {"hash": password_hash, "email": body.email},
    )
    if not result.fetchone():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "identity.user_not_found",
                "message": "Foydalanuvchi topilmadi",
            },
        )
    await db.commit()

    return ResetPasswordResponse(reset=True)
