"""Migration-level integration tests.

Exercises the live Postgres dev DB (port 5434). These tests are marked
``integration`` and skip cleanly when Docker isn't reachable.
"""

from __future__ import annotations

import re
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.integration


UUID_V7_VERSION_NIBBLE = "7"


async def _scalar(session: AsyncSession, sql: str) -> object:
    result = await session.execute(text(sql))
    return result.scalar()


@pytest.mark.asyncio
async def test_alembic_version_is_set(db_session: AsyncSession) -> None:
    version = await _scalar(db_session, "SELECT version_num FROM alembic_version")
    assert version is not None
    assert re.match(r"^[0-9a-z_]+$", str(version))


@pytest.mark.asyncio
async def test_required_extensions_installed(db_session: AsyncSession) -> None:
    required = {"pgcrypto", "pg_trgm", "unaccent", "citext", "ltree", "btree_gist", "vector"}
    result = await db_session.execute(
        text("SELECT extname FROM pg_extension WHERE extname = ANY(:names)").bindparams(
            names=list(required)
        )
    )
    installed = {row[0] for row in result.all()}
    missing = required - installed
    assert not missing, f"Missing PG extensions: {missing}"


@pytest.mark.asyncio
async def test_gen_uuid_v7_returns_version_7(db_session: AsyncSession) -> None:
    raw = await _scalar(db_session, "SELECT gen_uuid_v7()")
    assert raw is not None
    parsed = uuid.UUID(str(raw))
    assert parsed.version == 7, f"Expected UUIDv7, got version {parsed.version}: {parsed}"


@pytest.mark.asyncio
async def test_gen_uuid_v7_is_time_ordered(db_session: AsyncSession) -> None:
    """Successive UUIDs must be monotonically increasing (within the same ms,
    bytes 7-10 may not be — but the first 6 bytes are the timestamp prefix)."""
    first = uuid.UUID(str(await _scalar(db_session, "SELECT gen_uuid_v7()")))
    # Sleep a millisecond inside Postgres so the timestamp prefix advances.
    second = uuid.UUID(str(await _scalar(db_session, "SELECT gen_uuid_v7() FROM pg_sleep(0.002)")))
    # Compare the first 48 bits (timestamp prefix)
    assert second.int >> 80 >= first.int >> 80


@pytest.mark.asyncio
async def test_app_and_audit_schemas_exist(db_session: AsyncSession) -> None:
    schemas = await db_session.execute(
        text("SELECT nspname FROM pg_namespace WHERE nspname IN ('app','audit') ORDER BY nspname")
    )
    names = [row[0] for row in schemas.all()]
    assert names == ["app", "audit"]
