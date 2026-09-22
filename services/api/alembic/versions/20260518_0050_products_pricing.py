"""products + plans + features + pricing zones + currencies + prices

Per Agent 6 monetization architecture §3.2-§3.3, this migration lands the
catalog backbone of the billing system:

  currencies              — ISO 4217 catalog. Seeded with the operational set
                            (CIS + EU + NA + APAC majors).
  exchange_rate_snapshots — point-in-time rates captured at charge for FX
                            stability (Agent 6 §3 risk #1: never recompute
                            settled charges in a wobbly rate).
  products                — top-level SKU kinds (subscription / one_time /
                            credits / marketplace_item).
  product_plans           — billing variants of a product (monthly / yearly).
  feature_keys            — controlled vocabulary of entitlement primitives.
  plan_features           — admin entitlement matrix (plan x feature_key →
                            enabled + limit_value + soft_limit).
  pricing_zones           — regional PPP groupings (cis / eu / na / sea …).
  prices                  — temporal price points keyed on
                            (plan, zone, currency, effective_from).

Money columns: ``numeric(20, 4)``. Currency: ``char(3)`` ISO 4217.
Every monetizable table carries ``tenant_id`` for the multi-tenant RLS
isolation that lands in 0054.

Revision ID: 0050_products_pricing
Revises: 0043_moderation_pipeline
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0050_products_pricing"
down_revision: str | Sequence[str] | None = "0043_moderation_pipeline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- currencies (ISO 4217 catalog) ------------------------------------
    op.execute(
        """
        CREATE TABLE currencies (
            code            char(3) PRIMARY KEY,
            name            jsonb NOT NULL DEFAULT '{}'::jsonb,
            symbol          text NOT NULL,
            decimal_places  smallint NOT NULL DEFAULT 2
                CHECK (decimal_places BETWEEN 0 AND 4),
            is_active       boolean NOT NULL DEFAULT true,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            CHECK (code ~ '^[A-Z]{3}$')
        );

        CREATE INDEX idx_currencies_active
            ON currencies (code) WHERE is_active;

        CREATE TRIGGER tg_currencies_updated_at
            BEFORE UPDATE ON currencies
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE currencies IS
            'ISO 4217 catalog. decimal_places used for amount→minor-unit '
            'conversion at provider boundaries (Stripe wants cents, Payme wants tiyin).';
        """
    )

    op.execute(
        """
        INSERT INTO currencies (code, name, symbol, decimal_places) VALUES
            ('USD', '{"en":"US Dollar","ru":"Доллар США"}'::jsonb,        '$',   2),
            ('EUR', '{"en":"Euro","ru":"Евро"}'::jsonb,                    '€',   2),
            ('GBP', '{"en":"British Pound","ru":"Фунт стерлингов"}'::jsonb,'£',   2),
            ('RUB', '{"en":"Russian Ruble","ru":"Российский рубль"}'::jsonb,'₽',  2),
            ('CNY', '{"en":"Chinese Yuan","ru":"Юань"}'::jsonb,            '¥',   2),
            ('JPY', '{"en":"Japanese Yen","ru":"Иена"}'::jsonb,            '¥',   0),
            ('KRW', '{"en":"South Korean Won","ru":"Вона"}'::jsonb,        '₩',   0),
            ('TRY', '{"en":"Turkish Lira","ru":"Турецкая лира"}'::jsonb,   '₺',   2),
            ('INR', '{"en":"Indian Rupee","ru":"Индийская рупия"}'::jsonb, '₹',   2),
            ('AED', '{"en":"UAE Dirham","ru":"Дирхам ОАЭ"}'::jsonb,        'د.إ', 2),
            ('UZS', '{"en":"Uzbek Sum","ru":"Сум","uz":"Сўм"}'::jsonb,     'soʻm',2),
            ('KZT', '{"en":"Kazakhstani Tenge","ru":"Тенге"}'::jsonb,      '₸',   2),
            ('KGS', '{"en":"Kyrgyzstani Som","ru":"Сом"}'::jsonb,          'с',   2),
            ('TJS', '{"en":"Tajikistani Somoni","ru":"Сомони"}'::jsonb,    'SM',  2),
            ('TMT', '{"en":"Turkmenistan Manat","ru":"Манат"}'::jsonb,     'T',   2);
        """
    )

    # --- exchange_rate_snapshots (immutable FX records per charge) --------
    # Per Agent 6 §3 risk #1: rates are CAPTURED at the moment of charge and
    # never recomputed. PK includes captured_at so multiple snapshots per
    # (from, to) pair across time are first-class.
    op.execute(
        """
        CREATE TABLE exchange_rate_snapshots (
            from_currency   char(3) NOT NULL REFERENCES currencies(code) ON DELETE RESTRICT,
            to_currency     char(3) NOT NULL REFERENCES currencies(code) ON DELETE RESTRICT,
            rate            numeric(20, 10) NOT NULL CHECK (rate > 0),
            source          text NOT NULL,
            captured_at     timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (from_currency, to_currency, captured_at),
            CHECK (from_currency <> to_currency)
        );

        CREATE INDEX idx_xrate_lookup
            ON exchange_rate_snapshots (from_currency, to_currency, captured_at DESC);

        COMMENT ON TABLE exchange_rate_snapshots IS
            'Immutable FX captures. Settled payments reference the row used at '
            'charge time so refunds and accounting use the SAME rate (Agent 6 §3 risk #1).';
        """
    )

    # --- products (top-level SKU kinds) -----------------------------------
    op.execute(
        """
        CREATE TABLE products (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            tenant_id       uuid NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            slug            text NOT NULL,
            name            jsonb NOT NULL DEFAULT '{}'::jsonb,
            description     jsonb NOT NULL DEFAULT '{}'::jsonb,
            kind            text NOT NULL CHECK (kind IN (
                'subscription','one_time','credits','marketplace_item'
            )),
            is_active       boolean NOT NULL DEFAULT true,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            UNIQUE (tenant_id, slug),
            CHECK (slug ~ '^[a-z0-9][a-z0-9_-]*$')
        );

        CREATE INDEX idx_products_tenant_active
            ON products (tenant_id) WHERE is_active;
        CREATE INDEX idx_products_kind
            ON products (kind) WHERE is_active;

        CREATE TRIGGER tg_products_updated_at
            BEFORE UPDATE ON products
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE products IS
            'Top-level SKU. kind discriminates lifecycle: subscription/one_time/credits/marketplace_item.';
        """
    )

    # --- product_plans (billing-variants of a product) --------------------
    op.execute(
        """
        CREATE TABLE product_plans (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            tenant_id       uuid NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            product_id      uuid NOT NULL REFERENCES products(id) ON DELETE CASCADE,
            slug            text NOT NULL,
            name            jsonb NOT NULL DEFAULT '{}'::jsonb,
            billing_period  text NOT NULL CHECK (billing_period IN (
                'monthly','quarterly','yearly','lifetime','one_time'
            )),
            trial_days      int NOT NULL DEFAULT 0 CHECK (trial_days >= 0),
            is_default      boolean NOT NULL DEFAULT false,
            sort_order      int NOT NULL DEFAULT 0,
            is_active       boolean NOT NULL DEFAULT true,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            UNIQUE (product_id, slug),
            CHECK (slug ~ '^[a-z0-9][a-z0-9_-]*$')
        );

        -- At most one default plan per product.
        CREATE UNIQUE INDEX uq_product_plans_default
            ON product_plans (product_id) WHERE is_default;
        CREATE INDEX idx_product_plans_product
            ON product_plans (product_id, sort_order) WHERE is_active;

        CREATE TRIGGER tg_product_plans_updated_at
            BEFORE UPDATE ON product_plans
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- feature_keys (entitlement vocabulary) ----------------------------
    op.execute(
        """
        CREATE TABLE feature_keys (
            slug            text PRIMARY KEY,
            name            jsonb NOT NULL DEFAULT '{}'::jsonb,
            description     jsonb NOT NULL DEFAULT '{}'::jsonb,
            kind            text NOT NULL CHECK (kind IN ('boolean','quota','threshold')),
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            CHECK (slug ~ '^[a-z0-9][a-z0-9_]*$')
        );

        CREATE TRIGGER tg_feature_keys_updated_at
            BEFORE UPDATE ON feature_keys
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE feature_keys IS
            'Controlled vocabulary of entitlement primitives. boolean → on/off; '
            'quota → numeric usage cap; threshold → numeric soft-limit before warning.';
        """
    )

    op.execute(
        """
        INSERT INTO feature_keys (slug, name, kind) VALUES
            ('ai_chat_unlimited',          '{"en":"Unlimited AI chat"}'::jsonb,         'boolean'),
            ('audio_guides_unlimited',     '{"en":"Unlimited audio guides"}'::jsonb,    'boolean'),
            ('offline_bundles',            '{"en":"Offline city bundles"}'::jsonb,      'quota'),
            ('ar_overlay',                 '{"en":"AR overlay"}'::jsonb,                'boolean'),
            ('route_planner',              '{"en":"Route planner"}'::jsonb,             'boolean'),
            ('ad_free',                    '{"en":"Ad-free experience"}'::jsonb,        'boolean'),
            ('premium_voice',              '{"en":"Premium TTS voices"}'::jsonb,        'boolean'),
            ('b2b_featured_listing_slots', '{"en":"B2B featured listing slots"}'::jsonb,'quota'),
            ('api_calls_per_day',          '{"en":"Enterprise API calls per day"}'::jsonb,'quota');
        """
    )

    # --- plan_features (admin entitlement matrix) -------------------------
    op.execute(
        """
        CREATE TABLE plan_features (
            plan_id         uuid NOT NULL REFERENCES product_plans(id) ON DELETE CASCADE,
            feature_key     text NOT NULL REFERENCES feature_keys(slug) ON DELETE RESTRICT,
            enabled         boolean NOT NULL DEFAULT true,
            limit_value     bigint,
            soft_limit      bigint,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (plan_id, feature_key),
            CHECK (limit_value IS NULL OR limit_value >= 0),
            CHECK (soft_limit IS NULL OR soft_limit >= 0),
            CHECK (soft_limit IS NULL OR limit_value IS NULL OR soft_limit <= limit_value)
        );

        CREATE INDEX idx_plan_features_feature
            ON plan_features (feature_key) WHERE enabled;

        CREATE TRIGGER tg_plan_features_updated_at
            BEFORE UPDATE ON plan_features
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE plan_features IS
            'Plan × feature entitlement matrix. enabled=false explicitly disables a '
            'feature even if a future bundling enables it elsewhere.';
        """
    )

    # --- products / plans seed -------------------------------------------
    # Seeded onto the default tenant (well-known UUID from migration 0002).
    op.execute(
        """
        WITH t AS (
            SELECT id FROM tenants
            WHERE id = '00000000-0000-0000-0000-000000000001'::uuid
            LIMIT 1
        )
        INSERT INTO products (tenant_id, slug, name, kind)
        SELECT t.id, p.slug, p.name, p.kind FROM t, (VALUES
            ('silklens_premium_monthly',
                '{"en":"SilkLens Premium (monthly)"}'::jsonb, 'subscription'),
            ('silklens_premium_yearly',
                '{"en":"SilkLens Premium (yearly)"}'::jsonb, 'subscription'),
            ('b2b_listing_monthly',
                '{"en":"B2B Listing (monthly)"}'::jsonb, 'subscription'),
            ('enterprise_api',
                '{"en":"Enterprise API"}'::jsonb, 'subscription'),
            ('ai_credit_pack_10k',
                '{"en":"AI Credit Pack — 10k"}'::jsonb, 'credits')
        ) AS p(slug, name, kind);
        """
    )

    # --- pricing_zones (regional PPP groupings) ---------------------------
    op.execute(
        """
        CREATE TABLE pricing_zones (
            id                      uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            slug                    text NOT NULL UNIQUE,
            name                    jsonb NOT NULL DEFAULT '{}'::jsonb,
            country_codes           char(2)[] NOT NULL DEFAULT ARRAY[]::char(2)[],
            default_currency        char(3) NOT NULL REFERENCES currencies(code) ON DELETE RESTRICT,
            purchasing_power_index  numeric(4, 2) NOT NULL DEFAULT 1.00
                CHECK (purchasing_power_index > 0),
            is_active               boolean NOT NULL DEFAULT true,
            created_at              timestamptz NOT NULL DEFAULT now(),
            updated_at              timestamptz NOT NULL DEFAULT now(),
            CHECK (slug ~ '^[a-z][a-z0-9_]*$')
        );

        CREATE INDEX idx_pricing_zones_country_codes
            ON pricing_zones USING GIN (country_codes);

        CREATE TRIGGER tg_pricing_zones_updated_at
            BEFORE UPDATE ON pricing_zones
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE pricing_zones IS
            'Regional groupings for PPP-adjusted pricing. country_codes is the '
            'enrollment list; default_currency drives the checkout currency '
            'when no explicit user preference exists (Agent 6 §8.1).';
        """
    )

    op.execute(
        """
        INSERT INTO pricing_zones (slug, name, country_codes, default_currency, purchasing_power_index) VALUES
            ('cis',     '{"en":"CIS"}'::jsonb,
                ARRAY['UZ','KZ','KG','TJ','TM','RU','BY','AM','AZ']::char(2)[],
                'USD', 0.35),
            ('eu',      '{"en":"European Union"}'::jsonb,
                ARRAY['DE','FR','IT','ES','NL','PL','PT','SE','DK','FI','IE','BE','AT']::char(2)[],
                'EUR', 1.00),
            ('na',      '{"en":"North America"}'::jsonb,
                ARRAY['US','CA','MX']::char(2)[],
                'USD', 1.10),
            ('sea',     '{"en":"South-East Asia"}'::jsonb,
                ARRAY['ID','VN','TH','MY','PH','SG']::char(2)[],
                'USD', 0.45),
            ('latam',   '{"en":"Latin America"}'::jsonb,
                ARRAY['BR','AR','CO','CL','PE']::char(2)[],
                'USD', 0.40),
            ('mena',    '{"en":"Middle East & North Africa"}'::jsonb,
                ARRAY['AE','SA','EG','MA','TR','QA']::char(2)[],
                'USD', 0.55),
            ('oceania', '{"en":"Oceania"}'::jsonb,
                ARRAY['AU','NZ']::char(2)[],
                'USD', 1.15);
        """
    )

    # --- prices (temporal price points) -----------------------------------
    # The natural identity is (plan, zone, currency, effective_from). Each
    # row supersedes the previous when effective_until is set. is_active is
    # denormalized for cheap point-in-time lookups.
    op.execute(
        """
        CREATE TABLE prices (
            plan_id             uuid NOT NULL REFERENCES product_plans(id) ON DELETE CASCADE,
            pricing_zone_id     uuid NOT NULL REFERENCES pricing_zones(id) ON DELETE RESTRICT,
            currency            char(3) NOT NULL REFERENCES currencies(code) ON DELETE RESTRICT,
            effective_from      timestamptz NOT NULL DEFAULT now(),
            amount              numeric(20, 4) NOT NULL CHECK (amount >= 0),
            effective_until     timestamptz,
            is_active           boolean NOT NULL DEFAULT true,
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (plan_id, pricing_zone_id, currency, effective_from),
            CHECK (effective_until IS NULL OR effective_until > effective_from)
        );

        CREATE INDEX idx_prices_active_lookup
            ON prices (plan_id, pricing_zone_id) WHERE is_active;
        CREATE INDEX idx_prices_zone_currency
            ON prices (pricing_zone_id, currency) WHERE is_active;

        CREATE TRIGGER tg_prices_updated_at
            BEFORE UPDATE ON prices
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE prices IS
            'Time-windowed price points. Resolution order at checkout (Agent 6 §8.1): '
            '(plan_id, pricing_zone_id, currency, now()). New rows never edit; previous '
            'rows get effective_until set.';
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS prices CASCADE;")
    op.execute("DROP TABLE IF EXISTS pricing_zones CASCADE;")
    op.execute("DROP TABLE IF EXISTS plan_features CASCADE;")
    op.execute("DROP TABLE IF EXISTS feature_keys CASCADE;")
    op.execute("DROP TABLE IF EXISTS product_plans CASCADE;")
    op.execute("DROP TABLE IF EXISTS products CASCADE;")
    op.execute("DROP TABLE IF EXISTS exchange_rate_snapshots CASCADE;")
    op.execute("DROP TABLE IF EXISTS currencies CASCADE;")
