"""White-label reseller onboarding + revenue share

Wave-6 Agent C (B2B + B2G monetization) lands the public reseller onboarding
funnel and the parent/child revenue-share book-keeping table that the billing
service consults when allocating payouts.

Tables introduced:

  reseller_application      — public, anonymous submission of an interest-form
                              from a prospective reseller (tourism agency,
                              government body, academic partner, corporate).
                              Lifecycle: submitted → under_review → approved
                              or rejected (terminal); withdrawn = applicant
                              pulled out before review. ``tenant_id_assigned``
                              is filled on approval with the freshly minted
                              child tenant so the audit trail links forward.

  tenant_revenue_share      — parent × child × period revenue-share rows.
                              PK is composite so the same pair can have a
                              history of rate changes over time. The billing
                              payout job picks the row whose ``effective_from``
                              is most-recent and whose ``effective_until`` is
                              either NULL or in the future.

Permissions seeded:

  reseller:read                       — see submitted applications.
  reseller:approve                    — flip status to approved/rejected.
  reseller:configure_revenue_share    — change parent/child cuts.

Granted to ``super_admin`` (always) and ``tenant_admin`` (so reseller-aware
chains can self-manage their downstream agencies without going through SilkLens
HQ — Project-Decisions §19).

Plan features seeded against the ``enterprise_api`` product's default plan
(seeded ad-hoc here so the entitlement matrix has a row even before billing
data flows). These flag the white-label capabilities a tenant gets when on
the enterprise tier:

  white_label_branding        — full theming, logo, primary/accent colors
  white_label_api_access      — Enterprise API key issuance
  white_label_custom_domain   — vanity domain on tenant_domains

Finally, the ``b2b_accounts.kyc_status`` CHECK constraint is widened to
include ``verified_by_admin`` so the manual review path (Project-Decisions
§19 — small partners cannot pass KYC-by-document and need a human override)
is representable.

Revision ID: 0083_white_label
Revises: 0072_wikidata_link
Create Date: 2026-05-18

Note: this chains after ``0072_wikidata_link`` rather than the current head
``0081_central_asia_currencies``. The Wave-6 merge migration
``0080_central_asia_seed`` already lists ``0084_b2g_partnerships`` as one of
its parents (alongside ``0082_provider_routing`` and ``0084_mfa``); chaining
this pair into that merge is what keeps ``alembic upgrade head`` callable.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0083_white_label"
down_revision: str | Sequence[str] | None = "0072_wikidata_link"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- reseller_application -------------------------------------------------
    op.execute(
        """
        CREATE TABLE reseller_application (
            id                  uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            applicant_email     text NOT NULL,
            applicant_name      text NOT NULL,
            company_name        text NOT NULL,
            country_code        char(2),
            tax_id              text,
            plan_kind           text NOT NULL CHECK (plan_kind IN (
                'tourism_agency','government','academic','corporate'
            )),
            expected_users      int NOT NULL DEFAULT 0 CHECK (expected_users >= 0),
            message             text,
            status              text NOT NULL DEFAULT 'submitted' CHECK (status IN (
                'submitted','under_review','approved','rejected','withdrawn'
            )),
            submitted_at        timestamptz NOT NULL DEFAULT now(),
            reviewed_at         timestamptz,
            reviewed_by         uuid,  -- soft ref to users(id); users is partitioned by residency_region, so no PG-level FK
            notes               text,
            tenant_id_assigned  uuid REFERENCES tenants(id) ON DELETE SET NULL,
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now(),
            CHECK (applicant_email ~ '^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$'),
            CHECK (country_code IS NULL OR country_code ~ '^[A-Z]{2}$'),
            CHECK (reviewed_at IS NULL OR status IN ('approved','rejected','withdrawn','under_review'))
        );

        CREATE INDEX idx_reseller_application_status
            ON reseller_application (status, submitted_at DESC);
        CREATE INDEX idx_reseller_application_email
            ON reseller_application (lower(applicant_email));
        CREATE UNIQUE INDEX uq_reseller_application_open_email_company
            ON reseller_application (lower(applicant_email), lower(company_name))
            WHERE status IN ('submitted','under_review');

        CREATE TRIGGER tg_reseller_application_updated_at
            BEFORE UPDATE ON reseller_application
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE reseller_application IS
            'Public reseller / white-label intake form. Anonymous submission, '
            'reviewed by super_admin or tenant_admin via the reseller router.';
        COMMENT ON COLUMN reseller_application.tenant_id_assigned IS
            'Set on approval — points at the freshly minted child tenant. NULL '
            'before approval and remains NULL on rejection/withdrawal.';
        """
    )

    # --- tenant_revenue_share -------------------------------------------------
    # Composite PK so a (parent, child) pair can have a history of rate
    # changes. The billing job selects the latest ``effective_from`` whose
    # ``effective_until`` is NULL or in the future.
    op.execute(
        """
        CREATE TABLE tenant_revenue_share (
            parent_tenant_id    uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            child_tenant_id     uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            percentage          numeric(5, 2) NOT NULL
                CHECK (percentage >= 0 AND percentage <= 100),
            effective_from      timestamptz NOT NULL DEFAULT now(),
            effective_until     timestamptz,
            notes               text,
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (parent_tenant_id, child_tenant_id, effective_from),
            CHECK (effective_until IS NULL OR effective_until > effective_from),
            CHECK (parent_tenant_id <> child_tenant_id)
        );

        CREATE INDEX idx_tenant_revenue_share_child
            ON tenant_revenue_share (child_tenant_id, effective_from DESC);
        CREATE INDEX idx_tenant_revenue_share_parent_active
            ON tenant_revenue_share (parent_tenant_id, child_tenant_id)
            WHERE effective_until IS NULL;

        CREATE TRIGGER tg_tenant_revenue_share_updated_at
            BEFORE UPDATE ON tenant_revenue_share
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE tenant_revenue_share IS
            'Parent x child revenue cut, time-versioned. Billing payout job '
            'picks the latest still-effective row when allocating funds. The '
            'sum of all active parents for a given child must not exceed 100%; '
            'enforced at service-layer (cross-row math is awkward in a CHECK).';
        """
    )

    # --- Permissions seed -----------------------------------------------------
    op.execute(
        """
        INSERT INTO permissions (slug, description) VALUES
            ('reseller:read',
             'List + read reseller applications'),
            ('reseller:approve',
             'Approve or reject reseller applications'),
            ('reseller:configure_revenue_share',
             'Set parent/child revenue-share percentages')
        ON CONFLICT (slug) DO NOTHING;

        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.slug IN ('super_admin','tenant_admin')
          AND p.slug IN (
              'reseller:read',
              'reseller:approve',
              'reseller:configure_revenue_share'
          )
        ON CONFLICT DO NOTHING;
        """
    )

    # --- Event types ----------------------------------------------------------
    op.execute(
        """
        INSERT INTO event_types (event_name, display_name, retention_days, kafka_topic) VALUES
            ('reseller.applied.v1',
             '{"en":"Reseller application submitted"}'::jsonb,
             365, 'silklens.reseller.events'),
            ('reseller.approved.v1',
             '{"en":"Reseller application approved"}'::jsonb,
             1825, 'silklens.reseller.events'),
            ('reseller.rejected.v1',
             '{"en":"Reseller application rejected"}'::jsonb,
             1825, 'silklens.reseller.events'),
            ('reseller.revenue_share_configured.v1',
             '{"en":"Tenant revenue share configured"}'::jsonb,
             1825, 'silklens.reseller.events')
        ON CONFLICT (event_name) DO NOTHING;
        """
    )

    # --- b2b_accounts.kyc_status: widen CHECK to allow verified_by_admin -----
    # The original CHECK is anonymous; drop the column constraint + replace it.
    op.execute(
        """
        DO $$
        DECLARE
            check_name text;
        BEGIN
            SELECT conname INTO check_name
            FROM pg_constraint
            WHERE conrelid = 'b2b_accounts'::regclass
              AND contype = 'c'
              AND pg_get_constraintdef(oid) LIKE '%kyc_status%';
            IF check_name IS NOT NULL THEN
                EXECUTE format(
                    'ALTER TABLE b2b_accounts DROP CONSTRAINT %I',
                    check_name
                );
            END IF;
        END
        $$;

        ALTER TABLE b2b_accounts
            ADD CONSTRAINT b2b_accounts_kyc_status_check
            CHECK (kyc_status IN ('pending','verified','rejected','verified_by_admin'));
        """
    )

    # --- feature_keys seed for white-label flags -----------------------------
    op.execute(
        """
        INSERT INTO feature_keys (slug, name, kind) VALUES
            ('white_label_branding',
             '{"en":"White-label branding (logo, theme, fonts)"}'::jsonb,
             'boolean'),
            ('white_label_api_access',
             '{"en":"White-label Enterprise API access"}'::jsonb,
             'boolean'),
            ('white_label_custom_domain',
             '{"en":"White-label custom domain"}'::jsonb,
             'boolean')
        ON CONFLICT (slug) DO NOTHING;
        """
    )

    # Bind the three flags to the enterprise_api product's default plan,
    # materializing the plan on the fly if it doesn't yet exist. This
    # keeps the entitlement matrix queryable from the moment the migration
    # lands without requiring billing-seed fixtures.
    op.execute(
        """
        INSERT INTO product_plans (
            tenant_id, product_id, slug, name, billing_period, trial_days,
            is_default, is_active
        )
        SELECT pr.tenant_id, pr.id, 'enterprise_default',
               '{"en":"Enterprise (default plan)"}'::jsonb,
               'monthly', 0, true, true
        FROM products pr
        WHERE pr.slug = 'enterprise_api'
        ON CONFLICT (product_id, slug) DO NOTHING;
        """
    )

    op.execute(
        """
        INSERT INTO plan_features (plan_id, feature_key, enabled, limit_value)
        SELECT pp.id, fk.slug, true, NULL
        FROM product_plans pp
        JOIN products pr ON pr.id = pp.product_id
        CROSS JOIN feature_keys fk
        WHERE pr.slug = 'enterprise_api'
          AND pp.slug = 'enterprise_default'
          AND fk.slug IN (
              'white_label_branding',
              'white_label_api_access',
              'white_label_custom_domain'
          )
        ON CONFLICT (plan_id, feature_key) DO NOTHING;
        """
    )


def downgrade() -> None:
    # Unbind the seeded plan_features first.
    op.execute(
        """
        DELETE FROM plan_features
        WHERE feature_key IN (
            'white_label_branding',
            'white_label_api_access',
            'white_label_custom_domain'
        );
        DELETE FROM feature_keys
        WHERE slug IN (
            'white_label_branding',
            'white_label_api_access',
            'white_label_custom_domain'
        );
        DELETE FROM product_plans
        WHERE slug = 'enterprise_default'
          AND product_id IN (SELECT id FROM products WHERE slug = 'enterprise_api');
        """
    )

    op.execute(
        """
        ALTER TABLE b2b_accounts DROP CONSTRAINT IF EXISTS b2b_accounts_kyc_status_check;
        ALTER TABLE b2b_accounts
            ADD CONSTRAINT b2b_accounts_kyc_status_check
            CHECK (kyc_status IN ('pending','verified','rejected'));
        """
    )

    op.execute(
        """
        DELETE FROM event_types
        WHERE event_name IN (
            'reseller.applied.v1',
            'reseller.approved.v1',
            'reseller.rejected.v1',
            'reseller.revenue_share_configured.v1'
        );

        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id FROM permissions
            WHERE slug IN (
                'reseller:read',
                'reseller:approve',
                'reseller:configure_revenue_share'
            )
        );
        DELETE FROM permissions
        WHERE slug IN (
            'reseller:read',
            'reseller:approve',
            'reseller:configure_revenue_share'
        );
        """
    )

    op.execute("DROP TABLE IF EXISTS tenant_revenue_share CASCADE;")
    op.execute("DROP TABLE IF EXISTS reseller_application CASCADE;")
