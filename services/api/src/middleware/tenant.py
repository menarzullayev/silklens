"""Tenant-context dependency.

Migration 0054 enabled Row-Level Security on every ``tenant_id``-bearing
table. The RLS policy reads ``current_setting('app.tenant_id')`` — but until
something actually sets that variable per request, the policy either hides
all rows (if the DB role does NOT have ``BYPASSRLS``) or is decorative (if
it does). Fixes CRIT-1 / SEC-006.

This dependency wraps the standard ``get_session`` dependency and additionally
binds the tenant_id from the bearer AuthContext.

Usage in routers:

    @router.get("/foo")
    async def foo(
        ctx: CurrentUserDep,
        db: TenantSessionDep,  # ← use this instead of SessionDep on tenant-scoped routes
    ):
        ...
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.settings import get_settings
from src.middleware.auth import AuthContext, current_user


async def get_tenant_session(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AsyncIterator[AsyncSession]:
    """Bind ``app.tenant_id`` for the lifetime of the session.

    If the request is anonymous, falls back to the default tenant so public
    endpoints can still query through the policy.
    """
    settings = get_settings()
    ctx: AuthContext | None = current_user(request)
    tenant_id = str(ctx.tenant_id) if ctx else settings.default_tenant_id
    await session.execute(
        text("SELECT set_config('app.tenant_id', :tid, true)"),
        {"tid": tenant_id},
    )
    yield session


TenantSessionDep = Annotated[AsyncSession, Depends(get_tenant_session)]
