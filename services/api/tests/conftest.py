"""Shared pytest fixtures.

Three fixture tiers:

1. **unit** — pure-Python, no DB, no network. Default.
2. **integration** — real Postgres (the ``silklens_test`` database created by
   ``infra/docker/postgres/init.sql``), Redis, MinIO. Tests opt in by depending
   on the ``db_session`` fixture or marking ``@pytest.mark.integration``.
3. **e2e** — full ASGI app round-trip with httpx AsyncClient.

Integration tests assume the dev Docker stack is up (``make dev``). The
``_apply_migrations`` session fixture ensures the test DB schema is up to date
once per pytest run; it's autouse so individual tests don't need to remember.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from alembic import command

# Force test environment before settings cache materializes.
os.environ.setdefault("SILKLENS_ENV", "test")
os.environ.setdefault(
    "SILKLENS_DATABASE_URL",
    "postgresql+psycopg://silklens:silklens_dev@localhost:5434/silklens_test",
)
# Tests fire dozens of /v1/auth/register hits per file; the production-grade
# 200/min limit would 429 the suite. Tests that specifically assert rate-limit
# behaviour set this back to "true" inside their own fixture scope.
os.environ.setdefault("SILKLENS_RATE_LIMIT_ENABLED", "false")
# Force StubEmailClient for ALL providers — no live email sends during tests.
# Plain assignment overrides values already loaded from .env.
os.environ["SILKLENS_RESEND_API_KEY"] = ""
os.environ["SILKLENS_BREVO_API_KEY"] = ""
os.environ["SILKLENS_BREVO_SMTP_LOGIN"] = ""
os.environ["SILKLENS_BREVO_SMTP_PASSWORD"] = ""

from src.api.app import create_app
from src.core.database import dispose_engine
from src.core.settings import get_settings


@pytest.fixture(scope="session")
def settings():
    get_settings.cache_clear()  # type: ignore[attr-defined]
    return get_settings()


@pytest.fixture(scope="session", autouse=True)
def _apply_migrations(settings):
    """Bring the test DB schema up to head once per session.

    Skips quietly if Docker isn't reachable so unit-only test runs still work.
    """
    try:
        cfg = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
        cfg.set_main_option(
            "script_location", str(Path(__file__).resolve().parent.parent / "alembic")
        )
        cfg.set_main_option("sqlalchemy.url", settings.database_url_sync)
        command.upgrade(cfg, "heads")
    except Exception as exc:
        pytest.skip(f"Migrations could not be applied (is the dev DB running?): {exc}")


@pytest_asyncio.fixture
async def app():
    instance = create_app()
    yield instance
    await dispose_engine()


@pytest_asyncio.fixture
async def http(app) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest_asyncio.fixture
async def db_session(settings) -> AsyncIterator[AsyncSession]:
    """Integration-grade session against the silklens_test DB.

    Tests using this fixture should be marked ``@pytest.mark.integration``
    so they're skipped when Docker isn't available.
    """
    engine = create_async_engine(settings.database_url_async, pool_pre_ping=True)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()
