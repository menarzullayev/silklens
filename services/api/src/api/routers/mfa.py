"""MFA endpoints — TOTP / WebAuthn / backup codes + login step-up.

All routes are auth-required (the dependency ``CurrentUserDep`` runs the
bearer middleware decode + rejects anonymous). High-stakes routes layer the
``require_recent_mfa`` step-up dependency on top.
"""

from __future__ import annotations

from typing import Annotated, Any, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.settings import get_settings
from src.domain.identity.entities import ResidencyRegion
from src.domain.mfa.entities import MfaMethodKind, MfaUserContext
from src.domain.mfa.errors import MfaError, MfaRequired
from src.domain.mfa.service import MfaService
from src.infrastructure.identity.repositories import SqlUserRepository
from src.infrastructure.mfa.backup_codes import Argon2BackupCodeHasher
from src.infrastructure.mfa.repository import SqlMfaRepository
from src.infrastructure.mfa.totp import PyOtpTotpAdapter
from src.infrastructure.mfa.webauthn import WebAuthnAdapterImpl
from src.infrastructure.security import JwtTokenIssuer
from src.middleware.auth import (
    CurrentUserDep,
    require_recent_mfa,
)
from src.middleware.ratelimit import rate_limit

router = APIRouter(prefix="/v1", tags=["mfa"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


# --- Wiring ----------------------------------------------------------------


def _service(db: AsyncSession) -> MfaService:
    settings = get_settings()
    return MfaService(
        repo=SqlMfaRepository(db),
        totp=PyOtpTotpAdapter(),
        webauthn=WebAuthnAdapterImpl(
            rp_id=settings.webauthn_rp_id,
            rp_name=settings.webauthn_rp_name,
            origin=settings.webauthn_origin,
        ),
        backup_hasher=Argon2BackupCodeHasher(),
        challenge_ttl_seconds=settings.mfa_challenge_ttl_seconds,
        rp_id=settings.webauthn_rp_id,
        rp_name=settings.webauthn_rp_name,
    )


async def _user_ctx(ctx: CurrentUserDep, db: AsyncSession) -> MfaUserContext:
    users = SqlUserRepository(db)
    user = await users.get_by_id(ctx.user_id, ctx.residency_region)
    return MfaUserContext(
        user_id=ctx.user_id,
        residency_region=ctx.residency_region.value,
        tenant_id=ctx.tenant_id,
        pub_id=user.pub_id if user else None,
    )


def _raise(exc: MfaError) -> NoReturn:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": str(exc)},
    ) from exc


# --- Schemas ----------------------------------------------------------------


class EnrollTotpRequest(BaseModel):
    label: str = Field(min_length=1, max_length=64)


class EnrollTotpResponse(BaseModel):
    mfa_id: UUID
    secret_base32: str
    provisioning_uri: str
    digits: int = 6
    period: int = 30
    algorithm: str = "sha1"


class VerifyTotpEnrollmentRequest(BaseModel):
    mfa_id: UUID
    code: str = Field(min_length=4, max_length=10)


class MfaMethodOut(BaseModel):
    id: UUID
    method: str
    label: str
    status: str
    enrolled_at: str | None
    last_used_at: str | None


class MfaListResponse(BaseModel):
    methods: list[MfaMethodOut]


class WebAuthnBeginRequest(BaseModel):
    label: str = Field(min_length=1, max_length=64)


class WebAuthnBeginResponse(BaseModel):
    challenge_id: UUID
    options: dict[str, Any]


class WebAuthnFinishRequest(BaseModel):
    challenge_id: UUID
    attestation: dict[str, Any]


class WebAuthnFinishResponse(BaseModel):
    mfa_id: UUID
    method: str = "webauthn"


class BackupCodesResponse(BaseModel):
    codes: list[str]
    count: int


class ChallengeRequest(BaseModel):
    user_id: UUID
    method: str = Field(pattern="^(totp|webauthn|backup_codes)$")


class ChallengeResponse(BaseModel):
    challenge_id: UUID
    method: str
    expires_in: int


class VerifyRequest(BaseModel):
    challenge_id: UUID
    method: str = Field(pattern="^(totp|webauthn|backup_codes)$")
    code: str | None = None
    assertion: dict[str, Any] | None = None


class UserOut(BaseModel):
    """Minimal user projection returned when MFA completes a login gate."""

    id: UUID
    pub_id: str
    tenant_id: UUID
    residency_region: str
    trust_tier: str
    preferred_locale: str
    preferred_timezone: str
    is_verified: bool


class VerifyResponse(BaseModel):
    access_token: str
    # Populated when this verify call completes a login-gate dance
    # (challenge purpose == "step_up_or_login").  None for pure step-up.
    refresh_token: str | None = None
    token_type: str = "Bearer"
    expires_in: int | None = None
    mfa: bool = True
    # Full user object — present only for login-gate completions.
    user: UserOut | None = None


# --- Routes -----------------------------------------------------------------


@router.get("/me/mfa", response_model=MfaListResponse)
async def list_methods(ctx: CurrentUserDep, db: SessionDep) -> MfaListResponse:
    service = _service(db)
    user_ctx = await _user_ctx(ctx, db)
    methods = await service.list_methods(user_ctx)
    return MfaListResponse(
        methods=[
            MfaMethodOut(
                id=m.id,
                method=m.method.value,
                label=m.label,
                status=m.status.value,
                enrolled_at=m.enrolled_at.isoformat() if m.enrolled_at else None,
                last_used_at=m.last_used_at.isoformat() if m.last_used_at else None,
            )
            for m in methods
        ]
    )


@router.post(
    "/me/mfa/totp/enroll",
    response_model=EnrollTotpResponse,
    status_code=status.HTTP_201_CREATED,
)
async def enroll_totp(
    payload: EnrollTotpRequest,
    ctx: CurrentUserDep,
    db: SessionDep,
) -> EnrollTotpResponse:
    service = _service(db)
    user_ctx = await _user_ctx(ctx, db)
    try:
        enrollment = await service.enroll_totp(user_ctx, label=payload.label)
    except MfaError as exc:
        _raise(exc)
    return EnrollTotpResponse(
        mfa_id=enrollment.mfa_id,
        secret_base32=enrollment.secret_base32,
        provisioning_uri=enrollment.provisioning_uri,
    )


@router.post("/me/mfa/totp/verify-enrollment", response_model=MfaMethodOut)
async def verify_totp_enrollment(
    payload: VerifyTotpEnrollmentRequest,
    ctx: CurrentUserDep,
    db: SessionDep,
) -> MfaMethodOut:
    service = _service(db)
    user_ctx = await _user_ctx(ctx, db)
    try:
        method = await service.verify_totp_enrollment(
            user_ctx, mfa_id=payload.mfa_id, code=payload.code
        )
    except MfaError as exc:
        _raise(exc)
    return MfaMethodOut(
        id=method.id,
        method=method.method.value,
        label=method.label,
        status=method.status.value,
        enrolled_at=method.enrolled_at.isoformat() if method.enrolled_at else None,
        last_used_at=method.last_used_at.isoformat() if method.last_used_at else None,
    )


@router.post(
    "/me/mfa/webauthn/begin-registration",
    response_model=WebAuthnBeginResponse,
    status_code=status.HTTP_201_CREATED,
)
async def webauthn_begin(
    payload: WebAuthnBeginRequest,
    ctx: CurrentUserDep,
    db: SessionDep,
) -> WebAuthnBeginResponse:
    service = _service(db)
    user_ctx = await _user_ctx(ctx, db)
    try:
        challenge_id, options = await service.enroll_webauthn_begin(user_ctx, label=payload.label)
    except MfaError as exc:
        _raise(exc)
    return WebAuthnBeginResponse(challenge_id=challenge_id, options=options)


@router.post("/me/mfa/webauthn/finish-registration", response_model=WebAuthnFinishResponse)
async def webauthn_finish(
    payload: WebAuthnFinishRequest,
    ctx: CurrentUserDep,
    db: SessionDep,
) -> WebAuthnFinishResponse:
    service = _service(db)
    user_ctx = await _user_ctx(ctx, db)
    try:
        method = await service.enroll_webauthn_complete(
            user_ctx,
            challenge_id=payload.challenge_id,
            attestation=payload.attestation,
        )
    except MfaError as exc:
        _raise(exc)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "identity.mfa_invalid_code", "message": str(exc)},
        ) from exc
    return WebAuthnFinishResponse(mfa_id=method.id)


