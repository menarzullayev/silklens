"""oauth_providers (admin catalog) + user_identities + emails + phones

Per Agent 2 §4 the **catalog** (which providers exist) and the **binding**
(which provider is linked to which user) are separate concerns. Collapsing
them would prevent admin from toggling Facebook on/off without a deploy
(Project-Decisions §33).

Revision ID: 0005_oauth_identities
Revises: 0004_users
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0005_oauth_identities"
down_revision: str | Sequence[str] | None = "0004_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- oauth_providers (admin catalog) -----------------------------------
    op.execute(
        """
        CREATE TABLE oauth_providers (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            slug            text NOT NULL UNIQUE,
            display_name    jsonb NOT NULL DEFAULT '{}'::jsonb,
            kind            text NOT NULL
                CHECK (kind IN ('oauth2','oidc','saml','telegram','custom')),
            is_enabled      boolean NOT NULL DEFAULT true,
            client_id       text,
            authorize_url   text,
            token_url       text,
            userinfo_url    text,
            jwks_url        text,
            scopes          text[] NOT NULL DEFAULT ARRAY[]::text[],
            icon_url        text,
            sort_order      int NOT NULL DEFAULT 100,
            metadata        jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            CHECK (slug ~ '^[a-z][a-z0-9_]*$')
        );

        CREATE INDEX idx_oauth_providers_enabled
            ON oauth_providers(sort_order) WHERE is_enabled;

        CREATE TRIGGER tg_oauth_providers_updated_at
            BEFORE UPDATE ON oauth_providers
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE oauth_providers IS
            'Admin-editable catalog of available auth providers. Per Agent 2 §4 '
            'separated from user_identities (the actual user-provider bindings).';
        """
    )

    # --- oauth_provider_secrets (separate table for privilege isolation) --
    # Per Agent 2: client_secret lives away from the main catalog so admin-read
    # of the catalog never exposes secrets. Reading this table requires a
    # higher privilege than the catalog itself.
    op.execute(
        """
        CREATE TABLE oauth_provider_secrets (
            provider_id      uuid PRIMARY KEY REFERENCES oauth_providers(id) ON DELETE CASCADE,
            client_secret    text NOT NULL,
            rotation_due_at  timestamptz,
            created_at       timestamptz NOT NULL DEFAULT now(),
            updated_at       timestamptz NOT NULL DEFAULT now()
        );

        CREATE TRIGGER tg_oauth_provider_secrets_updated_at
            BEFORE UPDATE ON oauth_provider_secrets
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        REVOKE ALL ON oauth_provider_secrets FROM PUBLIC;
        """
    )

    # --- user_identities (the actual provider→user bindings) --------------
    # Composite FK to (users.id, residency_region) preserves partitioning.
    op.execute(
        """
        CREATE TABLE user_identities (
            id                  uuid NOT NULL DEFAULT gen_uuid_v7(),
            user_id             uuid NOT NULL,
            residency_region    text NOT NULL,
            tenant_id           uuid NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            provider_id         uuid NOT NULL REFERENCES oauth_providers(id) ON DELETE RESTRICT,
            provider_subject    text NOT NULL,
            email_at_link       text,
            display_name_at_link text,
            access_token        text,
            refresh_token       text,
            token_expires_at    timestamptz,
            raw_profile         jsonb NOT NULL DEFAULT '{}'::jsonb,
            linked_at           timestamptz NOT NULL DEFAULT now(),
            last_used_at        timestamptz,
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now(),

            PRIMARY KEY (id, residency_region),
            FOREIGN KEY (user_id, residency_region)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (residency_region IN ('uz','eu','us','global'))
        ) PARTITION BY LIST (residency_region);
        """
    )
    for region in ("uz", "eu", "us", "global"):
        op.execute(
            f"CREATE TABLE user_identities_{region} "
            f"PARTITION OF user_identities FOR VALUES IN ('{region}');"
        )

    op.execute(
        """
        -- Partitioned tables require partition key in any UNIQUE constraint.
        -- Cross-region uniqueness is enforced at app layer; identity-merge is
        -- a separate workflow that detects the same provider_subject in two
        -- regions before they diverge.
        CREATE UNIQUE INDEX uq_user_identities_provider_subject
            ON user_identities (provider_id, provider_subject, residency_region);
        CREATE INDEX idx_user_identities_user
            ON user_identities (user_id);

        CREATE TRIGGER tg_user_identities_updated_at
            BEFORE UPDATE ON user_identities
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- user_emails (multi-email + primary flag) -------------------------
    op.execute(
        """
        CREATE TABLE user_emails (
            id                  uuid NOT NULL DEFAULT gen_uuid_v7(),
            user_id             uuid NOT NULL,
            residency_region    text NOT NULL,
            tenant_id           uuid NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            email               citext NOT NULL,
            is_primary          boolean NOT NULL DEFAULT false,
            verified_at         timestamptz,
            verification_sent_at timestamptz,
            bounce_count        int NOT NULL DEFAULT 0,
            -- Apple Hide-My-Email forwarding tracking:
            is_forwarded        boolean NOT NULL DEFAULT false,
            forwarded_from      text,
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now(),

            PRIMARY KEY (id, residency_region),
            FOREIGN KEY (user_id, residency_region)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (residency_region IN ('uz','eu','us','global'))
        ) PARTITION BY LIST (residency_region);
        """
    )
    for region in ("uz", "eu", "us", "global"):
        op.execute(
            f"CREATE TABLE user_emails_{region} "
            f"PARTITION OF user_emails FOR VALUES IN ('{region}');"
        )

    op.execute(
        """
        -- Email uniqueness within (tenant, residency): app-layer enforces
        -- cross-region duplication during signup so a Uz-resident and an
        -- EU-resident with the same address are not silently the same person.
        CREATE UNIQUE INDEX uq_user_emails_unique
            ON user_emails (tenant_id, email, residency_region);
        CREATE UNIQUE INDEX uq_user_emails_one_primary
            ON user_emails (user_id, residency_region) WHERE is_primary;
        CREATE INDEX idx_user_emails_unverified
            ON user_emails (verification_sent_at)
            WHERE verified_at IS NULL;

        CREATE TRIGGER tg_user_emails_updated_at
            BEFORE UPDATE ON user_emails
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- user_phones ------------------------------------------------------
    op.execute(
        """
        CREATE TABLE user_phones (
            id                  uuid NOT NULL DEFAULT gen_uuid_v7(),
            user_id             uuid NOT NULL,
            residency_region    text NOT NULL,
            tenant_id           uuid NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            phone_e164          text NOT NULL,
            country_code        char(2),
            is_primary          boolean NOT NULL DEFAULT false,
            verified_at         timestamptz,
            verification_sent_at timestamptz,
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now(),

            PRIMARY KEY (id, residency_region),
            FOREIGN KEY (user_id, residency_region)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (residency_region IN ('uz','eu','us','global')),
            CHECK (phone_e164 ~ '^\\+[1-9][0-9]{6,14}$')
        ) PARTITION BY LIST (residency_region);
        """
    )
    for region in ("uz", "eu", "us", "global"):
        op.execute(
            f"CREATE TABLE user_phones_{region} "
            f"PARTITION OF user_phones FOR VALUES IN ('{region}');"
        )

    op.execute(
        """
        CREATE UNIQUE INDEX uq_user_phones_unique
            ON user_phones (tenant_id, phone_e164, residency_region);
        CREATE UNIQUE INDEX uq_user_phones_one_primary
            ON user_phones (user_id, residency_region) WHERE is_primary;

        CREATE TRIGGER tg_user_phones_updated_at
            BEFORE UPDATE ON user_phones
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- Seed common providers --------------------------------------------
    op.execute(
        """
        INSERT INTO oauth_providers (slug, display_name, kind, scopes, sort_order, is_enabled)
        VALUES
            ('google',   '{"en":"Google"}',    'oidc',     ARRAY['openid','email','profile'], 10, true),
            ('apple',    '{"en":"Apple"}',     'oidc',     ARRAY['name','email'],             20, true),
            ('telegram', '{"en":"Telegram"}',  'telegram', ARRAY[]::text[],                   30, true),
            ('facebook', '{"en":"Facebook"}',  'oauth2',   ARRAY['email','public_profile'],   40, false),
            ('email',    '{"en":"Email + password"}', 'custom', ARRAY[]::text[],              90, true),
            ('phone_otp','{"en":"Phone + OTP"}',     'custom', ARRAY[]::text[],               95, true),
            ('guest',    '{"en":"Guest"}',     'custom',   ARRAY[]::text[],                   99, true);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_phones CASCADE;")
    op.execute("DROP TABLE IF EXISTS user_emails CASCADE;")
    op.execute("DROP TABLE IF EXISTS user_identities CASCADE;")
    op.execute("DROP TABLE IF EXISTS oauth_provider_secrets CASCADE;")
    op.execute("DROP TABLE IF EXISTS oauth_providers CASCADE;")
