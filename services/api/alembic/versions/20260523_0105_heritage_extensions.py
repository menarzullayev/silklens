"""heritage_extension_tables — people, materials, localized_strings. SILK-0092.

Partial implementation of architecture 01-core-domain.md extension tables.

Revision ID: 0105
Revises: 0104
Create Date: 2026-05-23
"""

from __future__ import annotations

from alembic import op

revision = "0105"
down_revision = "0104"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # People associated with heritage (architects, patrons, rulers)
    op.execute("""
        CREATE TABLE IF NOT EXISTS people (
            id           uuid        PRIMARY KEY DEFAULT gen_uuid_v7(),
            full_name    jsonb       NOT NULL DEFAULT '{}',
            birth_year   int,
            death_year   int,
            nationality  varchar(50),
            role_kind    varchar(30) NOT NULL DEFAULT 'person',
            bio_md       jsonb       NOT NULL DEFAULT '{}',
            wikidata_qid varchar(20),
            is_active    boolean     NOT NULL DEFAULT true,
            created_at   timestamptz NOT NULL DEFAULT now(),
            updated_at   timestamptz NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TRIGGER tg_people_updated_at
            BEFORE UPDATE ON people
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at()
    """)

    op.execute("""
        CREATE INDEX ix_people_wikidata ON people (wikidata_qid)
            WHERE wikidata_qid IS NOT NULL
    """)

    # M:N heritage <-> people with role
    op.execute("""
        CREATE TABLE IF NOT EXISTS heritage_people_roles (
            id           uuid        PRIMARY KEY DEFAULT gen_uuid_v7(),
            heritage_id  uuid        NOT NULL,
            person_id    uuid        NOT NULL REFERENCES people(id) ON DELETE RESTRICT,
            role         varchar(50) NOT NULL DEFAULT 'associated',
            period_start int,
            period_end   int,
            notes        text,
            created_at   timestamptz NOT NULL DEFAULT now(),
            UNIQUE (heritage_id, person_id, role)
        )
    """)

    op.execute("""
        CREATE INDEX ix_heritage_people_heritage
            ON heritage_people_roles (heritage_id)
    """)

    op.execute("""
        CREATE INDEX ix_heritage_people_person
            ON heritage_people_roles (person_id)
    """)

    # Building materials controlled vocabulary
    op.execute("""
        CREATE TABLE IF NOT EXISTS materials (
            id             uuid        PRIMARY KEY DEFAULT gen_uuid_v7(),
            name           jsonb       NOT NULL DEFAULT '{}',
            kind           varchar(30) NOT NULL DEFAULT 'stone',
            description_md jsonb       NOT NULL DEFAULT '{}',
            is_active      boolean     NOT NULL DEFAULT true,
            sort_order     int         NOT NULL DEFAULT 0,
            created_at     timestamptz NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE INDEX ix_materials_kind ON materials (kind, sort_order)
            WHERE is_active = true
    """)

    op.execute("""
        INSERT INTO materials (name, kind, sort_order) VALUES
            ('{"en": "Brick", "uz": "G''isht", "ru": "Кирпич"}',                      'fired_clay', 1),
            ('{"en": "Marble", "uz": "Marmar", "ru": "Мрамор"}',                      'stone',      2),
            ('{"en": "Glazed Tile", "uz": "Koshin", "ru": "Глазурованная плитка"}',   'ceramic',    3),
            ('{"en": "Wood", "uz": "Yog''och", "ru": "Дерево"}',                      'timber',     4),
            ('{"en": "Adobe/Mud brick", "uz": "Guvalach", "ru": "Саман"}',            'earthen',    5)
        ON CONFLICT DO NOTHING
    """)

    # Localized strings — central translation table for arbitrary entity fields
    op.execute("""
        CREATE TABLE IF NOT EXISTS localized_strings (
            id              uuid         PRIMARY KEY DEFAULT gen_uuid_v7(),
            entity_kind     varchar(50)  NOT NULL,
            entity_id       uuid         NOT NULL,
            field_name      varchar(100) NOT NULL,
            language_tag    varchar(10)  NOT NULL,
            content_md      text         NOT NULL,
            is_ai_generated boolean      NOT NULL DEFAULT false,
            reviewed_at     timestamptz,
            created_at      timestamptz  NOT NULL DEFAULT now(),
            updated_at      timestamptz  NOT NULL DEFAULT now(),
            UNIQUE (entity_kind, entity_id, field_name, language_tag)
        )
    """)

    op.execute("""
        CREATE INDEX ix_localized_strings_entity
            ON localized_strings (entity_kind, entity_id, language_tag)
    """)

    op.execute("""
        CREATE TRIGGER tg_localized_strings_updated_at
            BEFORE UPDATE ON localized_strings
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at()
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS localized_strings CASCADE")
    op.execute("DROP TABLE IF EXISTS heritage_people_roles CASCADE")
    op.execute("DROP TABLE IF EXISTS people CASCADE")
    op.execute("DROP TABLE IF EXISTS materials CASCADE")
