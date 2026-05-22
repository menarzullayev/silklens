"""languages + scripts admin registry.

SILK-0064: BCP-47 language registry with provider codes, RTL flag,
and admin on/off toggle. Enables 6-language support management.

Tables introduced:

  languages  — BCP-47 catalogue with NLLB/DeepL/Google provider codes,
               RTL flag, admin is_active toggle, and sort_order for UI.

Seeds:
  7 initial languages: uz, ru, en, zh, de, ko, ar (ar is RTL).

Revision ID: 0094
Revises: 0093
Create Date: 2026-05-23
"""

from __future__ import annotations

from sqlalchemy import text

from alembic import op

revision = "0094"
down_revision = "0093"
branch_labels = None
depends_on = None

# (bcp47_tag, endonym, exonym_en, nllb_code, deepl_code, google_code, is_rtl, sort_order)
_LANGUAGES: list[tuple] = [
    ("uz", "O'zbek",   "Uzbek",   "uzb_Latn", None,    "uz", False, 1),
    ("ru", "Русский",  "Russian", "rus_Cyrl", "RU",    "ru", False, 2),
    ("en", "English",  "English", "eng_Latn", "EN-US", "en", False, 3),
    ("zh", "中文",     "Chinese", "zho_Hans", "ZH",    "zh", False, 4),
    ("de", "Deutsch",  "German",  "deu_Latn", "DE",    "de", False, 5),
    ("ko", "한국어",   "Korean",  "kor_Hang", "KO",    "ko", False, 6),
    ("ar", "العربية",  "Arabic",  "arb_Arab", "AR",    "ar", True,  7),
]


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS languages (
            bcp47_tag   varchar(20)  PRIMARY KEY,
            endonym     varchar(100) NOT NULL,
            exonym_en   varchar(100) NOT NULL,
            nllb_code   varchar(30),
            deepl_code  varchar(10),
            google_code varchar(10),
            is_rtl      boolean      NOT NULL DEFAULT false,
            is_active   boolean      NOT NULL DEFAULT true,
            sort_order  int          NOT NULL DEFAULT 0,
            created_at  timestamptz  NOT NULL DEFAULT now(),
            updated_at  timestamptz  NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        COMMENT ON TABLE languages IS
            'BCP-47 language catalogue. Admin-managed via is_active toggle. '
            'Provider codes drive runtime routing to NLLB-200, DeepL, and Google Translate.';
        COMMENT ON COLUMN languages.bcp47_tag IS
            'RFC 5646 / BCP-47 primary language subtag (e.g. ''uz'', ''zh-Hant'').';
        COMMENT ON COLUMN languages.endonym IS
            'Language name written in that language itself (e.g. ''O''''zbek'', ''Русский'').';
        COMMENT ON COLUMN languages.nllb_code IS
            'Facebook NLLB-200 model language code used for on-prem translation.';
        COMMENT ON COLUMN languages.deepl_code IS
            'DeepL API target-language code. NULL if DeepL does not support this language.';
        COMMENT ON COLUMN languages.is_active IS
            'Admin toggle. When false the language is hidden from end-user surfaces '
            'but its data is preserved for future re-activation.';
        COMMENT ON COLUMN languages.sort_order IS
            'Display order on language-picker UIs. Lower = higher.';
        """
    )

    op.execute(
        """
        CREATE TRIGGER tg_languages_updated_at
            BEFORE UPDATE ON languages
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at()
        """
    )

    # Partial index for active-language UI queries (sort_order ASC WHERE is_active).
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_languages_active_sort
            ON languages (sort_order)
            WHERE is_active = true
        """
    )

    # Seed the 7 launch languages via bound parameters — no string interpolation.
    _insert = text(
        """
        INSERT INTO languages
            (bcp47_tag, endonym, exonym_en, nllb_code, deepl_code,
             google_code, is_rtl, sort_order)
        VALUES
            (:tag, :endonym, :exonym, :nllb, :deepl,
             :google, :rtl, :sort_order)
        ON CONFLICT (bcp47_tag) DO NOTHING
        """
    )
    bind_rows = [
        {
            "tag": tag, "endonym": endonym, "exonym": exonym,
            "nllb": nllb, "deepl": deepl, "google": google,
            "rtl": rtl, "sort_order": order,
        }
        for tag, endonym, exonym, nllb, deepl, google, rtl, order in _LANGUAGES
    ]
    conn = op.get_bind()
    conn.execute(_insert, bind_rows)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS languages CASCADE")
