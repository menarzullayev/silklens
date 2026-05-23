"""extensions and uuidv7 function

Sets up PostgreSQL extensions and the project-canonical ``gen_uuid_v7()``
function per ADR-0004. Every subsequent migration may assume these exist.

Revision ID: 0001_extensions_uuidv7
Revises:
Create Date: 2026-05-18

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_extensions_uuidv7"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


EXTENSIONS = (
    "pgcrypto",
    "pg_trgm",
    "unaccent",
    "citext",
    "ltree",
    "btree_gist",
    "btree_gin",
    "vector",
    # cube + earthdistance — required by listings/weather/mood/quick-plan
    # queries that use the `point <@> point` great-circle distance operator.
    # Order matters: earthdistance depends on cube.
    "cube",
    "earthdistance",
)


GEN_UUID_V7_SQL = """
CREATE OR REPLACE FUNCTION gen_uuid_v7() RETURNS uuid AS $$
DECLARE
    unix_ts_ms bytea;
    uuid_bytes bytea;
BEGIN
    -- 48-bit Unix epoch in milliseconds
    unix_ts_ms := substring(
        int8send((extract(epoch from clock_timestamp()) * 1000)::bigint) from 3
    );
    -- 10 random bytes for the remainder
    uuid_bytes := unix_ts_ms || gen_random_bytes(10);
    -- Set version (7) in the 7th byte
    uuid_bytes := set_byte(
        uuid_bytes,
        6,
        (
            b'01110000'::bit(8)
            | (get_byte(uuid_bytes, 6)::bit(8) & b'00001111'::bit(8))
        )::int
    );
    -- Set variant (10xxxxxx) in the 9th byte
    uuid_bytes := set_byte(
        uuid_bytes,
        8,
        (
            b'10000000'::bit(8)
            | (get_byte(uuid_bytes, 8)::bit(8) & b'00111111'::bit(8))
        )::int
    );
    RETURN encode(uuid_bytes, 'hex')::uuid;
END;
$$ LANGUAGE plpgsql VOLATILE;

COMMENT ON FUNCTION gen_uuid_v7() IS
    'Generates a UUIDv7 (RFC 9562) — time-ordered for B-tree locality. See ADR-0004.';
"""


APP_SCHEMA_SQL = """
CREATE SCHEMA IF NOT EXISTS app;
CREATE SCHEMA IF NOT EXISTS audit;
COMMENT ON SCHEMA app   IS 'Application data — owned by silklens role.';
COMMENT ON SCHEMA audit IS 'Append-only audit & event log; restricted writes.';
"""


def upgrade() -> None:
    for ext in EXTENSIONS:
        op.execute(f'CREATE EXTENSION IF NOT EXISTS "{ext}";')
    op.execute(APP_SCHEMA_SQL)
    op.execute(GEN_UUID_V7_SQL)


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS gen_uuid_v7();")
    # We intentionally do NOT drop the schemas or extensions on downgrade:
    # other schemas / databases may share them on the same cluster.
