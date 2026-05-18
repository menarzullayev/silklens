"""Shared helpers reused across migrations.

Imported by migration scripts via ``from alembic.versions._helpers import ...``.
Kept here (rather than in ``src/``) because migrations should not depend on
application code that may change shape over time — a 2026 migration must still
apply in 2030 even if ``src/`` has been refactored.
"""

from __future__ import annotations

from sqlalchemy import text

# --- Common column DDL fragments ----------------------------------------------

PK_UUID_V7 = "id uuid PRIMARY KEY DEFAULT gen_uuid_v7()"

TIMESTAMPS = """
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    deleted_at timestamptz
"""

ACTOR_AUDIT = """
    created_by uuid,
    updated_by uuid,
    deleted_by uuid
"""


# --- Reusable triggers -------------------------------------------------------

UPDATED_AT_TRIGGER_FN = text(
    """
    CREATE OR REPLACE FUNCTION app.tg_set_updated_at() RETURNS trigger AS $$
    BEGIN
        NEW.updated_at := now();
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """
)


def attach_updated_at_trigger(table: str, schema: str = "public") -> str:
    """SQL to attach the updated_at trigger to a table. Idempotent."""
    return f"""
    DROP TRIGGER IF EXISTS tg_{table}_updated_at ON {schema}.{table};
    CREATE TRIGGER tg_{table}_updated_at
        BEFORE UPDATE ON {schema}.{table}
        FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
    """


# --- Audit-anchor helpers ----------------------------------------------------

AUDIT_HMAC_FN = text(
    """
    CREATE OR REPLACE FUNCTION audit.row_hmac(
        prev_hash bytea,
        row_payload jsonb,
        secret text
    ) RETURNS bytea AS $$
    BEGIN
        RETURN hmac(
            coalesce(prev_hash, '\\x'::bytea) || convert_to(row_payload::text, 'UTF8'),
            convert_to(secret, 'UTF8'),
            'sha256'
        );
    END;
    $$ LANGUAGE plpgsql IMMUTABLE;
    """
)