@router.post(
    "/me/mfa/backup-codes/generate",
    response_model=BackupCodesResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_recent_mfa(seconds=300, allow_first_setup=True))],
)
async def generate_backup_codes(
    ctx: CurrentUserDep,
    db: SessionDep,
) -> BackupCodesResponse:
    service = _service(db)
    user_ctx = await _user_ctx(ctx, db)
    codes = await service.generate_backup_codes(user_ctx)
    return BackupCodesResponse(codes=codes, count=len(codes))


@router.delete(
    "/me/mfa/{mfa_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_recent_mfa(seconds=300, allow_first_setup=False))],
)
async def disable_method(
    mfa_id: UUID,
    ctx: CurrentUserDep,
    db: SessionDep,
) -> None:
    service = _service(db)
    user_ctx = await _user_ctx(ctx, db)
    try:
        await service.disable_method(user_ctx, mfa_id=mfa_id)
    except MfaError as exc:
        _raise(exc)


# --- Auth-side step-up endpoints (anonymous-friendly post-password) --------


@router.post(
    "/auth/mfa/challenge",
    response_model=ChallengeResponse,
    status_code=status.HTTP_201_CREATED,
    # HIGH-1 fix: rate-limit per-IP to prevent TOTP brute-force enumeration.
    # 5 challenges/min per IP gives legitimate users plenty of headroom.
    dependencies=[Depends(rate_limit("5/minute", per="ip", scope="mfa:challenge"))],
)
async def initiate_challenge(
    payload: ChallengeRequest,
    db: SessionDep,
) -> ChallengeResponse:
    """Initiate an MFA challenge for the given user_id.

    Used post-password to start step-up. The /verify endpoint exchanges the
    challenge_id + code for elevated tokens.
    """
    # SEC-W5 / H-2: do NOT leak account existence via 404 here. Return a
    # synthetic challenge for unknown user_id (the /verify endpoint will then
    # 401 because no real challenge row will match the random ID).
    service = _service(db)
    users = SqlUserRepository(db)
    user = None
    for region in (
        ResidencyRegion.GLOBAL,
        ResidencyRegion.UZ,
        ResidencyRegion.EU,
        ResidencyRegion.US,
    ):
        user = await users.get_by_id(payload.user_id, region)
        if user is not None:
            break
    settings = get_settings()
    if user is None:
        # Return a plausible-looking response so timing + status don't reveal
        # whether the account exists. /verify will reject the synthetic id.
        from uuid import uuid4 as _uuid4

        method_str = payload.method
        try:
            MfaMethodKind(method_str)
        except ValueError:
            method_str = "totp"
        return ChallengeResponse(
            challenge_id=_uuid4(),
            method=method_str,
            expires_in=settings.mfa_challenge_ttl_seconds,
        )
    user_ctx = MfaUserContext(
        user_id=user.id,
        residency_region=user.residency_region.value,
        tenant_id=user.tenant_id,
        pub_id=user.pub_id,
    )
    method = MfaMethodKind(payload.method)
    challenge = await service.initiate_challenge(user_ctx, method=method)
    return ChallengeResponse(
        challenge_id=challenge.id,
        method=method.value,
        expires_in=settings.mfa_challenge_ttl_seconds,
    )


