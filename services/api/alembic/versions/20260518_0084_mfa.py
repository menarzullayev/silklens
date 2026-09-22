"""mfa_methods + totp_secrets + webauthn_credentials + backup_codes + challenges

FAZA 5 / Wave-6 Agent D. Adds the auth-strengthening surface:

- ``mfa_methods``           — per-user enrolled method (totp, webauthn, backup_codes, sms_otp)
- ``mfa_totp_secrets``      — TOTP shared secret encrypted via pgcrypto pgp_sym_encrypt
- ``mfa_webauthn_credentials`` — FIDO2 credential id + COSE public key + sign counter
- ``mfa_backup_codes``      — argon2id-hashed single-use recovery codes
- ``mfa_challenges``        — short-lived (5 min) verification challenges, daily RANGE-partitioned

Also adds:
- ``users.last_mfa_at`` — last time the user satisfied an MFA challenge (step-up clock)
- Permission ``mfa:bypass_for_user`` granted to super_admin only (incident response).

The ``mfa_required`` flag on ``users`` already exists as ``mfa_enabled`` (migration 0004).
Per architecture §3.27/3.28 the model carries the data per-residency; all PII-bearing
tables follow ``LIST(residency_region)``.

Revision ID: 0084_mfa
Revises: 0071_compliance
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta

from alembic import op

revision: str = "0084_mfa"
down_revision: str | Sequence[str] | None = "0071_compliance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- mfa_methods (LIST partitioned by residency) -----------------------
    op.execute(
        """
        CREATE TABLE mfa_methods (
            id                  uuid NOT NULL DEFAULT gen_uuid_v7(),
            user_id             uuid NOT NULL,
            residency_region    text NOT NULL,
            tenant_id           uuid NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            method              text NOT NULL
                CHECK (method IN ('totp','webauthn','backup_codes','sms_otp')),
            label               text NOT NULL DEFAULT '',
            status              text NOT NULL DEFAULT 'pending'
                CHECK (status IN ('active','disabled','pending')),
            enrolled_at         timestamptz,
            last_used_at        timestamptz,
            metadata            jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now(),

            PRIMARY KEY (id, residency_region),
            UNIQUE (user_id, residency_region, method, label),
            FOREIGN KEY (user_id, residency_region)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (residency_region IN ('uz','eu','us','global'))
        ) PARTITION BY LIST (residency_region);

        COMMENT ON TABLE mfa_methods IS
            'Per-user enrolled MFA factors. One row per (user, method, label). '
            'Partitioned by residency to keep PII on regional partitions.';
        """
    )
    for region in ("uz", "eu", "us", "global"):
        op.execute(
            f"CREATE TABLE mfa_methods_{region} "
            f"PARTITION OF mfa_methods FOR VALUES IN ('{region}');"
        )

    op.execute(
        """
        CREATE INDEX idx_mfa_methods_user_active
            ON mfa_methods (user_id, method)
            WHERE status = 'active';

        CREATE TRIGGER tg_mfa_methods_updated_at
            BEFORE UPDATE ON mfa_methods
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- mfa_totp_secrets ---------------------------------------------------
    # secret_bytes is the output of pgp_sym_encrypt(plaintext, key). The
    # application code goes through SQL functions, never carries the raw
    # plaintext on the wire as bytes.
    op.execute(
        """
        CREATE TABLE mfa_totp_secrets (
            mfa_id              uuid NOT NULL,
            residency_region    text NOT NULL,
            secret_bytes        bytea NOT NULL,
            period              int NOT NULL DEFAULT 30,
            digits              int NOT NULL DEFAULT 6
                CHECK (digits IN (6, 8)),
            algorithm           text NOT NULL DEFAULT 'sha1'
                CHECK (algorithm IN ('sha1','sha256','sha512')),
            created_at          timestamptz NOT NULL DEFAULT now(),

            PRIMARY KEY (mfa_id, residency_region),
            FOREIGN KEY (mfa_id, residency_region)
                REFERENCES mfa_methods(id, residency_region) ON DELETE CASCADE,
            CHECK (residency_region IN ('uz','eu','us','global'))
        );

        COMMENT ON TABLE mfa_totp_secrets IS
            'TOTP shared secret encrypted via pgcrypto pgp_sym_encrypt. '
            'Decryption key sourced from SILKLENS_MFA_AT_REST_KEY (KMS in prod).';
        """
    )

    # --- mfa_webauthn_credentials -------------------------------------------
    op.execute(
        """
        CREATE TABLE mfa_webauthn_credentials (
            mfa_id              uuid NOT NULL,
            residency_region    text NOT NULL,
            credential_id       bytea NOT NULL,
            public_key_bytes    bytea NOT NULL,
            sign_count          bigint NOT NULL DEFAULT 0,
            transports          text[] NOT NULL DEFAULT ARRAY[]::text[],
            attestation_format  text,
            aaguid              uuid,
            created_at          timestamptz NOT NULL DEFAULT now(),

            PRIMARY KEY (mfa_id, residency_region),
            FOREIGN KEY (mfa_id, residency_region)
                REFERENCES mfa_methods(id, residency_region) ON DELETE CASCADE,
            CHECK (residency_region IN ('uz','eu','us','global'))
        );

        CREATE UNIQUE INDEX uq_mfa_webauthn_credentials_credential_id
            ON mfa_webauthn_credentials (credential_id);
        """
    )

    # --- mfa_backup_codes (LIST partitioned by residency) -------------------
    op.execute(
        """
        CREATE TABLE mfa_backup_codes (
            id                  uuid NOT NULL DEFAULT gen_uuid_v7(),
            user_id             uuid NOT NULL,
            residency_region    text NOT NULL,
            tenant_id           uuid NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            code_hash           bytea NOT NULL,
            used_at             timestamptz,
            created_at          timestamptz NOT NULL DEFAULT now(),

            PRIMARY KEY (id, residency_region),
            UNIQUE (user_id, residency_region, code_hash),
            FOREIGN KEY (user_id, residency_region)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (residency_region IN ('uz','eu','us','global'))
        ) PARTITION BY LIST (residency_region);
        """
    )
    for region in ("uz", "eu", "us", "global"):
        op.execute(
            f"CREATE TABLE mfa_backup_codes_{region} "
            f"PARTITION OF mfa_backup_codes FOR VALUES IN ('{region}');"
        )
    op.execute(
        """
        CREATE INDEX idx_mfa_backup_codes_user_active
            ON mfa_backup_codes (user_id) WHERE used_at IS NULL;
        """
    )

    # --- mfa_challenges (daily RANGE partition on created_at) --------------
    op.execute(
        """
        CREATE TABLE mfa_challenges (
            id                  uuid NOT NULL DEFAULT gen_uuid_v7(),
            user_id             uuid NOT NULL,
            residency_region    text NOT NULL,
            method              text NOT NULL
                CHECK (method IN ('totp','webauthn','backup_codes','sms_otp')),
            challenge_bytes     bytea,
            metadata            jsonb NOT NULL DEFAULT '{}'::jsonb,
            expires_at          timestamptz NOT NULL,
            completed_at        timestamptz,
            created_at          timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (id, created_at),
            CHECK (residency_region IN ('uz','eu','us','global'))
        ) PARTITION BY RANGE (created_at);

        COMMENT ON TABLE mfa_challenges IS
            'Short-lived MFA challenges (5 min). Daily RANGE partitions; '
            'older partitions get dropped by the GDPR retention worker.';
        """
    )

    # ±7 day partitions; pg_partman extends in prod.
    today = date.today()
    for offset in range(-1, 8):
        d = today + timedelta(days=offset)
        d_next = d + timedelta(days=1)
        part_name = f"mfa_challenges_{d.strftime('%Y%m%d')}"
        op.execute(
            f"""
            CREATE TABLE {part_name}
                PARTITION OF mfa_challenges
                FOR VALUES FROM ('{d.isoformat()}') TO ('{d_next.isoformat()}');
            """
        )
    op.execute(
        """
        CREATE INDEX idx_mfa_challenges_user
            ON mfa_challenges (user_id, created_at DESC);
        """
    )

    # --- users.last_mfa_at -------------------------------------------------
    op.execute(
        """
        ALTER TABLE users
            ADD COLUMN IF NOT EXISTS last_mfa_at timestamptz;

        COMMENT ON COLUMN users.last_mfa_at IS
            'Last time the user satisfied an MFA challenge. Used by the '
            'step-up auth dependency (5 min default freshness).';
        """
    )

    # --- mfa:bypass_for_user permission (super_admin only) ----------------
    op.execute(
        """
        INSERT INTO permissions (slug, description)
        VALUES ('mfa:bypass_for_user', 'Bypass MFA for a user (incident response)')
        ON CONFLICT (slug) DO NOTHING;

        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.slug = 'super_admin'
          AND p.slug = 'mfa:bypass_for_user'
        ON CONFLICT DO NOTHING;
        """
    )

    # --- event types (so emitters never trip the registry) ----------------
    op.execute(
        """
        INSERT INTO event_types (event_name, display_name, retention_days, kafka_topic)
        VALUES
            ('mfa.enrolled.v1',
             '{"en": "MFA method enrolled"}'::jsonb,
             365, 'mfa.enrolled.v1'),
            ('mfa.disabled.v1',
             '{"en": "MFA method disabled"}'::jsonb,
             365, 'mfa.disabled.v1'),
            ('mfa.verified.v1',
             '{"en": "MFA challenge verified"}'::jsonb,
             90, 'mfa.verified.v1'),
            ('mfa.challenge_failed.v1',
             '{"en": "MFA challenge failed"}'::jsonb,
             90, 'mfa.challenge_failed.v1')
        ON CONFLICT (event_name) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM event_types WHERE event_name IN (
            'mfa.enrolled.v1','mfa.disabled.v1','mfa.verified.v1','mfa.challenge_failed.v1'
        );
        """
    )
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE permission_id IN (SELECT id FROM permissions WHERE slug = 'mfa:bypass_for_user');
        DELETE FROM permissions WHERE slug = 'mfa:bypass_for_user';
        """
    )
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS last_mfa_at;")
    op.execute("DROP TABLE IF EXISTS mfa_challenges CASCADE;")
    op.execute("DROP TABLE IF EXISTS mfa_backup_codes CASCADE;")
    op.execute("DROP TABLE IF EXISTS mfa_webauthn_credentials CASCADE;")
    op.execute("DROP TABLE IF EXISTS mfa_totp_secrets CASCADE;")
    op.execute("DROP TABLE IF EXISTS mfa_methods CASCADE;")
