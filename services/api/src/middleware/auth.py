"""Auth middleware + FastAPI dependencies.

Two layers of identity extraction:

1. **Middleware** (``BearerContextMiddleware``) — runs once per request, parses
   the ``Authorization: Bearer ...`` header, validates the JWT, and binds
   ``(user_id, residency, tenant_id, session_id, trust_tier)`` to
   ``request.state.auth``. Requests without a bearer get ``None`` here — the
   middleware never rejects, so public endpoints stay reachable.

2. **Dependencies** — ``require_user`` rejects unauthenticated requests;
   ``current_user`` returns ``AuthContext | None``; ``require_permission``
   factory rejects callers without a server-side permission grant.

Audit and RBAC checks happen in the dependency layer because they need a DB
session, while the JWT decode in the middleware is stateless.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.core.database import get_session
from src.core.logging import get_logger
from src.domain.identity.entities import ResidencyRegion, TrustTier
from src.infrastructure.security import JwtTokenIssuer

log = get_logger("silklens.auth")


@dataclass(slots=True, frozen=True)
class AuthContext:
    """The subset of identity claims the rest of the request needs."""

    user_id: UUID
    session_id: UUID
    tenant_id: UUID
    residency_region: ResidencyRegion
    trust_tier: TrustTier


class BearerContextMiddleware(BaseHTTPMiddleware):
    """Decode ``Authorization: Bearer ...`` into ``request.state.auth``."""

    def __init__(self, app: ASGIApp, *, issuer: JwtTokenIssuer | None = None) -> None:
        super().__init__(app)
        self._issuer = issuer or JwtTokenIssuer()

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        header = request.headers.get("authorization") or request.headers.get("Authorization")
        request.state.auth = None
        if header and header.lower().startswith("bearer "):
            token = header.split(" ", 1)[1].strip()
            try:
                claims = self._issuer.decode_access(token)
                request.state.auth = AuthContext(
                    user_id=UUID(str(claims["sub"])),
                    session_id=UUID(str(claims["sid"])),
                    tenant_id=UUID(str(claims["tenant"])),
                    residency_region=ResidencyRegion(str(claims["residency"])),
                    trust_tier=TrustTier(str(claims.get("trust_tier", "new"))),
                )
            except jwt.ExpiredSignatureError:
                log.debug("auth.token_expired")
                request.state.auth_error = ("token_expired", "access token has expired")
            except (jwt.PyJWTError, KeyError, ValueError) as exc:
                log.debug("auth.token_invalid", error=str(exc))
                request.state.auth_error = ("token_invalid", "access token is invalid")
        return await call_next(request)


# --- FastAPI dependencies --------------------------------------------------


def current_user(request: Request) -> AuthContext | None:
    """Return the AuthContext bound by middleware, or None for anonymous."""
    return getattr(request.state, "auth", None)


def require_user(request: Request) -> AuthContext:
    """Reject if no bearer was sent or it was invalid."""
    ctx = getattr(request.state, "auth", None)
    if ctx is None:
        err = getattr(request.state, "auth_error", None)
        if err is not None:
            code, message = err
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": f"identity.{code}", "message": message},
                headers={"WWW-Authenticate": "Bearer"},
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "identity.unauthenticated", "message": "missing bearer token"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    return ctx


CurrentUserDep = Annotated[AuthContext, Depends(require_user)]
OptionalUserDep = Annotated[AuthContext | None, Depends(current_user)]


def require_permission(permission_slug: str):
    """Factory: returns a dependency that 403s if the user lacks the permission."""

    async def _checker(
        ctx: CurrentUserDep,
        db: Annotated[AsyncSession, Depends(get_session)],
    ) -> AuthContext:
        granted = (
            await db.execute(
                text(
                    """
                    SELECT app.has_permission(:uid, :residency, :perm, :tenant)
                    """
                ),
                {
                    "uid": ctx.user_id,
                    "residency": ctx.residency_region.value,
                    "perm": permission_slug,
                    "tenant": ctx.tenant_id,
                },
            )
        ).scalar_one()
        if not granted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "identity.permission_denied",
                    "message": f"missing permission '{permission_slug}'",
                    "permission": permission_slug,
                },
            )
        return ctx

    return _checker
