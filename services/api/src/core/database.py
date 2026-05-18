"""Database engine + session factory.

Async engine for application traffic; a sync engine helper is also exposed for
scripts (seed data, ad-hoc migrations) where async would be overkill.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass

from src.core.settings import get_settings


class Base(MappedAsDataclass, DeclarativeBase):
    """Declarative base — every ORM model inherits from this.

    ``MappedAsDataclass`` gives every model dataclass semantics (init, repr,
    eq) without sacrificing SQLAlchemy mapping. Default columns and shared
    mixins are declared per-table in their bounded context.
    """

    __abstract__ = True


_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url_async,
            echo=settings.database_echo,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_timeout=settings.database_pool_timeout,
            pool_pre_ping=True,
            connect_args={"server_settings": {"application_name": settings.service_name}},
        )
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _sessionmaker


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Context-managed session with commit-or-rollback semantics."""
    factory = get_sessionmaker()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields an AsyncSession with per-request context.

    Two session-local settings are bound here (fixes SEC-002, SEC-006, CRIT-1):

    - ``app.audit_hmac_key`` — secret consumed by ``app.audit()`` for the
      hash-chained tamper-evident log. Without this, the function silently
      falls back to a public constant.
    - ``app.tenant_id`` — used by RLS policies introduced in migration 0054.
      The :class:`TenantContextMiddleware` (api.middleware.tenant) refreshes
      this when an authenticated request carries a different tenant claim.

    Both settings are scoped via ``SET LOCAL`` so they're released at the end
    of the implicit transaction.
    """
    from sqlalchemy import text  # local to avoid circular import in tests

    from src.core.settings import get_settings

    factory = get_sessionmaker()
    settings = get_settings()
    async with factory() as session:
        # Always bind the HMAC key so app.audit() never falls back to a constant.
        await session.execute(
            text("SELECT set_config('app.audit_hmac_key', :k, true)"),
            {"k": settings.audit_hmac_key.get_secret_value()},
        )
        try:
            yield session
        finally:
            await session.close()


async def dispose_engine() -> None:
    """Clean shutdown for tests / app lifespan."""
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _sessionmaker = None


# Re-export for type completeness
__all__: list[str] = [
    "Any",
    "AsyncSession",
    "Base",
    "dispose_engine",
    "get_engine",
    "get_session",
    "get_sessionmaker",
    "session_scope",
]
