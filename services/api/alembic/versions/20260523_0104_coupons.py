"""coupons + coupon_redemptions. SILK-0089.

Revision ID: 0104
Revises: 0103
Create Date: 2026-05-23
"""

from __future__ import annotations

from alembic import op

revision = "0104"
down_revision = "0103"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS coupons (
            id              uuid         PRIMARY KEY DEFAULT app.uuidv7(),
            code            varchar(50)  NOT NULL UNIQUE,
            kind            varchar(20)  NOT NULL DEFAULT 'percent',
            discount_value  numeric(8,2) NOT NULL,
            max_uses        int,
            uses_count      int          NOT NULL DEFAULT 0,
            min_order_usd   numeric(8,2) DEFAULT 0,
            valid_from      timestamptz  NOT NULL DEFAULT now(),
            valid_until     timestamptz,
            applicable_plans text[]      NOT NULL DEFAULT '{}',
            is_active       boolean      NOT NULL DEFAULT true,
            description     varchar(200),
            created_at      timestamptz  NOT NULL DEFAULT now(),
            updated_at      timestamptz  NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TRIGGER tg_coupons_updated_at
            BEFORE UPDATE ON coupons
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at()
    """)

    op.execute("""
        CREATE INDEX ix_coupons_code ON coupons (code) WHERE is_active = true
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS coupon_redemptions (
            id                   uuid         PRIMARY KEY DEFAULT app.uuidv7(),
            coupon_id            uuid         NOT NULL REFERENCES coupons(id) ON DELETE RESTRICT,
            user_id              uuid         NOT NULL,
            subscription_id      uuid,
            discount_applied_usd numeric(8,2),
            redeemed_at          timestamptz  NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE UNIQUE INDEX ix_coupon_redemptions_user
            ON coupon_redemptions (coupon_id, user_id)
    """)

    op.execute("""
        CREATE INDEX ix_coupon_redemptions_coupon
            ON coupon_redemptions (coupon_id, redeemed_at DESC)
    """)

    op.execute("""
        INSERT INTO coupons (code, kind, discount_value, max_uses, description)
        VALUES
            ('SILKROAD2026', 'percent', 20.0, 1000, '20% off for Silk Road explorers'),
            ('WELCOME10',    'percent', 10.0, NULL,  '10% welcome discount'),
            ('FLATFIVE',     'fixed',    5.0,  500,  '$5 off first purchase')
        ON CONFLICT (code) DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS coupon_redemptions CASCADE")
    op.execute("DROP TABLE IF EXISTS coupons CASCADE")
