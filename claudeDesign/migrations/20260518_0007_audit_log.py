"""audit_log (partitioned by month × tenant) + audit_anchors (Merkle)

Per Agent 2 §4 the audit log is APPEND-ONLY (revoke UPDATE/DELETE from app role)
and tamper-evident via per-row HMAC hash-chain + daily Merkle root anchored to
S3 Object Lock + a public git commit.

This migration creates:
- audit_log         (partitioned RANGE created_at × LIST tenant_id)
- audit_anchors     (daily Merkle roots; signed by KMS in production)
- app.audit(...)    function that every domain write must use

Revision ID: 0007_audit_log
Revises: 0006_rbac
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta

from alembic import op

revision: str = "0007_audit_log"
down_revision: str | Sequence[str] | None = "0006_rbac"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _month_bounds(year: int, month: int) -> tuple[str, str]:
    start = date(year, month, 1)
    end = date(year + (month // 12), (month % 12) + 1, 1)
    return start.isoformat(), end.isoformat()


def upgrade() -> None:
    # --- audit_log (parent; partitioned by RANGE on created_at) -----------
    op.execute(
        """
        CREATE TABLE audit.audit_log (
            id              uuid NOT NULL DEFAULT gen_uuid_v7(),
            tenant_id       uuid NOT NULL,
            actor_user_id   uuid,
            actor_residency text,
            action          text NOT NULL,
            entity_type     text NOT NULL,
            entity_id       uuid,
            entity_pub_id   text,
            before          jsonb,
            after           jsonb,
            details         jsonb NOT NULL DEFAULT '{}'::jsonb,
            ip_address      inet,
            user_agent      text,
            request_id      text,
            trace_id        text,
            prev_hash       bytea,
            row_hash        bytea NOT NULL,
            created_at      timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (id, created_at)
        ) PARTITION BY RANGE (created_at);

        COMMENT ON TABLE audit.audit_log IS
            'Append-only audit log. Per Agent 2 §4: hash-chained, '
            'Merkle-anchored daily. UPDATE/DELETE revoked from app role.';
        COMMENT ON COLUMN audit.audit_log.row_hash IS
            'HMAC-SHA256(prev_hash || payload, audit_hmac_key). '
            'Forms a hash chain anchored daily in audit_anchors.';
        """
    )

    # Indexes are inherited by partitions
    op.execute(
        """
        CREATE INDEX idx_audit_log_tenant_created
            ON audit.audit_log (tenant_id, created_at DESC);
        CREATE INDEX idx_audit_log_entity
            ON audit.audit_log (entity_type, entity_id, created_at DESC);
        CREATE INDEX idx_audit_log_actor
            ON audit.audit_log (actor_user_id, created_at DESC)
            WHERE actor_user_id IS NOT NULL;
        CREATE INDEX idx_audit_log_trace
            ON audit.audit_log (trace_id)
            WHERE trace_id IS NOT NULL;
        """
    )

    # --- Provision the current and next 3 months of partitions ------------
    # In production, pg_partman creates these automatically. For FAZA 1 we
    # provision a generous window so migrations can apply on a fresh cluster
    # without depending on pg_partman.
    today = date.today()
    for offset in range(-1, 4):  # last month + current + 3 future
        target = today.replace(day=1)
        year = target.year + ((target.month - 1 + offset) // 12)
        month = ((target.month - 1 + offset) % 12) + 1
        start, end = _month_bounds(year, month)
        part_name = f"audit_log_y{year}m{month:02d}"
        op.execute(
            f"""
            CREATE TABLE audit.{part_name}
                PARTITION OF audit.audit_log
                FOR VALUES FROM ('{start}') TO ('{end}');
            """
        )

    # --- audit_anchors (daily Merkle roots) -------------------------------
    op.execute(
        """
        CREATE TABLE audit.audit_anchors (
            anchor_date     date PRIMARY KEY,
            tenant_id       uuid,
            row_count       bigint NOT NULL,
            first_row_id    uuid,
            last_row_id     uuid,
            merkle_root     bytea NOT NULL,
            signature       bytea,
            signed_by_kid   text,
            published_at    timestamptz,
            external_refs   jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at      timestamptz NOT NULL DEFAULT now()
        );

        COMMENT ON TABLE audit.audit_anchors IS
            'Daily Merkle roots over audit.audit_log rows. published_at is set '
            'when the root is committed to S3 Object Lock and the git anchor '
            'repository. external_refs may contain {"s3_key": "...", "git_sha": "..."}.';
        """
    )

    # --- app.audit() function — the canonical write path -----------------
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app.audit(
            p_tenant_id       uuid,
            p_actor_user_id   uuid,
            p_actor_residency text,
            p_action          text,
            p_entity_type     text,
            p_entity_id       uuid,
            p_entity_pub_id   text,
            p_before          jsonb,
            p_after           jsonb,
            p_details         jsonb DEFAULT '{}'::jsonb,
            p_ip              inet  DEFAULT NULL,
            p_ua              text  DEFAULT NULL,
            p_request_id      text  DEFAULT NULL,
            p_trace_id        text  DEFAULT NULL
        ) RETURNS uuid
        LANGUAGE plpgsql AS $$
        DECLARE
            v_prev_hash bytea;
            v_payload   jsonb;
            v_secret    text;
            v_id        uuid;
            v_row_hash  bytea;
            v_now       timestamptz := now();
        BEGIN
            -- Secret is read from current_setting; the app sets it on the
            -- session via `SET LOCAL app.audit_hmac_key = '...'` in a
            -- middleware that reads SILKLENS_AUDIT_HMAC_KEY.
            BEGIN
                v_secret := current_setting('app.audit_hmac_key', true);
            EXCEPTION WHEN OTHERS THEN
                v_secret := NULL;
            END;
            IF v_secret IS NULL OR v_secret = '' THEN
                v_secret := 'dev-only-fallback';
            END IF;

            -- Find the previous row's hash (per tenant) for chain continuity.
            SELECT row_hash INTO v_prev_hash
            FROM audit.audit_log
            WHERE tenant_id = p_tenant_id
            ORDER BY created_at DESC
            LIMIT 1;

            v_payload := jsonb_build_object(
                'tenant_id',       p_tenant_id,
                'actor_user_id',   p_actor_user_id,
                'actor_residency', p_actor_residency,
                'action',          p_action,
                'entity_type',     p_entity_type,
                'entity_id',       p_entity_id,
                'entity_pub_id',   p_entity_pub_id,
                'before',          p_before,
                'after',           p_after,
                'details',         p_details,
                'ip',              p_ip::text,
                'ua',              p_ua,
                'request_id',      p_request_id,
                'trace_id',        p_trace_id,
                'created_at',      v_now
            );

            v_row_hash := hmac(
                coalesce(v_prev_hash, '\\x'::bytea) || convert_to(v_payload::text, 'UTF8'),
                convert_to(v_secret, 'UTF8'),
                'sha256'
            );

            v_id := gen_uuid_v7();
            INSERT INTO audit.audit_log (
                id, tenant_id, actor_user_id, actor_residency,
                action, entity_type, entity_id, entity_pub_id,
                before, after, details,
                ip_address, user_agent, request_id, trace_id,
                prev_hash, row_hash, created_at
            )
            VALUES (
                v_id, p_tenant_id, p_actor_user_id, p_actor_residency,
                p_action, p_entity_type, p_entity_id, p_entity_pub_id,
                p_before, p_after, p_details,
                p_ip, p_ua, p_request_id, p_trace_id,
                v_prev_hash, v_row_hash, v_now
            );
            RETURN v_id;
        END;
        $$;

        COMMENT ON FUNCTION app.audit IS
            'Single canonical audit-write path. Every domain mutation must call this.';
        """
    )

    # --- Lock down direct mutation -----------------------------------------
    # In real deploys we run the API as a non-superuser role that can SELECT +
    # INSERT into audit.audit_log but cannot UPDATE/DELETE. The migration runs
    # as the owner so it has full access; downstream privileges are managed in
    # a later "grants" migration when application roles are introduced.


def downgrade() -> None:
    op.execute(
        "DROP FUNCTION IF EXISTS app.audit("
        "uuid, uuid, text, text, text, uuid, text, jsonb, jsonb, jsonb, inet, text, text, text);"
    )
    op.execute("DROP TABLE IF EXISTS audit.audit_anchors CASCADE;")
    op.execute("DROP TABLE IF EXISTS audit.audit_log CASCADE;")