@router.post(
    "/auth/mfa/verify",
    response_model=VerifyResponse,
    # HIGH-1 fix: 5/min per IP, same as the challenge endpoint.
    dependencies=[Depends(rate_limit("5/minute", per="ip", scope="mfa:verify"))],
)
async def verify_challenge(
    payload: VerifyRequest,
    db: SessionDep,
) -> VerifyResponse:
    """Verify TOTP / WebAuthn / backup code → elevated access token with mfa=true.

    The verify endpoint takes the user_id from the challenge metadata; it does
    NOT trust a client-supplied user_id, so anonymous callers cannot escalate
    onto someone else's account. The minted access token carries ``mfa: true``.
    """
    service = _service(db)
    # Look up the challenge → user
    challenge = await SqlMfaRepository(db).get_challenge(payload.challenge_id)
    if challenge is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "identity.mfa_challenge_not_found",
                "message": "challenge not found",
            },
        )
    users = SqlUserRepository(db)
    user = await users.get_by_id(challenge.user_id, ResidencyRegion(challenge.residency_region))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "identity.user_not_found", "message": "user not found"},
        )
    user_ctx = MfaUserContext(
        user_id=user.id,
        residency_region=user.residency_region.value,
        tenant_id=user.tenant_id,
        pub_id=user.pub_id,
    )

    method = MfaMethodKind(payload.method)
    try:
        if method == MfaMethodKind.TOTP:
            if not payload.code:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail={
                        "code": "identity.mfa_invalid_code",
                        "message": "missing code",
                    },
                )
            await service.verify_totp(
                user_ctx, challenge_id=payload.challenge_id, code=payload.code
            )
        elif method == MfaMethodKind.WEBAUTHN:
            if not payload.assertion:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail={
                        "code": "identity.mfa_invalid_code",
                        "message": "missing assertion",
                    },
                )
            await service.verify_webauthn(
                user_ctx,
                challenge_id=payload.challenge_id,
                assertion=payload.assertion,
            )
        elif method == MfaMethodKind.BACKUP_CODES:
            if not payload.code:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail={
                        "code": "identity.mfa_invalid_code",
                        "message": "missing code",
                    },
                )
            await service.verify_backup_code(
                user_ctx, challenge_id=payload.challenge_id, code=payload.code
            )
    except MfaError as exc:
        _raise(exc)

    settings = get_settings()

    # Determine whether this challenge is completing a login gate or a pure step-up.
    # The login gate sets purpose="step_up_or_login" in MfaGateAdapter.require_if_enrolled
    # (via MfaService.initiate_challenge which always writes purpose="step_up_or_login").
    is_login_gate = challenge.metadata.get("purpose") == "step_up_or_login"

    if is_login_gate:
        # Issue a full real session (access + refresh) so the client can
        # maintain the session after completing the login → MFA gate dance.
        # The router is the composition root — wire infra components directly.
        from uuid import uuid4 as _uuid4

        from src.infrastructure.identity.repositories import SqlSessionRepository

        sessions = SqlSessionRepository(db)
        issuer = JwtTokenIssuer()
        family_id = _uuid4()
        refresh_plain, refresh_hashed, refresh_expires = issuer.issue_refresh()
        session = await sessions.create_session(
            user=user,
            ip_address=None,  # IP not available post-challenge; omit for MFA completion
            user_agent=None,
            access_token_expires_at=refresh_expires,
            refresh_token_hash=refresh_hashed,
            refresh_token_expires_at=refresh_expires,
            family_id=family_id,
        )
        access_token, _exp = issuer.issue_access(user=user, session_id=session.id, mfa=True)
        return VerifyResponse(
            access_token=access_token,
            refresh_token=refresh_plain,
            expires_in=settings.jwt_access_token_ttl_seconds,
            mfa=True,
            user=UserOut(
                id=user.id,
                pub_id=user.pub_id,
                tenant_id=user.tenant_id,
                residency_region=user.residency_region.value,
                trust_tier=user.trust_tier.value,
                preferred_locale=user.preferred_locale,
                preferred_timezone=user.preferred_timezone,
                is_verified=user.is_verified,
            ),
        )

    # Pure step-up path: mint a short-lived phantom access token only.
    # SEC-W56-003 fix:
    # (a) Use a fresh phantom UUID for session_id — never collides with real
    #     session rows so revocation keyed on sid can't target this token.
    # (b) Honour mfa_step_up_freshness_seconds (default 300s / 5 min) rather
    #     than the full jwt_access_token_ttl_seconds (900s / 15 min).
    from uuid import uuid4

    issuer = JwtTokenIssuer(access_ttl=settings.mfa_step_up_freshness_seconds)
    phantom_session_id = uuid4()
    token, _exp = issuer.issue_access(user=user, session_id=phantom_session_id, mfa=True)
    return VerifyResponse(access_token=token, mfa=True)


# --- Module-level MfaGate adapter -----------------------------------------


class MfaGateAdapter:
    """Implements :class:`src.domain.identity.service.MfaGate`.

    Wired into ``AuthService`` so the login flow can check ``user_has_active_mfa``
    and either issue tokens directly or raise ``MfaRequired`` with a fresh
    challenge_id.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def require_if_enrolled(self, *, user) -> None:  # type: ignore[no-untyped-def]
        service = _service(self._db)
        user_ctx = MfaUserContext(
            user_id=user.id,
            residency_region=user.residency_region.value,
            tenant_id=user.tenant_id,
            pub_id=user.pub_id,
        )
        if not await service.user_has_active_mfa(user_ctx):
            return
        methods = await service.list_methods(user_ctx)
        method_kinds = sorted({m.method.value for m in methods if m.is_active})
        # Default to TOTP if present, else first available.
        primary = (
            MfaMethodKind.TOTP
            if MfaMethodKind.TOTP.value in method_kinds
            else MfaMethodKind(method_kinds[0])
        )
        challenge = await service.initiate_challenge(user_ctx, method=primary)
        raise MfaRequired(str(challenge.id), available_methods=method_kinds)
