"""sessions, refresh tokens, device fingerprints

Per Agent 2 §8: JWT access tokens are stateless; refresh tokens are opaque
rows we can revoke. Sessions tie everything to a device so users can list /
revoke active sessions from their account screen. Device fingerprints feed
Agent 5's sock-puppet damping pipeline.

Revision ID: 0009_sessions
Revises: 0008_event_bus
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0009_sessions"
down_revision: str | Sequence[str] | None = "0008_event_bus"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- device_fingerprints (not partitioned — fingerprints are tenant-global) ---
    op.execute(
        """
        CREATE TABLE device_fingerprints (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            fingerprint_hash text NOT NULL UNIQUE,
            -- raw_components is hashed because the components themselves are PII;
            -- we keep them only for short windows for forensics.
            raw_components  jsonb,
            user_agent_hint text,
            platform_hint   text CHECK (platform_hint IN ('ios','android','web','desktop','unknown')),
            first_seen_at   timestamptz NOT NULL DEFAULT now(),
            last_seen_at    timestamptz NOT NULL DEFAULT now(),
            seen_count      int NOT NULL DEFAULT 1,
            -- abuse signals
            is_flagged      boolean NOT NULL DEFAULT false,
            flag_reason     text,
            associated_user_count int NOT NULL DEFAULT 0,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now()
        );

        CREATE INDEX idx_device_fingerprints_flagged
            ON device_fingerprints (last_seen_at DESC) WHERE is_flagged;
        CREATE INDEX idx_device_fingerprints_last_seen
            ON device_fingerprints (last_seen_at DESC);

        CREATE TRIGGER tg_device_fingerprints_updated_at
            BEFORE UPDATE ON device_fingerprints
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE device_fingerprints IS
            'Stable per-device hash from client fingerprint components. Sock-puppet '
            'detection (Agent 5) reads associated_user_count. raw_components is purged '
            'after the retention window (default 30d).';
        """
    )

    # --- sessions (partitioned by residency_region) ----------------------
    op.execute(
        """
        CREATE TABLE sessions (
            id                  uuid NOT NULL DEFAULT gen_uuid_v7(),
            user_id             uuid NOT NULL,
            residency_region    text NOT NULL,
            tenant_id           uuid NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            device_fingerprint_id uuid REFERENCES device_fingerprints(id) ON DELETE SET NULL,
            ip_address          inet,
            user_agent          text,
            issued_at           timestamptz NOT NULL DEFAULT now(),
            last_seen_at        timestamptz NOT NULL DEFAULT now(),
            expires_at          timestamptz NOT NULL,
            revoked_at          timestamptz,
            revoke_reason       text,
            metadata            jsonb NOT NULL DEFAULT '{}'::jsonb,

            PRIMARY KEY (id, residency_region),
            FOREIGN KEY (user_id, residency_region)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (residency_region IN ('uz','eu','us','global'))
        ) PARTITION BY LIST (residency_region);
        """
    )
    for region in ("uz", "eu", "us", "global"):
        op.execute(
            f"CREATE TABLE sessions_{region} "
            f"PARTITION OF sessions FOR VALUES IN ('{region}');"
        )

    op.execute(
        """
        CREATE INDEX idx_sessions_user_active
            ON sessions (user_id, last_seen_at DESC)
            WHERE revoked_at IS NULL;
        CREATE INDEX idx_sessions_expires
            ON sessions (expires_at)
            WHERE revoked_at IS NULL;
        """
    )

    # --- refresh_tokens (partitioned by residency_region) ----------------
    op.execute(
        """
        CREATE TABLE refresh_tokens (
            id                  uuid NOT NULL DEFAULT gen_uuid_v7(),
            session_id          uuid NOT NULL,
            session_residency   text NOT NULL,
            user_id             uuid NOT NULL,
            residency_region    text NOT NULL,
            tenant_id           uuid NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            -- We store HMAC(token), not the token itself, so a DB read doesn't
            -- yield usable refresh tokens.
            token_hash          bytea NOT NULL,
            family_id           uuid NOT NULL,
            -- Rotation: when a refresh is used, the next refresh inherits family_id.
            replaced_by_id      uuid,
            issued_at           timestamptz NOT NULL DEFAULT now(),
            expires_at          timestamptz NOT NULL,
            used_at             timestamptz,
            revoked_at          timestamptz,
            revoke_reason       text,

            PRIMARY KEY (id, residency_region),
            FOREIGN KEY (session_id, session_residency)
                REFERENCES sessions(id, residency_region) ON DELETE CASCADE,
            FOREIGN KEY (user_id, residency_region)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (residency_region IN ('uz','eu','us','global'))
        ) PARTITION BY LIST (residency_region);
        """
    )
    for region in ("uz", "eu", "us", "global"):
        op.execute(
            f"CREATE TABLE refresh_tokens_{region} "
            f"PARTITION OF refresh_tokens FOR VALUES IN ('{region}');"
        )

    op.execute(
        """
        CREATE UNIQUE INDEX uq_refresh_tokens_hash
            ON refresh_tokens (token_hash, residency_region);
        CREATE INDEX idx_refresh_tokens_family
            ON refresh_tokens (family_id, residency_region);
        CREATE INDEX idx_refresh_tokens_session
            ON refresh_tokens (session_id, residency_region)
            WHERE revoked_at IS NULL AND used_at IS NULL;

        COMMENT ON TABLE refresh_tokens IS
            'Opaque refresh tokens with family-based rotation. Re-use of a used '
            'token revokes the entire family (token-replay defence per Agent 2).';
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS refresh_tokens CASCADE;")
    op.execute("DROP TABLE IF EXISTS sessions CASCADE;")
    op.execute("DROP TABLE IF EXISTS device_fingerprints CASCADE;")
