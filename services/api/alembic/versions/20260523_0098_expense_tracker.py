"""travel_budgets + budget_entries — Smart Expense Tracker. SILK-0072.

Revision ID: 0098
Revises: 0096
Create Date: 2026-05-23
"""

from __future__ import annotations

from alembic import op

revision = "0098"
down_revision = "0097"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE travel_budgets (
            id               uuid          PRIMARY KEY DEFAULT gen_uuid_v7(),
            user_id          uuid          NOT NULL,
            residency_region varchar(20)   NOT NULL DEFAULT 'global',
            title            varchar(200),
            total_budget_usd numeric(10,2) NOT NULL CHECK (total_budget_usd > 0),
            currency         char(3)       NOT NULL DEFAULT 'USD',
            start_date       date,
            end_date         date,
            is_active        boolean       NOT NULL DEFAULT true,
            created_at       timestamptz   NOT NULL DEFAULT now(),
            updated_at       timestamptz   NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE INDEX ix_travel_budgets_user
            ON travel_budgets (user_id, created_at DESC)
        """
    )

    op.execute(
        """
        CREATE TRIGGER tg_travel_budgets_updated_at
            BEFORE UPDATE ON travel_budgets
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at()
        """
    )

    op.execute(
        """
        CREATE TABLE budget_entries (
            id          uuid         PRIMARY KEY DEFAULT gen_uuid_v7(),
            budget_id   uuid         NOT NULL
                            REFERENCES travel_budgets(id) ON DELETE CASCADE,
            category    varchar(30)  NOT NULL DEFAULT 'other',
            amount_usd  numeric(8,2) NOT NULL CHECK (amount_usd >= 0),
            description varchar(200),
            entry_date  date         NOT NULL DEFAULT CURRENT_DATE,
            created_at  timestamptz  NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE INDEX ix_budget_entries_budget
            ON budget_entries (budget_id, entry_date DESC)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS budget_entries CASCADE")
    op.execute("DROP TABLE IF EXISTS travel_budgets CASCADE")
