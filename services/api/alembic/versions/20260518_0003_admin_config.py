"""system_settings, feature_flags, controlled_vocabularies

Admin-managed runtime configuration per Project-Decisions §1 ("hech narsa
hardcode qilinmaydi"). These tables exist so the operator changes behaviour
*without* a redeploy.

- ``system_settings``: typed key/value scoped to (tenant_id, key) with audit history
- ``feature_flags``: typed rollout flags (boolean, percentage, allow-list)
- ``controlled_vocabularies`` + ``vocabulary_terms``: every place we'd otherwise
  use a Postgres ENUM is a row here so the admin can extend at runtime

Revision ID: 0003_admin_config
Revises: 0002_tenants_branding
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0003_admin_config"
down_revision: str | Sequence[str] | None = "0002_tenants_branding"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- system_settings ---------------------------------------------------
    op.execute(
        """
        CREATE TABLE system_settings (
            id           uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            tenant_id    uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            key          text NOT NULL,
            value        jsonb NOT NULL,
            value_type   text NOT NULL CHECK (value_type IN (
                'string','int','float','bool','json','duration','color','url'
            )),
            scope        text NOT NULL DEFAULT 'tenant'
                CHECK (scope IN ('tenant','global','user_overrideable')),
            description  text,
            is_secret    boolean NOT NULL DEFAULT false,
            requires_role text,
            created_at   timestamptz NOT NULL DEFAULT now(),
            updated_at   timestamptz NOT NULL DEFAULT now(),
            updated_by   uuid,
            UNIQUE (tenant_id, key)
        );

        CREATE INDEX idx_system_settings_tenant_key
            ON system_settings(tenant_id, key);

        DROP TRIGGER IF EXISTS tg_system_settings_updated_at ON system_settings;
        CREATE TRIGGER tg_system_settings_updated_at
            BEFORE UPDATE ON system_settings
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE system_settings IS
            'Admin-driven runtime settings (one row per (tenant, key)). Cached in '
            'Redis with event-driven invalidation per master architecture §16.';
        COMMENT ON COLUMN system_settings.is_secret IS
            'When true the API will redact this in read responses for non-admin actors.';
        COMMENT ON COLUMN system_settings.requires_role IS
            'Optional role name needed to read/write this setting. NULL = anyone with '
            'tenant_admin can edit.';
        """
    )

    # --- feature_flags -----------------------------------------------------
    op.execute(
        """
        CREATE TABLE feature_flags (
            id            uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            tenant_id     uuid REFERENCES tenants(id) ON DELETE CASCADE,
            flag_key      text NOT NULL,
            enabled       boolean NOT NULL DEFAULT false,
            rollout_kind  text NOT NULL DEFAULT 'boolean'
                CHECK (rollout_kind IN ('boolean','percentage','user_allowlist','user_denylist','jsonl_rules')),
            rollout_value jsonb NOT NULL DEFAULT '{}'::jsonb,
            description   text,
            owner         text,
            created_at    timestamptz NOT NULL DEFAULT now(),
            updated_at    timestamptz NOT NULL DEFAULT now(),
            UNIQUE (tenant_id, flag_key)
        );

        CREATE INDEX idx_feature_flags_enabled
            ON feature_flags(tenant_id, flag_key)
            WHERE enabled;

        DROP TRIGGER IF EXISTS tg_feature_flags_updated_at ON feature_flags;
        CREATE TRIGGER tg_feature_flags_updated_at
            BEFORE UPDATE ON feature_flags
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE feature_flags IS
            'Per-tenant feature flags. NULL tenant_id = platform default.';
        """
    )

    # --- controlled_vocabularies ------------------------------------------
    op.execute(
        """
        CREATE TABLE controlled_vocabularies (
            id             uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            slug           text NOT NULL UNIQUE,
            display_name   jsonb NOT NULL DEFAULT '{}'::jsonb,
            description    text,
            is_extensible  boolean NOT NULL DEFAULT true,
            is_hierarchical boolean NOT NULL DEFAULT false,
            created_at     timestamptz NOT NULL DEFAULT now(),
            updated_at     timestamptz NOT NULL DEFAULT now(),
            CHECK (slug ~ '^[a-z_][a-z0-9_]*$')
        );

        COMMENT ON TABLE controlled_vocabularies IS
            'Every place a Postgres ENUM would be tempted, use a vocabulary row '
            'instead. See Project-Decisions §1 (dynamic everything).';
        """
    )

    op.execute(
        """
        CREATE TABLE vocabulary_terms (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            vocabulary_id   uuid NOT NULL REFERENCES controlled_vocabularies(id) ON DELETE CASCADE,
            slug            text NOT NULL,
            display_name    jsonb NOT NULL DEFAULT '{}'::jsonb,
            description     jsonb NOT NULL DEFAULT '{}'::jsonb,
            parent_id       uuid REFERENCES vocabulary_terms(id) ON DELETE SET NULL,
            sort_order      int NOT NULL DEFAULT 0,
            is_active       boolean NOT NULL DEFAULT true,
            metadata        jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            UNIQUE (vocabulary_id, slug)
        );

        CREATE INDEX idx_vocabulary_terms_vocab_active
            ON vocabulary_terms(vocabulary_id, sort_order)
            WHERE is_active;

        CREATE INDEX idx_vocabulary_terms_parent
            ON vocabulary_terms(parent_id)
            WHERE parent_id IS NOT NULL;

        DROP TRIGGER IF EXISTS tg_vocabulary_terms_updated_at ON vocabulary_terms;
        CREATE TRIGGER tg_vocabulary_terms_updated_at
            BEFORE UPDATE ON vocabulary_terms
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- Seed core vocabularies --------------------------------------------
    # Heritage kinds, languages, residency regions — extendable by admin later.
    op.execute(
        """
        INSERT INTO controlled_vocabularies (slug, display_name, description, is_hierarchical)
        VALUES
            ('languages', '{"en":"Languages","uz":"Tillar"}', 'BCP-47 language tags', false),
            ('residency_regions', '{"en":"Residency regions","uz":"Hudud rezidentligi"}',
             'Data-residency buckets for PII partitioning', false),
            ('heritage_kinds', '{"en":"Heritage kinds","uz":"Meros turlari"}',
             'Polymorphic heritage discriminator', true),
            ('architectural_styles', '{"en":"Architectural styles","uz":"Me''morchilik uslublari"}',
             'For mosques, madrasas, palaces, etc.', false),
            ('moderation_actions', '{"en":"Moderation actions"}',
             'approve/reject/quarantine/escalate', false),
            ('ai_task_types', '{"en":"AI task types"}',
             'vision/tts/llm/translation', false),
            ('payment_providers', '{"en":"Payment providers"}',
             'stripe/payme/click/apple_iap/google_iap/paypal', false);

        INSERT INTO vocabulary_terms (vocabulary_id, slug, display_name, sort_order)
        SELECT v.id, x.slug, x.display_name::jsonb, x.sort_order
        FROM controlled_vocabularies v
        CROSS JOIN LATERAL (VALUES
            ('uz', '{"en":"Uzbek","uz":"O''zbekcha"}', 10),
            ('en', '{"en":"English","uz":"Inglizcha"}', 20),
            ('ru', '{"en":"Russian","uz":"Ruscha"}', 30),
            ('zh', '{"en":"Chinese","uz":"Xitoycha"}', 40)
        ) AS x(slug, display_name, sort_order)
        WHERE v.slug = 'languages';

        INSERT INTO vocabulary_terms (vocabulary_id, slug, display_name, sort_order)
        SELECT v.id, x.slug, x.display_name::jsonb, x.sort_order
        FROM controlled_vocabularies v
        CROSS JOIN LATERAL (VALUES
            ('uz', '{"en":"Uzbekistan","uz":"O''zbekiston"}', 10),
            ('eu', '{"en":"European Union","uz":"Yevropa Ittifoqi"}', 20),
            ('us', '{"en":"United States"}', 30),
            ('global', '{"en":"Global (default)","uz":"Global"}', 99)
        ) AS x(slug, display_name, sort_order)
        WHERE v.slug = 'residency_regions';

        INSERT INTO vocabulary_terms (vocabulary_id, slug, display_name, sort_order)
        SELECT v.id, x.slug, x.display_name::jsonb, x.sort_order
        FROM controlled_vocabularies v
        CROSS JOIN LATERAL (VALUES
            ('monument',     '{"en":"Monument","uz":"Yodgorlik"}', 10),
            ('mosque',       '{"en":"Mosque","uz":"Masjid"}', 20),
            ('madrasa',      '{"en":"Madrasa","uz":"Madrasa"}', 30),
            ('mausoleum',    '{"en":"Mausoleum","uz":"Maqbara"}', 40),
            ('caravanserai', '{"en":"Caravanserai","uz":"Karvonsaroy"}', 50),
            ('archaeological_site', '{"en":"Archaeological site","uz":"Arxeologik yodgorlik"}', 60),
            ('museum',       '{"en":"Museum","uz":"Muzey"}', 70),
            ('palace',       '{"en":"Palace","uz":"Saroy"}', 80),
            ('intangible_practice', '{"en":"Intangible practice","uz":"Nomoddiy meros"}', 90)
        ) AS x(slug, display_name, sort_order)
        WHERE v.slug = 'heritage_kinds';
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS vocabulary_terms CASCADE;")
    op.execute("DROP TABLE IF EXISTS controlled_vocabularies CASCADE;")
    op.execute("DROP TABLE IF EXISTS feature_flags CASCADE;")
    op.execute("DROP TABLE IF EXISTS system_settings CASCADE;")
