"""ticketing — ticket_types + tickets tables. SILK-0065.

Revision ID: 0102
Revises: 0101
Create Date: 2026-05-23
"""

from __future__ import annotations

from alembic import op

revision = "0102"
down_revision = "0101"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS ticket_types (
            id              uuid         PRIMARY KEY DEFAULT gen_uuid_v7(),
            heritage_pub_id text         NOT NULL,
            name            jsonb        NOT NULL DEFAULT '{}',
            kind            varchar(20)  NOT NULL DEFAULT 'standard',
            description_md  jsonb        NOT NULL DEFAULT '{}',
            price_usd       numeric(8,2) NOT NULL,
            valid_days      int          NOT NULL DEFAULT 1,
            max_per_booking int          NOT NULL DEFAULT 10,
            available_from  time,
            available_until time,
            is_active       boolean      NOT NULL DEFAULT true,
            sort_order      int          NOT NULL DEFAULT 0,
            created_at      timestamptz  NOT NULL DEFAULT now(),
            updated_at      timestamptz  NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TRIGGER tg_ticket_types_updated_at
            BEFORE UPDATE ON ticket_types
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at()
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id                  uuid         PRIMARY KEY DEFAULT gen_uuid_v7(),
            user_id             uuid         NOT NULL,
            residency_region    varchar(20)  NOT NULL DEFAULT 'global',
            ticket_type_id      uuid         NOT NULL REFERENCES ticket_types(id),
            status              varchar(20)  NOT NULL DEFAULT 'valid',
            qr_secret           varchar(64)  NOT NULL,
            visit_date          date,
            scanned_at          timestamptz,
            scanned_by_user_id  uuid,
            price_paid_usd      numeric(8,2),
            created_at          timestamptz  NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE UNIQUE INDEX ix_tickets_qr_secret ON tickets (qr_secret)
    """)

    op.execute("""
        CREATE INDEX ix_tickets_user ON tickets (user_id, created_at DESC)
    """)

    op.execute("""
        CREATE INDEX ix_tickets_heritage ON tickets (ticket_type_id, visit_date)
    """)

    # Seed demo ticket types for Samarkand heritage sites (no-op if table is empty
    # or heritage_objects does not exist yet in this environment).
    op.execute("""
        INSERT INTO ticket_types (heritage_pub_id, name, kind, description_md, price_usd, sort_order)
        SELECT
            ho.pub_id,
            '{"en": "Standard Entry", "uz": "Standart kirish", "ru": "Стандартный вход", "zh": "标准入场"}',
            'standard',
            '{"en": "General admission to the site.", "uz": "Ob''ektga umumiy kirish.", "ru": "Общий вход на объект.", "zh": "景点普通票。"}',
            10.00,
            1
        FROM heritage_objects ho
        WHERE ho.name->>'en' ILIKE '%registon%'
        LIMIT 1
        ON CONFLICT DO NOTHING
    """)

    op.execute("""
        INSERT INTO ticket_types (heritage_pub_id, name, kind, description_md, price_usd, sort_order)
        SELECT
            ho.pub_id,
            '{"en": "Fast Track Entry", "uz": "Tezkor kirish", "ru": "Быстрый вход", "zh": "快速通道入场"}',
            'fast_track',
            '{"en": "Skip the queue with priority access.", "uz": "Navbatsiz ustuvor kirish.", "ru": "Приоритетный вход без очереди.", "zh": "免排队优先入场。"}',
            25.00,
            2
        FROM heritage_objects ho
        WHERE ho.name->>'en' ILIKE '%registon%'
        LIMIT 1
        ON CONFLICT DO NOTHING
    """)

    op.execute("""
        INSERT INTO ticket_types (heritage_pub_id, name, kind, description_md, price_usd, sort_order)
        SELECT
            ho.pub_id,
            '{"en": "Standard Entry", "uz": "Standart kirish", "ru": "Стандартный вход", "zh": "标准入场"}',
            'standard',
            '{"en": "General admission to Shah-i-Zinda necropolis.", "uz": "Shohizinda majmuasiga kirish.", "ru": "Вход в некрополь Шахи-Зинда.", "zh": "沙赫静达陵墓群普通票。"}',
            8.00,
            1
        FROM heritage_objects ho
        WHERE ho.name->>'en' ILIKE '%shah%zinda%'
            OR ho.name->>'en' ILIKE '%shahi%zinda%'
        LIMIT 1
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tickets CASCADE")
    op.execute("DROP TABLE IF EXISTS ticket_types CASCADE")
