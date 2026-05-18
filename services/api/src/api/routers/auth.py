"""Auth endpoints: register, login, refresh.

OAuth start/callback and phone-OTP land in a follow-up migration once
provider secrets are wired (per [[reference-ai-providers]]).
"""

from __future__ import annotations

from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.settings import get_settings
from src.domain.identity.entities import (
    Credentials,
    RegistrationRequest,
    ResidencyRegion,
)
from src.domain.identity.errors import AccountLocked, IdentityError
from src.domain.identity.service import AuthService
from src.infrastructure.identity.repositories import (
    SqlLoginAttemptRepository,
    SqlSessionRepository,
    SqlUserRepository,
)
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
    return AuthService(
        users=SqlUserRepository(session),
        sessions=SqlSessionRepository(session),
        hasher=Argon2PasswordHasher(),
        tokens=JwtTokenIssuer(),
        login_attempts=SqlLoginAttemptRepository(session),
        lockout_max_failures=settings.login_lockout_max_failures,
        lockout_window_seconds=settings.login_lockout_window_seconds,
        lockout_duration_seconds=settings.login_lockout_duration_seconds,
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
        Credentials(email=str(payload.email), password=payload.password),
        tenant_id=user.tenant_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
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


class LogoutResponse(BaseModel):
    status: str = "ok"


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
