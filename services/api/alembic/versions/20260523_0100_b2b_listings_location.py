"""b2b_listings — add location + search columns. SILK-0056.

Adds columns needed for geographic and dietary-preference search:
  - dietary_tags  : text[] for halal/vegetarian/vegan/etc filters
  - transport_type: varchar for transport-category listings
  - city          : varchar for text-based city filter
  - rating_avg    : numeric average of user reviews
  - review_count  : integer review count
  - sort_order    : integer for manual editorial sorting

Note: lat/lng already exist from migration 0053.  The GIN index on
dietary_tags and a composite active-category index are added here.

Revision ID: 0100
Revises: 0099
Create Date: 2026-05-23
"""

from __future__ import annotations

from alembic import op

revision = "0100"
down_revision = "0099"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE b2b_listings
            ADD COLUMN IF NOT EXISTS dietary_tags   text[]       NOT NULL DEFAULT '{}',
            ADD COLUMN IF NOT EXISTS transport_type varchar(50),
            ADD COLUMN IF NOT EXISTS city           varchar(100),
            ADD COLUMN IF NOT EXISTS rating_avg     numeric(3,2) NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS review_count   int          NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS sort_order     int          NOT NULL DEFAULT 0
        """
    )

    # GIN index for dietary tags array search  (@> ANY operator)
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_b2b_listings_dietary
            ON b2b_listings USING gin(dietary_tags)
        """
    )

    # Composite index for the common search pattern: active rows by category + city
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_b2b_listings_cat_city
            ON b2b_listings (category_slug, city)
            WHERE status = 'active'
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_b2b_listings_cat_city")
    op.execute("DROP INDEX IF EXISTS ix_b2b_listings_dietary")
    op.execute(
        """
        ALTER TABLE b2b_listings
            DROP COLUMN IF EXISTS dietary_tags,
            DROP COLUMN IF EXISTS transport_type,
            DROP COLUMN IF EXISTS city,
            DROP COLUMN IF EXISTS rating_avg,
            DROP COLUMN IF EXISTS review_count,
            DROP COLUMN IF EXISTS sort_order
        """
    )
