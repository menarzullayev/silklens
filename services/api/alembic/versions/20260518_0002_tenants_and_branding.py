"""tenants and per-tenant branding (white-label foundation)

Per Project-Decisions §50 and Agent 6 architecture: every monetizable / brandable
row carries ``tenant_id``. A default tenant is seeded so single-tenant deployments
just-work without any setup. Branding is split into its own table because it
changes frequently and is not load-bearing for FK integrity.

Revision ID: 0002_tenants_branding
Revises: 0001_extensions_uuidv7
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0002_tenants_branding"
down_revision: str | Sequence[str] | None = "0001_extensions_uuidv7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    # --- Trigger fn for updated_at, used here and re-used by everything else ---
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app.tg_set_updated_at() RETURNS trigger AS $$
        BEGIN
            NEW.updated_at := now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    # --- tenants -----------------------------------------------------------
    op.execute(
        """
        CREATE TABLE tenants (
            id          uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            slug        citext NOT NULL UNIQUE,
            display_name jsonb NOT NULL DEFAULT '{}'::jsonb,
            status      text NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'suspended', 'archived')),
            plan_tier   text NOT NULL DEFAULT 'free',
            owner_user_id uuid,
            parent_tenant_id uuid REFERENCES tenants(id) ON DELETE SET NULL,
            metadata    jsonb NOT NULL DEFAULT '{}'::jsonb,

            created_at  timestamptz NOT NULL DEFAULT now(),
            updated_at  timestamptz NOT NULL DEFAULT now(),
            deleted_at  timestamptz,
            CHECK (length(slug) BETWEEN 2 AND 64),
            CHECK (slug ~ '^[a-z0-9]([a-z0-9-]*[a-z0-9])?$')
        );

        COMMENT ON TABLE tenants IS
            'White-label tenants. Default tenant id 00000000-0000-0000-0000-000000000001 '
            'is the catch-all for single-tenant deployments.';
        COMMENT ON COLUMN tenants.display_name IS
            'BCP-47 keyed JSONB, e.g. {"uz":"SilkLens","en":"SilkLens"}. '
            'See docs/architecture/00-MASTER-ARCHITECTURE.md §7.';
        COMMENT ON COLUMN tenants.parent_tenant_id IS
            'Reseller hierarchy: a B2B partner may own sub-tenants. Per Agent 6 §4.';
        """
    )

    op.execute(
        "CREATE INDEX idx_tenants_status_not_deleted ON tenants(status) "
        "WHERE deleted_at IS NULL;"
    )
    op.execute(
        "CREATE INDEX idx_tenants_parent ON tenants(parent_tenant_id) "
        "WHERE parent_tenant_id IS NOT NULL;"
    )
    op.execute(
        """
        DROP TRIGGER IF EXISTS tg_tenants_updated_at ON tenants;
        CREATE TRIGGER tg_tenants_updated_at
            BEFORE UPDATE ON tenants
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- tenant_branding ---------------------------------------------------
    # One row per tenant. Versioned via a separate revision history table
    # (see migration 0008 audit_log). Per Project-Decisions §50.
    op.execute(
        """
        CREATE TABLE tenant_branding (
            tenant_id      uuid PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,

            app_name       jsonb NOT NULL DEFAULT '{}'::jsonb,
            logo_url       text,
            logo_dark_url  text,
            primary_color  text CHECK (primary_color IS NULL OR primary_color ~ '^#[0-9A-Fa-f]{6}$'),
            accent_color   text CHECK (accent_color  IS NULL OR accent_color  ~ '^#[0-9A-Fa-f]{6}$'),
            splash_url     text,
            font_family    text,
            theme_mode_default text DEFAULT 'system'
                CHECK (theme_mode_default IN ('light','dark','system','national','high_contrast')),
            extra          jsonb NOT NULL DEFAULT '{}'::jsonb,

            created_at     timestamptz NOT NULL DEFAULT now(),
            updated_at     timestamptz NOT NULL DEFAULT now()
        );

        COMMENT ON TABLE tenant_branding IS
            'Dynamic branding per Project-Decisions §50. Read on app startup '
            'via the public branding endpoint.';
        """
    )
    op.execute(
        """
        DROP TRIGGER IF EXISTS tg_tenant_branding_updated_at ON tenant_branding;
        CREATE TRIGGER tg_tenant_branding_updated_at
            BEFORE UPDATE ON tenant_branding
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- tenant_domains ----------------------------------------------------
    # Resellers map their own domain to a tenant (admin.toshkent.uz → tenant X)
    op.execute(
        """
        CREATE TABLE tenant_domains (
            id          uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            tenant_id   uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            domain      citext NOT NULL UNIQUE,
            is_primary  boolean NOT NULL DEFAULT false,
            verified_at timestamptz,
            created_at  timestamptz NOT NULL DEFAULT now()
        );

        CREATE UNIQUE INDEX uq_tenant_domains_primary
            ON tenant_domains(tenant_id)
            WHERE is_primary;

        COMMENT ON TABLE tenant_domains IS
            'Custom domains per tenant. Verified via DNS TXT challenge.';
        """
    )

    # --- Seed the default tenant ------------------------------------------
    op.execute(
        f"""
        INSERT INTO tenants (id, slug, display_name, status, plan_tier)
        VALUES (
            '{DEFAULT_TENANT_ID}',
            'default',
            '{{"uz":"SilkLens","en":"SilkLens","ru":"SilkLens","zh":"SilkLens"}}',
            'active',
            'internal'
        );

        INSERT INTO tenant_branding (tenant_id, app_name, primary_color, theme_mode_default)
        VALUES (
            '{DEFAULT_TENANT_ID}',
            '{{"uz":"SilkLens","en":"SilkLens","ru":"SilkLens","zh":"SilkLens"}}',
            '#1A3A5C',
            'system'
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tenant_domains CASCADE;")
    op.execute("DROP TABLE IF EXISTS tenant_branding CASCADE;")
    op.execute("DROP TABLE IF EXISTS tenants CASCADE;")
    # tg_set_updated_at is left in place — many tables depend on it.
    # Migration 0001 owns the schema-level setup; this migration owns its tables only.
