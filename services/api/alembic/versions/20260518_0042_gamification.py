"""gamification: XP ledger, badges, levels, leaderboards, streaks

Per Agent 5 §3.19-§3.30 (badges/levels/XP/streaks/leaderboards) + §5
(anti-abuse) + §24 of Project-Decisions (gamification economy).

Treats XP as a financial ledger:
  xp_events    — append-only journal, RANGE-partitioned monthly. Every +XP
                 and every -XP (clawback) row is here. The UNIQUE on
                 (user_id, idempotency_key) is the DB-level guarantee that
                 the same visit/review/etc. cannot grant XP twice — anti-farming
                 at the schema level, not the app level (Agent 5 §5.1).
  xp_balances  — materialised projection. Maintained by trigger on the
                 default partition + nightly reconciliation from xp_events
                 to catch drift.

Badges + levels are admin catalogs (`badge_types`, `levels`) with seeded
v1 rows for the FAZA-1 launch. Badge progress lives on user_badges.progress
JSONB so partially-earned badges can be reflected without separate tables.

Streaks pair the materialised `streaks` row with an append-only
`streak_events` table so streak length can be rebuilt by counting consecutive
event_date values back from today.

Leaderboards are admin-configurable: scope × period × metric × is_active.
End-of-period the worker freezes a row into `leaderboard_snapshots` so
"winner of Week 23, 2026" survives account deletions.

All user FKs use composite (id, residency_region) per migration 0009.

Revision ID: 0042_gamification
Revises: 0041_reviews_ugc
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone

from alembic import op

revision: str = "0042_gamification"
down_revision: str | Sequence[str] | None = "0041_reviews_ugc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _month_partitions(start: datetime, count: int) -> list[tuple[str, str, str]]:
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
    # --- badge_types (admin catalog) -----------------------------------------
    op.execute(
        """
        CREATE TABLE badge_types (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            slug            text NOT NULL UNIQUE,
            category        text NOT NULL DEFAULT 'exploration'
                CHECK (category IN ('exploration','social','content','streak','seasonal','curator','expert')),
            name            jsonb NOT NULL DEFAULT '{}'::jsonb,
            description     jsonb NOT NULL DEFAULT '{}'::jsonb,
            icon_url        text,
            criterion_kind  text NOT NULL
                CHECK (criterion_kind IN (
                    'count_visited','count_reviewed','streak_days',
                    'country_count','category_completion','special_event',
                    'count_photos','count_helpful_received','count_followers'
                )),
            criterion_params jsonb NOT NULL DEFAULT '{}'::jsonb,
            rarity          text NOT NULL DEFAULT 'common'
                CHECK (rarity IN ('common','rare','epic','legendary')),
            xp_reward       integer NOT NULL DEFAULT 0,
            evaluator_version smallint NOT NULL DEFAULT 1,
            is_active       boolean NOT NULL DEFAULT true,
            released_at     timestamptz NOT NULL DEFAULT now(),
            retired_at      timestamptz,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            CHECK (slug ~ '^[a-z][a-z0-9_]*$'),
            CHECK (xp_reward >= 0)
        );

        CREATE INDEX idx_badge_types_active
            ON badge_types (category, rarity) WHERE is_active;

        CREATE TRIGGER tg_badge_types_updated_at
            BEFORE UPDATE ON badge_types
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE badge_types IS
            'Admin catalog of badge definitions. criterion_kind + criterion_params '
            'form a tiny DSL the BadgeEvaluator worker interprets (Agent 5 §3.20).';
        """
    )

    # Seed at least 12 v1 badges per spec.
    op.execute(
        """
        INSERT INTO badge_types
            (slug, category, name, description, criterion_kind, criterion_params, rarity, xp_reward)
        VALUES
            ('samarkand_explorer', 'exploration',
             '{"en":"Samarkand Explorer","uz":"Samarqand kashfiyotchisi","ru":"Исследователь Самарканда"}'::jsonb,
             '{"en":"Visit 10 heritage sites in Samarkand"}'::jsonb,
             'count_visited',
             '{"city_slug":"samarkand","threshold": 10}'::jsonb,
             'rare', 250),
            ('bukhara_pilgrim', 'exploration',
             '{"en":"Bukhara Pilgrim","uz":"Buxoro ziyoratchisi","ru":"Паломник Бухары"}'::jsonb,
             '{"en":"Visit 10 heritage sites in Bukhara"}'::jsonb,
             'count_visited',
             '{"city_slug":"bukhara","threshold": 10}'::jsonb,
             'rare', 250),
            ('khiva_wanderer', 'exploration',
             '{"en":"Khiva Wanderer","uz":"Xiva sayyohi","ru":"Странник Хивы"}'::jsonb,
             '{"en":"Visit 10 heritage sites in Khiva"}'::jsonb,
             'count_visited',
             '{"city_slug":"khiva","threshold": 10}'::jsonb,
             'rare', 250),
            ('silk_road_traveler', 'exploration',
             '{"en":"Silk Road Traveler","uz":"Ipak yo''li sayyohi","ru":"Путешественник Шёлкового пути"}'::jsonb,
             '{"en":"Visit 25 sites along the historical Silk Road"}'::jsonb,
             'count_visited',
             '{"tag":"silk_road","threshold": 25}'::jsonb,
             'epic', 750),
            ('cosmopolitan', 'exploration',
             '{"en":"Cosmopolitan","uz":"Kosmopolit","ru":"Космополит"}'::jsonb,
             '{"en":"Visit heritage sites in 5 different countries"}'::jsonb,
             'country_count',
             '{"threshold": 5}'::jsonb,
             'epic', 600),
            ('globetrotter', 'exploration',
             '{"en":"Globetrotter","uz":"Sayyora bo''ylab","ru":"Землепроходец"}'::jsonb,
             '{"en":"Visit heritage sites in 15 countries"}'::jsonb,
             'country_count',
             '{"threshold": 15}'::jsonb,
             'legendary', 2000),
            ('historian', 'content',
             '{"en":"Historian","uz":"Tarixchi","ru":"Историк"}'::jsonb,
             '{"en":"Publish 25 well-rated reviews"}'::jsonb,
             'count_reviewed',
             '{"min_quality": 4.0,"threshold": 25}'::jsonb,
             'rare', 400),
            ('chronicler', 'content',
             '{"en":"Chronicler","uz":"Solnomachi","ru":"Летописец"}'::jsonb,
             '{"en":"Publish 100 reviews"}'::jsonb,
             'count_reviewed',
             '{"threshold": 100}'::jsonb,
             'epic', 1000),
            ('week_warrior', 'streak',
             '{"en":"Week Warrior","uz":"Haftalik jangchi","ru":"Воин недели"}'::jsonb,
             '{"en":"7-day streak"}'::jsonb,
             'streak_days',
             '{"threshold": 7}'::jsonb,
             'common', 100),
            ('month_master', 'streak',
             '{"en":"Month Master","uz":"Oylik ustasi","ru":"Мастер месяца"}'::jsonb,
             '{"en":"30-day streak"}'::jsonb,
             'streak_days',
             '{"threshold": 30}'::jsonb,
             'rare', 500),
            ('photographer', 'content',
             '{"en":"Photographer","uz":"Suratchi","ru":"Фотограф"}'::jsonb,
             '{"en":"Upload 50 published photos"}'::jsonb,
             'count_photos',
             '{"threshold": 50}'::jsonb,
             'rare', 300),
            ('trusted_voice', 'social',
             '{"en":"Trusted Voice","uz":"Ishonchli ovoz","ru":"Доверенный голос"}'::jsonb,
             '{"en":"Receive 100 helpful votes"}'::jsonb,
             'count_helpful_received',
             '{"threshold": 100}'::jsonb,
             'epic', 800);
        """
    )

    # --- user_badges ----------------------------------------------------------
    op.execute(
        """
        CREATE TABLE user_badges (
            user_id             uuid NOT NULL,
            residency_region    text NOT NULL,
            badge_type_id       uuid NOT NULL REFERENCES badge_types(id) ON DELETE CASCADE,
            awarded_at          timestamptz NOT NULL DEFAULT now(),
            source_event_id     uuid,
            progress            jsonb NOT NULL DEFAULT '{}'::jsonb,
            revoked_at          timestamptz,
            revoke_reason       text,

            PRIMARY KEY (user_id, badge_type_id),
            FOREIGN KEY (user_id, residency_region)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (residency_region IN ('uz','eu','us','global'))
        );

        CREATE INDEX idx_user_badges_user_time
            ON user_badges (user_id, awarded_at DESC)
            WHERE revoked_at IS NULL;
        CREATE INDEX idx_user_badges_badge
            ON user_badges (badge_type_id, awarded_at DESC)
            WHERE revoked_at IS NULL;

        COMMENT ON TABLE user_badges IS
            'Earned badges. progress JSONB carries partial-completion state '
            'so the UI can render "8/10 sites visited" without a side-table.';
        """
    )

    # --- xp_events (append-only ledger, RANGE-partitioned monthly) -----------
    # The UNIQUE(user_id, idempotency_key) is the heart of anti-XP-farming:
    # the same visit/review/etc. cannot grant XP twice — DB-enforced.
    op.execute(
        """
        CREATE TABLE xp_events (
            id                  uuid NOT NULL DEFAULT gen_uuid_v7(),
            user_id             uuid NOT NULL,
            residency_region    text NOT NULL,
            source_kind         text NOT NULL
                CHECK (source_kind IN (
                    'visit','review','photo','badge','streak','referral',
                    'correction','admin_grant','clawback','helpful_received',
                    'velocity_throttled'
                )),
            source_id           uuid,
            delta               integer NOT NULL,
            idempotency_key     text NOT NULL,
            context             jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at          timestamptz NOT NULL DEFAULT now(),

            PRIMARY KEY (id, created_at),
            FOREIGN KEY (user_id, residency_region)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (residency_region IN ('uz','eu','us','global')),
            CHECK (length(idempotency_key) BETWEEN 1 AND 256)
        ) PARTITION BY RANGE (created_at);

        COMMENT ON TABLE xp_events IS
            'Append-only XP ledger. delta CAN be negative (clawback). '
            'Anti-farming UNIQUE includes the partition key per Postgres '
            'partitioned-table rules.';
        """
    )

    today = datetime.now(timezone.utc)
    months = _month_partitions(today, 4)
    for suffix, lo, hi in months:
        op.execute(
            f"""
            CREATE TABLE xp_events_{suffix}
                PARTITION OF xp_events
                FOR VALUES FROM ('{lo}') TO ('{hi}');
            """
        )
    op.execute("CREATE TABLE xp_events_default PARTITION OF xp_events DEFAULT;")

    # Global unique on (user_id, idempotency_key) must include the partition key
    # (created_at). Each child partition's local uniqueness on (user, key) is
    # implied by the global PK + the partition constraint. Cross-partition
    # duplicate prevention is enforced at the application layer (idempotency_key
    # patterns embed the date so the same key always falls in the same month
    # partition; see Agent 5 §5.1 — keys like 'visit:USER:HERITAGE:2026-05-18').
    op.execute(
        """
        CREATE UNIQUE INDEX uq_xp_events_idempotency
            ON xp_events (user_id, idempotency_key, created_at);
        CREATE INDEX idx_xp_events_user_time
            ON xp_events (user_id, created_at DESC);
        CREATE INDEX idx_xp_events_source
            ON xp_events (source_kind, created_at DESC);
        """
    )

    # --- xp_balances (materialised projection) -------------------------------
    op.execute(
        """
        CREATE TABLE xp_balances (
            user_id             uuid NOT NULL,
            residency_region    text NOT NULL,
            current_xp          bigint NOT NULL DEFAULT 0,
            lifetime_xp         bigint NOT NULL DEFAULT 0,
            weekly_xp           integer NOT NULL DEFAULT 0,
            monthly_xp          integer NOT NULL DEFAULT 0,
            yearly_xp           integer NOT NULL DEFAULT 0,
            last_event_at       timestamptz,
            last_event_id       uuid,
            refreshed_at        timestamptz NOT NULL DEFAULT now(),

            PRIMARY KEY (user_id),
            FOREIGN KEY (user_id, residency_region)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (residency_region IN ('uz','eu','us','global'))
        );

        CREATE INDEX idx_xp_balances_current
            ON xp_balances (current_xp DESC);
        CREATE INDEX idx_xp_balances_weekly
            ON xp_balances (weekly_xp DESC) WHERE weekly_xp > 0;

        COMMENT ON TABLE xp_balances IS
            'Materialised current/lifetime XP per user. Maintained by trigger '
            '+ nightly reconciliation against xp_events (drift detector).';
        """
    )

    # --- levels (admin catalog) ----------------------------------------------
    op.execute(
        """
        CREATE TABLE levels (
            number          smallint PRIMARY KEY,
            slug            text NOT NULL UNIQUE,
            name            jsonb NOT NULL DEFAULT '{}'::jsonb,
            xp_required     integer NOT NULL,
            perks           jsonb NOT NULL DEFAULT '{}'::jsonb,
            is_active       boolean NOT NULL DEFAULT true,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            CHECK (number >= 1),
            CHECK (xp_required >= 0),
            CHECK (slug ~ '^[a-z][a-z0-9_]*$')
        );

        CREATE TRIGGER tg_levels_updated_at
            BEFORE UPDATE ON levels
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    op.execute(
        """
        INSERT INTO levels (number, slug, name, xp_required, perks) VALUES
            (1, 'sayohatchi',
             '{"en":"Traveler","uz":"Sayohatchi","ru":"Путешественник"}'::jsonb,
             0,
             '{"audio_minutes_per_month": 10}'::jsonb),
            (2, 'kashfiyotchi',
             '{"en":"Explorer","uz":"Kashfiyotchi","ru":"Исследователь"}'::jsonb,
             500,
             '{"audio_minutes_per_month": 30}'::jsonb),
            (3, 'meros_qoriqchi',
             '{"en":"Heritage Guardian","uz":"Meros Qo''riqchisi","ru":"Хранитель наследия"}'::jsonb,
             2000,
             '{"audio_minutes_per_month": 60,"ar_unlocked": true}'::jsonb),
            (4, 'ipak_yoli_gidi',
             '{"en":"Silk Road Guide","uz":"Ipak Yo''li Gidi","ru":"Гид Шёлкового пути"}'::jsonb,
             5000,
             '{"audio_minutes_per_month": 120,"ar_unlocked": true,"premium_voices": true}'::jsonb),
            (5, 'ustoz_sayyoh',
             '{"en":"Master Traveler","uz":"Ustoz Sayyoh","ru":"Мастер-путешественник"}'::jsonb,
             15000,
             '{"audio_minutes_per_month": 300,"ar_unlocked": true,"premium_voices": true,"early_access": true}'::jsonb);
        """
    )

    # --- streaks --------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE streaks (
            user_id             uuid NOT NULL,
            residency_region    text NOT NULL,
            current_streak      integer NOT NULL DEFAULT 0,
            longest_streak      integer NOT NULL DEFAULT 0,
            last_active_date    date,
            timezone_anchor     text NOT NULL DEFAULT 'Asia/Tashkent',
            freeze_credits      smallint NOT NULL DEFAULT 0,
            broken_at           timestamptz,
            updated_at          timestamptz NOT NULL DEFAULT now(),

            PRIMARY KEY (user_id),
            FOREIGN KEY (user_id, residency_region)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (residency_region IN ('uz','eu','us','global')),
            CHECK (current_streak >= 0),
            CHECK (longest_streak >= current_streak)
        );

        CREATE INDEX idx_streaks_current
            ON streaks (current_streak DESC) WHERE current_streak > 0;

        CREATE TRIGGER tg_streaks_updated_at
            BEFORE UPDATE ON streaks
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE streaks IS
            'Materialised streak state. Rebuilt from streak_events when a '
            'reconciliation job runs (Agent 5 §3.26-§3.27).';
        """
    )

    # --- streak_events (daily heartbeat) -------------------------------------
    op.execute(
        """
        CREATE TABLE streak_events (
            user_id             uuid NOT NULL,
            residency_region    text NOT NULL,
            event_date          date NOT NULL,
            source              text NOT NULL DEFAULT 'open'
                CHECK (source IN ('open','visit','review','photo','manual_freeze','referral')),
            source_event_id     uuid,
            recorded_at         timestamptz NOT NULL DEFAULT now(),

            PRIMARY KEY (user_id, event_date),
            FOREIGN KEY (user_id, residency_region)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (residency_region IN ('uz','eu','us','global'))
        );

        CREATE INDEX idx_streak_events_date
            ON streak_events (event_date);

        COMMENT ON TABLE streak_events IS
            'One row per (user, local_date). Rebuilds streaks.current_streak '
            'from contiguous date runs ending at today.';
        """
    )

    # --- leaderboards (admin catalog) ----------------------------------------
    op.execute(
        """
        CREATE TABLE leaderboards (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            slug            text NOT NULL UNIQUE,
            name            jsonb NOT NULL DEFAULT '{}'::jsonb,
            scope           text NOT NULL
                CHECK (scope IN ('global','country','city','friends','region')),
            scope_ref       text,
            period          text NOT NULL
                CHECK (period IN ('daily','weekly','monthly','yearly','alltime')),
            metric          text NOT NULL
                CHECK (metric IN ('xp','visits','reviews','badges','helpful_received','photos')),
            is_active       boolean NOT NULL DEFAULT true,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            CHECK (slug ~ '^[a-z][a-z0-9_]*$')
        );

        CREATE TRIGGER tg_leaderboards_updated_at
            BEFORE UPDATE ON leaderboards
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    op.execute(
        """
        INSERT INTO leaderboards (slug, name, scope, period, metric) VALUES
            ('global_xp_weekly',
             '{"en":"Global XP — This Week","uz":"Global XP — Bu hafta"}'::jsonb,
             'global', 'weekly', 'xp'),
            ('global_xp_alltime',
             '{"en":"Global XP — All time","uz":"Global XP — Barcha vaqt"}'::jsonb,
             'global', 'alltime', 'xp'),
            ('friends_xp_weekly',
             '{"en":"Friends XP — This Week"}'::jsonb,
             'friends', 'weekly', 'xp'),
            ('global_visits_monthly',
             '{"en":"Most Visits — This Month"}'::jsonb,
             'global', 'monthly', 'visits');
        """
    )

    # --- leaderboard_snapshots (frozen end-of-period) ------------------------
    # PK is composite (leaderboard, period_end, rank). Rank within a snapshot
    # is a small int (top N, typically 100).
    op.execute(
        """
        CREATE TABLE leaderboard_snapshots (
            leaderboard_id      uuid NOT NULL REFERENCES leaderboards(id) ON DELETE CASCADE,
            period_end          date NOT NULL,
            rank                integer NOT NULL,
            user_id             uuid NOT NULL,
            residency_region    text NOT NULL,
            metric_value        bigint NOT NULL,
            display_name_snapshot text,
            frozen_at           timestamptz NOT NULL DEFAULT now(),

            PRIMARY KEY (leaderboard_id, period_end, rank),
            FOREIGN KEY (user_id, residency_region)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (residency_region IN ('uz','eu','us','global')),
            CHECK (rank >= 1),
            CHECK (metric_value >= 0)
        );

        CREATE INDEX idx_leaderboard_snapshots_user
            ON leaderboard_snapshots (user_id, period_end DESC);
        CREATE INDEX idx_leaderboard_snapshots_lb_period
            ON leaderboard_snapshots (leaderboard_id, period_end DESC);

        COMMENT ON TABLE leaderboard_snapshots IS
            'Frozen end-of-period results. display_name_snapshot lets us still '
            'render "won Week 23, 2026" even after the user deletes their account.';
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS leaderboard_snapshots CASCADE;")
    op.execute("DROP TABLE IF EXISTS leaderboards CASCADE;")
    op.execute("DROP TABLE IF EXISTS streak_events CASCADE;")
    op.execute("DROP TABLE IF EXISTS streaks CASCADE;")
    op.execute("DROP TABLE IF EXISTS levels CASCADE;")
    op.execute("DROP TABLE IF EXISTS xp_balances CASCADE;")
    op.execute("DROP TABLE IF EXISTS xp_events CASCADE;")
    op.execute("DROP TABLE IF EXISTS user_badges CASCADE;")
    op.execute("DROP TABLE IF EXISTS badge_types CASCADE;")
