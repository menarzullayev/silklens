"""ai_generations / ai_inference_jobs / ai_cache / ai_token_usage / ai_cost_ledger / ai_moderation_results

Per Agent 3 §§3.14-3.20 + MASTER §6 (vector search) + §15 (caching):

Runtime + observability tables. Generation log, async-job mirror, deterministic
prompt cache, per-day token usage, cost ledger (consumed by Agent 6 billing),
and moderation verdicts. The high-cardinality tables (``ai_generations``,
``ai_token_usage``, ``ai_cost_ledger``) are range-partitioned monthly so old
months can be detached and archived cheaply.

Partitioning rules (per HANDOFF §4):
- partition key MUST be part of the PK
- provision ±2 months around today so a fresh cluster can serve immediately
  without depending on pg_partman.

Tables (6): ai_generations (RANGE created_at), ai_inference_jobs,
ai_cache, ai_token_usage (RANGE day), ai_cost_ledger (RANGE created_at),
ai_moderation_results.

Revision ID: 0032_ai_runtime
Revises: 0031_embeddings
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from alembic import op

revision: str = "0032_ai_runtime"
down_revision: str | Sequence[str] | None = "0031_embeddings"
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
    """Yield (year, month) tuples for offsets relative to current month."""
    today = date.today().replace(day=1)
    out: list[tuple[int, int]] = []
    for offset in range(offset_start, offset_end + 1):
        year = today.year + ((today.month - 1 + offset) // 12)
        month = ((today.month - 1 + offset) % 12) + 1
        out.append((year, month))
    return out


def upgrade() -> None:
    # ====================================================================
    # ai_generations — range-partitioned monthly on created_at
    # ====================================================================
    op.execute(
        """
        CREATE TABLE ai_generations (
            id                  uuid NOT NULL DEFAULT gen_uuid_v7(),
            tenant_id           uuid NOT NULL,
            user_id             uuid,
            model_version_id    uuid NOT NULL,
            prompt_template_id  uuid,
            task_type           text NOT NULL
                CHECK (task_type IN ('vision','text','tts','translation','embedding','asr','moderation')),
            input_hash          bytea NOT NULL,
            input_summary       text,
            output_text         text,
            output_jsonb        jsonb,
            input_tokens        int,
            output_tokens       int,
            latency_ms          int,
            cost_estimate       numeric(12,8),
            status              text NOT NULL DEFAULT 'ok'
                CHECK (status IN ('ok','error','timeout','safety_blocked')),
            trace_id            text,
            created_at          timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (id, created_at),
            CHECK (octet_length(input_hash) = 32),
            CHECK (input_tokens IS NULL OR input_tokens >= 0),
            CHECK (output_tokens IS NULL OR output_tokens >= 0),
            CHECK (latency_ms IS NULL OR latency_ms >= 0)
        ) PARTITION BY RANGE (created_at);

        CREATE INDEX idx_ai_generations_tenant_recent
            ON ai_generations(tenant_id, created_at DESC);
        CREATE INDEX idx_ai_generations_model_recent
            ON ai_generations(model_version_id, created_at DESC);
        CREATE INDEX idx_ai_generations_user_recent
            ON ai_generations(user_id, created_at DESC)
            WHERE user_id IS NOT NULL;
        CREATE INDEX idx_ai_generations_trace
            ON ai_generations(trace_id) WHERE trace_id IS NOT NULL;
        CREATE INDEX idx_ai_generations_task
            ON ai_generations(task_type, created_at DESC);

        COMMENT ON TABLE ai_generations IS
            'Immutable log of every AI call. Range-partitioned by month so old '
            'months can be detached to cold storage (Agent 3 §3.15 append-only).';
        """
    )

    # Provision ±2 months
    for year, month in _months_around(-2, 2):
        start, end = _month_bounds(year, month)
        part_name = f"ai_generations_y{year}m{month:02d}"
        op.execute(
            f"""
            CREATE TABLE {part_name}
                PARTITION OF ai_generations
                FOR VALUES FROM ('{start}') TO ('{end}');
            """
        )

    # ====================================================================
    # ai_inference_jobs — Celery mirror
    # ====================================================================
    op.execute(
        """
        CREATE TABLE ai_inference_jobs (
            id                  uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            kind                text NOT NULL
                CHECK (kind IN ('recognition','tts','translation','embedding','moderation')),
            payload             jsonb NOT NULL DEFAULT '{}'::jsonb,
            status              text NOT NULL DEFAULT 'queued'
                CHECK (status IN ('queued','running','done','failed','cancelled')),
            attempts            int NOT NULL DEFAULT 0,
            worker_id           text,
            requested_at        timestamptz NOT NULL DEFAULT now(),
            started_at          timestamptz,
            finished_at         timestamptz,
            result_ref          text,
            error               text,
            CHECK (attempts >= 0),
            CHECK (started_at IS NULL OR started_at >= requested_at),
            CHECK (finished_at IS NULL OR started_at IS NULL OR finished_at >= started_at)
        );

        CREATE INDEX idx_ai_inference_jobs_active
            ON ai_inference_jobs(status, requested_at)
            WHERE status IN ('queued','running');
        CREATE INDEX idx_ai_inference_jobs_kind_recent
            ON ai_inference_jobs(kind, requested_at DESC);

        COMMENT ON TABLE ai_inference_jobs IS
            'Async-queue mirror of Celery tasks (Agent 3 §3.14). result_ref points '
            'into ai_generations or media_assets depending on job kind.';
        """
    )

    # ====================================================================
    # ai_cache — deterministic prompt dedup
    # ====================================================================
    op.execute(
        """
        CREATE TABLE ai_cache (
            input_hash          bytea PRIMARY KEY,
            model_version_id    uuid NOT NULL REFERENCES ai_model_versions(id) ON DELETE CASCADE,
            output_jsonb        jsonb NOT NULL,
            hit_count           int NOT NULL DEFAULT 1,
            last_hit_at         timestamptz,
            created_at          timestamptz NOT NULL DEFAULT now(),
            expires_at          timestamptz,
            CHECK (octet_length(input_hash) = 32),
            CHECK (hit_count >= 0),
            CHECK (expires_at IS NULL OR expires_at > created_at)
        );

        CREATE INDEX idx_ai_cache_expires
            ON ai_cache(expires_at) WHERE expires_at IS NOT NULL;
        CREATE INDEX idx_ai_cache_model
            ON ai_cache(model_version_id);
        CREATE INDEX idx_ai_cache_recent
            ON ai_cache(last_hit_at DESC NULLS LAST);

        COMMENT ON TABLE ai_cache IS
            'Deduplication of deterministic prompts (Agent 3 §3.16). Redis mirrors '
            'hot keys; this table is source of truth and survives Redis flush.';
        """
    )

    # ====================================================================
    # ai_token_usage — range-partitioned by month on ``day``
    # ====================================================================
    op.execute(
        """
        CREATE TABLE ai_token_usage (
            user_id             uuid NOT NULL,
            model_id            uuid NOT NULL,
            day                 date NOT NULL,
            input_tokens        bigint NOT NULL DEFAULT 0,
            output_tokens       bigint NOT NULL DEFAULT 0,
            cost                numeric(12,8) NOT NULL DEFAULT 0,
            request_count       int NOT NULL DEFAULT 0,
            updated_at          timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (user_id, model_id, day),
            CHECK (input_tokens >= 0),
            CHECK (output_tokens >= 0),
            CHECK (request_count >= 0),
            CHECK (cost >= 0)
        ) PARTITION BY RANGE (day);

        CREATE INDEX idx_ai_token_usage_model_day
            ON ai_token_usage(model_id, day);
        CREATE INDEX idx_ai_token_usage_user_day
            ON ai_token_usage(user_id, day DESC);

        COMMENT ON TABLE ai_token_usage IS
            'Per (user, model, day) usage roll-up. Range-partitioned monthly. '
            'Feeds ai_cost_ledger and Agent 6 quota enforcement.';
        """
    )

    for year, month in _months_around(-2, 2):
        start, end = _month_bounds(year, month)
        part_name = f"ai_token_usage_y{year}m{month:02d}"
        op.execute(
            f"""
            CREATE TABLE {part_name}
                PARTITION OF ai_token_usage
                FOR VALUES FROM ('{start}') TO ('{end}');
            """
        )

    # ====================================================================
    # ai_cost_ledger — append-only billing handoff to Agent 6
    # ====================================================================
    op.execute(
        """
        CREATE TABLE ai_cost_ledger (
            id                      uuid NOT NULL DEFAULT gen_uuid_v7(),
            tenant_id               uuid NOT NULL,
            user_id                 uuid,
            model_id                uuid NOT NULL REFERENCES ai_models(id) ON DELETE RESTRICT,
            kind                    text NOT NULL,
            tokens_in               int NOT NULL DEFAULT 0,
            tokens_out              int NOT NULL DEFAULT 0,
            cost                    numeric(12,8) NOT NULL DEFAULT 0,
            billable_to_tenant_id   uuid,
            created_at              timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (id, created_at),
            CHECK (tokens_in >= 0),
            CHECK (tokens_out >= 0),
            CHECK (cost >= 0)
        ) PARTITION BY RANGE (created_at);

        CREATE INDEX idx_ai_cost_ledger_tenant_recent
            ON ai_cost_ledger(tenant_id, created_at DESC);
        CREATE INDEX idx_ai_cost_ledger_billable
            ON ai_cost_ledger(billable_to_tenant_id, created_at DESC)
            WHERE billable_to_tenant_id IS NOT NULL;
        CREATE INDEX idx_ai_cost_ledger_model
            ON ai_cost_ledger(model_id, created_at DESC);
        CREATE INDEX idx_ai_cost_ledger_user
            ON ai_cost_ledger(user_id, created_at DESC)
            WHERE user_id IS NOT NULL;

        COMMENT ON TABLE ai_cost_ledger IS
            'Append-only billing source (Agent 3 §3.24, consumed by Agent 6). '
            'billable_to_tenant_id supports reseller markups: caller pays X, '
            'reseller is billed Y > X.';
        """
    )

    for year, month in _months_around(-2, 2):
        start, end = _month_bounds(year, month)
        part_name = f"ai_cost_ledger_y{year}m{month:02d}"
        op.execute(
            f"""
            CREATE TABLE {part_name}
                PARTITION OF ai_cost_ledger
                FOR VALUES FROM ('{start}') TO ('{end}');
            """
        )

    # ====================================================================
    # ai_moderation_results
    # ====================================================================
    op.execute(
        """
        CREATE TABLE ai_moderation_results (
            id                  uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            target_kind         text NOT NULL
                CHECK (target_kind IN (
                    'heritage_description','review','user_upload_image',
                    'user_upload_text','chat_input'
                )),
            target_id           uuid NOT NULL,
            model_version_id    uuid NOT NULL REFERENCES ai_model_versions(id) ON DELETE RESTRICT,
            classification      text NOT NULL
                CHECK (classification IN (
                    'safe','nsfw','violence','spam','hate',
                    'self_harm','prompt_injection','multi'
                )),
            score               numeric(4,3),
            labels              jsonb NOT NULL DEFAULT '{}'::jsonb,
            action_taken        text NOT NULL DEFAULT 'allowed'
                CHECK (action_taken IN ('allowed','queued_for_review','auto_rejected','quarantined')),
            created_at          timestamptz NOT NULL DEFAULT now(),
            CHECK (score IS NULL OR (score >= 0 AND score <= 1))
        );

        CREATE INDEX idx_ai_moderation_results_target
            ON ai_moderation_results(target_kind, target_id);
        CREATE INDEX idx_ai_moderation_results_class
            ON ai_moderation_results(classification, created_at DESC);
        CREATE INDEX idx_ai_moderation_results_review_queue
            ON ai_moderation_results(created_at)
            WHERE action_taken = 'queued_for_review';

        COMMENT ON TABLE ai_moderation_results IS
            'Per-artifact moderation verdict (Agent 3 §3.20). target_id is '
            'polymorphic — resolved via target_kind.';
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ai_moderation_results CASCADE;")
    op.execute("DROP TABLE IF EXISTS ai_cost_ledger CASCADE;")
    op.execute("DROP TABLE IF EXISTS ai_token_usage CASCADE;")
    op.execute("DROP TABLE IF EXISTS ai_cache CASCADE;")
    op.execute("DROP TABLE IF EXISTS ai_inference_jobs CASCADE;")
    op.execute("DROP TABLE IF EXISTS ai_generations CASCADE;")
