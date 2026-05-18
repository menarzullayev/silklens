"""event_types catalog + event_outbox (transactional) + event_log (history)

Per Agent 7 §4–§5 these are SEPARATE concerns:

  event_outbox  — transient queue, written in same transaction as the domain
                  mutation. Drained by Celery reaper which forwards to
                  Redpanda. Reaper deletes rows after successful publish.

  event_log     — immutable canonical event history. Append-only. Range-
                  partitioned daily. The source of truth for replay,
                  analytics warehouse seed, and disaster recovery.

  event_types   — admin-managed catalog of supported event names. Provides
                  schema_url, retention_days, downstream routing config.

Collapsing outbox + log is the classic anti-pattern Agent 7 §5 warns against.

Revision ID: 0008_event_bus
Revises: 0007_audit_log
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta

from alembic import op

revision: str = "0008_event_bus"
down_revision: str | Sequence[str] | None = "0007_audit_log"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- event_types (admin catalog) --------------------------------------
    op.execute(
        """
        CREATE TABLE event_types (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            event_name      text NOT NULL UNIQUE,
            display_name    jsonb NOT NULL DEFAULT '{}'::jsonb,
            schema_url      text,
            retention_days  int NOT NULL DEFAULT 90 CHECK (retention_days > 0),
            kafka_topic     text,
            downstream_targets jsonb NOT NULL DEFAULT '[]'::jsonb,
            is_deprecated   boolean NOT NULL DEFAULT false,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            CHECK (event_name ~ '^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*)+\\.v[0-9]+$')
        );

        CREATE TRIGGER tg_event_types_updated_at
            BEFORE UPDATE ON event_types
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON COLUMN event_types.event_name IS
            'Versioned dotted name: ''<domain>.<action>.<v>''. Example: ''heritage.created.v1''.';
        COMMENT ON COLUMN event_types.downstream_targets IS
            'JSON array: [{"kind":"elasticsearch","index":"heritage"},{"kind":"clickhouse","table":"events_raw"}]';
        """
    )

    # --- event_outbox (transient, partition not needed at this scale) -----
    op.execute(
        """
        CREATE TABLE event_outbox (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            tenant_id       uuid NOT NULL,
            event_name      text NOT NULL,
            aggregate_type  text NOT NULL,
            aggregate_id    uuid,
            payload         jsonb NOT NULL,
            headers         jsonb NOT NULL DEFAULT '{}'::jsonb,
            trace_id        text,
            created_at      timestamptz NOT NULL DEFAULT now(),
            scheduled_for   timestamptz NOT NULL DEFAULT now(),
            attempts        int NOT NULL DEFAULT 0,
            last_attempt_at timestamptz,
            last_error      text
        );

        CREATE INDEX idx_event_outbox_ready
            ON event_outbox (scheduled_for, created_at)
            WHERE attempts < 10;

        COMMENT ON TABLE event_outbox IS
            'Transactional outbox: domain writes INSERT here in the same TX. '
            'Reaper drains to Redpanda then DELETEs. Per Agent 7 §5.';
        """
    )

    # --- event_log (immutable history; partitioned by day) ---------------
    op.execute(
        """
        CREATE TABLE event_log (
            id              uuid NOT NULL DEFAULT gen_uuid_v7(),
            tenant_id       uuid NOT NULL,
            event_name      text NOT NULL,
            aggregate_type  text NOT NULL,
            aggregate_id    uuid,
            payload         jsonb NOT NULL,
            headers         jsonb NOT NULL DEFAULT '{}'::jsonb,
            trace_id        text,
            published_at    timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (id, published_at)
        ) PARTITION BY RANGE (published_at);

        CREATE INDEX idx_event_log_tenant_published
            ON event_log (tenant_id, published_at DESC);
        CREATE INDEX idx_event_log_event_name
            ON event_log (event_name, published_at DESC);
        CREATE INDEX idx_event_log_aggregate
            ON event_log (aggregate_type, aggregate_id, published_at DESC);
        """
    )

    # Provision daily partitions for ±7 days; pg_partman extends in production
    today = date.today()
    for offset in range(-7, 8):
        d = today + timedelta(days=offset)
        d_next = d + timedelta(days=1)
        part_name = f"event_log_{d.strftime('%Y%m%d')}"
        op.execute(
            f"""
            CREATE TABLE {part_name}
                PARTITION OF event_log
                FOR VALUES FROM ('{d.isoformat()}') TO ('{d_next.isoformat()}');
            """
        )

    # --- Seed common event types -----------------------------------------
    op.execute(
        """
        INSERT INTO event_types (event_name, display_name, retention_days, kafka_topic) VALUES
            ('user.registered.v1',      '{"en":"User registered"}',       365, 'silklens.user.events'),
            ('user.merged.v1',          '{"en":"User merged"}',           365, 'silklens.user.events'),
            ('user.banned.v1',          '{"en":"User banned"}',           365, 'silklens.user.events'),
            ('user.anonymized.v1',      '{"en":"User anonymized"}',       730, 'silklens.user.events'),
            ('user.role_changed.v1',    '{"en":"User role changed"}',     365, 'silklens.user.events'),
            ('consent.changed.v1',      '{"en":"Consent changed"}',       730, 'silklens.consent.events'),
            ('heritage.created.v1',     '{"en":"Heritage created"}',      365, 'silklens.heritage.events'),
            ('heritage.updated.v1',     '{"en":"Heritage updated"}',      180, 'silklens.heritage.events'),
            ('heritage.viewed.v1',      '{"en":"Heritage viewed"}',        90, 'silklens.heritage.events'),
            ('review.created.v1',       '{"en":"Review created"}',        180, 'silklens.social.events'),
            ('follow.created.v1',       '{"en":"Follow created"}',        180, 'silklens.social.events'),
            ('vision.recognition.v1',   '{"en":"Vision inference"}',       90, 'silklens.ai.events'),
            ('tts.generated.v1',        '{"en":"TTS generation"}',         90, 'silklens.ai.events'),
            ('subscription.created.v1', '{"en":"Subscription created"}',  730, 'silklens.billing.events'),
            ('subscription.cancelled.v1','{"en":"Subscription cancelled"}',730, 'silklens.billing.events'),
            ('payment.captured.v1',     '{"en":"Payment captured"}',     2555, 'silklens.billing.events'),
            ('payment.refunded.v1',     '{"en":"Payment refunded"}',     2555, 'silklens.billing.events');
        """
    )

    # --- emit_event() helper used by domain writes ------------------------
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app.emit_event(
            p_tenant_id       uuid,
            p_event_name      text,
            p_aggregate_type  text,
            p_aggregate_id    uuid,
            p_payload         jsonb,
            p_headers         jsonb DEFAULT '{}'::jsonb,
            p_trace_id        text  DEFAULT NULL
        ) RETURNS uuid
        LANGUAGE plpgsql AS $$
        DECLARE
            v_id uuid;
        BEGIN
            -- Validate that the event_name is registered. Hard-fail to catch typos.
            PERFORM 1 FROM event_types WHERE event_name = p_event_name AND NOT is_deprecated;
            IF NOT FOUND THEN
                RAISE EXCEPTION USING
                    MESSAGE = format('unregistered event_name %L (register in event_types)', p_event_name),
                    ERRCODE = '23514';
            END IF;

            v_id := gen_uuid_v7();
            INSERT INTO event_outbox (
                id, tenant_id, event_name, aggregate_type, aggregate_id,
                payload, headers, trace_id
            )
            VALUES (
                v_id, p_tenant_id, p_event_name, p_aggregate_type, p_aggregate_id,
                p_payload, p_headers, p_trace_id
            );
            RETURN v_id;
        END;
        $$;

        COMMENT ON FUNCTION app.emit_event IS
            'Canonical event-emit path. Inserts into outbox in the caller''s '
            'transaction. Reaper forwards to Redpanda and event_log.';
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP FUNCTION IF EXISTS app.emit_event("
        "uuid, text, text, uuid, jsonb, jsonb, text);"
    )
    op.execute("DROP TABLE IF EXISTS event_log CASCADE;")
    op.execute("DROP TABLE IF EXISTS event_outbox CASCADE;")
    op.execute("DROP TABLE IF EXISTS event_types CASCADE;")
