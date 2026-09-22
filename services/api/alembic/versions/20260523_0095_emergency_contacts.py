"""Emergency contacts public safety directory.

SILK-0057: Country-keyed, multilingual emergency contacts table.
Powers the public /v1/emergency endpoints — no auth required.

Tables introduced:

  emergency_contacts — ambulance, police, fire, hospital, embassy,
                       consulate, tourist_police records keyed by
                       ISO 3166-1 alpha-2 country_code.

Seeds:
  11 initial rows for Uzbekistan (national emergency numbers +
  5 embassy contacts in Tashkent).

Revision ID: 0095
Revises: 0094
Create Date: 2026-05-23
"""

from __future__ import annotations

from alembic import op

revision = "0095"
down_revision = "0094"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS emergency_contacts (
            id              uuid         PRIMARY KEY DEFAULT gen_uuid_v7(),
            country_code    char(2)      NOT NULL,
            kind            varchar(30)  NOT NULL,
            name            jsonb        NOT NULL DEFAULT '{}',
            phone           varchar(30),
            phone_alt       varchar(30),
            address         jsonb        NOT NULL DEFAULT '{}',
            latitude        numeric(10,7),
            longitude       numeric(10,7),
            languages_spoken text[]      NOT NULL DEFAULT '{}',
            is_24h          boolean      NOT NULL DEFAULT false,
            is_active       boolean      NOT NULL DEFAULT true,
            sort_order      int          NOT NULL DEFAULT 0,
            created_at      timestamptz  NOT NULL DEFAULT now(),
            updated_at      timestamptz  NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        COMMENT ON TABLE emergency_contacts IS
            'Country-keyed multilingual emergency contact directory. '
            'Admin-managed. Powered by /v1/emergency public endpoints.';
        COMMENT ON COLUMN emergency_contacts.kind IS
            'Contact category: ambulance|police|fire|hospital|embassy|'
            'consulate|tourist_police|gas_emergency or any future slug.';
        COMMENT ON COLUMN emergency_contacts.name IS
            'Multilingual display name keyed by BCP-47 tag: {uz, ru, en, zh, de, ko, ...}.';
        COMMENT ON COLUMN emergency_contacts.address IS
            'Multilingual physical address keyed by BCP-47 tag.';
        COMMENT ON COLUMN emergency_contacts.languages_spoken IS
            'BCP-47 tags for languages spoken at this contact point.';
        COMMENT ON COLUMN emergency_contacts.is_24h IS
            'True when the service is available 24 hours a day.';
        COMMENT ON COLUMN emergency_contacts.sort_order IS
            'Display order within a country+kind group. Lower = higher priority.';
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_emergency_contacts_country
            ON emergency_contacts (country_code, kind, sort_order)
            WHERE is_active = true
        """
    )

    op.execute(
        """
        CREATE TRIGGER tg_emergency_contacts_updated_at
            BEFORE UPDATE ON emergency_contacts
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at()
        """
    )

    # Seed Uzbekistan national emergency numbers and key embassy contacts.
    # All values are compile-time string/bool/int constants — no user input.
    # noqa: S608 — false positive, no user-controlled strings in these f-strings.
    _seeds = [
        # (country, kind, name_json, phone, langs, is_24h, sort)
        ("UZ", "ambulance",      '{"uz": "Tez tibbiy yordam", "ru": "Скорая помощь", "en": "Ambulance"}',                                                                                    "103",           "ARRAY['uz','ru']",        True,  1),
        ("UZ", "police",         '{"uz": "Politsiya", "ru": "Полиция", "en": "Police"}',                                                                                                     "102",           "ARRAY['uz','ru']",        True,  2),
        ("UZ", "fire",           '{"uz": "O''t o''chirish xizmati", "ru": "Пожарная служба", "en": "Fire Department"}',                                                                      "101",           "ARRAY['uz','ru']",        True,  3),
        ("UZ", "gas_emergency",  '{"uz": "Gaz xizmati", "ru": "Газовая служба", "en": "Gas Emergency"}',                                                                                     "104",           "ARRAY['uz','ru']",        True,  4),
        ("UZ", "tourist_police", '{"uz": "Sayyohlik politsiyasi", "ru": "Туристическая полиция", "en": "Tourist Police"}',                                                                    "+998712444444", "ARRAY['uz','ru','en']",   True,  5),
        ("UZ", "embassy_us",     '{"uz": "AQSh elchixonasi", "ru": "Посольство США", "en": "US Embassy Tashkent"}',                                                                          "+998712120350", "ARRAY['en']",             False, 10),
        ("UZ", "embassy_uk",     '{"uz": "Buyuk Britaniya elchixonasi", "ru": "Посольство Великобритании", "en": "British Embassy Tashkent"}',                                                "+998712672852", "ARRAY['en']",             False, 11),
        ("UZ", "embassy_de",     '{"uz": "Germaniya elchixonasi", "ru": "Посольство Germaniyasi", "en": "German Embassy Tashkent"}',                                                          "+998712281714", "ARRAY['de','en']",        False, 12),
        ("UZ", "embassy_cn",     '{"uz": "Xitoy elchixonasi", "ru": "Посольство Китая", "en": "Chinese Embassy Tashkent"}',                                                                  "+998712336053", "ARRAY['zh','en']",        False, 13),
        ("UZ", "embassy_kr",     '{"uz": "Koreya elchixonasi", "ru": "Посольство Кореи", "en": "Korean Embassy Tashkent"}',                                                                  "+998712523151", "ARRAY['ko','en']",        False, 14),
        ("UZ", "hospital",       '{"uz": "Respublika shoshilinch tibbiyot markazi", "ru": "Республиканский центр экстренной медицины", "en": "Republican Emergency Medical Center"}',        "+998712358803", "ARRAY['uz','ru']",        True,  20),
    ]

    for country, kind, name_json, phone, langs_sql, is_24h, sort in _seeds:
        # name_json contains only static string data defined above.
        sql = (  # noqa: S608
            f"INSERT INTO emergency_contacts"
            f" (country_code, kind, name, phone, languages_spoken, is_24h, sort_order)"
            f" VALUES"
            f" ('{country}', '{kind}', $${name_json}$$::jsonb, '{phone}',"
            f"  {langs_sql}, {str(is_24h).lower()}, {sort})"
        )
        op.execute(sql)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS emergency_contacts CASCADE")
