"""B2G (business-to-government) partnerships + enterprise tier extension

Wave-6 Agent C lands the formal Government partnership relation. This is
distinct from ordinary ``enterprise_accounts`` because B2G arrangements
involve country-level / regional scope, MOU paperwork, and a non-commercial
terms_md body (national platform deals, grants, data-sharing, digital-ID
integrations — Project-Decisions §28).

Tables introduced:

  b2g_partnerships    — one row per agreement. ``terms_md`` carries the
                        agreed terms (long-form Markdown); ``mou_url`` is
                        the canonical PDF in MinIO; ``agreement_kind`` is
                        the discriminator. Lifecycle status: negotiating
                        → active → expired or terminated.

Also extends ``enterprise_accounts.tier`` to include three new values:
  national_platform   — sovereign deployment of the platform.
  strategic_partner   — high-volume API + co-marketing.
  data_sharing_only   — read-only API for analytics; no platform branding.

Seeds two ``negotiating`` placeholder rows so the admin UI never has an
empty B2G screen in development (Uzbekistan tourism vazirligi + UNESCO).

Revision ID: 0084_b2g_partnerships
Revises: 0083_white_label
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0084_b2g_partnerships"
down_revision: str | Sequence[str] | None = "0083_white_label"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- enterprise_accounts.tier extension -----------------------------------
    op.execute(
        """
        DO $$
        DECLARE
            check_name text;
        BEGIN
            SELECT conname INTO check_name
            FROM pg_constraint
            WHERE conrelid = 'enterprise_accounts'::regclass
              AND contype = 'c'
              AND pg_get_constraintdef(oid) LIKE '%tier%';
            IF check_name IS NOT NULL THEN
                EXECUTE format(
                    'ALTER TABLE enterprise_accounts DROP CONSTRAINT %I',
                    check_name
                );
            END IF;
        END
        $$;

        ALTER TABLE enterprise_accounts
            ADD CONSTRAINT enterprise_accounts_tier_check
            CHECK (tier IN (
                'standard',
                'premium',
                'strategic',
                'national_platform',
                'strategic_partner',
                'data_sharing_only'
            ));
        """
    )

    # --- b2g_partnerships -----------------------------------------------------
    op.execute(
        """
        CREATE TABLE b2g_partnerships (
            id                      uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            tenant_id               uuid NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            government_entity_name  text NOT NULL,
            country_code            char(2) NOT NULL,
            region_code             text,
            mou_url                 text,
            mou_signed_at           timestamptz,
            agreement_kind          text NOT NULL CHECK (agreement_kind IN (
                'national_platform','grant','data_sharing','digital_id_integration'
            )),
            terms_md                text NOT NULL DEFAULT '',
            status                  text NOT NULL DEFAULT 'negotiating' CHECK (status IN (
                'negotiating','active','expired','terminated'
            )),
            created_at              timestamptz NOT NULL DEFAULT now(),
            updated_at              timestamptz NOT NULL DEFAULT now(),
            CHECK (country_code ~ '^[A-Z]{2}$'),
            CHECK (mou_signed_at IS NULL OR status IN ('active','expired','terminated'))
        );

        CREATE INDEX idx_b2g_partnerships_tenant
            ON b2g_partnerships (tenant_id);
        CREATE INDEX idx_b2g_partnerships_country
            ON b2g_partnerships (country_code, status);
        CREATE INDEX idx_b2g_partnerships_status
            ON b2g_partnerships (status, updated_at DESC);

        CREATE TRIGGER tg_b2g_partnerships_updated_at
            BEFORE UPDATE ON b2g_partnerships
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE b2g_partnerships IS
            'Government / NGO partnership records. terms_md carries the agreed '
            'terms (long-form Markdown); mou_url points at the signed PDF.';
        """
    )

    # --- Seed placeholder negotiating partnerships ----------------------------
    op.execute(
        """
        WITH t AS (
            SELECT id FROM tenants
            WHERE id = '00000000-0000-0000-0000-000000000001'::uuid
            LIMIT 1
        )
        INSERT INTO b2g_partnerships (
            tenant_id, government_entity_name, country_code, region_code,
            agreement_kind, terms_md, status
        )
        SELECT t.id, e.gov_name, e.cc, e.region, e.kind, e.terms, 'negotiating'
        FROM t, (VALUES
            ('Uzbekiston Respublikasi Turizm va madaniy meros vazirligi',
             'UZ',
             'national',
             'national_platform',
             '# Draft MOU — Republic of Uzbekistan Ministry of Tourism\n\n'
             'Status: negotiating. Placeholder seed; replace with the executed '
             'document before production.\n'),
            ('UNESCO World Heritage Centre',
             'FR',
             NULL,
             'data_sharing',
             '# Draft MOU — UNESCO World Heritage Centre\n\n'
             'Status: negotiating. Placeholder seed; replace with the executed '
             'document before production.\n')
        ) AS e(gov_name, cc, region, kind, terms);
        """
    )

    # --- Event type for partnership transitions -------------------------------
    op.execute(
        """
        INSERT INTO event_types (event_name, display_name, retention_days, kafka_topic) VALUES
            ('b2g.partnership_status_changed.v1',
             '{"en":"B2G partnership status changed"}'::jsonb,
             1825, 'silklens.b2g.events')
        ON CONFLICT (event_name) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM event_types
        WHERE event_name = 'b2g.partnership_status_changed.v1';
        """
    )

    op.execute("DROP TABLE IF EXISTS b2g_partnerships CASCADE;")

    op.execute(
        """
        ALTER TABLE enterprise_accounts DROP CONSTRAINT IF EXISTS enterprise_accounts_tier_check;
        ALTER TABLE enterprise_accounts
            ADD CONSTRAINT enterprise_accounts_tier_check
            CHECK (tier IN ('standard','premium','strategic'));
        """
    )
