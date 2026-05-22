"""Cultural tips and etiquette guidelines.

SILK-0069: Introduces the `cultural_tips` table with seeded Uzbekistan
etiquette data (12 rows across mosque, bazaar, home_visit, restaurant,
general, and archaeological_site contexts).

Tables introduced:

  cultural_tips — admin-managed, JSONB-localised cultural etiquette cards
                  indexed by (country_code, context, sort_order).

Revision ID: 0097
Revises: 0096
Create Date: 2026-05-23
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0097"
down_revision = "0096"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cultural_tips (
            id               uuid         PRIMARY KEY DEFAULT app.uuidv7(),
            country_code     char(2)      NOT NULL,
            context          varchar(50)  NOT NULL,
            kind             varchar(30)  NOT NULL,
            title            jsonb        NOT NULL DEFAULT '{}',
            body_md          jsonb        NOT NULL DEFAULT '{}',
            severity         varchar(10)  NOT NULL DEFAULT 'info',
            heritage_pub_id  uuid,
            is_active        boolean      NOT NULL DEFAULT true,
            sort_order       int          NOT NULL DEFAULT 0,
            created_at       timestamptz  NOT NULL DEFAULT now(),
            updated_at       timestamptz  NOT NULL DEFAULT now(),
            CONSTRAINT cultural_tips_severity_check
                CHECK (severity IN ('info', 'warning', 'critical'))
        )
        """
    )

    op.execute(
        """
        CREATE TRIGGER tg_cultural_tips_updated_at
            BEFORE UPDATE ON cultural_tips
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at()
        """
    )

    op.execute(
        """
        CREATE INDEX ix_cultural_tips_country_context
            ON cultural_tips (country_code, context, sort_order)
            WHERE is_active = true
        """
    )

    op.execute(
        """
        CREATE INDEX ix_cultural_tips_heritage
            ON cultural_tips (heritage_pub_id)
            WHERE heritage_pub_id IS NOT NULL
        """
    )

    op.execute(
        """
        COMMENT ON TABLE cultural_tips IS
            'Admin-managed cultural etiquette cards shown to travellers. '
            'JSONB title/body_md supports multi-locale content. '
            'Indexed by (country_code, context, sort_order) for fast mobile lookups.';
        COMMENT ON COLUMN cultural_tips.context IS
            'Display context bucket: mosque|bazaar|restaurant|home_visit|general|'
            'dress_code|archaeological_site';
        COMMENT ON COLUMN cultural_tips.kind IS
            'Tip category: dress_code|behavior|prohibited|recommended|greeting';
        COMMENT ON COLUMN cultural_tips.severity IS
            'Urgency level shown as card colour in the mobile UI: info|warning|critical';
        COMMENT ON COLUMN cultural_tips.heritage_pub_id IS
            'Optional pin to a specific heritage_objects.id for site-scoped tips.';
        """
    )

    _seed_uzbekistan_tips()


