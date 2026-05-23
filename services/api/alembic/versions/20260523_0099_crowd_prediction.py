"""heritage_check_ins + crowd_predictions — SILK-0075.

Revision ID: 0099
Revises: 0098
Create Date: 2026-05-23
"""

from __future__ import annotations

from alembic import op

revision = "0099"
down_revision = "0098"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check-in log (anonymized — user_id nullable for anonymous check-ins)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS heritage_check_ins (
            id              uuid         PRIMARY KEY DEFAULT gen_uuid_v7(),
            heritage_pub_id uuid         NOT NULL,
            user_id         uuid,
            checked_in_at   timestamptz  NOT NULL DEFAULT now(),
            day_of_week     smallint     NOT NULL DEFAULT 0,
            hour_of_day     smallint     NOT NULL DEFAULT 0,
            month_of_year   smallint     NOT NULL DEFAULT 1
        )
        """
    )

    # Populate generated-column equivalents via a trigger so INSERT can omit them
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app.tg_heritage_check_ins_time_parts()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            NEW.day_of_week   := EXTRACT(DOW   FROM NEW.checked_in_at)::smallint;
            NEW.hour_of_day   := EXTRACT(HOUR  FROM NEW.checked_in_at)::smallint;
            NEW.month_of_year := EXTRACT(MONTH FROM NEW.checked_in_at)::smallint;
            RETURN NEW;
        END;
        $$
        """
    )

    op.execute(
        """
        CREATE TRIGGER tg_heritage_check_ins_time_parts
            BEFORE INSERT OR UPDATE ON heritage_check_ins
            FOR EACH ROW EXECUTE FUNCTION app.tg_heritage_check_ins_time_parts()
        """
    )

    op.execute(
        """
        CREATE INDEX ix_heritage_check_ins_heritage
            ON heritage_check_ins (heritage_pub_id, checked_in_at DESC)
        """
    )

    op.execute(
        """
        CREATE INDEX ix_heritage_check_ins_time_pattern
            ON heritage_check_ins (heritage_pub_id, day_of_week, hour_of_day)
        """
    )

    # Materialized crowd prediction table (populated by a background job)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS crowd_predictions (
            heritage_pub_id uuid        NOT NULL,
            day_of_week     smallint    NOT NULL,
            hour_of_day     smallint    NOT NULL,
            month_of_year   smallint    NOT NULL,
            expected_crowd  varchar(10) NOT NULL DEFAULT 'unknown',
            sample_size     int         NOT NULL DEFAULT 0,
            updated_at      timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (heritage_pub_id, day_of_week, hour_of_day, month_of_year),
            CHECK (day_of_week   BETWEEN 0 AND 6),
            CHECK (hour_of_day   BETWEEN 0 AND 23),
            CHECK (month_of_year BETWEEN 1 AND 12),
            CHECK (expected_crowd IN ('unknown', 'low', 'medium', 'high', 'very_high'))
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS crowd_predictions CASCADE")
    op.execute("DROP TRIGGER IF EXISTS tg_heritage_check_ins_time_parts ON heritage_check_ins")
    op.execute("DROP FUNCTION IF EXISTS app.tg_heritage_check_ins_time_parts()")
    op.execute("DROP TABLE IF EXISTS heritage_check_ins CASCADE")
