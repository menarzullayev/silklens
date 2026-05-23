"""AI conversation history persistence.

SILK-0060: Persisted conversation sessions and messages for the AI chat
pipeline. Enables multi-turn context, history browsing, and token-efficient
context summarisation.

Tables introduced:

  conversation_sessions  — one row per user conversation; partitioned by
                           LIST(residency_region) with global/eu/us/uz leaves.
  conversation_messages  — individual user/assistant/system turns; partitioned
                           by RANGE(created_at) with monthly leaf tables for
                           2026-05 through 2026-07.

Revision ID: 0096
Revises: 0095
Create Date: 2026-05-23
"""

from __future__ import annotations

from alembic import op

revision = "0096"
down_revision = "0095"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # conversation_sessions
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE conversation_sessions (
            id               uuid         NOT NULL DEFAULT gen_uuid_v7(),
            user_id          uuid         NOT NULL,
            residency_region varchar(20)  NOT NULL,
            tenant_id        uuid         NOT NULL,
            title            varchar(200),
            context_kind     varchar(30)  NOT NULL DEFAULT 'general',
            heritage_pub_id  uuid,
            trip_id          uuid,
            language_tag     varchar(10)  NOT NULL DEFAULT 'en',
            message_count    int          NOT NULL DEFAULT 0,
            last_message_at  timestamptz,
            context_summary  text,
            is_active        boolean      NOT NULL DEFAULT true,
            created_at       timestamptz  NOT NULL DEFAULT now(),
            updated_at       timestamptz  NOT NULL DEFAULT now(),
            PRIMARY KEY (id, residency_region),
            FOREIGN KEY (user_id, residency_region)
                REFERENCES users (id, residency_region) ON DELETE RESTRICT,
            FOREIGN KEY (tenant_id)
                REFERENCES tenants (id) ON DELETE RESTRICT,
            CONSTRAINT conversation_sessions_context_kind_check
                CHECK (context_kind IN ('general', 'heritage', 'trip', 'food', 'emergency'))
        ) PARTITION BY LIST (residency_region)
        """
    )

    op.execute(
        """
        CREATE TABLE conversation_sessions_global
            PARTITION OF conversation_sessions
            FOR VALUES IN ('global')
        """
    )
    op.execute(
        """
        CREATE TABLE conversation_sessions_eu
            PARTITION OF conversation_sessions
            FOR VALUES IN ('eu')
        """
    )
    op.execute(
        """
        CREATE TABLE conversation_sessions_us
            PARTITION OF conversation_sessions
            FOR VALUES IN ('us')
        """
    )
    op.execute(
        """
        CREATE TABLE conversation_sessions_uz
            PARTITION OF conversation_sessions
            FOR VALUES IN ('uz')
        """
    )

    # Indexes
    op.execute(
        """
        CREATE INDEX ix_conv_sessions_user
            ON conversation_sessions (user_id, residency_region, last_message_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_conv_sessions_heritage
            ON conversation_sessions (heritage_pub_id)
            WHERE heritage_pub_id IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE INDEX ix_conv_sessions_tenant_active
            ON conversation_sessions (tenant_id, is_active)
        """
    )

    # RLS
    op.execute("ALTER TABLE conversation_sessions ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY conversation_sessions_tenant_isolation
            ON conversation_sessions
            USING (tenant_id = app.current_tenant_id())
        """
    )

    # updated_at trigger
    op.execute(
        """
        CREATE TRIGGER tg_conversation_sessions_updated_at
            BEFORE UPDATE ON conversation_sessions
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at()
        """
    )

    # Comments
    op.execute(
        """
        COMMENT ON TABLE conversation_sessions IS
            'One row per user AI conversation thread. Partitioned by residency_region. '
            'Drives history browsing (GET /v1/ai/conversations) and multi-turn context loading.';
        COMMENT ON COLUMN conversation_sessions.context_kind IS
            'Conversation subject domain: general|heritage|trip|food|emergency.';
        COMMENT ON COLUMN conversation_sessions.heritage_pub_id IS
            'Optional link to a heritage object this conversation is anchored to.';
        COMMENT ON COLUMN conversation_sessions.context_summary IS
            'AI-compressed summary of older messages rolled up to preserve token budget.';
        COMMENT ON COLUMN conversation_sessions.message_count IS
            'Running count of user+assistant turns; incremented atomically by the chat endpoint.';
        """
    )

    # ------------------------------------------------------------------
    # conversation_messages
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE conversation_messages (
            id               uuid         NOT NULL DEFAULT gen_uuid_v7(),
            session_id       uuid         NOT NULL,
            residency_region varchar(20)  NOT NULL,
            role             varchar(10)  NOT NULL,
            content_text     text         NOT NULL,
            content_tokens   int,
            input_tokens     int,
            output_tokens    int,
            model_slug       varchar(100),
            is_summarized    boolean      NOT NULL DEFAULT false,
            created_at       timestamptz  NOT NULL DEFAULT now(),
            PRIMARY KEY (id, created_at),
            CONSTRAINT conversation_messages_role_check
                CHECK (role IN ('user', 'assistant', 'system'))
        ) PARTITION BY RANGE (created_at)
        """
    )

    # Monthly leaf partitions for 2026
    op.execute(
        """
        CREATE TABLE conversation_messages_2026_05
            PARTITION OF conversation_messages
            FOR VALUES FROM ('2026-05-01') TO ('2026-06-01')
        """
    )
    op.execute(
        """
        CREATE TABLE conversation_messages_2026_06
            PARTITION OF conversation_messages
            FOR VALUES FROM ('2026-06-01') TO ('2026-07-01')
        """
    )
    op.execute(
        """
        CREATE TABLE conversation_messages_2026_07
            PARTITION OF conversation_messages
            FOR VALUES FROM ('2026-07-01') TO ('2026-08-01')
        """
    )

    # Indexes
    op.execute(
        """
        CREATE INDEX ix_conv_messages_session
            ON conversation_messages (session_id, created_at)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_conv_messages_residency
            ON conversation_messages (residency_region, created_at)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_conv_messages_not_summarized
            ON conversation_messages (session_id, created_at)
            WHERE is_summarized = false
        """
    )

    # Comments
    op.execute(
        """
        COMMENT ON TABLE conversation_messages IS
            'Individual AI conversation turns (user/assistant/system roles). '
            'Partitioned by RANGE(created_at) with monthly leaf tables. '
            'New leaf partitions must be added each month before the first insert.';
        COMMENT ON COLUMN conversation_messages.is_summarized IS
            'True once this row has been rolled up into conversation_sessions.context_summary '
            'and can be excluded from live context window assembly.';
        COMMENT ON COLUMN conversation_messages.content_tokens IS
            'Total token count for this message as reported by the model.';
        COMMENT ON COLUMN conversation_messages.input_tokens IS
            'Tokens consumed from the prompt (assistant turns: full context cost).';
        COMMENT ON COLUMN conversation_messages.output_tokens IS
            'Tokens produced in the completion (assistant turns only).';
        """
    )


def downgrade() -> None:
    # Drop in reverse order of creation.
    op.execute("DROP TABLE IF EXISTS conversation_messages_2026_07 CASCADE")
    op.execute("DROP TABLE IF EXISTS conversation_messages_2026_06 CASCADE")
    op.execute("DROP TABLE IF EXISTS conversation_messages_2026_05 CASCADE")
    op.execute("DROP TABLE IF EXISTS conversation_messages CASCADE")

    op.execute("DROP TABLE IF EXISTS conversation_sessions_uz CASCADE")
    op.execute("DROP TABLE IF EXISTS conversation_sessions_us CASCADE")
    op.execute("DROP TABLE IF EXISTS conversation_sessions_eu CASCADE")
    op.execute("DROP TABLE IF EXISTS conversation_sessions_global CASCADE")
    op.execute("DROP TABLE IF EXISTS conversation_sessions CASCADE")