def _seed_uzbekistan_tips() -> None:
    tips = [
        # (country, context, kind, title_en, body_en, title_uz, body_uz, severity)
        (
            "UZ",
            "mosque",
            "dress_code",
            "Dress Code for Mosques",
            "Both men and women must cover their arms and legs. "
            "Women must wear a headscarf inside.",
            "Masjidlarda kiyinish",
            "Erkaklar va ayollar qo''l va oyoqlarini yopishi kerak. "
            "Ayollar ichkarida bosh ro''mol taqishi shart.",
            "critical",
        ),
        (
            "UZ",
            "mosque",
            "behavior",
            "Mosque Etiquette",
            "Remove shoes before entering. Speak quietly. Do not take photos during prayer times.",
            "Masjid odob-axloqi",
            "Kirishdan oldin poyabzalni yeching. Jimgina gapiring. Namoz vaqtida rasm olmang.",
            "warning",
        ),
        (
            "UZ",
            "mosque",
            "prohibited",
            "Photography Rules",
            "Ask permission before photographing inside mosques. "
            "Photography is prohibited during prayers.",
            "Suratga olish qoidalari",
            "Masjid ichida rasm olishdan oldin ruxsat so''rang. "
            "Namoz paytida rasm olish taqiqlangan.",
            "warning",
        ),
        (
            "UZ",
            "bazaar",
            "behavior",
            "Bazaar Etiquette",
            "Bargaining is expected and welcome. "
            "Start at 50-60% of the asking price. Be polite and smile.",
            "Bozor odob-axloqi",
            "Savdolashish kutiladi va xush ko''riladi. "
            "So''ralgan narxning 50-60% dan boshlang. Muloyim va jilmayib turing.",
            "info",
        ),
        (
            "UZ",
            "bazaar",
            "behavior",
            "Handling Goods",
            "Ask before touching expensive items like silk and carpets. "
            "Pick up fruit and vegetables yourself.",
            "Tovarlarni ushlab ko''rish",
            "Ipak va gilamlar kabi qimmat buyumlarni ushlab ko''rishdan oldin so''rang. "
            "Meva-sabzavotlarni o''zingiz oling.",
            "info",
        ),
        (
            "UZ",
            "general",
            "greeting",
            "Greetings",
            "The traditional greeting is ''Assalomu alaykum''. "
            "A handshake with the right hand is standard between men.",
            "Salomlashish",
            "An''anaviy salomlashuv — ''Assalomu alaykum''. "
            "O''ng qo''l bilan qo''l berishish erkaklar orasida odatiy.",
            "info",
        ),
        (
            "UZ",
            "general",
            "behavior",
            "Ramadan Etiquette",
            "During Ramadan, avoid eating, drinking, or smoking in public "
            "during daylight hours out of respect.",
            "Ramazon odob-axloqi",
            "Ramazon davomida kun bo''yi ommaviy joylarda hurmat yuzasidan "
            "ovqat yemang, ichimlik ichmang va chekimang.",
            "warning",
        ),
        (
            "UZ",
            "home_visit",
            "behavior",
            "Visiting a Home",
            "Remove shoes at the entrance. Accept tea when offered — "
            "refusing is impolite. Bring a small gift.",
            "Uyga tashrif",
            "Kirishda poyabzalni yeching. Taklif qilingan choyni qabul qiling — "
            "rad etish odobsizlik. Kichik sovg''a olib boring.",
            "info",
        ),
        (
            "UZ",
            "restaurant",
            "behavior",
            "Dining Etiquette",
            "It is polite to try every dish offered. "
            "Leaving a little food shows you are satisfied.",
            "Ovqatlanish odob-axloqi",
            "Taklif qilingan har bir taomni tatib ko''rish odoblilik. "
            "Biroz ovqat qoldirish to''yganligingizni bildiradi.",
            "info",
        ),
        (
            "UZ",
            "general",
            "prohibited",
            "Alcohol",
            "Alcohol is available in restaurants but should be consumed "
            "discreetly. Public drinking is frowned upon.",
            "Alkogol",
            "Alkogol restoranlarda mavjud, lekin ehtiyotkorlik bilan "
            "iste''mol qiling. Ommaviy joyda ichish yaxshi ko''rilmaydi.",
            "info",
        ),
        (
            "UZ",
            "general",
            "dress_code",
            "General Dress Code",
            "Dress modestly, especially in religious areas and bazaars. "
            "Shorts are acceptable in tourist areas.",
            "Umumiy kiyinish qoidasi",
            "Ayniqsa diniy joylarda va bozorlarda kamtarona kiyining. "
            "Turist hududlarida shim kiyish mumkin.",
            "info",
        ),
        (
            "UZ",
            "archaeological_site",
            "behavior",
            "Heritage Site Rules",
            "Do not climb on ancient walls or ruins — they are fragile. Stay on marked paths.",
            "Meros joylari qoidalari",
            "Qadimiy devor va xarobalarga chiqmang — ular mo''rt. Belgilangan yo''lda yuring.",
            "critical",
        ),
    ]

    conn = op.get_bind()
    stmt = sa.text(
        """
        INSERT INTO cultural_tips
            (country_code, context, kind, title, body_md, severity)
        VALUES (
            :country, :context, :kind,
            jsonb_build_object('en', :title_en, 'uz', :title_uz),
            jsonb_build_object('en', :body_en,  'uz', :body_uz),
            :severity
        )
        """
    )
    for row in tips:
        (
            country,
            context,
            kind,
            title_en,
            body_en,
            title_uz,
            body_uz,
            severity,
        ) = row
        # Restore literal apostrophes that were doubled for the data literals above.
        conn.execute(
            stmt,
            {
                "country": country,
                "context": context,
                "kind": kind,
                "title_en": title_en.replace("''", "'"),
                "title_uz": title_uz.replace("''", "'"),
                "body_en": body_en.replace("''", "'"),
                "body_uz": body_uz.replace("''", "'"),
                "severity": severity,
            },
        )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS cultural_tips CASCADE")
