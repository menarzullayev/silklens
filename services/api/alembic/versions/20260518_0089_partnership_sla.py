"""Partnership tiers, agreements, SLA reports, uptime windows, partner badges.

FAZA 6 / Wave-8 Agent-5. Formalises the UNESCO / B2G / NGO partnership
surface that sits on top of the existing ``b2g_partnerships`` table
introduced in 0084_b2g_partnerships. The two layers are complementary:
0084 tracks the raw MOU paperwork; this migration adds the *operational*
side — SLA monitoring, uptime windows, issued badges, and tier definitions
that drive feature gates.

Tables introduced:

  partnership_tiers        — slug-keyed feature-gate + SLA template rows.
  partnership_agreements   — one per live or historical arrangement; ties a
                             tenant to a tier and records lifecycle state.
  sla_reports              — generated period snapshots (uptime %, incidents).
  uptime_windows           — planned / unplanned service disruptions + a
                             seeded resolved maintenance example.
  partner_badges           — issued per-agreement, linked to heritage objects
                             for public display.

ALTER TABLE:
  heritage_objects — adds ``partner_badge_ids uuid[]`` (denormalised, no FK,
  for low-latency read on the heritage detail view).

Seeds:
  4 tiers, 2 agreements (UZ Tourism + UNESCO WHC), 2 badges.

Revision ID: 0089_partnership_sla
Revises: 0084_b2g_partnerships
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0089_partnership_sla"
down_revision: str | Sequence[str] | None = "0084_b2g_partnerships"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        -- ------------------------------------------------------------------ --
        --  partnership_tiers                                                  --
        -- ------------------------------------------------------------------ --
        CREATE TABLE IF NOT EXISTS partnership_tiers (
            id               uuid        PRIMARY KEY DEFAULT gen_uuid_v7(),
            slug             text        NOT NULL UNIQUE,
            name             jsonb       NOT NULL DEFAULT '{}'::jsonb,
            kind             text        NOT NULL
                                CHECK (kind IN (
                                    'academic','government','ngo','unesco',
                                    'icomos','national_park','museum_network'
                                )),
            benefits         jsonb       NOT NULL DEFAULT '[]'::jsonb,
            sla_uptime_pct   numeric(5,2) NOT NULL DEFAULT 99.5,
            max_api_calls_per_day int    NOT NULL DEFAULT 10000,
            includes_white_label bool   NOT NULL DEFAULT false,
            revenue_share_pct numeric(5,2) NOT NULL DEFAULT 0,
            created_at       timestamptz NOT NULL DEFAULT now()
        );

        -- ------------------------------------------------------------------ --
        --  partnership_agreements                                             --
        -- ------------------------------------------------------------------ --
        CREATE TABLE IF NOT EXISTS partnership_agreements (
            id               uuid        PRIMARY KEY DEFAULT gen_uuid_v7(),
            tenant_id        uuid        NOT NULL
                                REFERENCES tenants(id) ON DELETE RESTRICT,
            partner_name     text        NOT NULL,
            partner_kind     text        NOT NULL
                                CHECK (partner_kind IN (
                                    'academic','government','ngo','unesco',
                                    'icomos','national_park','museum_network'
                                )),
            tier_id          uuid        NOT NULL
                                REFERENCES partnership_tiers(id) ON DELETE RESTRICT,
            status           text        NOT NULL DEFAULT 'draft'
                                CHECK (status IN (
                                    'draft','negotiating','active',
                                    'expired','terminated','paused'
                                )),
            signed_at        timestamptz,
            expires_at       timestamptz,
            auto_renew       bool        NOT NULL DEFAULT false,
            annual_value_usd numeric(20,4),
            contact_name     text,
            contact_email    text,
            contact_phone    text,
            notes_md         text,
            mou_url          text        CHECK (mou_url IS NULL OR mou_url LIKE 'https://%'),
            created_at       timestamptz NOT NULL DEFAULT now(),
            updated_at       timestamptz NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_partnership_agreements_tenant
            ON partnership_agreements(tenant_id);
        CREATE INDEX IF NOT EXISTS idx_partnership_agreements_status
            ON partnership_agreements(status);

        -- ------------------------------------------------------------------ --
        --  sla_reports                                                        --
        -- ------------------------------------------------------------------ --
        CREATE TABLE IF NOT EXISTS sla_reports (
            id                        uuid  PRIMARY KEY DEFAULT gen_uuid_v7(),
            agreement_id              uuid  NOT NULL
                                        REFERENCES partnership_agreements(id)
                                        ON DELETE CASCADE,
            period_start              date  NOT NULL,
            period_end                date  NOT NULL,
            measured_uptime_pct       numeric(5,2) NOT NULL,
            incidents_count           int   NOT NULL DEFAULT 0,
            incidents_resolved_in_sla int   NOT NULL DEFAULT 0,
            api_calls_total           bigint NOT NULL DEFAULT 0,
            data_exports_count        int   NOT NULL DEFAULT 0,
            generated_at              timestamptz NOT NULL DEFAULT now(),
            report_url                text,
            created_at                timestamptz NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_sla_reports_agreement
            ON sla_reports(agreement_id, period_start);

        -- ------------------------------------------------------------------ --
        --  uptime_windows                                                     --
        -- ------------------------------------------------------------------ --
        CREATE TABLE IF NOT EXISTS uptime_windows (
            id                uuid        PRIMARY KEY DEFAULT gen_uuid_v7(),
            started_at        timestamptz NOT NULL,
            ended_at          timestamptz,
            kind              text        NOT NULL
                                CHECK (kind IN ('scheduled','incident','partial')),
            severity          text        NOT NULL
                                CHECK (severity IN ('info','degraded','outage')),
            description_md    text,
            affected_services text[]      NOT NULL DEFAULT ARRAY['api'],
            is_resolved       bool        NOT NULL DEFAULT false,
            resolution_notes  text,
            created_at        timestamptz NOT NULL DEFAULT now()
        );

        -- ------------------------------------------------------------------ --
        --  partner_badges                                                     --
        -- ------------------------------------------------------------------ --
        CREATE TABLE IF NOT EXISTS partner_badges (
            id               uuid  PRIMARY KEY DEFAULT gen_uuid_v7(),
            agreement_id     uuid  NOT NULL
                                REFERENCES partnership_agreements(id)
                                ON DELETE CASCADE,
            badge_kind       text  NOT NULL
                                CHECK (badge_kind IN (
                                    'unesco_partner','official_gov','academic',
                                    'verified_museum','heritage_champion','data_provider'
                                )),
            issued_at        timestamptz NOT NULL DEFAULT now(),
            expires_at       timestamptz,
            display_on_heritage jsonb  NOT NULL DEFAULT '[]'::jsonb,
            is_active        bool   NOT NULL DEFAULT true
        );

        CREATE INDEX IF NOT EXISTS idx_partner_badges_agreement
            ON partner_badges(agreement_id);
        CREATE INDEX IF NOT EXISTS idx_partner_badges_active
            ON partner_badges(is_active) WHERE is_active = true;

        -- ------------------------------------------------------------------ --
        --  Extend heritage_objects (denormalised badge list for read perf)   --
        -- ------------------------------------------------------------------ --
        ALTER TABLE heritage_objects
            ADD COLUMN IF NOT EXISTS partner_badge_ids uuid[];

        -- ------------------------------------------------------------------ --
        --  SEEDS — tiers                                                      --
        -- ------------------------------------------------------------------ --
        INSERT INTO partnership_tiers
            (slug, name, kind, benefits, sla_uptime_pct,
             max_api_calls_per_day, includes_white_label, revenue_share_pct)
        VALUES
            (
                'free_ngo',
                '{"en":"Free NGO","uz":"Bepul NGO"}'::jsonb,
                'ngo',
                '["heritage_read","basic_export","community_badge"]'::jsonb,
                99.0, 5000, false, 0
            ),
            (
                'standard_gov',
                '{"en":"Standard Government","uz":"Standart hukumat"}'::jsonb,
                'government',
                '["heritage_read","heritage_write","bulk_export","official_gov_badge","priority_support"]'::jsonb,
                99.5, 50000, false, 0
            ),
            (
                'premium_partner',
                '{"en":"Premium Partner","uz":"Premium hamkor"}'::jsonb,
                'academic',
                '["heritage_read","heritage_write","bulk_export","ai_analysis","white_label","sla_report","priority_support"]'::jsonb,
                99.9, 200000, true, 5
            ),
            (
                'strategic_ally',
                '{"en":"Strategic Ally","uz":"Strategik ittifoqchi"}'::jsonb,
                'unesco',
                '["heritage_read","heritage_write","heritage_delete","bulk_export","ai_analysis","white_label","sla_report","dedicated_support","revenue_share"]'::jsonb,
                99.95, 0, true, 10
            )
        ON CONFLICT (slug) DO NOTHING;

        -- ------------------------------------------------------------------ --
        --  SEEDS — agreements                                                 --
        -- ------------------------------------------------------------------ --
        INSERT INTO partnership_agreements
            (id, tenant_id, partner_name, partner_kind, tier_id, status,
             signed_at, expires_at, auto_renew, annual_value_usd,
             contact_name, contact_email, notes_md)
        VALUES
            (
                '10000000-0000-0000-0000-000000000001'::uuid,
                '00000000-0000-0000-0000-000000000001'::uuid,
                'Uzbekistan Tourism Vazirligi',
                'government',
                (SELECT id FROM partnership_tiers WHERE slug = 'standard_gov'),
                'active',
                '2026-01-01 00:00:00+00',
                '2027-01-01 00:00:00+00',
                true,
                50000.0000,
                'Jamshid Toshmatov',
                'j.toshmatov@tourism.gov.uz',
                'Official digital heritage data-sharing agreement with the Ministry of Tourism.'
            ),
            (
                '10000000-0000-0000-0000-000000000002'::uuid,
                '00000000-0000-0000-0000-000000000001'::uuid,
                'UNESCO World Heritage Centre',
                'unesco',
                (SELECT id FROM partnership_tiers WHERE slug = 'strategic_ally'),
                'negotiating',
                NULL,
                NULL,
                false,
                NULL,
                'Dr. Aiko Suzuki',
                'a.suzuki@unesco.org',
                'Observer status under WHC digital-preservation initiative. MOU under legal review.'
            )
        ON CONFLICT (id) DO NOTHING;

        -- ------------------------------------------------------------------ --
        --  SEEDS — uptime window (example resolved maintenance)              --
        -- ------------------------------------------------------------------ --
        INSERT INTO uptime_windows
            (started_at, ended_at, kind, severity, description_md,
             affected_services, is_resolved, resolution_notes)
        VALUES (
            '2026-05-15 02:00:00+00',
            '2026-05-15 04:00:00+00',
            'scheduled',
            'info',
            '**Scheduled maintenance** — Postgres minor-version upgrade from 16.2 to 16.3. API in read-only mode during window.',
            ARRAY['api','database'],
            true,
            'Upgrade completed without incident. Downtime: 0 min (hot-standby failover used).'
        );

        -- ------------------------------------------------------------------ --
        --  SEEDS — partner badges                                            --
        -- ------------------------------------------------------------------ --
        INSERT INTO partner_badges
            (agreement_id, badge_kind, issued_at, display_on_heritage, is_active)
        VALUES
            (
                '10000000-0000-0000-0000-000000000002'::uuid,
                'unesco_partner',
                '2026-05-18 00:00:00+00',
                '[]'::jsonb,
                true
            ),
            (
                '10000000-0000-0000-0000-000000000001'::uuid,
                'official_gov',
                '2026-05-18 00:00:00+00',
                '[]'::jsonb,
                true
            )
        ON CONFLICT DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE heritage_objects DROP COLUMN IF EXISTS partner_badge_ids;
        DROP TABLE IF EXISTS partner_badges;
        DROP TABLE IF EXISTS sla_reports;
        DROP TABLE IF EXISTS uptime_windows;
        DROP TABLE IF EXISTS partnership_agreements;
        DROP TABLE IF EXISTS partnership_tiers;
        """
    )
