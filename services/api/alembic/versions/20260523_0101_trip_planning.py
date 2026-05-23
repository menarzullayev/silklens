"""trip_planning — trips + trip_stops tables. SILK-0061.

Revision ID: 0101
Revises: 0100
Create Date: 2026-05-23
"""

from __future__ import annotations

from alembic import op

revision = "0101"
down_revision = "0100"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS trips (
            id              uuid         PRIMARY KEY DEFAULT gen_uuid_v7(),
            user_id         uuid         NOT NULL,
            residency_region varchar(20) NOT NULL DEFAULT 'global',
            title           varchar(200),
            status          varchar(20)  NOT NULL DEFAULT 'draft',
            cities          text[]       NOT NULL DEFAULT '{}',
            start_date      date,
            end_date        date,
            budget_usd      numeric(10,2),
            interests       text[]       NOT NULL DEFAULT '{}',
            ai_plan_json    jsonb,
            total_days      int          GENERATED ALWAYS AS (
                CASE WHEN start_date IS NOT NULL AND end_date IS NOT NULL
                     THEN (end_date - start_date + 1)
                     ELSE NULL
                END
            ) STORED,
            created_at      timestamptz  NOT NULL DEFAULT now(),
            updated_at      timestamptz  NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TRIGGER tg_trips_updated_at
            BEFORE UPDATE ON trips
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at()
    """)

    op.execute("""
        CREATE INDEX ix_trips_user ON trips (user_id, created_at DESC)
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS trip_stops (
            id              uuid         PRIMARY KEY DEFAULT gen_uuid_v7(),
            trip_id         uuid         NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
            day_number      int          NOT NULL,
            order_in_day    int          NOT NULL DEFAULT 0,
            heritage_pub_id uuid,
            listing_id      uuid,
            stop_name       varchar(200),
            stop_kind       varchar(30)  DEFAULT 'heritage',
            visit_duration_min int       DEFAULT 60,
            estimated_cost_usd numeric(8,2),
            transport_to_next varchar(30),
            travel_time_min int,
            notes           text,
            lat             numeric(10,7),
            lng             numeric(10,7),
            created_at      timestamptz  NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE INDEX ix_trip_stops_trip ON trip_stops (trip_id, day_number, order_in_day)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS trip_stops CASCADE")
    op.execute("DROP TABLE IF EXISTS trips CASCADE")
