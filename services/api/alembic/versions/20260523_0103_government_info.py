"""government_info table — official info, laws, holidays. SILK-0086.

Revision ID: 0103
Revises: 0102
Create Date: 2026-05-23
"""

from __future__ import annotations

from alembic import op

revision = "0103"
down_revision = "0102"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS government_info (
            id          uuid         PRIMARY KEY DEFAULT gen_uuid_v7(),
            country_code char(2)     NOT NULL,
            kind        varchar(30)  NOT NULL,
            title       jsonb        NOT NULL DEFAULT '{}',
            body_md     jsonb        NOT NULL DEFAULT '{}',
            source_url  varchar(500),
            effective_date date,
            expires_date   date,
            is_active   boolean      NOT NULL DEFAULT true,
            sort_order  int          NOT NULL DEFAULT 0,
            created_at  timestamptz  NOT NULL DEFAULT now(),
            updated_at  timestamptz  NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TRIGGER tg_government_info_updated_at
            BEFORE UPDATE ON government_info
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at()
    """)

    op.execute("""
        CREATE INDEX ix_government_info_country_kind
            ON government_info (country_code, kind, sort_order)
            WHERE is_active = true
    """)

    _seed_uzbekistan()


def _seed_uzbekistan() -> None:
    rows = [
        (
            "UZ", "holiday", "New Year's Day", "Yangi yil",
            "1 yanvar — davlat bayrami", "January 1 — public holiday",
            "2026-01-01", None,
        ),
        (
            "UZ", "holiday", "Women's Day", "Xotin-qizlar kuni",
            "8 mart — xotin-qizlar kuni", "March 8 — Women's Day",
            "2026-03-08", None,
        ),
        (
            "UZ", "holiday", "Nowruz", "Navro'z bayrami",
            "21 mart — Navro'z milliy bayrami", "March 21 — Nowruz national holiday",
            "2026-03-21", None,
        ),
        (
            "UZ", "holiday", "Independence Day", "Mustaqillik kuni",
            "1 sentabr — Mustaqillik kuni", "September 1 — Independence Day",
            "2026-09-01", None,
        ),
        (
            "UZ", "visa_info", "e-Visa Available", "Elektron viza",
            "Ko'pchilik mamlakatlar uchun e-viza mavjud. evisa.e-gov.uz",
            "e-Visa available for most countries. Apply at evisa.e-gov.uz",
            None, None,
        ),
        (
            "UZ", "law", "Photography Rules", "Suratga olish qoidalari",
            "Harbiy obyektlar, chegara postlari va ba'zi hukumat binolari yonida suratga olish taqiqlangan.",
            "Photography near military objects, border posts and some government buildings is prohibited.",
            None, None,
        ),
        (
            "UZ", "law", "Currency Regulations", "Valyuta qoidalari",
            "10,000 USD dan ortiq pul olib kirish/chiqarish deklaratsiya qilinishi kerak.",
            "Currency over $10,000 must be declared at customs.",
            None, None,
        ),
        (
            "UZ", "emergency", "Emergency Numbers", "Favqulodda raqamlar",
            "Tez tibbiy yordam: 103 | Politsiya: 102 | O't o'chirish: 101",
            "Ambulance: 103 | Police: 102 | Fire: 101",
            None, None,
        ),
    ]
    for row in rows:
        country, kind, title_en, title_uz, body_uz, body_en, eff_date, exp_date = row
        eff = f"'{eff_date}'" if eff_date else "NULL"
        title_en_s = title_en.replace("'", "''")
        title_uz_s = title_uz.replace("'", "''")
        body_en_s = body_en.replace("'", "''")
        body_uz_s = body_uz.replace("'", "''")
        op.execute(
            f"""
            INSERT INTO government_info (country_code, kind, title, body_md, effective_date, expires_date)
            VALUES (
                '{country}', '{kind}',
                '{{"en": "{title_en_s}", "uz": "{title_uz_s}"}}'::jsonb,
                '{{"en": "{body_en_s}", "uz": "{body_uz_s}"}}'::jsonb,
                {eff}, {exp_date or 'NULL'}
            )
            """  # noqa: S608
        )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS government_info CASCADE")
