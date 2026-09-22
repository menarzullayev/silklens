"""heritage_relations + unesco_inscriptions + events (lifecycle one-offs)

Per Agent 1 core-domain architecture §1 (inter-site network), §3.19, and
§3.24-§3.25:

  heritage_relations    — typed edges between heritage objects (part_of,
                          near, restored_from, inspired_by, …). Forms the
                          knowledge graph layer over the polymorphic root.
  unesco_inscriptions   — UNESCO WHS / tentative / ICH records. Carries the
                          official UNESCO reference number, criteria array,
                          and the inscribed/buffer area in hectares.
  events                — one-off lifecycle events (built, destroyed,
                          renovated, discovered, excavated) with date or
                          year and a narrative markdown blob.

UUIDv7 PKs · jsonb i18n · CHECK constraints to keep relation types and
status taxonomies tight · unique edges on (from, to, type) · seed UNESCO
inscriptions for the Uzbek+regional core sites (after seeding the parent
``heritage_objects`` rows for the canonical Silk Road UNESCO sites).

Revision ID: 0014_heritage_relations
Revises: 0013_taxonomies
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0014_heritage_relations"
down_revision: str | Sequence[str] | None = "0013_taxonomies"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- heritage_relations ----------------------------------------------
    op.execute(
        """
        CREATE TABLE heritage_relations (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            from_heritage_id uuid NOT NULL REFERENCES heritage_objects(id) ON DELETE CASCADE,
            to_heritage_id  uuid NOT NULL REFERENCES heritage_objects(id) ON DELETE CASCADE,
            relation_type   text NOT NULL CHECK (relation_type IN (
                'part_of','contains','near','restored_from','replaced',
                'inspired_by','predecessor_of','successor_of','associated_with'
            )),
            confidence      smallint NOT NULL DEFAULT 80
                CHECK (confidence BETWEEN 0 AND 100),
            distance_m      numeric(12, 2),
            asserted_by     uuid,
            asserted_at     timestamptz NOT NULL DEFAULT now(),
            metadata        jsonb NOT NULL DEFAULT '{}'::jsonb,
            note            jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            deleted_at      timestamptz,
            CHECK (from_heritage_id <> to_heritage_id),
            UNIQUE (from_heritage_id, to_heritage_id, relation_type)
        );

        CREATE INDEX idx_heritage_relations_from
            ON heritage_relations(from_heritage_id, relation_type)
            WHERE deleted_at IS NULL;
        CREATE INDEX idx_heritage_relations_to
            ON heritage_relations(to_heritage_id, relation_type)
            WHERE deleted_at IS NULL;
        CREATE INDEX idx_heritage_relations_type
            ON heritage_relations(relation_type)
            WHERE deleted_at IS NULL;

        CREATE TRIGGER tg_heritage_relations_updated_at
            BEFORE UPDATE ON heritage_relations
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE heritage_relations IS
            'Typed graph edges between heritage objects. Forms the network on '
            'top of the polymorphic root. Cycle prevention for transitive '
            'relations (part_of, predecessor_of) lives in the service layer.';
        """
    )

    # --- unesco_inscriptions ---------------------------------------------
    op.execute(
        """
        CREATE TABLE unesco_inscriptions (
            id                  uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            heritage_id         uuid NOT NULL REFERENCES heritage_objects(id) ON DELETE CASCADE,
            inscription_id      text NOT NULL UNIQUE,
            inscription_year    smallint,
            extension_year      smallint,
            in_danger_since     smallint,
            removed_year        smallint,
            criteria            text[] NOT NULL DEFAULT ARRAY[]::text[],
            category            text NOT NULL CHECK (category IN
                ('cultural','natural','mixed')),
            status              text NOT NULL DEFAULT 'inscribed'
                CHECK (status IN ('inscribed','tentative','delisted','in_danger')),
            area_hectares       numeric(14, 2),
            buffer_zone_hectares numeric(14, 2),
            is_transboundary    boolean NOT NULL DEFAULT false,
            transboundary_countries char(2)[],
            official_url        text,
            statement           jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now(),
            deleted_at          timestamptz,
            CHECK (length(inscription_id) BETWEEN 1 AND 64),
            CHECK (inscription_year IS NULL OR inscription_year BETWEEN 1900 AND 2200)
        );

        CREATE INDEX idx_unesco_inscriptions_heritage
            ON unesco_inscriptions(heritage_id)
            WHERE deleted_at IS NULL;
        CREATE INDEX idx_unesco_inscriptions_year
            ON unesco_inscriptions(inscription_year)
            WHERE deleted_at IS NULL AND inscription_year IS NOT NULL;
        CREATE INDEX idx_unesco_inscriptions_status
            ON unesco_inscriptions(status)
            WHERE deleted_at IS NULL;
        CREATE INDEX idx_unesco_inscriptions_criteria
            ON unesco_inscriptions USING GIN (criteria);

        CREATE TRIGGER tg_unesco_inscriptions_updated_at
            BEFORE UPDATE ON unesco_inscriptions
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE unesco_inscriptions IS
            'UNESCO reference rows. inscription_id is the canonical UNESCO ref '
            'number (e.g. ''543'' for Itchan Kala). One heritage may have multiple '
            'rows (tentative → inscribed → extended).';
        """
    )

    # --- events (one-off lifecycle events) -------------------------------
    # Distinct from heritage_revisions (audit) and heritage_period_assoc (M:N
    # to periods). An event is a narrative milestone — "destroyed by Mongol
    # siege 1220", "rediscovered 1888". Fits Agent 1 §3.36 lifecycle_events
    # but lighter; bi-temporal richness deferred to a later migration.
    op.execute(
        """
        CREATE TABLE events (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            heritage_id     uuid NOT NULL REFERENCES heritage_objects(id) ON DELETE CASCADE,
            name            jsonb NOT NULL DEFAULT '{}'::jsonb,
            kind            text NOT NULL CHECK (kind IN (
                'built','destroyed','renovated','discovered','excavated',
                'abandoned','rededicated','inscribed','restored'
            )),
            event_year      smallint,
            event_date      date,
            uncertainty_years smallint NOT NULL DEFAULT 0
                CHECK (uncertainty_years BETWEEN 0 AND 1000),
            narrative_md    jsonb NOT NULL DEFAULT '{}'::jsonb,
            actor_person    text,
            source_id       uuid REFERENCES heritage_provenance(id) ON DELETE SET NULL,
            confidence      smallint NOT NULL DEFAULT 70
                CHECK (confidence BETWEEN 0 AND 100),
            metadata        jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            deleted_at      timestamptz,
            created_by      uuid,
            updated_by      uuid,
            CHECK (event_year IS NOT NULL OR event_date IS NOT NULL)
        );

        CREATE INDEX idx_events_heritage
            ON events(heritage_id, COALESCE(event_year, EXTRACT(YEAR FROM event_date)::smallint))
            WHERE deleted_at IS NULL;
        CREATE INDEX idx_events_kind
            ON events(kind)
            WHERE deleted_at IS NULL;
        CREATE INDEX idx_events_year
            ON events(event_year)
            WHERE deleted_at IS NULL AND event_year IS NOT NULL;

        CREATE TRIGGER tg_events_updated_at
            BEFORE UPDATE ON events
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE events IS
            'Narrative lifecycle milestones (built, destroyed, restored…). Lower '
            'cardinality than heritage_facts; richer than heritage_revisions. '
            'Either event_year or event_date must be set.';
        """
    )

    # --- Seed canonical UNESCO heritage_objects + their inscription rows --
    # We cannot reference a heritage_id that doesn't exist, so we seed the
    # five Uzbek/Tien-Shan UNESCO sites as draft heritage_objects first.
    # tenant_id = default tenant (seeded in migration 0002). admin_level_id
    # wires each site to the city node seeded in 0012.
    op.execute(
        """
        WITH default_tenant AS (
            SELECT id FROM tenants WHERE slug = 'default' LIMIT 1
        ),
        seed_sites(pub_id, kind_slug, name, city_code, country_code, lat, lng,
                   inscription_id, inscription_year, criteria, area_ha, buffer_ha,
                   category, status, statement) AS (
            VALUES
                ('itchan-kala', 'monument',
                    '{"en":"Itchan Kala","ru":"Ичан-Кала","uz":"Ichan-Qal''a"}'::jsonb,
                    'UZ.KHIVA', 'UZ', 41.378307::numeric, 60.358536::numeric,
                    '543', 1990::smallint, ARRAY['iii','iv','v'],
                    26.0::numeric, 0.0::numeric,
                    'cultural', 'inscribed',
                    '{"en":"The inner town of Khiva, last resting place of caravans on the route to Iran."}'::jsonb),
                ('historic-centre-bukhara', 'monument',
                    '{"en":"Historic Centre of Bukhara","ru":"Исторический центр Бухары","uz":"Buxoro tarixiy markazi"}'::jsonb,
                    'UZ.BUKHARA', 'UZ', 39.774947::numeric, 64.421913::numeric,
                    '602', 1993::smallint, ARRAY['ii','iv','vi'],
                    216.0::numeric, 0.0::numeric,
                    'cultural', 'inscribed',
                    '{"en":"The most complete example of a medieval city in Central Asia."}'::jsonb),
                ('samarkand-crossroads', 'monument',
                    '{"en":"Samarkand – Crossroads of Cultures","ru":"Самарканд – перекрёсток культур","uz":"Samarqand – madaniyatlar chorrahasi"}'::jsonb,
                    'UZ.SAMARKAND', 'UZ', 39.654331::numeric, 66.975832::numeric,
                    '603', 2001::smallint, ARRAY['i','ii','iv'],
                    1123.0::numeric, 1369.0::numeric,
                    'cultural', 'inscribed',
                    '{"en":"A crossroads of world cultures founded in the 7th century BCE."}'::jsonb),
                ('shahrisabz-historic-centre', 'monument',
                    '{"en":"Historic Centre of Shahrisabz","ru":"Исторический центр Шахрисабза","uz":"Shahrisabz tarixiy markazi"}'::jsonb,
                    'UZ.SHAHRISABZ', 'UZ', 39.057962::numeric, 66.832710::numeric,
                    '885', 2000::smallint, ARRAY['iii','iv'],
                    240.0::numeric, 82.0::numeric,
                    'cultural', 'in_danger',
                    '{"en":"Timurid-era capital with monumental buildings reflecting cultural and political peak."}'::jsonb),
                ('western-tien-shan', 'natural_site',
                    '{"en":"Western Tien-Shan","ru":"Западный Тянь-Шань","uz":"G''arbiy Tyan-Shan"}'::jsonb,
                    NULL, 'UZ', 41.500000::numeric, 70.000000::numeric,
                    '1490', 2016::smallint, ARRAY['x'],
                    528177.83::numeric, 102915.66::numeric,
                    'natural', 'inscribed',
                    '{"en":"Transboundary mountain ecosystem at the junction of Kazakhstan, Kyrgyzstan, Uzbekistan."}'::jsonb)
        ),
        inserted_heritage AS (
            INSERT INTO heritage_objects
                (tenant_id, pub_id, kind_slug, name, country_code,
                 latitude, longitude, status, admin_level_id, confidence_score)
            SELECT
                dt.id,
                ss.pub_id,
                ss.kind_slug,
                ss.name,
                ss.country_code,
                ss.lat,
                ss.lng,
                'published',
                (SELECT id FROM geographic_admin_levels gal
                  WHERE gal.code = ss.city_code AND gal.admin_level_type = 'city'
                  LIMIT 1),
                90
            FROM seed_sites ss CROSS JOIN default_tenant dt
            RETURNING id, pub_id
        )
        INSERT INTO unesco_inscriptions
            (heritage_id, inscription_id, inscription_year, criteria,
             category, status, area_hectares, buffer_zone_hectares,
             is_transboundary, transboundary_countries, statement, official_url)
        SELECT
            ih.id,
            ss.inscription_id,
            ss.inscription_year,
            ss.criteria,
            ss.category,
            ss.status,
            ss.area_ha,
            ss.buffer_ha,
            ss.inscription_id = '1490',
            CASE WHEN ss.inscription_id = '1490'
                 THEN ARRAY['KZ','KG','UZ']::char(2)[]
                 ELSE NULL END,
            ss.statement,
            'https://whc.unesco.org/en/list/' || ss.inscription_id
        FROM seed_sites ss
        JOIN inserted_heritage ih ON ih.pub_id = ss.pub_id;
        """
    )


def downgrade() -> None:
    # Seeded heritage_objects must go before unesco_inscriptions because the
    # latter cascades. Order: events → unesco_inscriptions → relations →
    # remove the seeded heritage rows.
    op.execute(
        """
        DELETE FROM heritage_objects
        WHERE pub_id IN (
            'itchan-kala','historic-centre-bukhara','samarkand-crossroads',
            'shahrisabz-historic-centre','western-tien-shan'
        );
        """
    )
    op.execute("DROP TABLE IF EXISTS events CASCADE;")
    op.execute("DROP TABLE IF EXISTS unesco_inscriptions CASCADE;")
    op.execute("DROP TABLE IF EXISTS heritage_relations CASCADE;")
