"""user_profiles — travel preferences and accessibility fields.

SILK-0062: age_group, kids_mode, dietary_prefs, travel_style, interests,
accessibility, preferred_language, is_discoverable fields.

Revision ID: 0093
Revises: 0092_investor_dataroom
Create Date: 2026-05-23
"""

from __future__ import annotations

from alembic import op

revision = "0093"
# Chain after the AR gamification mergepoint to avoid multiple heads.
# 0088_ar_gamification already merges 0085/0086/0090/0091/0092, so attaching
# the SILK-0093+ branch here keeps the migration graph linear.
down_revision = "0088_ar_gamification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add travel preference columns to user_profiles.
    # user_profiles is partitioned — ALTER applies to parent which cascades
    # to all partitions (uz, eu, us, global).
    op.execute(
        """
        ALTER TABLE user_profiles
            ADD COLUMN IF NOT EXISTS age_group          varchar(20),
            ADD COLUMN IF NOT EXISTS kids_mode          boolean NOT NULL DEFAULT false,
            ADD COLUMN IF NOT EXISTS dietary_prefs      text[]  NOT NULL DEFAULT '{}',
            ADD COLUMN IF NOT EXISTS travel_style       text[]  NOT NULL DEFAULT '{}',
            ADD COLUMN IF NOT EXISTS accessibility      text[]  NOT NULL DEFAULT '{}',
            ADD COLUMN IF NOT EXISTS preferred_language varchar(10),
            ADD COLUMN IF NOT EXISTS is_discoverable    boolean NOT NULL DEFAULT false
        """
    )

    op.execute(
        """
        COMMENT ON COLUMN user_profiles.age_group IS
            'Optional self-reported age bracket (e.g. ''18-24'', ''35-44''). '
            'Used to surface age-appropriate content and experiences.';
        COMMENT ON COLUMN user_profiles.kids_mode IS
            'When true, all content surfaces are restricted to family-safe material.';
        COMMENT ON COLUMN user_profiles.dietary_prefs IS
            'Array of dietary preference slugs (e.g. ''{halal,vegetarian}''). '
            'Drives restaurant and food-tour recommendations.';
        COMMENT ON COLUMN user_profiles.travel_style IS
            'Array of travel-style slugs (e.g. ''{budget,adventure,cultural}''). '
            'Used by the recommendation engine for personalisation.';
        COMMENT ON COLUMN user_profiles.accessibility IS
            'Array of accessibility-requirement slugs (e.g. ''{wheelchair,low_vision}''). '
            'Filters out venues and routes that cannot accommodate the user.';
        COMMENT ON COLUMN user_profiles.preferred_language IS
            'BCP-47 tag for audio guide and AI narration language preference. '
            'Overrides account-level preferred_locale for content delivery.';
        COMMENT ON COLUMN user_profiles.is_discoverable IS
            'Opt-in social discovery flag. When true the user appears in '
            'traveller-matching and nearby-travellers features.';
        """
    )

    # Partial index for discoverable users — social traveller discovery queries
    # always filter WHERE is_discoverable = true; keeping it partial avoids
    # bloating the index with the overwhelming majority of private profiles.
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_user_profiles_discoverable
            ON user_profiles (is_discoverable)
            WHERE is_discoverable = true
        """
    )

    # Partial index for kids_mode — content-safety filter applied on every
    # feed render for affected users; a partial index keeps it tight.
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_user_profiles_kids_mode
            ON user_profiles (kids_mode)
            WHERE kids_mode = true
        """
    )

    # GIN index on travel_style for array-overlap queries used by the
    # recommendation engine (e.g. travel_style && '{adventure,cultural}').
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_user_profiles_travel_style_gin
            ON user_profiles USING GIN (travel_style)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_user_profiles_travel_style_gin")
    op.execute("DROP INDEX IF EXISTS ix_user_profiles_kids_mode")
    op.execute("DROP INDEX IF EXISTS ix_user_profiles_discoverable")
    op.execute(
        """
        ALTER TABLE user_profiles
            DROP COLUMN IF EXISTS age_group,
            DROP COLUMN IF EXISTS kids_mode,
            DROP COLUMN IF EXISTS dietary_prefs,
            DROP COLUMN IF EXISTS travel_style,
            DROP COLUMN IF EXISTS accessibility,
            DROP COLUMN IF EXISTS preferred_language,
            DROP COLUMN IF EXISTS is_discoverable
        """
    )
