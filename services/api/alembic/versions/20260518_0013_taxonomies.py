"""historical_periods + architectural_styles + dynasties + M:N heritage assoc

Per Agent 1 core-domain architecture §3.8-§3.9, §3.28 and §8 (faceted
classification), this migration lands the curated cultural taxonomy:

  historical_periods       — named eras with start/end years, region scope.
  architectural_styles     — hierarchical style catalog (islamic →
                             timurid_architecture etc.) with period anchor.
  dynasties                — ruling dynasties anchored to periods/regions.
  heritage_period_assoc    — M:N heritage ↔ period with role (built / used …).
  heritage_style_assoc     — M:N heritage ↔ style.
  heritage_dynasty_assoc   — M:N heritage ↔ dynasty with role.

UUIDv7 PKs · jsonb i18n · CHECK constraints on year ordering and slug shape ·
``tg_set_updated_at`` trigger on each table with ``updated_at`` ·
seed data is Central-Asia / Silk-Road centric per the project brief.

Revision ID: 0013_taxonomies
Revises: 0012_geography
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0013_taxonomies"
down_revision: str | Sequence[str] | None = "0012_geography"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- historical_periods -----------------------------------------------
    op.execute(
        """
        CREATE TABLE historical_periods (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            slug            text NOT NULL UNIQUE,
            name            jsonb NOT NULL DEFAULT '{}'::jsonb,
            description     jsonb NOT NULL DEFAULT '{}'::jsonb,
            start_year      smallint,
            end_year        smallint,
            region_scope    text NOT NULL DEFAULT 'global',
            parent_period_id uuid REFERENCES historical_periods(id) ON DELETE SET NULL,
            sort_order      smallint NOT NULL DEFAULT 1000,
            color_hex       char(7),
            external_ids    jsonb NOT NULL DEFAULT '{}'::jsonb,
            is_active       boolean NOT NULL DEFAULT true,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            deleted_at      timestamptz,
            CHECK (slug ~ '^[a-z][a-z0-9_]*$'),
            CHECK (region_scope ~ '^[a-z][a-z0-9_]*$'),
            CHECK (end_year IS NULL OR start_year IS NULL OR end_year >= start_year),
            CHECK (color_hex IS NULL OR color_hex ~ '^#[0-9A-Fa-f]{6}$')
        );

        CREATE INDEX idx_historical_periods_years
            ON historical_periods(start_year, end_year)
            WHERE deleted_at IS NULL AND start_year IS NOT NULL;
        CREATE INDEX idx_historical_periods_region
            ON historical_periods(region_scope)
            WHERE deleted_at IS NULL;
        CREATE INDEX idx_historical_periods_parent
            ON historical_periods(parent_period_id)
            WHERE deleted_at IS NULL AND parent_period_id IS NOT NULL;
        CREATE INDEX idx_historical_periods_name_jsonb
            ON historical_periods USING GIN (name jsonb_path_ops);

        CREATE TRIGGER tg_historical_periods_updated_at
            BEFORE UPDATE ON historical_periods
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE historical_periods IS
            'Curated cultural epochs. Negative years for BCE. region_scope is a '
            'free-form key (global, central_asia, …) so the same site can be '
            'classified under multiple overlapping period rows.';
        """
    )

    # --- architectural_styles ---------------------------------------------
    op.execute(
        """
        CREATE TABLE architectural_styles (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            slug            text NOT NULL UNIQUE,
            name            jsonb NOT NULL DEFAULT '{}'::jsonb,
            description     jsonb NOT NULL DEFAULT '{}'::jsonb,
            period_id       uuid REFERENCES historical_periods(id) ON DELETE SET NULL,
            parent_style_id uuid REFERENCES architectural_styles(id) ON DELETE SET NULL,
            region_scope    text NOT NULL DEFAULT 'global',
            external_ids    jsonb NOT NULL DEFAULT '{}'::jsonb,
            is_active       boolean NOT NULL DEFAULT true,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            deleted_at      timestamptz,
            CHECK (slug ~ '^[a-z][a-z0-9_]*$'),
            CHECK (region_scope ~ '^[a-z][a-z0-9_]*$')
        );

        CREATE INDEX idx_architectural_styles_period
            ON architectural_styles(period_id)
            WHERE deleted_at IS NULL AND period_id IS NOT NULL;
        CREATE INDEX idx_architectural_styles_parent
            ON architectural_styles(parent_style_id)
            WHERE deleted_at IS NULL AND parent_style_id IS NOT NULL;
        CREATE INDEX idx_architectural_styles_region
            ON architectural_styles(region_scope)
            WHERE deleted_at IS NULL;
        CREATE INDEX idx_architectural_styles_name_jsonb
            ON architectural_styles USING GIN (name jsonb_path_ops);

        CREATE TRIGGER tg_architectural_styles_updated_at
            BEFORE UPDATE ON architectural_styles
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- dynasties --------------------------------------------------------
    op.execute(
        """
        CREATE TABLE dynasties (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            slug            text NOT NULL UNIQUE,
            name            jsonb NOT NULL DEFAULT '{}'::jsonb,
            description     jsonb NOT NULL DEFAULT '{}'::jsonb,
            start_year      smallint,
            end_year        smallint,
            period_id       uuid REFERENCES historical_periods(id) ON DELETE SET NULL,
            region_scope    text NOT NULL DEFAULT 'global',
            capital_city_slug text,
            successor_id    uuid REFERENCES dynasties(id) ON DELETE SET NULL,
            external_ids    jsonb NOT NULL DEFAULT '{}'::jsonb,
            is_active       boolean NOT NULL DEFAULT true,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            deleted_at      timestamptz,
            CHECK (slug ~ '^[a-z][a-z0-9_]*$'),
            CHECK (region_scope ~ '^[a-z][a-z0-9_]*$'),
            CHECK (end_year IS NULL OR start_year IS NULL OR end_year >= start_year)
        );

        CREATE INDEX idx_dynasties_years
            ON dynasties(start_year, end_year)
            WHERE deleted_at IS NULL AND start_year IS NOT NULL;
        CREATE INDEX idx_dynasties_period
            ON dynasties(period_id)
            WHERE deleted_at IS NULL AND period_id IS NOT NULL;
        CREATE INDEX idx_dynasties_region
            ON dynasties(region_scope)
            WHERE deleted_at IS NULL;
        CREATE INDEX idx_dynasties_name_jsonb
            ON dynasties USING GIN (name jsonb_path_ops);

        CREATE TRIGGER tg_dynasties_updated_at
            BEFORE UPDATE ON dynasties
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- M:N heritage_period_assoc ----------------------------------------
    op.execute(
        """
        CREATE TABLE heritage_period_assoc (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            heritage_id     uuid NOT NULL REFERENCES heritage_objects(id) ON DELETE CASCADE,
            period_id       uuid NOT NULL REFERENCES historical_periods(id) ON DELETE RESTRICT,
            role            text NOT NULL DEFAULT 'used'
                CHECK (role IN ('built','used','abandoned','restored','destroyed')),
            confidence      smallint NOT NULL DEFAULT 80
                CHECK (confidence BETWEEN 0 AND 100),
            note            jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            created_by      uuid,
            UNIQUE (heritage_id, period_id, role)
        );

        CREATE INDEX idx_heritage_period_assoc_heritage
            ON heritage_period_assoc(heritage_id);
        CREATE INDEX idx_heritage_period_assoc_period
            ON heritage_period_assoc(period_id);

        CREATE TRIGGER tg_heritage_period_assoc_updated_at
            BEFORE UPDATE ON heritage_period_assoc
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- M:N heritage_style_assoc -----------------------------------------
    op.execute(
        """
        CREATE TABLE heritage_style_assoc (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            heritage_id     uuid NOT NULL REFERENCES heritage_objects(id) ON DELETE CASCADE,
            style_id        uuid NOT NULL REFERENCES architectural_styles(id) ON DELETE RESTRICT,
            is_primary      boolean NOT NULL DEFAULT false,
            confidence      smallint NOT NULL DEFAULT 80
                CHECK (confidence BETWEEN 0 AND 100),
            note            jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            created_by      uuid,
            UNIQUE (heritage_id, style_id)
        );

        CREATE INDEX idx_heritage_style_assoc_heritage
            ON heritage_style_assoc(heritage_id);
        CREATE INDEX idx_heritage_style_assoc_style
            ON heritage_style_assoc(style_id);
        CREATE INDEX idx_heritage_style_assoc_primary
            ON heritage_style_assoc(heritage_id)
            WHERE is_primary;

        CREATE TRIGGER tg_heritage_style_assoc_updated_at
            BEFORE UPDATE ON heritage_style_assoc
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- M:N heritage_dynasty_assoc ---------------------------------------
    op.execute(
        """
        CREATE TABLE heritage_dynasty_assoc (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            heritage_id     uuid NOT NULL REFERENCES heritage_objects(id) ON DELETE CASCADE,
            dynasty_id      uuid NOT NULL REFERENCES dynasties(id) ON DELETE RESTRICT,
            role            text NOT NULL DEFAULT 'built_under'
                CHECK (role IN ('built_under','flourished_under','destroyed_under',
                                'restored_under','patronized_by','associated_with')),
            confidence      smallint NOT NULL DEFAULT 80
                CHECK (confidence BETWEEN 0 AND 100),
            note            jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            created_by      uuid,
            UNIQUE (heritage_id, dynasty_id, role)
        );

        CREATE INDEX idx_heritage_dynasty_assoc_heritage
            ON heritage_dynasty_assoc(heritage_id);
        CREATE INDEX idx_heritage_dynasty_assoc_dynasty
            ON heritage_dynasty_assoc(dynasty_id);

        CREATE TRIGGER tg_heritage_dynasty_assoc_updated_at
            BEFORE UPDATE ON heritage_dynasty_assoc
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- Seed historical_periods -----------------------------------------
    op.execute(
        """
        INSERT INTO historical_periods
            (slug, name, start_year, end_year, region_scope)
        VALUES
            ('bronze_age', '{"en":"Bronze Age","ru":"Бронзовый век","uz":"Bronza davri"}'::jsonb,
                -3300, -1200, 'global'),
            ('iron_age', '{"en":"Iron Age","ru":"Железный век","uz":"Temir davri"}'::jsonb,
                -1200, -550, 'global'),
            ('achaemenid', '{"en":"Achaemenid","ru":"Ахеменидская","uz":"Ahmoniylar"}'::jsonb,
                -550, -330, 'central_asia'),
            ('hellenistic', '{"en":"Hellenistic","ru":"Эллинистический","uz":"Hellinistik"}'::jsonb,
                -330, -150, 'central_asia'),
            ('kushan', '{"en":"Kushan","ru":"Кушанское царство","uz":"Kushonlar"}'::jsonb,
                30, 375, 'central_asia'),
            ('sassanid', '{"en":"Sassanid","ru":"Сасаниды","uz":"Sosoniylar"}'::jsonb,
                224, 651, 'central_asia'),
            ('umayyad', '{"en":"Umayyad Caliphate","ru":"Омейяды","uz":"Umaviylar xalifaligi"}'::jsonb,
                661, 750, 'central_asia'),
            ('abbasid', '{"en":"Abbasid Caliphate","ru":"Аббасиды","uz":"Abbosiylar xalifaligi"}'::jsonb,
                750, 1258, 'central_asia'),
            ('samanid', '{"en":"Samanid","ru":"Саманиды","uz":"Somoniylar"}'::jsonb,
                819, 999, 'central_asia'),
            ('karakhanid', '{"en":"Karakhanid","ru":"Караханиды","uz":"Qoraxoniylar"}'::jsonb,
                840, 1212, 'central_asia'),
            ('khwarazmian', '{"en":"Khwarazmian","ru":"Хорезмшахи","uz":"Xorazmshohlar"}'::jsonb,
                1077, 1231, 'central_asia'),
            ('mongol', '{"en":"Mongol Empire","ru":"Монгольская империя","uz":"Mo''g''ullar imperiyasi"}'::jsonb,
                1206, 1368, 'central_asia'),
            ('timurid', '{"en":"Timurid","ru":"Тимуриды","uz":"Temuriylar"}'::jsonb,
                1370, 1507, 'central_asia'),
            ('shaybanid', '{"en":"Shaybanid","ru":"Шейбаниды","uz":"Shayboniylar"}'::jsonb,
                1500, 1598, 'central_asia'),
            ('khanate_period', '{"en":"Khanate Period","ru":"Период ханств","uz":"Xonliklar davri"}'::jsonb,
                1500, 1920, 'central_asia'),
            ('tsarist', '{"en":"Tsarist Russia","ru":"Российская империя","uz":"Rossiya imperiyasi"}'::jsonb,
                1865, 1917, 'central_asia'),
            ('soviet', '{"en":"Soviet","ru":"Советский период","uz":"Sovet davri"}'::jsonb,
                1917, 1991, 'central_asia'),
            ('modern', '{"en":"Modern","ru":"Современность","uz":"Hozirgi zamon"}'::jsonb,
                1991, 2100, 'global');
        """
    )

    # --- Seed architectural_styles (with parent_style_id wiring) ----------
    # Insert top-level styles first so we can reference them for descendants.
    op.execute(
        """
        INSERT INTO architectural_styles (slug, name, region_scope, period_id) VALUES
            ('islamic', '{"en":"Islamic","ru":"Исламская","uz":"Islom"}'::jsonb, 'global', NULL),
            ('sogdian', '{"en":"Sogdian","ru":"Согдийская","uz":"So''g''d"}'::jsonb,
                'central_asia',
                (SELECT id FROM historical_periods WHERE slug = 'hellenistic')),
            ('hellenistic', '{"en":"Hellenistic","ru":"Эллинистическая","uz":"Hellinistik"}'::jsonb,
                'global',
                (SELECT id FROM historical_periods WHERE slug = 'hellenistic')),
            ('byzantine', '{"en":"Byzantine","ru":"Византийская","uz":"Vizantiya"}'::jsonb,
                'global', NULL),
            ('mongol', '{"en":"Mongol","ru":"Монгольская","uz":"Mo''g''ul"}'::jsonb,
                'central_asia',
                (SELECT id FROM historical_periods WHERE slug = 'mongol')),
            ('soviet_modernism',
                '{"en":"Soviet Modernism","ru":"Советский модернизм","uz":"Sovet modernizmi"}'::jsonb,
                'central_asia',
                (SELECT id FROM historical_periods WHERE slug = 'soviet')),
            ('central_asian_vernacular',
                '{"en":"Central Asian Vernacular","ru":"Центральноазиатская народная","uz":"Markaziy Osiyo xalq"}'::jsonb,
                'central_asia', NULL);

        -- Children that need a parent_style_id pointer
        INSERT INTO architectural_styles
            (slug, name, region_scope, period_id, parent_style_id)
        VALUES
            ('timurid_architecture',
                '{"en":"Timurid Architecture","ru":"Тимуридская архитектура","uz":"Temuriylar arxitekturasi"}'::jsonb,
                'central_asia',
                (SELECT id FROM historical_periods WHERE slug = 'timurid'),
                (SELECT id FROM architectural_styles WHERE slug = 'islamic'));
        """
    )

    # --- Seed dynasties ---------------------------------------------------
    op.execute(
        """
        INSERT INTO dynasties
            (slug, name, start_year, end_year, period_id, region_scope, capital_city_slug)
        VALUES
            ('samanid', '{"en":"Samanid","ru":"Саманиды","uz":"Somoniylar"}'::jsonb,
                819, 999,
                (SELECT id FROM historical_periods WHERE slug = 'samanid'),
                'central_asia', 'bukhara'),
            ('karakhanid', '{"en":"Karakhanid","ru":"Караханиды","uz":"Qoraxoniylar"}'::jsonb,
                840, 1212,
                (SELECT id FROM historical_periods WHERE slug = 'karakhanid'),
                'central_asia', 'samarkand'),
            ('khwarazmid', '{"en":"Khwarazmid","ru":"Хорезмшахи","uz":"Xorazmshohlar"}'::jsonb,
                1077, 1231,
                (SELECT id FROM historical_periods WHERE slug = 'khwarazmian'),
                'central_asia', NULL),
            ('timurid', '{"en":"Timurid","ru":"Тимуриды","uz":"Temuriylar"}'::jsonb,
                1370, 1507,
                (SELECT id FROM historical_periods WHERE slug = 'timurid'),
                'central_asia', 'samarkand'),
            ('shaybanid', '{"en":"Shaybanid","ru":"Шейбаниды","uz":"Shayboniylar"}'::jsonb,
                1500, 1598,
                (SELECT id FROM historical_periods WHERE slug = 'shaybanid'),
                'central_asia', 'bukhara'),
            ('ashtarkhanid', '{"en":"Ashtarkhanid (Janid)","ru":"Аштарханиды","uz":"Ashtarxoniylar"}'::jsonb,
                1599, 1747,
                (SELECT id FROM historical_periods WHERE slug = 'khanate_period'),
                'central_asia', 'bukhara'),
            ('mangit', '{"en":"Manghit","ru":"Мангытская династия","uz":"Mang''it sulolasi"}'::jsonb,
                1756, 1920,
                (SELECT id FROM historical_periods WHERE slug = 'khanate_period'),
                'central_asia', 'bukhara'),
            ('kungrat', '{"en":"Kungrat","ru":"Кунграты","uz":"Qo''ng''irot"}'::jsonb,
                1804, 1920,
                (SELECT id FROM historical_periods WHERE slug = 'khanate_period'),
                'central_asia', 'khiva');
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS heritage_dynasty_assoc CASCADE;")
    op.execute("DROP TABLE IF EXISTS heritage_style_assoc CASCADE;")
    op.execute("DROP TABLE IF EXISTS heritage_period_assoc CASCADE;")
    op.execute("DROP TABLE IF EXISTS dynasties CASCADE;")
    op.execute("DROP TABLE IF EXISTS architectural_styles CASCADE;")
    op.execute("DROP TABLE IF EXISTS historical_periods CASCADE;")
