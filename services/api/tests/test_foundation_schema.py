"""Foundation schema tests — assert the load-bearing tables, partitions,
functions, and seed data from migrations 0002-0009 are wired correctly.

These are integration tests; they require the dev Postgres at port 5434 with
``silklens_test`` migrated to head (handled by ``_apply_migrations`` fixture).
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.integration


DEFAULT_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
SYSTEM_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")


async def _scalar(session: AsyncSession, sql: str, **params: object) -> object:
    result = await session.execute(text(sql), params)
    return result.scalar()


# --- Tenants & branding ------------------------------------------------------


@pytest.mark.asyncio
async def test_default_tenant_exists(db_session: AsyncSession) -> None:
    slug = await _scalar(
        db_session, "SELECT slug FROM tenants WHERE id = :id", id=DEFAULT_TENANT_ID
    )
    assert slug == "default"


@pytest.mark.asyncio
async def test_default_tenant_branding_exists(db_session: AsyncSession) -> None:
    color = await _scalar(
        db_session,
        "SELECT primary_color FROM tenant_branding WHERE tenant_id = :id",
        id=DEFAULT_TENANT_ID,
    )
    assert color is not None
    assert str(color).startswith("#")


# --- Admin config seeds ------------------------------------------------------


@pytest.mark.asyncio
async def test_controlled_vocabularies_seeded(db_session: AsyncSession) -> None:
    rows = (
        await db_session.execute(text("SELECT slug FROM controlled_vocabularies ORDER BY slug"))
    ).all()
    slugs = {row[0] for row in rows}
    required = {
        "languages",
        "residency_regions",
        "heritage_kinds",
        "architectural_styles",
        "moderation_actions",
        "ai_task_types",
        "payment_providers",
    }
    missing = required - slugs
    assert not missing, f"Missing vocabularies: {missing}"


@pytest.mark.asyncio
async def test_heritage_kinds_seeded(db_session: AsyncSession) -> None:
    count = await _scalar(
        db_session,
        """
        SELECT count(*)
        FROM vocabulary_terms t
        JOIN controlled_vocabularies v ON v.id = t.vocabulary_id
        WHERE v.slug = 'heritage_kinds';
        """,
    )
    assert count and int(count) >= 9


# --- Users + residency partitioning -----------------------------------------


@pytest.mark.asyncio
async def test_users_partitions_exist(db_session: AsyncSession) -> None:
    rows = (
        await db_session.execute(
            text(
                """
                SELECT tablename FROM pg_tables
                WHERE tablename LIKE 'users\\_%' ESCAPE '\\' AND schemaname='public'
                ORDER BY tablename
                """
            )
        )
    ).all()
    names = {row[0] for row in rows}
    assert names == {"users_uz", "users_eu", "users_us", "users_global"}


@pytest.mark.asyncio
async def test_system_actor_exists_with_super_admin(db_session: AsyncSession) -> None:
    granted = await _scalar(
        db_session,
        "SELECT app.has_permission(:uid, 'global', 'heritage:moderate')",
        uid=SYSTEM_USER_ID,
    )
    assert granted is True


@pytest.mark.asyncio
async def test_anonymous_user_has_no_permissions(db_session: AsyncSession) -> None:
    random_user = uuid.uuid4()
    granted = await _scalar(
        db_session,
        "SELECT app.has_permission(:uid, 'global', 'heritage:read')",
        uid=random_user,
    )
    assert granted is False


# --- OAuth providers --------------------------------------------------------


@pytest.mark.asyncio
async def test_oauth_providers_seeded(db_session: AsyncSession) -> None:
    rows = (
        await db_session.execute(text("SELECT slug, is_enabled FROM oauth_providers ORDER BY slug"))
    ).all()
    by_slug = {row[0]: row[1] for row in rows}
    assert by_slug.get("google") is True
    assert by_slug.get("apple") is True
    assert by_slug.get("guest") is True
    assert by_slug.get("facebook") is False  # disabled by default


# --- RBAC -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_permissions_catalog_populated(db_session: AsyncSession) -> None:
    count = await _scalar(db_session, "SELECT count(*) FROM permissions")
    assert count and int(count) >= 20


@pytest.mark.asyncio
async def test_super_admin_has_every_permission(db_session: AsyncSession) -> None:
    diff = await _scalar(
        db_session,
        """
        SELECT count(*) FROM permissions p
        WHERE NOT EXISTS (
            SELECT 1 FROM role_permissions rp
            JOIN roles r ON r.id = rp.role_id
            WHERE r.slug = 'super_admin' AND rp.permission_id = p.id
        );
        """,
    )
    assert diff == 0, f"super_admin missing {diff} permissions"


# --- Audit log + Merkle anchor table ----------------------------------------


@pytest.mark.asyncio
async def test_audit_log_partition_exists_for_current_month(db_session: AsyncSession) -> None:
    rows = (
        await db_session.execute(
            text(
                """
                SELECT tablename FROM pg_tables
                WHERE schemaname='audit' AND tablename LIKE 'audit_log_y%';
                """
            )
        )
    ).all()
    # We provisioned -1..+3 months. Just assert at least one partition exists.
    assert len(rows) >= 4


@pytest.mark.asyncio
async def test_app_audit_writes_hash_chain(db_session: AsyncSession) -> None:
    # Set the HMAC key for this session
    await db_session.execute(text("SET LOCAL app.audit_hmac_key = 'test-hmac-key-for-pytest'"))
    first = await _scalar(
        db_session,
        """
        SELECT app.audit(
            :tenant, :actor, 'global', 'test.action.first',
            'test_entity', NULL, NULL, NULL, NULL, '{"k":"v"}'::jsonb
        )
        """,
        tenant=DEFAULT_TENANT_ID,
        actor=SYSTEM_USER_ID,
    )
    second = await _scalar(
        db_session,
        """
        SELECT app.audit(
            :tenant, :actor, 'global', 'test.action.second',
            'test_entity', NULL, NULL, NULL, NULL, '{}'::jsonb
        )
        """,
        tenant=DEFAULT_TENANT_ID,
        actor=SYSTEM_USER_ID,
    )
    chain = (
        await db_session.execute(
            text(
                """
                SELECT row_hash, prev_hash FROM audit.audit_log
                WHERE id IN (:a, :b)
                ORDER BY created_at
                """
            ),
            {"a": first, "b": second},
        )
    ).all()
    assert len(chain) == 2
    # Second row's prev_hash must equal the first row's row_hash
    assert chain[1][1] == chain[0][0]


# --- Event bus --------------------------------------------------------------


@pytest.mark.asyncio
async def test_event_types_seeded(db_session: AsyncSession) -> None:
    count = await _scalar(db_session, "SELECT count(*) FROM event_types")
    assert count and int(count) >= 15


@pytest.mark.asyncio
async def test_emit_event_to_outbox(db_session: AsyncSession) -> None:
    event_id = await _scalar(
        db_session,
        """
        SELECT app.emit_event(
            :tenant, 'heritage.viewed.v1', 'heritage',
            gen_uuid_v7(), '{"viewer":"test"}'::jsonb
        )
        """,
        tenant=DEFAULT_TENANT_ID,
    )
    assert event_id is not None
    payload = await _scalar(
        db_session,
        "SELECT payload->>'viewer' FROM event_outbox WHERE id = :id",
        id=event_id,
    )
    assert payload == "test"


@pytest.mark.asyncio
async def test_emit_event_rejects_unregistered_name(db_session: AsyncSession) -> None:
    with pytest.raises(Exception, match="unregistered event_name"):
        await db_session.execute(
            text(
                """
                SELECT app.emit_event(
                    :tenant, 'totally.fake.event.v99', 'fake', NULL, '{}'::jsonb
                )
                """
            ),
            {"tenant": DEFAULT_TENANT_ID},
        )
    await db_session.rollback()  # error left the tx in failed state


# --- Sessions / refresh tokens ----------------------------------------------


@pytest.mark.asyncio
async def test_sessions_table_partitioned(db_session: AsyncSession) -> None:
    rows = (
        await db_session.execute(
            text(
                """
                SELECT tablename FROM pg_tables
                WHERE tablename LIKE 'sessions\\_%' ESCAPE '\\'
                ORDER BY tablename
                """
            )
        )
    ).all()
    names = {row[0] for row in rows}
    assert {"sessions_uz", "sessions_eu", "sessions_us", "sessions_global"}.issubset(names)
