"""social graph: follows, friendships, blocks/mutes, close friends, whales, activity feed

Per Agent 5 §3 (social-gamification-ugc) §2.3 (social graph) + §2.4 (activity feed)
+ §3.18 (whale_users) + §4 (hybrid push/pull fanout).

Five social-edge tables shape the directed and symmetric graph:
  follows        — directed (follower → followee). Counter caches on users live
                   in app layer; nightly reconciliation per §3.9.
  friendships    — symmetric, stored canonically with sort (user_a < user_b)
                   to halve storage and disambiguate lookups.
  friend_invitations — pending invitations including external (email) targets.
  block_list     — hard suppression (search, comments, reactions).
  mutes          — soft suppression (don't show posts; subject is unaware).
  close_friends  — Instagram-style inner circle for restricted journals/posts.

Followed by the celebrity-throughput escape hatch:
  whale_users    — users above the follower threshold get marked here and
                   excluded from push-fanout; their feed entries are pulled
                   on read instead (Agent 5 §4.3 whale problem).

Followed by the feed itself (both range-partitioned monthly per §3.15-§3.16):
  activity_events — append-only verb log; the source of truth for every
                    social-worthy action.
  activity_fanout — pre-delivered feed items keyed on (recipient, event_id).
                    No FK to activity_events.id because both are partitioned
                    by different keys → cross-partition FKs are forbidden.

All user FKs use composite (id, residency_region) per the partitioning regime
established in migration 0009 (sessions).

Revision ID: 0040_social_graph
Revises: 0033_ai_safety_and_tm
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta, timezone

from alembic import op

revision: str = "0040_social_graph"
down_revision: str | Sequence[str] | None = "0033_ai_safety_and_tm"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Activity tables are RANGE-partitioned monthly. We pre-create 4 months
# starting at the current month so writes never hit the default partition.
def _month_partitions(start: datetime, count: int) -> list[tuple[str, str, str]]:
    """Return [(suffix, lower_bound, upper_bound)] for `count` consecutive months."""
    out: list[tuple[str, str, str]] = []
    cursor = datetime(start.year, start.month, 1, tzinfo=timezone.utc)
    for _ in range(count):
        if cursor.month == 12:
            nxt = datetime(cursor.year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            nxt = datetime(cursor.year, cursor.month + 1, 1, tzinfo=timezone.utc)
        suffix = f"{cursor.year:04d}_{cursor.month:02d}"
        out.append((suffix, cursor.isoformat(), nxt.isoformat()))
        cursor = nxt
    return out


def upgrade() -> None:
    # --- follows (directed edge) ----------------------------------------------
    # Composite FK to users on both sides because `users` is residency-partitioned.
    # PK is the (follower, followee) pair, deduplicating both directions.
    op.execute(
        """
        CREATE TABLE follows (
            follower_user_id        uuid NOT NULL,
            follower_residency      text NOT NULL,
            followee_user_id        uuid NOT NULL,
            followee_residency      text NOT NULL,
            created_at              timestamptz NOT NULL DEFAULT now(),

            PRIMARY KEY (follower_user_id, followee_user_id),
            FOREIGN KEY (follower_user_id, follower_residency)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            FOREIGN KEY (followee_user_id, followee_residency)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (follower_user_id <> followee_user_id),
            CHECK (follower_residency IN ('uz','eu','us','global')),
            CHECK (followee_residency IN ('uz','eu','us','global'))
        );

        CREATE INDEX idx_follows_followee
            ON follows (followee_user_id, created_at DESC);
        CREATE INDEX idx_follows_follower
            ON follows (follower_user_id, created_at DESC);

        COMMENT ON TABLE follows IS
            'Directed follow edges (asymmetric). Counter caches live in app layer; '
            'nightly reconciliation per Agent 5 §3.9.';
        """
    )

    # --- friendships (symmetric; canonical ordering) --------------------------
    # CHECK (user_a < user_b) means each friendship is exactly one row.
    op.execute(
        """
        CREATE TABLE friendships (
            user_a_id           uuid NOT NULL,
            user_a_residency    text NOT NULL,
            user_b_id           uuid NOT NULL,
            user_b_residency    text NOT NULL,
            status              text NOT NULL DEFAULT 'invited'
                CHECK (status IN ('invited','accepted','blocked')),
            invited_at          timestamptz NOT NULL DEFAULT now(),
            accepted_at         timestamptz,

            PRIMARY KEY (user_a_id, user_b_id),
            FOREIGN KEY (user_a_id, user_a_residency)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            FOREIGN KEY (user_b_id, user_b_residency)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (user_a_id < user_b_id),
            CHECK (user_a_residency IN ('uz','eu','us','global')),
            CHECK (user_b_residency IN ('uz','eu','us','global'))
        );

        CREATE INDEX idx_friendships_b
            ON friendships (user_b_id);
        CREATE INDEX idx_friendships_status_accepted
            ON friendships (user_a_id, user_b_id)
            WHERE status = 'accepted';

        COMMENT ON TABLE friendships IS
            'Symmetric friendship edges with canonical ordering user_a_id<user_b_id. '
            'Halves storage; eliminates duplicate-row reconciliation.';
        """
    )

    # --- friend_invitations (incl. external email targets) --------------------
    op.execute(
        """
        CREATE TABLE friend_invitations (
            id                  uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            from_user_id        uuid NOT NULL,
            from_residency      text NOT NULL,
            to_user_id          uuid,
            to_residency        text,
            to_email            citext,
            token               text NOT NULL UNIQUE,
            status              text NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending','accepted','declined','expired','revoked')),
            message             text,
            expires_at          timestamptz NOT NULL DEFAULT now() + INTERVAL '30 days',
            responded_at        timestamptz,
            created_at          timestamptz NOT NULL DEFAULT now(),

            FOREIGN KEY (from_user_id, from_residency)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            FOREIGN KEY (to_user_id, to_residency)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (to_user_id IS NOT NULL OR to_email IS NOT NULL),
            CHECK ((to_user_id IS NULL) = (to_residency IS NULL)),
            CHECK (from_residency IN ('uz','eu','us','global')),
            CHECK (to_residency IS NULL OR to_residency IN ('uz','eu','us','global')),
            CHECK (length(token) BETWEEN 16 AND 128)
        );

        CREATE INDEX idx_friend_invitations_to_user
            ON friend_invitations (to_user_id) WHERE status = 'pending';
        CREATE INDEX idx_friend_invitations_to_email
            ON friend_invitations (to_email) WHERE status = 'pending' AND to_email IS NOT NULL;
        CREATE UNIQUE INDEX uq_friend_invitations_pair_pending
            ON friend_invitations (from_user_id, to_user_id)
            WHERE status = 'pending' AND to_user_id IS NOT NULL;

        COMMENT ON TABLE friend_invitations IS
            'Outbound friend invitations. to_user_id is nullable so we can invite '
            'people who do not yet have a SilkLens account (via email).';
        """
    )

    # --- block_list -----------------------------------------------------------
    op.execute(
        """
        CREATE TABLE block_list (
            blocker_user_id     uuid NOT NULL,
            blocker_residency   text NOT NULL,
            blocked_user_id     uuid NOT NULL,
            blocked_residency   text NOT NULL,
            reason              text,
            created_at          timestamptz NOT NULL DEFAULT now(),

            PRIMARY KEY (blocker_user_id, blocked_user_id),
            FOREIGN KEY (blocker_user_id, blocker_residency)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            FOREIGN KEY (blocked_user_id, blocked_residency)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (blocker_user_id <> blocked_user_id),
            CHECK (blocker_residency IN ('uz','eu','us','global')),
            CHECK (blocked_residency IN ('uz','eu','us','global'))
        );

        CREATE INDEX idx_block_list_blocked
            ON block_list (blocked_user_id);

        COMMENT ON TABLE block_list IS
            'Hard suppression: hides content of blocked from blocker in both '
            'directions (search, comments, reactions). Async worker cascades '
            'unfollow on both sides.';
        """
    )

    # --- mutes (softer than block) --------------------------------------------
    op.execute(
        """
        CREATE TABLE mutes (
            muter_user_id       uuid NOT NULL,
            muter_residency     text NOT NULL,
            muted_user_id       uuid NOT NULL,
            muted_residency     text NOT NULL,
            reason              text,
            expires_at          timestamptz,
            created_at          timestamptz NOT NULL DEFAULT now(),

            PRIMARY KEY (muter_user_id, muted_user_id),
            FOREIGN KEY (muter_user_id, muter_residency)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            FOREIGN KEY (muted_user_id, muted_residency)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (muter_user_id <> muted_user_id),
            CHECK (muter_residency IN ('uz','eu','us','global')),
            CHECK (muted_residency IN ('uz','eu','us','global'))
        );

        CREATE INDEX idx_mutes_muted
            ON mutes (muted_user_id);

        COMMENT ON TABLE mutes IS
            'Soft suppression — muted user does not see anything. The muted user '
            'is unaware; the muter just stops seeing their posts.';
        """
    )

    # --- close_friends (Instagram inner-circle) -------------------------------
    op.execute(
        """
        CREATE TABLE close_friends (
            user_id             uuid NOT NULL,
            user_residency      text NOT NULL,
            close_user_id       uuid NOT NULL,
            close_residency     text NOT NULL,
            created_at          timestamptz NOT NULL DEFAULT now(),

            PRIMARY KEY (user_id, close_user_id),
            FOREIGN KEY (user_id, user_residency)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            FOREIGN KEY (close_user_id, close_residency)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (user_id <> close_user_id),
            CHECK (user_residency IN ('uz','eu','us','global')),
            CHECK (close_residency IN ('uz','eu','us','global'))
        );

        CREATE INDEX idx_close_friends_close
            ON close_friends (close_user_id);

        COMMENT ON TABLE close_friends IS
            'Inner-circle list. Drives visibility=''close_friends'' on journals, '
            'reviews, and activity feed entries.';
        """
    )

    # --- whale_users (celebrity-creator escape hatch) -------------------------
    # Per Agent 5 §3.18: high-follower users opt out of push fanout.
    op.execute(
        """
        CREATE TABLE whale_users (
            user_id                         uuid NOT NULL,
            residency_region                text NOT NULL,
            threshold_reached_at            timestamptz NOT NULL DEFAULT now(),
            follower_count_at_threshold     integer NOT NULL,
            fanout_mode                     text NOT NULL DEFAULT 'pull'
                CHECK (fanout_mode IN ('pull','push','hybrid')),
            last_recomputed_at              timestamptz NOT NULL DEFAULT now(),

            PRIMARY KEY (user_id),
            FOREIGN KEY (user_id, residency_region)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (residency_region IN ('uz','eu','us','global')),
            CHECK (follower_count_at_threshold >= 0)
        );

        CREATE INDEX idx_whale_users_mode
            ON whale_users (fanout_mode);

        COMMENT ON TABLE whale_users IS
            'High-follower users (default threshold 5000, admin-tunable in settings). '
            'On read, feed merges push-delivered items with a small pull from these '
            'actors per Agent 5 §4.3.';
        """
    )

    # --- activity_events (append-only, RANGE-partitioned monthly) -------------
    op.execute(
        """
        CREATE TABLE activity_events (
            id                  uuid NOT NULL DEFAULT gen_uuid_v7(),
            actor_user_id       uuid NOT NULL,
            actor_residency     text NOT NULL,
            verb                text NOT NULL
                CHECK (verb IN (
                    'created','reviewed','visited','liked','followed',
                    'earned_badge','joined_trip','commented','reacted',
                    'photographed','journal_published'
                )),
            object_kind         text NOT NULL,
            object_id           uuid NOT NULL,
            target_kind         text,
            target_id           uuid,
            visibility          text NOT NULL DEFAULT 'public'
                CHECK (visibility IN ('public','followers','friends','close_friends','private')),
            payload             jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at          timestamptz NOT NULL DEFAULT now(),

            PRIMARY KEY (id, created_at),
            FOREIGN KEY (actor_user_id, actor_residency)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (actor_residency IN ('uz','eu','us','global')),
            CHECK ((target_kind IS NULL) = (target_id IS NULL)),
            CHECK (object_kind ~ '^[a-z][a-z0-9_]*$'),
            CHECK (target_kind IS NULL OR target_kind ~ '^[a-z][a-z0-9_]*$')
        ) PARTITION BY RANGE (created_at);

        COMMENT ON TABLE activity_events IS
            'Append-only verb log (actor verb object [target]). Source of truth '
            'for the social feed. Range-partitioned monthly so 90-day retention '
            'is a single DETACH+DROP.';
        """
    )

    # --- activity_fanout (delivered feed items, RANGE-partitioned monthly) ----
    op.execute(
        """
        CREATE TABLE activity_fanout (
            id                  uuid NOT NULL DEFAULT gen_uuid_v7(),
            recipient_user_id   uuid NOT NULL,
            recipient_residency text NOT NULL,
            event_id            uuid NOT NULL,
            event_created_at    timestamptz NOT NULL,
            actor_user_id       uuid NOT NULL,
            verb                text NOT NULL,
            delivered_at        timestamptz NOT NULL DEFAULT now(),
            read_at             timestamptz,

            PRIMARY KEY (id, delivered_at),
            FOREIGN KEY (recipient_user_id, recipient_residency)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (recipient_residency IN ('uz','eu','us','global'))
        ) PARTITION BY RANGE (delivered_at);

        COMMENT ON TABLE activity_fanout IS
            'Pre-delivered feed items. NO FK to activity_events.id because both '
            'are range-partitioned (cross-partition FK is forbidden in Postgres). '
            'Logical referent only — repair job reconciles drift.';
        """
    )

    # --- Monthly partitions: 4 months starting at 2026-05 ---------------------
    today = datetime.now(timezone.utc)
    months = _month_partitions(today, 4)
    for parent in ("activity_events", "activity_fanout"):
        for suffix, lo, hi in months:
            op.execute(
                f"""
                CREATE TABLE {parent}_{suffix}
                    PARTITION OF {parent}
                    FOR VALUES FROM ('{lo}') TO ('{hi}');
                """
            )
        # Default partition catches anything outside the pre-created ranges so
        # a misconfigured clock never crashes inserts.
        op.execute(
            f"CREATE TABLE {parent}_default PARTITION OF {parent} DEFAULT;"
        )

    # Indexes on partitioned parents are auto-applied to every child.
    op.execute(
        """
        CREATE INDEX idx_activity_events_actor_time
            ON activity_events (actor_user_id, created_at DESC);
        CREATE INDEX idx_activity_events_verb_time
            ON activity_events (verb, created_at DESC);
        CREATE INDEX idx_activity_events_payload
            ON activity_events USING GIN (payload jsonb_path_ops);

        CREATE INDEX idx_activity_fanout_recipient_time
            ON activity_fanout (recipient_user_id, delivered_at DESC);
        CREATE INDEX idx_activity_fanout_unread
            ON activity_fanout (recipient_user_id, delivered_at DESC)
            WHERE read_at IS NULL;
        CREATE INDEX idx_activity_fanout_event
            ON activity_fanout (event_id);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS activity_fanout CASCADE;")
    op.execute("DROP TABLE IF EXISTS activity_events CASCADE;")
    op.execute("DROP TABLE IF EXISTS whale_users CASCADE;")
    op.execute("DROP TABLE IF EXISTS close_friends CASCADE;")
    op.execute("DROP TABLE IF EXISTS mutes CASCADE;")
    op.execute("DROP TABLE IF EXISTS block_list CASCADE;")
    op.execute("DROP TABLE IF EXISTS friend_invitations CASCADE;")
    op.execute("DROP TABLE IF EXISTS friendships CASCADE;")
    op.execute("DROP TABLE IF EXISTS follows CASCADE;")
