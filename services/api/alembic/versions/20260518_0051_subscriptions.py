"""subscriptions + items + events + entitlements + dunning + trials

Per Agent 6 monetization architecture §3.4 + §6 (state machine):

  subscriptions         — user-bound recurring entitlement contracts.
  subscription_items    — what the subscription provides (product + plan + qty).
  subscription_events   — append-only state-transition log; the source of truth
                          for billing analytics (Agent 6 §3 — never derive state
                          purely from current row, always replayable from log).
  entitlements          — derived denormalized cache (plan flowed through to
                          (user, feature_key) for <5 ms p99 lookups, Agent 6 §5).
  dunning_state         — retry-machine state for past_due subscriptions
                          (Agent 6 §3 risk #3: dunning runs idempotently).
  trials                — one-trial-per-(user, plan) enforcement.

User refs use composite (user_id, residency_region) FK because ``users`` is
LIST-partitioned by residency_region (migration 0004 / Agent 2 §11).

Revision ID: 0051_subscriptions
Revises: 0050_products_pricing
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0051_subscriptions"
down_revision: str | Sequence[str] | None = "0050_products_pricing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- subscriptions ----------------------------------------------------
    op.execute(
        """
        CREATE TABLE subscriptions (
            id                      uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            tenant_id               uuid NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            user_id                 uuid NOT NULL,
            residency_region        text NOT NULL,
            plan_id                 uuid NOT NULL REFERENCES product_plans(id) ON DELETE RESTRICT,
            status                  text NOT NULL DEFAULT 'trial' CHECK (status IN (
                'trial','active','past_due','canceled','expired','paused'
            )),
            current_period_start    timestamptz NOT NULL,
            current_period_end      timestamptz NOT NULL,
            trial_ends_at           timestamptz,
            cancel_at_period_end    boolean NOT NULL DEFAULT false,
            canceled_at             timestamptz,
            ended_at                timestamptz,
            created_at              timestamptz NOT NULL DEFAULT now(),
            updated_at              timestamptz NOT NULL DEFAULT now(),
            FOREIGN KEY (user_id, residency_region)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (residency_region IN ('uz','eu','us','global')),
            CHECK (current_period_end > current_period_start)
        );

        -- Hot path: list a user's live subscriptions.
        CREATE INDEX idx_subscriptions_user_active
            ON subscriptions (user_id, status)
            WHERE status IN ('active','trial');
        CREATE INDEX idx_subscriptions_renewal
            ON subscriptions (current_period_end)
            WHERE status IN ('active','trial');
        CREATE INDEX idx_subscriptions_tenant
            ON subscriptions (tenant_id, status);

        CREATE TRIGGER tg_subscriptions_updated_at
            BEFORE UPDATE ON subscriptions
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE subscriptions IS
            'Recurring entitlement contracts. State machine per Agent 6 §6 — '
            'transitions are recorded in subscription_events (append-only).';
        """
    )

    # --- subscription_items ----------------------------------------------
    op.execute(
        """
        CREATE TABLE subscription_items (
            subscription_id uuid NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
            product_id      uuid NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
            plan_id         uuid NOT NULL REFERENCES product_plans(id) ON DELETE RESTRICT,
            quantity        int NOT NULL DEFAULT 1 CHECK (quantity > 0),
            created_at      timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (subscription_id, product_id, plan_id)
        );

        CREATE INDEX idx_subscription_items_product
            ON subscription_items (product_id);
        """
    )

    # --- subscription_events (append-only state log) ---------------------
    op.execute(
        """
        CREATE TABLE subscription_events (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            subscription_id uuid NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
            event           text NOT NULL CHECK (event IN (
                'created','trial_started','activated','renewed','upgraded',
                'downgraded','paused','resumed','canceled','refunded','expired'
            )),
            from_status     text,
            to_status       text,
            payload         jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at      timestamptz NOT NULL DEFAULT now()
        );

        CREATE INDEX idx_subscription_events_subscription
            ON subscription_events (subscription_id, created_at DESC);
        CREATE INDEX idx_subscription_events_event
            ON subscription_events (event, created_at DESC);

        COMMENT ON TABLE subscription_events IS
            'Append-only state-transition log (Agent 6 §3 + §6). The source of '
            'truth for billing analytics — never UPDATE this table.';
        """
    )

    # --- entitlements (derived, residency-aware) -------------------------
    # source_id is polymorphic: ``plan`` → product_plans.id, ``manual_grant``
    # → admin grant id (future), ``promo`` → promotion id (future), ``admin``
    # → arbitrary admin action. No FK because the target depends on source.
    op.execute(
        """
        CREATE TABLE entitlements (
            user_id             uuid NOT NULL,
            residency_region    text NOT NULL,
            feature_key         text NOT NULL REFERENCES feature_keys(slug) ON DELETE RESTRICT,
            granted             boolean NOT NULL DEFAULT true,
            limit_value         bigint CHECK (limit_value IS NULL OR limit_value >= 0),
            source              text NOT NULL CHECK (source IN (
                'plan','manual_grant','promo','admin'
            )),
            source_id           uuid,
            effective_until     timestamptz,
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (user_id, residency_region, feature_key),
            FOREIGN KEY (user_id, residency_region)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (residency_region IN ('uz','eu','us','global'))
        );

        CREATE INDEX idx_entitlements_feature
            ON entitlements (feature_key) WHERE granted;
        CREATE INDEX idx_entitlements_expiring
            ON entitlements (effective_until)
            WHERE effective_until IS NOT NULL;

        CREATE TRIGGER tg_entitlements_updated_at
            BEFORE UPDATE ON entitlements
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE entitlements IS
            'Derived denormalized cache (Agent 6 §5 three-tier resolution). Recomputed '
            'from subscriptions + plan_features by the entitlement-resolver job. Read path '
            'is single-row index lookup → <5ms p99.';
        """
    )

    # --- dunning_state (retry machine for past_due subs) -----------------
    op.execute(
        """
        CREATE TABLE dunning_state (
            subscription_id uuid PRIMARY KEY REFERENCES subscriptions(id) ON DELETE CASCADE,
            attempts        int NOT NULL DEFAULT 0 CHECK (attempts >= 0),
            next_retry_at   timestamptz,
            failure_reason  text,
            last_attempt_at timestamptz,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now()
        );

        -- Index for the dunning scheduler that picks up due retries.
        CREATE INDEX idx_dunning_state_next_retry
            ON dunning_state (next_retry_at)
            WHERE next_retry_at IS NOT NULL;

        CREATE TRIGGER tg_dunning_state_updated_at
            BEFORE UPDATE ON dunning_state
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE dunning_state IS
            'Retry state for past_due subscriptions (Agent 6 §3 risk #3 / §9). '
            'Idempotent retries — attempts is monotonic, next_retry_at backed off.';
        """
    )

    # --- trials (one-trial-per-(user, plan) enforcement) -----------------
    op.execute(
        """
        CREATE TABLE trials (
            id                  uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            user_id             uuid NOT NULL,
            residency_region    text NOT NULL,
            plan_id             uuid NOT NULL REFERENCES product_plans(id) ON DELETE RESTRICT,
            started_at          timestamptz NOT NULL DEFAULT now(),
            ends_at             timestamptz NOT NULL,
            converted_at        timestamptz,
            created_at          timestamptz NOT NULL DEFAULT now(),
            UNIQUE (user_id, residency_region, plan_id),
            FOREIGN KEY (user_id, residency_region)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (residency_region IN ('uz','eu','us','global')),
            CHECK (ends_at > started_at)
        );

        CREATE INDEX idx_trials_active
            ON trials (ends_at)
            WHERE converted_at IS NULL;

        COMMENT ON TABLE trials IS
            'One free trial per (user, plan). Prevents trial-stacking abuse '
            'across (re-)registrations within the same residency partition.';
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS trials CASCADE;")
    op.execute("DROP TABLE IF EXISTS dunning_state CASCADE;")
    op.execute("DROP TABLE IF EXISTS entitlements CASCADE;")
    op.execute("DROP TABLE IF EXISTS subscription_events CASCADE;")
    op.execute("DROP TABLE IF EXISTS subscription_items CASCADE;")
    op.execute("DROP TABLE IF EXISTS subscriptions CASCADE;")
