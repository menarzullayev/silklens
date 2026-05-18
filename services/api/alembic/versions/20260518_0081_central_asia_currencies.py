"""Central Asia pricing zone + USD price points for premium plans

FAZA 5 (TURBO) — Wave-6 Agent A. Patch over the 0050 catalog:

- Confirm KZT, TJS, TMT, KGS currencies (already seeded in 0050; idempotent).
- Add ``central_asia`` pricing zone covering [UZ, KZ, KG, TJ, TM] with PPP
  index 0.42, default currency USD (Central Asian local-rail providers are not
  online yet — users pay in USD against MockProvider until provider regions
  land).
- Add ``prices`` rows for SilkLens Premium monthly @ $1.99 USD and yearly @
  $19.99 USD, keyed on the freshly minted central_asia zone.

Idempotent: ON CONFLICT DO NOTHING on the pricing_zones slug and on the
prices PK.

Revision ID: 0081_central_asia_currencies
Revises: 0080_central_asia_seed
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0081_central_asia_currencies"
down_revision: str | Sequence[str] | None = "0080_central_asia_seed"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- 1. Currencies — re-assert KZT/TJS/TMT/KGS (idempotent) -----------
    op.execute(
        """
        INSERT INTO currencies (code, name, symbol, decimal_places) VALUES
            ('KZT', '{"en":"Kazakhstani Tenge","ru":"Тенге"}'::jsonb,      '₸',  2),
            ('TJS', '{"en":"Tajikistani Somoni","ru":"Сомони"}'::jsonb,    'SM', 2),
            ('TMT', '{"en":"Turkmenistan Manat","ru":"Манат"}'::jsonb,     'T',  2),
            ('KGS', '{"en":"Kyrgyzstani Som","ru":"Сом"}'::jsonb,          'с',  2)
        ON CONFLICT (code) DO NOTHING;
        """
    )

    # --- 2. central_asia pricing zone -------------------------------------
    op.execute(
        """
        INSERT INTO pricing_zones
            (slug, name, country_codes, default_currency, purchasing_power_index)
        VALUES
            ('central_asia',
             '{"en":"Central Asia","ru":"Центральная Азия","uz":"Markaziy Osiyo"}'::jsonb,
             ARRAY['UZ','KZ','KG','TJ','TM']::char(2)[],
             'USD',
             0.42)
        ON CONFLICT (slug) DO NOTHING;
        """
    )

    # --- 3. product_plans — ensure premium_monthly + premium_yearly exist -
    # Migration 0050 seeds the parent products only; plans land here so the
    # central_asia prices have something to attach to. The plan slugs follow
    # the canonical naming used by app code: ``premium_monthly`` and
    # ``premium_yearly`` (sub-resources of the silklens_premium_* products).
    op.execute(
        """
        WITH t AS (
            SELECT id FROM tenants
            WHERE id = '00000000-0000-0000-0000-000000000001'::uuid
            LIMIT 1
        )
        INSERT INTO product_plans
            (tenant_id, product_id, slug, name, billing_period, is_default, sort_order)
        SELECT t.id, p.id, plan.slug, plan.name, plan.period, plan.is_default, plan.sort_order
        FROM t
        JOIN products p ON p.tenant_id = t.id
        CROSS JOIN LATERAL (VALUES
            ('silklens_premium_monthly', 'premium_monthly',
                '{"en":"Premium (monthly)"}'::jsonb, 'monthly', true, 10),
            ('silklens_premium_yearly', 'premium_yearly',
                '{"en":"Premium (yearly)"}'::jsonb, 'yearly', true, 20)
        ) AS plan(product_slug, slug, name, period, is_default, sort_order)
        WHERE p.slug = plan.product_slug
        ON CONFLICT (product_id, slug) DO NOTHING;
        """
    )

    # --- 4. Prices for premium_monthly @ $1.99 USD in central_asia --------
    op.execute(
        """
        INSERT INTO prices
            (plan_id, pricing_zone_id, currency, amount, is_active)
        SELECT pp.id, pz.id, 'USD', 1.9900, true
        FROM product_plans pp
        JOIN pricing_zones pz ON pz.slug = 'central_asia'
        WHERE pp.slug = 'premium_monthly'
        ON CONFLICT (plan_id, pricing_zone_id, currency, effective_from) DO NOTHING;
        """
    )

    # --- 5. Prices for premium_yearly @ $19.99 USD in central_asia --------
    op.execute(
        """
        INSERT INTO prices
            (plan_id, pricing_zone_id, currency, amount, is_active)
        SELECT pp.id, pz.id, 'USD', 19.9900, true
        FROM product_plans pp
        JOIN pricing_zones pz ON pz.slug = 'central_asia'
        WHERE pp.slug = 'premium_yearly'
        ON CONFLICT (plan_id, pricing_zone_id, currency, effective_from) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM prices
        WHERE pricing_zone_id IN (
            SELECT id FROM pricing_zones WHERE slug = 'central_asia'
        );
        """
    )
    op.execute(
        """
        DELETE FROM product_plans
        WHERE slug IN ('premium_monthly','premium_yearly');
        """
    )
    op.execute("DELETE FROM pricing_zones WHERE slug = 'central_asia';")
