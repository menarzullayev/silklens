"""ai_translation_memory + injection log + recommendation state + interactions + feedback + drift + safety

Per Agent 3 §§3.18-3.27:

The "long tail" of the AI substrate — translation memory + bulk-translation
orchestration, prompt-injection audit trail, per-user recommendation
state with collaborative-filter latent vectors, interaction log feeding
the recommender, human feedback on AI outputs (for FAZA 7 fine-tuning),
periodic drift snapshots, and safety-incident bookkeeping.

Tables (8):
    ai_translation_memory, ai_translation_jobs, ai_prompt_injection_log,
    ai_recommendation_state, ai_user_item_interactions (RANGE-partitioned),
    ai_feedback, ai_drift_metrics, ai_safety_incidents.

Revision ID: 0033_ai_safety_and_tm
Revises: 0032_ai_runtime
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from alembic import op

revision: str = "0033_ai_safety_and_tm"
down_revision: str | Sequence[str] | None = "0032_ai_runtime"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _month_bounds(year: int, month: int) -> tuple[str, str]:
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return start.isoformat(), end.isoformat()


def _months_around(offset_start: int, offset_end: int) -> list[tuple[int, int]]:
    today = date.today().replace(day=1)
    out: list[tuple[int, int]] = []
    for offset in range(offset_start, offset_end + 1):
        year = today.year + ((today.month - 1 + offset) // 12)
        month = ((today.month - 1 + offset) % 12) + 1
        out.append((year, month))
    return out


def upgrade() -> None:
    # ====================================================================
    # ai_translation_memory — segment-level TM with fuzzy match via trgm
    # ====================================================================
    # Composite PK includes model_version_id so we can keep the *same* source
    # text translated by different model generations and compare quality.
    op.execute(
        """
        CREATE TABLE ai_translation_memory (
            source_hash         bytea NOT NULL,
            source_lang         text NOT NULL,
            target_lang         text NOT NULL,
            model_version_id    uuid NOT NULL REFERENCES ai_model_versions(id) ON DELETE RESTRICT,
            source_text         text NOT NULL,
            target_text         text NOT NULL,
            bleu_score          numeric(4,3),
            confidence          smallint NOT NULL DEFAULT 50,
            hit_count           int NOT NULL DEFAULT 0,
            last_hit_at         timestamptz,
            created_at          timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (source_hash, source_lang, target_lang, model_version_id),
            CHECK (octet_length(source_hash) = 32),
            CHECK (confidence BETWEEN 0 AND 100),
            CHECK (length(source_lang) BETWEEN 2 AND 8),
            CHECK (length(target_lang) BETWEEN 2 AND 8),
            CHECK (source_lang <> target_lang),
            CHECK (bleu_score IS NULL OR (bleu_score >= 0 AND bleu_score <= 1)),
            CHECK (hit_count >= 0)
        );

        CREATE INDEX idx_ai_tm_lang
            ON ai_translation_memory(source_lang, target_lang);
        CREATE INDEX idx_ai_tm_recent
            ON ai_translation_memory(last_hit_at DESC NULLS LAST);
        -- Trigram fuzzy match (~92% similar source_text → TM hit) per Agent 3 §3.18
        CREATE INDEX idx_ai_tm_source_trgm
            ON ai_translation_memory USING GIN (source_text gin_trgm_ops);

        COMMENT ON TABLE ai_translation_memory IS
            'Segment-level translation memory (Agent 3 §3.18). source_text retained '
            'verbatim so trigram fuzzy match can surface near-duplicate inputs.';
        """
    )

    # ====================================================================
    # ai_translation_jobs — bulk translation orchestration
    # ====================================================================
    op.execute(
        """
        CREATE TABLE ai_translation_jobs (
            id                  uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            target_kind         text NOT NULL,
            target_id           uuid NOT NULL,
            source_lang         text NOT NULL,
            target_lang         text NOT NULL,
            status              text NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending','running','done','failed','cancelled')),
            model_version_id    uuid NOT NULL REFERENCES ai_model_versions(id) ON DELETE RESTRICT,
            output_text         text,
            confidence          smallint,
            created_at          timestamptz NOT NULL DEFAULT now(),
            finished_at         timestamptz,
            CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 100),
            CHECK (length(source_lang) BETWEEN 2 AND 8),
            CHECK (length(target_lang) BETWEEN 2 AND 8),
            CHECK (source_lang <> target_lang),
            CHECK (finished_at IS NULL OR finished_at >= created_at)
        );

        CREATE INDEX idx_ai_translation_jobs_status
            ON ai_translation_jobs(status, created_at)
            WHERE status IN ('pending','running');
        CREATE INDEX idx_ai_translation_jobs_target
            ON ai_translation_jobs(target_kind, target_id);
        """
    )

    # ====================================================================
    # ai_prompt_injection_log — security audit trail
    # ====================================================================
    op.execute(
        """
        CREATE TABLE ai_prompt_injection_log (
            id                          uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            user_id                     uuid,
            session_id                  uuid,
            input_text                  text NOT NULL,
            score                       numeric(4,3),
            classifier_model_version_id uuid NOT NULL REFERENCES ai_model_versions(id) ON DELETE RESTRICT,
            action                      text NOT NULL
                CHECK (action IN ('flagged','blocked','allowed')),
            request_id                  text,
            created_at                  timestamptz NOT NULL DEFAULT now(),
            CHECK (score IS NULL OR (score >= 0 AND score <= 1))
        );

        CREATE INDEX idx_ai_injection_log_user_recent
            ON ai_prompt_injection_log(user_id, created_at DESC)
            WHERE user_id IS NOT NULL;
        CREATE INDEX idx_ai_injection_log_action_recent
            ON ai_prompt_injection_log(action, created_at DESC);
        CREATE INDEX idx_ai_injection_log_session
            ON ai_prompt_injection_log(session_id, created_at DESC)
            WHERE session_id IS NOT NULL;

        COMMENT ON TABLE ai_prompt_injection_log IS
            'Per-input prompt-injection signals (Agent 3 §3.22). input_text is '
            'expected to be truncated to a safe preview by the caller.';
        """
    )

    # ====================================================================
    # ai_recommendation_state — per-user CF state
    # ====================================================================
    # user_id is NOT an FK because users is LIST-partitioned with composite PK
    # (id, residency_region) per migration 0004 — outside-table FKs to that
    # combination require carrying residency_region everywhere, which we avoid.
    op.execute(
        """
        CREATE TABLE ai_recommendation_state (
            user_id             uuid NOT NULL,
            model_version_id    uuid NOT NULL REFERENCES ai_model_versions(id) ON DELETE CASCADE,
            latent_vector       vector(64),
            last_recomputed_at  timestamptz NOT NULL DEFAULT now(),
            sample_count        int NOT NULL DEFAULT 0,
            updated_at          timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (user_id, model_version_id),
            CHECK (sample_count >= 0)
        );

        CREATE INDEX idx_ai_recommendation_state_hnsw
            ON ai_recommendation_state
            USING hnsw (latent_vector vector_cosine_ops)
            WITH (m = 16, ef_construction = 200);

        CREATE INDEX idx_ai_recommendation_state_recent
            ON ai_recommendation_state(last_recomputed_at);

        CREATE TRIGGER tg_ai_recommendation_state_updated_at
            BEFORE UPDATE ON ai_recommendation_state
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON COLUMN ai_recommendation_state.user_id IS
            'No FK to users(id) because users is residency-partitioned with '
            'composite PK. Resolution is application-side.';
        """
    )

    # ====================================================================
    # ai_user_item_interactions — RANGE-partitioned monthly on created_at
    # ====================================================================
    op.execute(
        """
        CREATE TABLE ai_user_item_interactions (
            id              uuid NOT NULL DEFAULT gen_uuid_v7(),
            user_id         uuid NOT NULL,
            item_kind       text NOT NULL,
            item_id         uuid NOT NULL,
            interaction     text NOT NULL
                CHECK (interaction IN ('viewed','dwelled','liked','saved','shared','dismissed')),
            weight          numeric(6,3) NOT NULL DEFAULT 1,
            created_at      timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (id, created_at),
            CHECK (weight >= 0)
        ) PARTITION BY RANGE (created_at);

        CREATE INDEX idx_ai_interactions_user_recent
            ON ai_user_item_interactions(user_id, created_at DESC);
        CREATE INDEX idx_ai_interactions_item
            ON ai_user_item_interactions(item_kind, item_id, created_at DESC);
        CREATE INDEX idx_ai_interactions_kind_recent
            ON ai_user_item_interactions(interaction, created_at DESC);

        COMMENT ON TABLE ai_user_item_interactions IS
            'Implicit + explicit user/item signals feeding the recommender '
            '(Agent 3 §3.27). Range-partitioned monthly so cold months can be archived.';
        """
    )

    for year, month in _months_around(-2, 2):
        start, end = _month_bounds(year, month)
        part_name = f"ai_user_item_interactions_y{year}m{month:02d}"
        op.execute(
            f"""
            CREATE TABLE {part_name}
                PARTITION OF ai_user_item_interactions
                FOR VALUES FROM ('{start}') TO ('{end}');
            """
        )

    # ====================================================================
    # ai_feedback — thumbs up/down on generations (fine-tune dataset seed)
    # ====================================================================
    # generation_id is a UUID without FK because ai_generations is RANGE-
    # partitioned (composite PK (id, created_at)); resolution is app-side.
    op.execute(
        """
        CREATE TABLE ai_feedback (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            generation_id   uuid NOT NULL,
            user_id         uuid NOT NULL,
            rating          smallint NOT NULL,
            comment         text,
            created_at      timestamptz NOT NULL DEFAULT now(),
            CHECK (rating BETWEEN 1 AND 5)
        );

        CREATE INDEX idx_ai_feedback_generation
            ON ai_feedback(generation_id);
        CREATE INDEX idx_ai_feedback_user_recent
            ON ai_feedback(user_id, created_at DESC);
        CREATE INDEX idx_ai_feedback_low_ratings
            ON ai_feedback(created_at DESC) WHERE rating <= 2;

        COMMENT ON TABLE ai_feedback IS
            'Human feedback on AI outputs (Agent 3 §3.31). Becomes labelled '
            'training data for FAZA 7 fine-tuning. No FK to ai_generations '
            'because ai_generations is range-partitioned.';
        """
    )

    # ====================================================================
    # ai_drift_metrics — periodic captures
    # ====================================================================
    op.execute(
        """
        CREATE TABLE ai_drift_metrics (
            id                  uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            model_version_id    uuid NOT NULL REFERENCES ai_model_versions(id) ON DELETE CASCADE,
            captured_at         timestamptz NOT NULL DEFAULT now(),
            metric_name         text NOT NULL,
            metric_value        numeric NOT NULL,
            sample_size         int NOT NULL,
            metadata            jsonb NOT NULL DEFAULT '{}'::jsonb,
            CHECK (sample_size >= 0),
            CHECK (metric_name ~ '^[a-z][a-z0-9_]*$')
        );

        CREATE INDEX idx_ai_drift_metrics_model_recent
            ON ai_drift_metrics(model_version_id, captured_at DESC);
        CREATE INDEX idx_ai_drift_metrics_name_recent
            ON ai_drift_metrics(metric_name, captured_at DESC);

        COMMENT ON TABLE ai_drift_metrics IS
            'Periodic captures of model drift signals (Agent 3 §3.25). Filled by '
            'a scheduled job comparing recent generations to baseline.';
        """
    )

    # ====================================================================
    # ai_safety_incidents
    # ====================================================================
    # related_generation_id is a plain UUID (no FK) — ai_generations is
    # range-partitioned so direct FKs are deferred.
    op.execute(
        """
        CREATE TABLE ai_safety_incidents (
            id                      uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            kind                    text NOT NULL,
            severity                text NOT NULL
                CHECK (severity IN ('low','medium','high','critical')),
            description             text NOT NULL,
            related_generation_id   uuid,
            assigned_to             uuid,
            status                  text NOT NULL DEFAULT 'open'
                CHECK (status IN ('open','investigating','resolved','dismissed')),
            created_at              timestamptz NOT NULL DEFAULT now(),
            resolved_at             timestamptz,
            CHECK (resolved_at IS NULL OR resolved_at >= created_at)
        );

        CREATE INDEX idx_ai_safety_incidents_status
            ON ai_safety_incidents(status, created_at DESC)
            WHERE status IN ('open','investigating');
        CREATE INDEX idx_ai_safety_incidents_severity
            ON ai_safety_incidents(severity, created_at DESC);
        CREATE INDEX idx_ai_safety_incidents_assignee
            ON ai_safety_incidents(assigned_to, status)
            WHERE assigned_to IS NOT NULL;

        COMMENT ON TABLE ai_safety_incidents IS
            'Tracking record for confirmed safety events (Agent 3 §3.21). '
            'related_generation_id is FK-free because ai_generations is partitioned.';
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ai_safety_incidents CASCADE;")
    op.execute("DROP TABLE IF EXISTS ai_drift_metrics CASCADE;")
    op.execute("DROP TABLE IF EXISTS ai_feedback CASCADE;")
    op.execute("DROP TABLE IF EXISTS ai_user_item_interactions CASCADE;")
    op.execute("DROP TABLE IF EXISTS ai_recommendation_state CASCADE;")
    op.execute("DROP TABLE IF EXISTS ai_prompt_injection_log CASCADE;")
    op.execute("DROP TABLE IF EXISTS ai_translation_jobs CASCADE;")
    op.execute("DROP TABLE IF EXISTS ai_translation_memory CASCADE;")
