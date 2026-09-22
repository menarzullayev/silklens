"""moderation pipeline: policies, queue, actions, reports, sockpuppet graph, abuse rules

Per Agent 5 §3.38-§3.51 + §6 (state machine) + §5.4 (sock-puppet detection).

Layered on top of ugc_submissions (created in 0041) and device_fingerprints
(created in 0009):

  moderation_policies     — admin-tunable per (region, content_kind, trust_tier).
                            Resolves to one row per submission via the most-specific
                            match (Agent 5 §6.2). Drives pre/post/AI-gated mode.
  moderation_queue        — work-queue rows for submissions needing human eyes.
                            One row per submission_id (PK = UNIQUE).
  moderation_actions      — append-only audit of every decision an actor takes.
  reports                 — user-submitted flags. De-duped by
                            (reporter, target_kind, target_id, reason_slug).
  report_resolutions      — what happened to each report.
  auto_moderation_results — link to Agent C's ai_moderation_results (cross-domain
                            UUID — no FK to keep agents independently deployable).
  device_fingerprints_link — sockpuppet suspicion graph: pairs of users who shared
                            a device_fingerprint, with a confidence score and
                            first/last-seen window.
  gamification_anti_abuse_rules — admin-tunable rules consumed by the XP
                            evaluator worker. Decoupled from xp_events so admins
                            can change thresholds without code.

All user FKs use composite (id, residency_region) per migration 0009.

Revision ID: 0043_moderation_pipeline
Revises: 0042_gamification
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0043_moderation_pipeline"
down_revision: str | Sequence[str] | None = "0042_gamification"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- moderation_policies (admin-tunable) ---------------------------------
    # region_id refers to Agent 1's geographic_admin_levels (created in the
    # heritage geography migration). Nullable region_id means "global default";
    # nullable user_trust_tier means "applies to all tiers".
    op.execute(
        """
        CREATE TABLE moderation_policies (
            id                      uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            slug                    text NOT NULL UNIQUE,
            region_id               uuid,
            content_kind            text NOT NULL,
            user_trust_tier         text,
            mode                    text NOT NULL
                CHECK (mode IN ('pre_moderation','post_moderation','ai_gated')),
            auto_approve_threshold  numeric(4,3) NOT NULL DEFAULT 0.900,
            auto_reject_threshold   numeric(4,3) NOT NULL DEFAULT 0.200,
            human_required_above    text[] NOT NULL DEFAULT ARRAY[]::text[],
            human_lane              text NOT NULL DEFAULT 'human_general'
                CHECK (human_lane IN (
                    'human_general','human_safety','human_cultural','appeal'
                )),
            sla_minutes             integer NOT NULL DEFAULT 240,
            is_active               boolean NOT NULL DEFAULT true,
            effective_from          timestamptz NOT NULL DEFAULT now(),
            created_at              timestamptz NOT NULL DEFAULT now(),
            updated_at              timestamptz NOT NULL DEFAULT now(),
            CHECK (slug ~ '^[a-z][a-z0-9_]*$'),
            CHECK (auto_approve_threshold > auto_reject_threshold),
            CHECK (auto_approve_threshold BETWEEN 0 AND 1),
            CHECK (auto_reject_threshold BETWEEN 0 AND 1),
            CHECK (sla_minutes > 0),
            CHECK (content_kind ~ '^[a-z][a-z0-9_]*$')
        );

        CREATE INDEX idx_moderation_policies_lookup
            ON moderation_policies (content_kind, region_id, user_trust_tier)
            WHERE is_active;

        CREATE TRIGGER tg_moderation_policies_updated_at
            BEFORE UPDATE ON moderation_policies
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE moderation_policies IS
            'Admin-tunable policies per (content_kind × region × user_trust_tier). '
            'Resolution order: tier-specific → region-specific → content global. '
            'No FK on region_id to keep this migration independent of the '
            'geographic_admin_levels migration ordering.';
        """
    )

    # Seed a global default policy per content_kind so the resolver never
    # returns an empty match.
    op.execute(
        """
        INSERT INTO moderation_policies
            (slug, content_kind, mode, auto_approve_threshold, auto_reject_threshold, sla_minutes)
        VALUES
            ('default_review',  'review',  'ai_gated', 0.900, 0.200, 240),
            ('default_photo',   'photo',   'ai_gated', 0.950, 0.150,  60),
            ('default_video',   'video',   'pre_moderation', 0.980, 0.100, 240),
            ('default_comment', 'comment', 'post_moderation', 0.900, 0.150, 240),
            ('default_alias',   'heritage_alias', 'pre_moderation', 0.970, 0.150, 480),
            ('default_journal', 'journal', 'ai_gated', 0.920, 0.200, 1440);
        """
    )

    # --- moderation_queue ----------------------------------------------------
    # PK = submission_id so a submission can be enqueued at most once.
    op.execute(
        """
        CREATE TABLE moderation_queue (
            submission_id           uuid PRIMARY KEY
                REFERENCES ugc_submissions(id) ON DELETE CASCADE,
            assigned_to_user_id     uuid,
            assigned_to_residency   text,
            lane                    text NOT NULL DEFAULT 'human_general'
                CHECK (lane IN (
                    'ai_review','human_general','human_safety',
                    'human_cultural','appeal'
                )),
            priority                smallint NOT NULL DEFAULT 5,
            sla_due_at              timestamptz NOT NULL,
            enqueued_at             timestamptz NOT NULL DEFAULT now(),
            claimed_at              timestamptz,
            resolved_at             timestamptz,

            FOREIGN KEY (assigned_to_user_id, assigned_to_residency)
                REFERENCES users(id, residency_region) ON DELETE SET NULL,
            CHECK ((assigned_to_user_id IS NULL) = (assigned_to_residency IS NULL)),
            CHECK (assigned_to_residency IS NULL
                   OR assigned_to_residency IN ('uz','eu','us','global')),
            CHECK (priority BETWEEN 1 AND 10)
        );

        CREATE INDEX idx_moderation_queue_lane_priority
            ON moderation_queue (lane, priority, sla_due_at)
            WHERE assigned_to_user_id IS NULL AND resolved_at IS NULL;
        CREATE INDEX idx_moderation_queue_assigned
            ON moderation_queue (assigned_to_user_id, sla_due_at)
            WHERE resolved_at IS NULL;
        CREATE INDEX idx_moderation_queue_sla
            ON moderation_queue (sla_due_at)
            WHERE resolved_at IS NULL;

        COMMENT ON TABLE moderation_queue IS
            'Work queue onto ugc_submissions for human review. Single row per '
            'submission. Lane + priority drives moderator UI assignment.';
        """
    )

    # --- moderation_actions (append-only audit) ------------------------------
    op.execute(
        """
        CREATE TABLE moderation_actions (
            id                      uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            submission_id           uuid NOT NULL
                REFERENCES ugc_submissions(id) ON DELETE CASCADE,
            moderator_user_id       uuid,
            moderator_residency     text,
            actor_kind              text NOT NULL DEFAULT 'moderator'
                CHECK (actor_kind IN ('system','ai','moderator','admin','user_self')),
            action                  text NOT NULL
                CHECK (action IN (
                    'approve','reject','quarantine','escalate','edit',
                    'restore','shadow_ban','unfreeze'
                )),
            reason                  text,
            notes                   text,
            policy_id               uuid REFERENCES moderation_policies(id) ON DELETE SET NULL,
            created_at              timestamptz NOT NULL DEFAULT now(),

            FOREIGN KEY (moderator_user_id, moderator_residency)
                REFERENCES users(id, residency_region) ON DELETE SET NULL,
            CHECK ((moderator_user_id IS NULL) = (moderator_residency IS NULL)),
            CHECK (moderator_residency IS NULL
                   OR moderator_residency IN ('uz','eu','us','global'))
        );

        CREATE INDEX idx_moderation_actions_submission
            ON moderation_actions (submission_id, created_at);
        CREATE INDEX idx_moderation_actions_moderator
            ON moderation_actions (moderator_user_id, created_at DESC)
            WHERE moderator_user_id IS NOT NULL;
        CREATE INDEX idx_moderation_actions_action
            ON moderation_actions (action, created_at DESC);

        COMMENT ON TABLE moderation_actions IS
            'Append-only audit of every moderator/AI/system decision against a '
            'submission. Forms the trail for moderator-quality evaluation and '
            'user-facing appeal evidence.';
        """
    )

    # --- reports (user-submitted) --------------------------------------------
    op.execute(
        """
        CREATE TABLE reports (
            id                      uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            reporter_user_id        uuid NOT NULL,
            reporter_residency      text NOT NULL,
            target_kind             text NOT NULL
                CHECK (target_kind IN (
                    'review','comment','photo','video','journal','journal_entry',
                    'user','heritage','heritage_fact','trip','trip_chat'
                )),
            target_id               uuid NOT NULL,
            reason_slug             text NOT NULL
                CHECK (reason_slug IN (
                    'spam','nsfw','hate','copyright','misinformation',
                    'cultural_insensitive','impersonation','harassment',
                    'wrong_geotag','other'
                )),
            details                 text,
            status                  text NOT NULL DEFAULT 'open'
                CHECK (status IN ('open','investigating','closed_actioned','closed_no_action')),
            submission_id           uuid REFERENCES ugc_submissions(id) ON DELETE SET NULL,
            created_at              timestamptz NOT NULL DEFAULT now(),
            closed_at               timestamptz,

            FOREIGN KEY (reporter_user_id, reporter_residency)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (reporter_residency IN ('uz','eu','us','global')),
            UNIQUE (reporter_user_id, target_kind, target_id, reason_slug)
        );

        CREATE INDEX idx_reports_target
            ON reports (target_kind, target_id, status);
        CREATE INDEX idx_reports_open
            ON reports (created_at DESC) WHERE status = 'open';
        CREATE INDEX idx_reports_reporter
            ON reports (reporter_user_id, created_at DESC);

        COMMENT ON TABLE reports IS
            'User flags. Dedup-unique on (reporter, target, reason) prevents '
            'spam-reporting. N distinct reports of the same target+reason '
            'auto-escalates queue priority.';
        """
    )

    # --- report_resolutions --------------------------------------------------
    op.execute(
        """
        CREATE TABLE report_resolutions (
            id                      uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            report_id               uuid NOT NULL UNIQUE
                REFERENCES reports(id) ON DELETE CASCADE,
            resolution_kind         text NOT NULL
                CHECK (resolution_kind IN (
                    'upheld','dismissed','removed','warning_issued',
                    'user_banned','escalated','no_action'
                )),
            actor_user_id           uuid,
            actor_residency         text,
            moderation_action_id    uuid REFERENCES moderation_actions(id) ON DELETE SET NULL,
            notes                   text,
            created_at              timestamptz NOT NULL DEFAULT now(),

            FOREIGN KEY (actor_user_id, actor_residency)
                REFERENCES users(id, residency_region) ON DELETE SET NULL,
            CHECK ((actor_user_id IS NULL) = (actor_residency IS NULL)),
            CHECK (actor_residency IS NULL OR actor_residency IN ('uz','eu','us','global'))
        );

        CREATE INDEX idx_report_resolutions_kind
            ON report_resolutions (resolution_kind, created_at DESC);
        CREATE INDEX idx_report_resolutions_actor
            ON report_resolutions (actor_user_id, created_at DESC)
            WHERE actor_user_id IS NOT NULL;

        COMMENT ON TABLE report_resolutions IS
            'Outcome of each report. UNIQUE(report_id) — a report resolves at '
            'most once.';
        """
    )

    # --- auto_moderation_results (Agent 3 link) ------------------------------
    # No FK on ai_moderation_id: Agent C's ai_moderation_results table is in
    # a separate bounded context; we keep the UUID as a logical pointer so
    # deploys can roll independently.
    op.execute(
        """
        CREATE TABLE auto_moderation_results (
            submission_id           uuid PRIMARY KEY
                REFERENCES ugc_submissions(id) ON DELETE CASCADE,
            ai_moderation_id        uuid NOT NULL,
            nsfw_score              numeric(4,3),
            violence_score          numeric(4,3),
            hate_score              numeric(4,3),
            spam_score              numeric(4,3),
            geotag_valid            boolean,
            language_detected       text,
            duplicate_of            uuid,
            cultural_flags          jsonb NOT NULL DEFAULT '{}'::jsonb,
            raw_payload             jsonb NOT NULL DEFAULT '{}'::jsonb,
            scored_at               timestamptz NOT NULL DEFAULT now(),
            CHECK (nsfw_score     IS NULL OR nsfw_score     BETWEEN 0 AND 1),
            CHECK (violence_score IS NULL OR violence_score BETWEEN 0 AND 1),
            CHECK (hate_score     IS NULL OR hate_score     BETWEEN 0 AND 1),
            CHECK (spam_score     IS NULL OR spam_score     BETWEEN 0 AND 1)
        );

        CREATE INDEX idx_auto_moderation_results_ai_id
            ON auto_moderation_results (ai_moderation_id);
        CREATE INDEX idx_auto_moderation_results_duplicate
            ON auto_moderation_results (duplicate_of) WHERE duplicate_of IS NOT NULL;
        CREATE INDEX idx_auto_moderation_results_cultural
            ON auto_moderation_results USING GIN (cultural_flags jsonb_path_ops);

        COMMENT ON TABLE auto_moderation_results IS
            'AI scoring per submission. ai_moderation_id references Agent C''s '
            'ai_moderation_results.id WITHOUT an FK so the two bounded contexts '
            'can deploy independently.';
        """
    )

    # --- device_fingerprints_link (sock-puppet suspicion graph) --------------
    # Pairs of users who have shared a device_fingerprint, with confidence.
    # Canonical ordering user_a_id < user_b_id deduplicates the symmetric edge.
    op.execute(
        """
        CREATE TABLE device_fingerprints_link (
            user_a_id               uuid NOT NULL,
            user_a_residency        text NOT NULL,
            user_b_id               uuid NOT NULL,
            user_b_residency        text NOT NULL,
            device_fingerprint_id   uuid NOT NULL
                REFERENCES device_fingerprints(id) ON DELETE CASCADE,
            similarity_score        numeric(4,3) NOT NULL,
            shared_count            integer NOT NULL DEFAULT 1,
            first_observed_at       timestamptz NOT NULL DEFAULT now(),
            last_observed_at        timestamptz NOT NULL DEFAULT now(),

            PRIMARY KEY (user_a_id, user_b_id, device_fingerprint_id),
            FOREIGN KEY (user_a_id, user_a_residency)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            FOREIGN KEY (user_b_id, user_b_residency)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (user_a_id < user_b_id),
            CHECK (user_a_residency IN ('uz','eu','us','global')),
            CHECK (user_b_residency IN ('uz','eu','us','global')),
            CHECK (similarity_score BETWEEN 0 AND 1)
        );

        CREATE INDEX idx_device_fingerprints_link_a
            ON device_fingerprints_link (user_a_id);
        CREATE INDEX idx_device_fingerprints_link_b
            ON device_fingerprints_link (user_b_id);
        CREATE INDEX idx_device_fingerprints_link_fp
            ON device_fingerprints_link (device_fingerprint_id);
        CREATE INDEX idx_device_fingerprints_link_high
            ON device_fingerprints_link (similarity_score DESC)
            WHERE similarity_score >= 0.8;

        COMMENT ON TABLE device_fingerprints_link IS
            'Pairs of users sharing a device_fingerprint. Dampens mutual '
            'helpful-votes and XP-from-referral when confidence >= 0.8 '
            '(Agent 5 §5.4).';
        """
    )

    # --- gamification_anti_abuse_rules (admin-tunable) ----------------------
    op.execute(
        """
        CREATE TABLE gamification_anti_abuse_rules (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            slug            text NOT NULL UNIQUE,
            rule_kind       text NOT NULL
                CHECK (rule_kind IN ('velocity','duplicate_geo','sockpuppet','oddity','geofence')),
            threshold       jsonb NOT NULL DEFAULT '{}'::jsonb,
            penalty         text NOT NULL
                CHECK (penalty IN ('shadow_damp','notify','auto_clawback','lock_account','reject')),
            is_active       boolean NOT NULL DEFAULT true,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            CHECK (slug ~ '^[a-z][a-z0-9_]*$')
        );

        CREATE INDEX idx_gamification_rules_kind
            ON gamification_anti_abuse_rules (rule_kind) WHERE is_active;

        CREATE TRIGGER tg_gamification_anti_abuse_rules_updated_at
            BEFORE UPDATE ON gamification_anti_abuse_rules
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE gamification_anti_abuse_rules IS
            'Admin DSL: threshold JSONB is interpreted by the XP evaluator '
            'worker per rule_kind. Adding a new rule = INSERT.';
        """
    )

    # Seed sane v1 anti-abuse rules per Agent 5 §5.2-§5.4.
    op.execute(
        """
        INSERT INTO gamification_anti_abuse_rules (slug, rule_kind, threshold, penalty) VALUES
            ('visit_velocity_60m',
             'velocity',
             '{"event":"visit","max_per_window": 8,"window_minutes": 60}'::jsonb,
             'shadow_damp'),
            ('review_velocity_60m',
             'velocity',
             '{"event":"review","max_per_window": 5,"window_minutes": 60}'::jsonb,
             'shadow_damp'),
            ('check_in_geofence_default',
             'geofence',
             '{"max_distance_meters": 500,"min_gps_accuracy_meters": 100}'::jsonb,
             'reject'),
            ('sockpuppet_helpful_chain',
             'sockpuppet',
             '{"min_confidence": 0.80,"action":"dampen"}'::jsonb,
             'shadow_damp'),
            ('sockpuppet_referral',
             'sockpuppet',
             '{"min_confidence": 0.85}'::jsonb,
             'auto_clawback'),
            ('oddity_timezone_jump',
             'oddity',
             '{"max_timezone_changes_per_day": 1}'::jsonb,
             'notify');
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS gamification_anti_abuse_rules CASCADE;")
    op.execute("DROP TABLE IF EXISTS device_fingerprints_link CASCADE;")
    op.execute("DROP TABLE IF EXISTS auto_moderation_results CASCADE;")
    op.execute("DROP TABLE IF EXISTS report_resolutions CASCADE;")
    op.execute("DROP TABLE IF EXISTS reports CASCADE;")
    op.execute("DROP TABLE IF EXISTS moderation_actions CASCADE;")
    op.execute("DROP TABLE IF EXISTS moderation_queue CASCADE;")
    op.execute("DROP TABLE IF EXISTS moderation_policies CASCADE;")
