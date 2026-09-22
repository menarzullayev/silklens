"""Enterprise SLA tiers, subscriptions, incidents, usage snapshots, credits.

FAZA 7 — Wave-8 Agent-7: B2B Enterprise API with SLA + real uptime tracking.

New tables:
  enterprise_sla_tiers          — tier catalogue (starter/professional/enterprise/strategic)
  enterprise_subscriptions      — account ↔ tier lifecycle
  sla_incident_reports          — P1-P4 incidents (public + internal)
  enterprise_usage_snapshots    — daily snapshot per account (powers compliance report)
  enterprise_credits            — SLA breach credits

ALTERs:
  api_keys                      — adds sla_tier_id + burst_limit_per_min

Seeds:
  4 SLA tiers, 1 starter subscription, 1 resolved P2 incident (default tenant).

Revision ID: 0091_enterprise_sla
Revises: 0087_virtual_tours
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0091_enterprise_sla"
down_revision: str | Sequence[str] | None = "0087_virtual_tours"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # enterprise_sla_tiers
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE enterprise_sla_tiers (
            id                          uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            slug                        text NOT NULL UNIQUE,
            name                        jsonb NOT NULL DEFAULT '{}'::jsonb,
            monthly_price_usd           numeric(20, 4),
            uptime_commitment_pct       numeric(5, 2) NOT NULL CHECK (uptime_commitment_pct BETWEEN 0 AND 100),
            support_response_hours      smallint NOT NULL CHECK (support_response_hours > 0),
            dedicated_csm               bool NOT NULL DEFAULT false,
            custom_domain               bool NOT NULL DEFAULT false,
            max_seats                   int,
            api_rate_limit_per_min      int NOT NULL DEFAULT 60 CHECK (api_rate_limit_per_min > 0),
            analytics_retention_days    int NOT NULL DEFAULT 90,
            includes_white_label        bool NOT NULL DEFAULT false,
            white_label_subdomains      int NOT NULL DEFAULT 0,
            created_at                  timestamptz NOT NULL DEFAULT now(),
            CHECK (slug ~ '^[a-z][a-z0-9_]*$'),
            CHECK (max_seats IS NULL OR max_seats > 0)
        );

        CREATE INDEX idx_enterprise_sla_tiers_slug
            ON enterprise_sla_tiers (slug);
        """
    )

    # Seed 4 tiers
    op.execute(
        """
        INSERT INTO enterprise_sla_tiers (
            slug, name, monthly_price_usd, uptime_commitment_pct,
            support_response_hours, dedicated_csm, custom_domain,
            max_seats, api_rate_limit_per_min, analytics_retention_days,
            includes_white_label, white_label_subdomains
        ) VALUES
        (
            'starter',
            '{"en":"Starter","ru":"Стартовый","uz":"Starter"}'::jsonb,
            499.0000,
            99.00,
            24,
            false,
            false,
            100,
            1000,
            90,
            false,
            0
        ),
        (
            'professional',
            '{"en":"Professional","ru":"Профессиональный","uz":"Professional"}'::jsonb,
            1999.0000,
            99.50,
            8,
            false,
            true,
            500,
            5000,
            365,
            false,
            0
        ),
        (
            'enterprise',
            '{"en":"Enterprise","ru":"Корпоративный","uz":"Enterprise"}'::jsonb,
            4999.0000,
            99.90,
            4,
            false,
            true,
            NULL,
            20000,
            730,
            true,
            5
        ),
        (
            'strategic',
            '{"en":"Strategic Partner","ru":"Стратегический партнёр","uz":"Strategik hamkor"}'::jsonb,
            NULL,
            99.95,
            1,
            true,
            true,
            NULL,
            100000,
            1095,
            true,
            20
        );
        """
    )

    # ------------------------------------------------------------------
    # enterprise_subscriptions
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE enterprise_subscriptions (
            id                      uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            enterprise_account_id   uuid NOT NULL REFERENCES enterprise_accounts(id) ON DELETE CASCADE,
            sla_tier_id             uuid NOT NULL REFERENCES enterprise_sla_tiers(id) ON DELETE RESTRICT,
            status                  text NOT NULL DEFAULT 'trial' CHECK (status IN (
                'trial','active','past_due','canceled','expired'
            )),
            billing_period          text NOT NULL DEFAULT 'monthly' CHECK (billing_period IN (
                'monthly','quarterly','yearly'
            )),
            started_at              timestamptz NOT NULL DEFAULT now(),
            current_period_end      timestamptz NOT NULL,
            trial_ends_at           timestamptz,
            mrr_usd                 numeric(20, 4) NOT NULL DEFAULT 0 CHECK (mrr_usd >= 0),
            contracted_annual_usd   numeric(20, 4) CHECK (contracted_annual_usd IS NULL OR contracted_annual_usd >= 0),
            created_at              timestamptz NOT NULL DEFAULT now(),
            updated_at              timestamptz NOT NULL DEFAULT now()
        );

        CREATE INDEX idx_enterprise_subscriptions_account
            ON enterprise_subscriptions (enterprise_account_id);
        CREATE INDEX idx_enterprise_subscriptions_status
            ON enterprise_subscriptions (status) WHERE status IN ('trial','active','past_due');

        CREATE TRIGGER tg_enterprise_subscriptions_updated_at
            BEFORE UPDATE ON enterprise_subscriptions
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # ------------------------------------------------------------------
    # sla_incident_reports
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE sla_incident_reports (
            id                      uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            enterprise_account_id   uuid REFERENCES enterprise_accounts(id) ON DELETE SET NULL,
            title                   text NOT NULL,
            severity                text NOT NULL CHECK (severity IN ('p1','p2','p3','p4')),
            affected_services       text[] NOT NULL DEFAULT ARRAY[]::text[],
            status                  text NOT NULL DEFAULT 'investigating' CHECK (status IN (
                'investigating','identified','monitoring','resolved'
            )),
            started_at              timestamptz NOT NULL DEFAULT now(),
            resolved_at             timestamptz,
            root_cause              text,
            remediation_md          text,
            post_mortem_url         text,
            public_visible          bool NOT NULL DEFAULT false,
            created_at              timestamptz NOT NULL DEFAULT now(),
            updated_at              timestamptz NOT NULL DEFAULT now()
        );

        CREATE INDEX idx_sla_incidents_time_severity
            ON sla_incident_reports (started_at DESC, severity);
        CREATE INDEX idx_sla_incidents_account
            ON sla_incident_reports (enterprise_account_id)
            WHERE enterprise_account_id IS NOT NULL;
        CREATE INDEX idx_sla_incidents_public
            ON sla_incident_reports (started_at DESC)
            WHERE public_visible = true;

        CREATE TRIGGER tg_sla_incident_reports_updated_at
            BEFORE UPDATE ON sla_incident_reports
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # ------------------------------------------------------------------
    # enterprise_usage_snapshots
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE enterprise_usage_snapshots (
            id                      uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            enterprise_account_id   uuid NOT NULL REFERENCES enterprise_accounts(id) ON DELETE CASCADE,
            snapshot_date           date NOT NULL,
            api_calls               bigint NOT NULL DEFAULT 0 CHECK (api_calls >= 0),
            successful_calls        bigint NOT NULL DEFAULT 0 CHECK (successful_calls >= 0),
            error_calls             bigint NOT NULL DEFAULT 0 CHECK (error_calls >= 0),
            avg_latency_ms          numeric(6, 1) NOT NULL DEFAULT 0 CHECK (avg_latency_ms >= 0),
            p95_latency_ms          numeric(6, 1) NOT NULL DEFAULT 0 CHECK (p95_latency_ms >= 0),
            data_exported_mb        numeric(10, 2) NOT NULL DEFAULT 0 CHECK (data_exported_mb >= 0),
            active_seats            int NOT NULL DEFAULT 0 CHECK (active_seats >= 0),
            created_at              timestamptz NOT NULL DEFAULT now(),
            UNIQUE (enterprise_account_id, snapshot_date)
        );

        CREATE INDEX idx_enterprise_usage_snapshots_account_date
            ON enterprise_usage_snapshots (enterprise_account_id, snapshot_date DESC);
        """
    )

    # ------------------------------------------------------------------
    # enterprise_credits
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE enterprise_credits (
            id                      uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            enterprise_account_id   uuid NOT NULL REFERENCES enterprise_accounts(id) ON DELETE CASCADE,
            amount_usd              numeric(20, 4) NOT NULL CHECK (amount_usd > 0),
            reason                  text NOT NULL,
            applied_at              timestamptz NOT NULL DEFAULT now(),
            expires_at              timestamptz,
            created_at              timestamptz NOT NULL DEFAULT now()
        );

        CREATE INDEX idx_enterprise_credits_account
            ON enterprise_credits (enterprise_account_id, applied_at DESC);
        """
    )

    # ------------------------------------------------------------------
    # ALTER api_keys — add sla_tier_id + burst_limit_per_min
    # ------------------------------------------------------------------
    op.execute(
        """
        ALTER TABLE api_keys
            ADD COLUMN IF NOT EXISTS sla_tier_id       uuid REFERENCES enterprise_sla_tiers(id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS burst_limit_per_min int CHECK (burst_limit_per_min IS NULL OR burst_limit_per_min > 0);

        CREATE INDEX IF NOT EXISTS idx_api_keys_sla_tier
            ON api_keys (sla_tier_id) WHERE sla_tier_id IS NOT NULL;
        """
    )

    # ------------------------------------------------------------------
    # Seeds — 1 starter subscription + 1 resolved P2 incident (default tenant)
    # ------------------------------------------------------------------
    op.execute(
        """
        DO $$
        DECLARE
            v_account_id    uuid;
            v_tier_id       uuid;
            v_tenant_id     uuid := '00000000-0000-0000-0000-000000000001'::uuid;
        BEGIN
            -- Fetch or create the default enterprise account for the seed tenant
            SELECT id INTO v_account_id
            FROM enterprise_accounts
            WHERE tenant_id = v_tenant_id
            LIMIT 1;

            IF v_account_id IS NULL THEN
                INSERT INTO enterprise_accounts (tenant_id, company_name, primary_contact_email, tier)
                VALUES (v_tenant_id, 'SilkLens Demo Corp', 'enterprise@silklens.uz', 'premium')
                RETURNING id INTO v_account_id;
            END IF;

            -- Starter tier
            SELECT id INTO v_tier_id FROM enterprise_sla_tiers WHERE slug = 'starter';

            -- Subscription (trial → active in 30 days)
            INSERT INTO enterprise_subscriptions (
                enterprise_account_id, sla_tier_id, status, billing_period,
                started_at, current_period_end, trial_ends_at, mrr_usd
            ) VALUES (
                v_account_id, v_tier_id, 'trial', 'monthly',
                now(), now() + interval '30 days', now() + interval '14 days', 499.0000
            ) ON CONFLICT DO NOTHING;

            -- Resolved P2 incident (platform-wide, public)
            INSERT INTO sla_incident_reports (
                enterprise_account_id, title, severity, affected_services,
                status, started_at, resolved_at,
                root_cause, remediation_md, public_visible
            ) VALUES (
                NULL,
                'Elevated API latency — Heritage Search endpoint',
                'p2',
                ARRAY['heritage_search', 'api_gateway'],
                'resolved',
                now() - interval '3 days',
                now() - interval '3 days' + interval '2 hours 15 minutes',
                'PostgreSQL query planner chose a sequential scan on heritage_objects due to stale statistics after bulk import.',
                E'## Remediation\n\n- Ran `ANALYZE heritage_objects` to refresh planner statistics.\n- Added `pg_cron` job to run `ANALYZE` nightly.\n- Deployed connection-pool tuning (PgBouncer pool_size 50 → 80).',
                true
            ) ON CONFLICT DO NOTHING;
        END;
        $$;
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE api_keys DROP COLUMN IF EXISTS burst_limit_per_min;")
    op.execute("ALTER TABLE api_keys DROP COLUMN IF EXISTS sla_tier_id;")
    op.execute("DROP TABLE IF EXISTS enterprise_credits CASCADE;")
    op.execute("DROP TABLE IF EXISTS enterprise_usage_snapshots CASCADE;")
    op.execute("DROP TABLE IF EXISTS sla_incident_reports CASCADE;")
    op.execute("DROP TABLE IF EXISTS enterprise_subscriptions CASCADE;")
    op.execute("DROP TABLE IF EXISTS enterprise_sla_tiers CASCADE;")
