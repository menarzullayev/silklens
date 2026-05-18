"""users + user_profiles partitioned by residency_region

Implements Agent 2 architecture §11 (data residency) and ADR-pending on
Uzbek PD-law compliance. Every PII-bearing row lives in a partition keyed
on the user's residency region; partitions can later be moved to
region-specific tablespaces without data migration.

Trust scores, password hashes, and verification timestamps live here.
OAuth identities and other auth methods are introduced in migration 0005.

Revision ID: 0004_users
Revises: 0003_admin_config
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0004_users"
down_revision: str | Sequence[str] | None = "0003_admin_config"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


RESIDENCY_PARTITIONS = ("uz", "eu", "us", "global")


def upgrade() -> None:
    # --- users (partitioned by residency_region) ---------------------------
    # We partition by LIST(residency_region). Each partition is a child table
    # on which we can later set a region-specific tablespace.
    op.execute(
        """
        CREATE TABLE users (
            id                  uuid NOT NULL DEFAULT gen_uuid_v7(),
            tenant_id           uuid NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            residency_region    text NOT NULL DEFAULT 'global',
            pub_id              text NOT NULL,
            -- credentials --
            password_hash       text,
            password_algorithm  text DEFAULT 'argon2id'
                CHECK (password_algorithm IN ('argon2id','bcrypt')),
            -- account state --
            status              text NOT NULL DEFAULT 'active'
                CHECK (status IN ('active','suspended','pending_verification','banned','deleted')),
            is_guest            boolean NOT NULL DEFAULT false,
            email_verified_at   timestamptz,
            phone_verified_at   timestamptz,
            mfa_enabled         boolean NOT NULL DEFAULT false,
            -- trust + behaviour --
            trust_score         smallint NOT NULL DEFAULT 0
                CHECK (trust_score BETWEEN 0 AND 100),
            trust_tier          text NOT NULL DEFAULT 'new'
                CHECK (trust_tier IN ('new','regular','trusted','contributor','staff','admin')),
            login_count         int NOT NULL DEFAULT 0,
            last_login_at       timestamptz,
            last_active_at      timestamptz,
            -- preferences --
            preferred_locale    text NOT NULL DEFAULT 'en',
            preferred_timezone  text NOT NULL DEFAULT 'UTC',
            -- audit + soft-delete --
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now(),
            deleted_at          timestamptz,
            anonymized_at       timestamptz,
            created_by          uuid,
            updated_by          uuid,

            PRIMARY KEY (id, residency_region),
            UNIQUE (pub_id, residency_region),
            CHECK (residency_region IN ('uz','eu','us','global')),
            CHECK (pub_id ~ '^[a-zA-Z0-9_-]{8,32}$')
        ) PARTITION BY LIST (residency_region);

        COMMENT ON TABLE users IS
            'Root user table partitioned by residency_region (Agent 2 §11). '
            'Every PII-bearing child table must share the same partition key.';
        COMMENT ON COLUMN users.pub_id IS
            'Public-facing identifier (URL-safe). Generated app-side at registration.';
        COMMENT ON COLUMN users.trust_score IS
            '0-100, computed from reputation_events. Anti-abuse signal per Agent 5.';
        """
    )

    for region in RESIDENCY_PARTITIONS:
        op.execute(
            f"""
            CREATE TABLE users_{region}
                PARTITION OF users
                FOR VALUES IN ('{region}');
            """
        )

    # Indexes are created on each partition automatically when made on the parent.
    op.execute(
        """
        CREATE INDEX idx_users_tenant_status
            ON users(tenant_id, status)
            WHERE deleted_at IS NULL;
        CREATE INDEX idx_users_last_active
            ON users(last_active_at)
            WHERE deleted_at IS NULL AND last_active_at IS NOT NULL;
        CREATE INDEX idx_users_trust_tier
            ON users(trust_tier)
            WHERE deleted_at IS NULL;
        """
    )

    op.execute(
        """
        CREATE TRIGGER tg_users_updated_at
            BEFORE UPDATE ON users
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- user_profiles (also partitioned by residency_region) -------------
    op.execute(
        """
        CREATE TABLE user_profiles (
            user_id            uuid NOT NULL,
            residency_region   text NOT NULL,
            tenant_id          uuid NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            display_name       citext,
            full_name          text,
            avatar_url         text,
            bio                text,
            country_code       char(2),
            city               text,
            interests          text[] NOT NULL DEFAULT ARRAY[]::text[],
            stats              jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at         timestamptz NOT NULL DEFAULT now(),
            updated_at         timestamptz NOT NULL DEFAULT now(),

            PRIMARY KEY (user_id, residency_region),
            FOREIGN KEY (user_id, residency_region)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (residency_region IN ('uz','eu','us','global'))
        ) PARTITION BY LIST (residency_region);

        COMMENT ON TABLE user_profiles IS
            'User-visible profile data. display_name is citext for case-insensitive uniqueness '
            'within a tenant — enforced via unique partial index below.';
        """
    )

    for region in RESIDENCY_PARTITIONS:
        op.execute(
            f"""
            CREATE TABLE user_profiles_{region}
                PARTITION OF user_profiles
                FOR VALUES IN ('{region}');
            """
        )

    op.execute(
        """
        CREATE INDEX idx_user_profiles_country
            ON user_profiles(country_code)
            WHERE country_code IS NOT NULL;
        CREATE INDEX idx_user_profiles_interests
            ON user_profiles USING GIN (interests);

        CREATE TRIGGER tg_user_profiles_updated_at
            BEFORE UPDATE ON user_profiles
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- System user (FK target for system-driven writes) ------------------
    op.execute(
        """
        INSERT INTO users (
            id, tenant_id, residency_region, pub_id,
            status, is_guest, trust_tier, trust_score
        )
        VALUES (
            '00000000-0000-0000-0000-000000000002',
            '00000000-0000-0000-0000-000000000001',
            'global',
            'system_actor',
            'active',
            false,
            'staff',
            100
        );

        INSERT INTO user_profiles (
            user_id, residency_region, tenant_id, display_name
        )
        VALUES (
            '00000000-0000-0000-0000-000000000002',
            'global',
            '00000000-0000-0000-0000-000000000001',
            'System Actor'
        );

        COMMENT ON COLUMN users.created_by IS
            'NULL for self-registration; FK target users.id for admin-created accounts. '
            'Use the system user id 00000000-0000-0000-0000-000000000002 for automated writes.';
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_profiles CASCADE;")
    op.execute("DROP TABLE IF EXISTS users CASCADE;")
