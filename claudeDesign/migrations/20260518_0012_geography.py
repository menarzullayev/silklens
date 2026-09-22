"""geographic_admin_levels (ltree hierarchy) + countries + cities

Per Agent 1 core-domain architecture §7:
- ``geographic_admin_levels`` is the polymorphic geographic node (continent
  → country → region → city → district → site), keyed by an ltree ``path``
  for sub-tree queries (``path <@ 'earth.asia.uz'``). Each row carries the
  ISO country code, a level discriminator, jsonb i18n names, and an OPTIONAL
  polygon. PostGIS is *not* assumed to be present on this dev image (see
  ``infra/docker/postgres/init.sql`` DO-block) so we store polygons as text
  WKT when postgis is absent and as geography(Polygon,4326) when present.
- ``countries`` mirrors ISO 3166-1 with denormalized hot fields (capital,
  centroid lat/lng, currency, languages). Seeded with the Silk Road core
  plus a top-50 set.
- ``cities`` cross-references ``geographic_admin_levels`` and ``countries``
  and seeds the iconic Silk Road urban network (Samarkand → Xi'an …).
- ``heritage_objects.admin_level_id`` is soft-added (NULL allowed) so
  existing rows (none yet — but defensive) and future inserts can attach
  to the hierarchy without backfill.

UUIDv7 PKs · jsonb i18n · ltree path with GIST index · soft delete via
deleted_at · CHECK constraints on ISO codes and lat/lng ranges.

Revision ID: 0012_geography
Revises: 0011_heritage_facts
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0012_geography"
down_revision: str | Sequence[str] | None = "0011_heritage_facts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- geographic_admin_levels (ltree hierarchy) ------------------------
    # Polygon column type is decided at runtime: geography(Polygon,4326)
    # when PostGIS is present, else text (WKT). Decision lives in a DO-block
    # because Alembic can't see runtime extensions when generating revisions.
    op.execute(
        """
        DO $$
        DECLARE
            polygon_type text;
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'postgis') THEN
                polygon_type := 'geography(Polygon,4326)';
            ELSE
                polygon_type := 'text';
            END IF;

            EXECUTE format($ddl$
                CREATE TABLE geographic_admin_levels (
                    id                  uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
                    parent_id           uuid REFERENCES geographic_admin_levels(id)
                                            ON DELETE RESTRICT,
                    level               smallint NOT NULL
                                            CHECK (level BETWEEN 0 AND 5),
                    admin_level_type    text NOT NULL CHECK (admin_level_type IN
                        ('continent','country','region','city','district','site')),
                    code                text NOT NULL,
                    name                jsonb NOT NULL DEFAULT '{}'::jsonb,
                    aliases             text[] NOT NULL DEFAULT ARRAY[]::text[],
                    country_code        char(2),
                    path                ltree NOT NULL,
                    centroid_lat        numeric(9, 6),
                    centroid_lng        numeric(9, 6),
                    polygon             %s,
                    polygon_wkt         text,
                    timezone            text,
                    population          bigint,
                    elevation_m         integer,
                    external_ids        jsonb NOT NULL DEFAULT '{}'::jsonb,
                    is_active           boolean NOT NULL DEFAULT true,
                    created_at          timestamptz NOT NULL DEFAULT now(),
                    updated_at          timestamptz NOT NULL DEFAULT now(),
                    deleted_at          timestamptz,
                    created_by          uuid,
                    updated_by          uuid,
                    revision            int NOT NULL DEFAULT 1,
                    CHECK (code ~ '^[A-Za-z0-9._-]{1,64}$'),
                    CHECK (country_code IS NULL OR country_code ~ '^[A-Z]{2}$'),
                    CHECK (centroid_lat IS NULL OR centroid_lat BETWEEN -90 AND 90),
                    CHECK (centroid_lng IS NULL OR centroid_lng BETWEEN -180 AND 180),
                    UNIQUE (path)
                );
            $ddl$, polygon_type);
        END$$;

        COMMENT ON TABLE geographic_admin_levels IS
            'ltree-based geographic hierarchy: continent → country → region '
            '→ city → district → site. Polygon column is geography(Polygon,4326) '
            'when PostGIS is installed, else text WKT (column polygon_wkt is '
            'always available as a text fallback regardless of mode).';

        CREATE INDEX idx_gal_path_gist
            ON geographic_admin_levels USING GIST (path);
        CREATE INDEX idx_gal_parent
            ON geographic_admin_levels(parent_id)
            WHERE deleted_at IS NULL AND parent_id IS NOT NULL;
        CREATE INDEX idx_gal_country
            ON geographic_admin_levels(country_code)
            WHERE deleted_at IS NULL AND country_code IS NOT NULL;
        CREATE INDEX idx_gal_level
            ON geographic_admin_levels(level)
            WHERE deleted_at IS NULL;
        CREATE INDEX idx_gal_type
            ON geographic_admin_levels(admin_level_type)
            WHERE deleted_at IS NULL;
        CREATE INDEX idx_gal_name_jsonb
            ON geographic_admin_levels USING GIN (name jsonb_path_ops);

        CREATE TRIGGER tg_geographic_admin_levels_updated_at
            BEFORE UPDATE ON geographic_admin_levels
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- countries (ISO 3166-1) -------------------------------------------
    op.execute(
        """
        CREATE TABLE countries (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            iso2            char(2) NOT NULL UNIQUE,
            iso3            char(3) NOT NULL UNIQUE,
            iso_numeric     char(3) NOT NULL UNIQUE,
            name            jsonb NOT NULL DEFAULT '{}'::jsonb,
            capital         text,
            region          text,
            subregion       text,
            lat             numeric(9, 6),
            lng             numeric(9, 6),
            area_km2        numeric(14, 2),
            population      bigint,
            currency_code   char(3),
            languages       text[] NOT NULL DEFAULT ARRAY[]::text[],
            calling_code    text,
            tld             text,
            flag_emoji      text,
            admin_level_id  uuid REFERENCES geographic_admin_levels(id) ON DELETE SET NULL,
            is_unesco_party boolean NOT NULL DEFAULT false,
            is_silk_road    boolean NOT NULL DEFAULT false,
            external_ids    jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            deleted_at      timestamptz,
            -- Allow ISO standard plus 'XK' (Kosovo, user-assigned).
            CHECK (iso2 ~ '^[A-Z]{2}$'),
            CHECK (iso3 ~ '^[A-Z]{3}$'),
            CHECK (iso_numeric ~ '^[0-9]{3}$'),
            CHECK (currency_code IS NULL OR currency_code ~ '^[A-Z]{3}$'),
            CHECK (lat IS NULL OR lat BETWEEN -90 AND 90),
            CHECK (lng IS NULL OR lng BETWEEN -180 AND 180)
        );

        COMMENT ON TABLE countries IS
            'ISO 3166-1 country reference. Kosovo (XK) accepted as user-assigned '
            'exception. is_silk_road flags the corridor for fast filter on the '
            'opinionated Silk-Road landing pages.';

        CREATE INDEX idx_countries_region
            ON countries(region) WHERE deleted_at IS NULL;
        CREATE INDEX idx_countries_subregion
            ON countries(subregion) WHERE deleted_at IS NULL;
        CREATE INDEX idx_countries_silk_road
            ON countries(iso2) WHERE is_silk_road AND deleted_at IS NULL;
        CREATE INDEX idx_countries_name_jsonb
            ON countries USING GIN (name jsonb_path_ops);

        CREATE TRIGGER tg_countries_updated_at
            BEFORE UPDATE ON countries
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- cities (major urban hubs cross-ref'd) ----------------------------
    op.execute(
        """
        CREATE TABLE cities (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            admin_level_id  uuid REFERENCES geographic_admin_levels(id) ON DELETE SET NULL,
            country_code    char(2) NOT NULL,
            slug            text NOT NULL,
            name            jsonb NOT NULL DEFAULT '{}'::jsonb,
            lat             numeric(9, 6),
            lng             numeric(9, 6),
            population      bigint,
            is_capital      boolean NOT NULL DEFAULT false,
            is_silk_road    boolean NOT NULL DEFAULT false,
            timezone        text,
            external_ids    jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            deleted_at      timestamptz,
            CHECK (slug ~ '^[a-z0-9][a-z0-9_-]*$'),
            CHECK (country_code ~ '^[A-Z]{2}$'),
            CHECK (lat IS NULL OR lat BETWEEN -90 AND 90),
            CHECK (lng IS NULL OR lng BETWEEN -180 AND 180),
            UNIQUE (country_code, slug)
        );

        CREATE INDEX idx_cities_country
            ON cities(country_code) WHERE deleted_at IS NULL;
        CREATE INDEX idx_cities_admin_level
            ON cities(admin_level_id) WHERE deleted_at IS NULL;
        CREATE INDEX idx_cities_silk_road
            ON cities(country_code, slug) WHERE is_silk_road AND deleted_at IS NULL;
        CREATE INDEX idx_cities_name_jsonb
            ON cities USING GIN (name jsonb_path_ops);
        CREATE INDEX idx_cities_geo
            ON cities (lat, lng)
            WHERE deleted_at IS NULL AND lat IS NOT NULL;

        CREATE TRIGGER tg_cities_updated_at
            BEFORE UPDATE ON cities
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- soft-add heritage_objects.admin_level_id -------------------------
    op.execute(
        """
        ALTER TABLE heritage_objects
            ADD COLUMN admin_level_id uuid
                REFERENCES geographic_admin_levels(id) ON DELETE SET NULL;

        CREATE INDEX idx_heritage_objects_admin_level
            ON heritage_objects(admin_level_id)
            WHERE deleted_at IS NULL AND admin_level_id IS NOT NULL;

        COMMENT ON COLUMN heritage_objects.admin_level_id IS
            'Optional FK to geographic_admin_levels for hierarchical lookups. '
            'Coordinates remain authoritative; admin_level_id is a convenience '
            'pointer maintained by an offline geocoder.';
        """
    )

    # --- Seed continents (level 0, ltree roots) ---------------------------
    op.execute(
        """
        INSERT INTO geographic_admin_levels
            (level, admin_level_type, code, name, path)
        VALUES
            (0, 'continent', 'AF', '{"en":"Africa","ru":"Африка","uz":"Afrika"}'::jsonb, 'earth.africa'),
            (0, 'continent', 'AN', '{"en":"Antarctica","ru":"Антарктида","uz":"Antarktida"}'::jsonb, 'earth.antarctica'),
            (0, 'continent', 'AS', '{"en":"Asia","ru":"Азия","uz":"Osiyo"}'::jsonb, 'earth.asia'),
            (0, 'continent', 'EU', '{"en":"Europe","ru":"Европа","uz":"Yevropa"}'::jsonb, 'earth.europe'),
            (0, 'continent', 'NA', '{"en":"North America","ru":"Северная Америка","uz":"Shimoliy Amerika"}'::jsonb, 'earth.north_america'),
            (0, 'continent', 'OC', '{"en":"Oceania","ru":"Океания","uz":"Okeaniya"}'::jsonb, 'earth.oceania'),
            (0, 'continent', 'SA', '{"en":"South America","ru":"Южная Америка","uz":"Janubiy Amerika"}'::jsonb, 'earth.south_america');
        """
    )

    # --- Seed countries (top 50 + Silk Road + Central Asia) ---------------
    # Use Common English / Russian / Uzbek name jsonb. is_silk_road flags the
    # corridor (Central Asia, Iran, Turkey, China, plus modern stops).
    op.execute(
        """
        INSERT INTO countries
            (iso2, iso3, iso_numeric, name, capital, region, subregion,
             lat, lng, currency_code, languages, is_silk_road)
        VALUES
            -- Central Asia (Silk Road core)
            ('UZ','UZB','860','{"en":"Uzbekistan","ru":"Узбекистан","uz":"O''zbekiston"}'::jsonb,
                'Tashkent','Asia','Central Asia',41.377491,64.585262,'UZS',
                ARRAY['uz','ru','en'], true),
            ('KZ','KAZ','398','{"en":"Kazakhstan","ru":"Казахстан","uz":"Qozog''iston"}'::jsonb,
                'Astana','Asia','Central Asia',48.019573,66.923684,'KZT',
                ARRAY['kk','ru'], true),
            ('KG','KGZ','417','{"en":"Kyrgyzstan","ru":"Киргизия","uz":"Qirg''iziston"}'::jsonb,
                'Bishkek','Asia','Central Asia',41.20438,74.766098,'KGS',
                ARRAY['ky','ru'], true),
            ('TJ','TJK','762','{"en":"Tajikistan","ru":"Таджикистан","uz":"Tojikiston"}'::jsonb,
                'Dushanbe','Asia','Central Asia',38.861034,71.276093,'TJS',
                ARRAY['tg','ru'], true),
            ('TM','TKM','795','{"en":"Turkmenistan","ru":"Туркмения","uz":"Turkmaniston"}'::jsonb,
                'Ashgabat','Asia','Central Asia',38.969719,59.556278,'TMT',
                ARRAY['tk','ru'], true),
            ('AF','AFG','004','{"en":"Afghanistan","ru":"Афганистан","uz":"Afg''oniston"}'::jsonb,
                'Kabul','Asia','Southern Asia',33.93911,67.709953,'AFN',
                ARRAY['ps','fa'], true),

            -- Silk Road / wider corridor
            ('CN','CHN','156','{"en":"China","ru":"Китай","uz":"Xitoy"}'::jsonb,
                'Beijing','Asia','Eastern Asia',35.86166,104.195397,'CNY',
                ARRAY['zh'], true),
            ('IR','IRN','364','{"en":"Iran","ru":"Иран","uz":"Eron"}'::jsonb,
                'Tehran','Asia','Southern Asia',32.427908,53.688046,'IRR',
                ARRAY['fa'], true),
            ('TR','TUR','792','{"en":"Türkiye","ru":"Турция","uz":"Turkiya"}'::jsonb,
                'Ankara','Asia','Western Asia',38.963745,35.243322,'TRY',
                ARRAY['tr'], true),
            ('PK','PAK','586','{"en":"Pakistan","ru":"Пакистан","uz":"Pokiston"}'::jsonb,
                'Islamabad','Asia','Southern Asia',30.375321,69.345116,'PKR',
                ARRAY['ur','en'], true),
            ('IN','IND','356','{"en":"India","ru":"Индия","uz":"Hindiston"}'::jsonb,
                'New Delhi','Asia','Southern Asia',20.593684,78.96288,'INR',
                ARRAY['hi','en'], true),
            ('IQ','IRQ','368','{"en":"Iraq","ru":"Ирак","uz":"Iroq"}'::jsonb,
                'Baghdad','Asia','Western Asia',33.223191,43.679291,'IQD',
                ARRAY['ar','ku'], true),
            ('SY','SYR','760','{"en":"Syria","ru":"Сирия","uz":"Suriya"}'::jsonb,
                'Damascus','Asia','Western Asia',34.802075,38.996815,'SYP',
                ARRAY['ar'], true),
            ('AZ','AZE','031','{"en":"Azerbaijan","ru":"Азербайджан","uz":"Ozarbayjon"}'::jsonb,
                'Baku','Asia','Western Asia',40.143105,47.576927,'AZN',
                ARRAY['az'], true),
            ('AM','ARM','051','{"en":"Armenia","ru":"Армения","uz":"Armaniston"}'::jsonb,
                'Yerevan','Asia','Western Asia',40.069099,45.038189,'AMD',
                ARRAY['hy'], true),
            ('GE','GEO','268','{"en":"Georgia","ru":"Грузия","uz":"Gruziya"}'::jsonb,
                'Tbilisi','Asia','Western Asia',42.315407,43.356892,'GEL',
                ARRAY['ka'], true),
            ('MN','MNG','496','{"en":"Mongolia","ru":"Монголия","uz":"Mo''g''uliston"}'::jsonb,
                'Ulaanbaatar','Asia','Eastern Asia',46.862496,103.846656,'MNT',
                ARRAY['mn'], true),

            -- Mediterranean / Europe (Silk Road termini + top-50)
            ('GR','GRC','300','{"en":"Greece","ru":"Греция","uz":"Yunoniston"}'::jsonb,
                'Athens','Europe','Southern Europe',39.074208,21.824312,'EUR',
                ARRAY['el'], true),
            ('IT','ITA','380','{"en":"Italy","ru":"Италия","uz":"Italiya"}'::jsonb,
                'Rome','Europe','Southern Europe',41.87194,12.56738,'EUR',
                ARRAY['it'], true),
            ('ES','ESP','724','{"en":"Spain","ru":"Испания","uz":"Ispaniya"}'::jsonb,
                'Madrid','Europe','Southern Europe',40.463667,-3.74922,'EUR',
                ARRAY['es'], false),
            ('FR','FRA','250','{"en":"France","ru":"Франция","uz":"Fransiya"}'::jsonb,
                'Paris','Europe','Western Europe',46.227638,2.213749,'EUR',
                ARRAY['fr'], false),
            ('DE','DEU','276','{"en":"Germany","ru":"Германия","uz":"Germaniya"}'::jsonb,
                'Berlin','Europe','Western Europe',51.165691,10.451526,'EUR',
                ARRAY['de'], false),
            ('GB','GBR','826','{"en":"United Kingdom","ru":"Великобритания","uz":"Buyuk Britaniya"}'::jsonb,
                'London','Europe','Northern Europe',55.378051,-3.435973,'GBP',
                ARRAY['en'], false),
            ('NL','NLD','528','{"en":"Netherlands","ru":"Нидерланды","uz":"Niderlandiya"}'::jsonb,
                'Amsterdam','Europe','Western Europe',52.132633,5.291266,'EUR',
                ARRAY['nl'], false),
            ('BE','BEL','056','{"en":"Belgium","ru":"Бельгия","uz":"Belgiya"}'::jsonb,
                'Brussels','Europe','Western Europe',50.503887,4.469936,'EUR',
                ARRAY['nl','fr','de'], false),
            ('CH','CHE','756','{"en":"Switzerland","ru":"Швейцария","uz":"Shveysariya"}'::jsonb,
                'Bern','Europe','Western Europe',46.818188,8.227512,'CHF',
                ARRAY['de','fr','it'], false),
            ('AT','AUT','040','{"en":"Austria","ru":"Австрия","uz":"Avstriya"}'::jsonb,
                'Vienna','Europe','Western Europe',47.516231,14.550072,'EUR',
                ARRAY['de'], false),
            ('PL','POL','616','{"en":"Poland","ru":"Польша","uz":"Polsha"}'::jsonb,
                'Warsaw','Europe','Eastern Europe',51.919438,19.145136,'PLN',
                ARRAY['pl'], false),
            ('UA','UKR','804','{"en":"Ukraine","ru":"Украина","uz":"Ukraina"}'::jsonb,
                'Kyiv','Europe','Eastern Europe',48.379433,31.16558,'UAH',
                ARRAY['uk'], false),
            ('RU','RUS','643','{"en":"Russia","ru":"Россия","uz":"Rossiya"}'::jsonb,
                'Moscow','Europe','Eastern Europe',61.52401,105.318756,'RUB',
                ARRAY['ru'], true),
            ('PT','PRT','620','{"en":"Portugal","ru":"Португалия","uz":"Portugaliya"}'::jsonb,
                'Lisbon','Europe','Southern Europe',39.399872,-8.224454,'EUR',
                ARRAY['pt'], false),
            ('XK','XKX','999','{"en":"Kosovo","ru":"Косово","uz":"Kosovo"}'::jsonb,
                'Pristina','Europe','Southern Europe',42.602636,20.902977,'EUR',
                ARRAY['sq','sr'], false),

            -- East Asia
            ('JP','JPN','392','{"en":"Japan","ru":"Япония","uz":"Yaponiya"}'::jsonb,
                'Tokyo','Asia','Eastern Asia',36.204824,138.252924,'JPY',
                ARRAY['ja'], false),
            ('KR','KOR','410','{"en":"South Korea","ru":"Южная Корея","uz":"Janubiy Koreya"}'::jsonb,
                'Seoul','Asia','Eastern Asia',35.907757,127.766922,'KRW',
                ARRAY['ko'], false),
            ('TH','THA','764','{"en":"Thailand","ru":"Таиланд","uz":"Tailand"}'::jsonb,
                'Bangkok','Asia','South-Eastern Asia',15.870032,100.992541,'THB',
                ARRAY['th'], false),
            ('VN','VNM','704','{"en":"Vietnam","ru":"Вьетнам","uz":"Vyetnam"}'::jsonb,
                'Hanoi','Asia','South-Eastern Asia',14.058324,108.277199,'VND',
                ARRAY['vi'], false),
            ('ID','IDN','360','{"en":"Indonesia","ru":"Индонезия","uz":"Indoneziya"}'::jsonb,
                'Jakarta','Asia','South-Eastern Asia',-0.789275,113.921327,'IDR',
                ARRAY['id'], false),

            -- Middle East / North Africa
            ('EG','EGY','818','{"en":"Egypt","ru":"Египет","uz":"Misr"}'::jsonb,
                'Cairo','Africa','Northern Africa',26.820553,30.802498,'EGP',
                ARRAY['ar'], true),
            ('MA','MAR','504','{"en":"Morocco","ru":"Марокко","uz":"Marokash"}'::jsonb,
                'Rabat','Africa','Northern Africa',31.791702,-7.09262,'MAD',
                ARRAY['ar'], false),
            ('SA','SAU','682','{"en":"Saudi Arabia","ru":"Саудовская Аравия","uz":"Saudiya Arabistoni"}'::jsonb,
                'Riyadh','Asia','Western Asia',23.885942,45.079162,'SAR',
                ARRAY['ar'], true),
            ('AE','ARE','784','{"en":"United Arab Emirates","ru":"ОАЭ","uz":"Birlashgan Arab Amirliklari"}'::jsonb,
                'Abu Dhabi','Asia','Western Asia',23.424076,53.847818,'AED',
                ARRAY['ar'], false),

            -- Americas
            ('US','USA','840','{"en":"United States","ru":"США","uz":"AQSh"}'::jsonb,
                'Washington','Americas','Northern America',37.09024,-95.712891,'USD',
                ARRAY['en'], false),
            ('CA','CAN','124','{"en":"Canada","ru":"Канада","uz":"Kanada"}'::jsonb,
                'Ottawa','Americas','Northern America',56.130366,-106.346771,'CAD',
                ARRAY['en','fr'], false),
            ('MX','MEX','484','{"en":"Mexico","ru":"Мексика","uz":"Meksika"}'::jsonb,
                'Mexico City','Americas','Central America',23.634501,-102.552784,'MXN',
                ARRAY['es'], false),
            ('PE','PER','604','{"en":"Peru","ru":"Перу","uz":"Peru"}'::jsonb,
                'Lima','Americas','South America',-9.189967,-75.015152,'PEN',
                ARRAY['es'], false),
            ('AR','ARG','032','{"en":"Argentina","ru":"Аргентина","uz":"Argentina"}'::jsonb,
                'Buenos Aires','Americas','South America',-38.416097,-63.616672,'ARS',
                ARRAY['es'], false),
            ('BR','BRA','076','{"en":"Brazil","ru":"Бразилия","uz":"Braziliya"}'::jsonb,
                'Brasília','Americas','South America',-14.235004,-51.92528,'BRL',
                ARRAY['pt'], false),

            -- Oceania
            ('AU','AUS','036','{"en":"Australia","ru":"Австралия","uz":"Avstraliya"}'::jsonb,
                'Canberra','Oceania','Australia and New Zealand',-25.274398,133.775136,'AUD',
                ARRAY['en'], false),
            ('NZ','NZL','554','{"en":"New Zealand","ru":"Новая Зеландия","uz":"Yangi Zelandiya"}'::jsonb,
                'Wellington','Oceania','Australia and New Zealand',-40.900557,174.885971,'NZD',
                ARRAY['en','mi'], false);
        """
    )

    # --- Seed country admin_levels and link countries.admin_level_id ------
    # Pin each country row to a continent path; insert a country-level admin
    # node, then update countries.admin_level_id. Continent code derived
    # from countries.region.
    op.execute(
        """
        WITH continent_paths AS (
            SELECT * FROM (VALUES
                ('Asia',     'earth.asia'),
                ('Europe',   'earth.europe'),
                ('Africa',   'earth.africa'),
                ('Americas', 'earth.north_america'),
                ('Oceania',  'earth.oceania')
            ) AS t(region, base_path)
        ),
        new_levels AS (
            INSERT INTO geographic_admin_levels
                (parent_id, level, admin_level_type, code, name, country_code, path)
            SELECT
                gal.id,
                1,
                'country',
                c.iso2,
                c.name,
                c.iso2,
                CASE
                    WHEN c.subregion = 'South America'
                        THEN ('earth.south_america.' || lower(c.iso2))::ltree
                    ELSE (cp.base_path || '.' || lower(c.iso2))::ltree
                END
            FROM countries c
            JOIN continent_paths cp ON cp.region = c.region
            JOIN geographic_admin_levels gal ON
                gal.path = CASE
                    WHEN c.subregion = 'South America'
                        THEN 'earth.south_america'::ltree
                    ELSE cp.base_path::ltree
                END
            RETURNING id, country_code
        )
        UPDATE countries c
        SET admin_level_id = nl.id
        FROM new_levels nl
        WHERE c.iso2 = nl.country_code;
        """
    )

    # --- Seed Silk Road cities + their admin_level rows -------------------
    op.execute(
        """
        WITH city_seeds(country_code, slug, name, lat, lng, population, is_capital, is_silk_road) AS (
            VALUES
                ('UZ', 'samarkand',
                    '{"en":"Samarkand","ru":"Самарканд","uz":"Samarqand"}'::jsonb,
                    39.654331, 66.975832, 519700, false, true),
                ('UZ', 'bukhara',
                    '{"en":"Bukhara","ru":"Бухара","uz":"Buxoro"}'::jsonb,
                    39.774947, 64.421913, 280187, false, true),
                ('UZ', 'khiva',
                    '{"en":"Khiva","ru":"Хива","uz":"Xiva"}'::jsonb,
                    41.378307, 60.358536, 93000, false, true),
                ('UZ', 'tashkent',
                    '{"en":"Tashkent","ru":"Ташкент","uz":"Toshkent"}'::jsonb,
                    41.299496, 69.240073, 2570000, true, true),
                ('UZ', 'shahrisabz',
                    '{"en":"Shahrisabz","ru":"Шахрисабз","uz":"Shahrisabz"}'::jsonb,
                    39.057962, 66.832710, 105985, false, true),
                ('CN', 'kashgar',
                    '{"en":"Kashgar","ru":"Кашгар","uz":"Qashqar"}'::jsonb,
                    39.467091, 75.989138, 711300, false, true),
                ('CN', 'xian',
                    '{"en":"Xi''an","ru":"Сиань","uz":"Sian"}'::jsonb,
                    34.341575, 108.939774, 12952907, false, true),
                ('TR', 'istanbul',
                    '{"en":"Istanbul","ru":"Стамбул","uz":"Istanbul"}'::jsonb,
                    41.008238, 28.978359, 15462452, false, true),
                ('IR', 'isfahan',
                    '{"en":"Isfahan","ru":"Исфахан","uz":"Isfahon"}'::jsonb,
                    32.654630, 51.667980, 1961260, false, true)
        ),
        new_city_levels AS (
            INSERT INTO geographic_admin_levels
                (parent_id, level, admin_level_type, code, name, country_code,
                 centroid_lat, centroid_lng, population, path)
            SELECT
                country_lvl.id,
                3,
                'city',
                upper(cs.country_code) || '.' || upper(cs.slug),
                cs.name,
                cs.country_code,
                cs.lat,
                cs.lng,
                cs.population,
                (country_lvl.path::text || '.' || cs.slug)::ltree
            FROM city_seeds cs
            JOIN geographic_admin_levels country_lvl ON
                country_lvl.country_code = cs.country_code
                AND country_lvl.admin_level_type = 'country'
            RETURNING id, country_code, code
        )
        INSERT INTO cities
            (admin_level_id, country_code, slug, name, lat, lng,
             population, is_capital, is_silk_road)
        SELECT
            ncl.id,
            cs.country_code,
            cs.slug,
            cs.name,
            cs.lat,
            cs.lng,
            cs.population,
            cs.is_capital,
            cs.is_silk_road
        FROM city_seeds cs
        JOIN new_city_levels ncl ON
            ncl.country_code = cs.country_code
            AND ncl.code = upper(cs.country_code) || '.' || upper(cs.slug);
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_heritage_objects_admin_level;")
    op.execute("ALTER TABLE heritage_objects DROP COLUMN IF EXISTS admin_level_id;")
    op.execute("DROP TABLE IF EXISTS cities CASCADE;")
    op.execute("DROP TABLE IF EXISTS countries CASCADE;")
    op.execute("DROP TABLE IF EXISTS geographic_admin_levels CASCADE;")
