"""search index sync + background jobs + cron + analytics sink + observability

Per Agent 7 §2.6–§2.10 this migration lands:

  - Search: `search_index_mappings` (per-index Elasticsearch config),
    `search_indexing_jobs` (work queue for the ES sync worker),
    `search_query_log` (anonymised daily-partitioned query telemetry),
    `search_zero_results` (gap analysis aggregation).
  - Cron + jobs: `cron_schedules` and `cron_runs` mirror admin-managed
    periodic tasks; `background_jobs` + `job_retries` are the generic
    on-demand job mirror; `celery_tasks_mirror` is the durable mirror of
    Redis broker state per Agent 7 §11 so admins can inspect in-flight
    Celery work without touching Redis.
  - Analytics sink (Postgres → ClickHouse): `analytics_events_raw` is the
    short-TTL sink (daily RANGE partitions, 7-day retention), and
    `analytics_sessions` carries computed session boundaries.
  - Observability: `incidents`, `release_versions`,
    `feature_flag_evaluations`.

Range-partitioned tables include their partition key in the PRIMARY KEY
per Postgres rules.

Revision ID: 0061_search_jobs
Revises: 0060_notifications
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta

from alembic import op

revision: str = "0061_search_jobs"
down_revision: str | Sequence[str] | None = "0060_notifications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- search_index_mappings (admin config per ES index) ----------------
    op.execute(
        """
        CREATE TABLE search_index_mappings (
            slug                text PRIMARY KEY,
            kind                text NOT NULL
                CHECK (kind IN ('heritage','users','reviews','listings')),
            language_tier       text NOT NULL
                CHECK (language_tier IN ('tier1_dedicated','tier2_icu')),
            analyzer_config     jsonb NOT NULL DEFAULT '{}'::jsonb,
            last_rebuilt_at     timestamptz,
            current_doc_count   bigint NOT NULL DEFAULT 0 CHECK (current_doc_count >= 0),
            target_doc_count    bigint NOT NULL DEFAULT 0 CHECK (target_doc_count >= 0),
            is_active           boolean NOT NULL DEFAULT true,
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now(),
            CHECK (slug ~ '^[a-z][a-z0-9_-]*$')
        );

        CREATE INDEX idx_search_index_mappings_kind
            ON search_index_mappings(kind, language_tier) WHERE is_active;

        CREATE TRIGGER tg_search_index_mappings_updated_at
            BEFORE UPDATE ON search_index_mappings
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON COLUMN search_index_mappings.language_tier IS
            'tier1_dedicated = analyzer per language (uz,ru,en,zh,…); '
            'tier2_icu = shared ICU analyzer for low-traffic languages.';
        """
    )

    # --- search_indexing_jobs (ES sync work queue) ------------------------
    op.execute(
        """
        CREATE TABLE search_indexing_jobs (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            target_kind     text NOT NULL,
            target_id       uuid NOT NULL,
            action          text NOT NULL CHECK (action IN ('upsert','delete')),
            attempts        int  NOT NULL DEFAULT 0 CHECK (attempts >= 0),
            status          text NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending','running','done','failed')),
            requested_at    timestamptz NOT NULL DEFAULT now(),
            started_at      timestamptz,
            finished_at     timestamptz,
            error           text,
            CHECK (finished_at IS NULL OR started_at IS NULL OR finished_at >= started_at)
        );

        CREATE INDEX idx_search_indexing_jobs_pending
            ON search_indexing_jobs (status, requested_at)
            WHERE status IN ('pending','running');
        CREATE INDEX idx_search_indexing_jobs_target
            ON search_indexing_jobs (target_kind, target_id);

        COMMENT ON TABLE search_indexing_jobs IS
            'ES sync work queue. Worker claims FOR UPDATE SKIP LOCKED and pushes '
            'to Elasticsearch bulk API. action=delete cascades a tombstone.';
        """
    )

    # --- search_query_log (RANGE-partitioned DAILY, append-only) ---------
    # Anonymised: session_id is opaque, user_id is intentionally absent.
    op.execute(
        """
        CREATE TABLE search_query_log (
            id                  uuid NOT NULL DEFAULT gen_uuid_v7(),
            query_text          text NOT NULL,
            language_tag        text,
            result_count        int  NOT NULL CHECK (result_count >= 0),
            clicked_result_id   uuid,
            session_id          uuid,
            occurred_at         timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (id, occurred_at),
            CHECK (length(query_text) BETWEEN 1 AND 1024)
        ) PARTITION BY RANGE (occurred_at);

        CREATE INDEX idx_search_query_log_lang
            ON search_query_log (language_tag, occurred_at DESC)
            WHERE language_tag IS NOT NULL;
        CREATE INDEX idx_search_query_log_zero
            ON search_query_log (occurred_at DESC)
            WHERE result_count = 0;
        CREATE INDEX idx_search_query_log_trgm
            ON search_query_log USING GIN (query_text gin_trgm_ops);

        COMMENT ON TABLE search_query_log IS
            'Anonymised query telemetry per Agent 7 §2.6. Daily partitions; '
            'aggregated into search_zero_results nightly.';
        """
    )

    today = date.today()
    for offset in range(-7, 8):
        d = today + timedelta(days=offset)
        d_next = d + timedelta(days=1)
        suffix = d.strftime("%Y%m%d")
        op.execute(
            f"""
            CREATE TABLE search_query_log_{suffix}
                PARTITION OF search_query_log
                FOR VALUES FROM ('{d.isoformat()}') TO ('{d_next.isoformat()}');
            """
        )

    # --- search_zero_results (gap analysis aggregate) ---------------------
    op.execute(
        """
        CREATE TABLE search_zero_results (
            query_normalized    text NOT NULL,
            language_tag        text NOT NULL DEFAULT '',
            occurrences         int  NOT NULL DEFAULT 1 CHECK (occurrences > 0),
            last_seen_at        timestamptz NOT NULL DEFAULT now(),
            sample_user_id      uuid,
            updated_at          timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (query_normalized, language_tag),
            CHECK (length(query_normalized) BETWEEN 1 AND 512)
        );

        CREATE INDEX idx_search_zero_results_recent
            ON search_zero_results (last_seen_at DESC);
        CREATE INDEX idx_search_zero_results_hot
            ON search_zero_results (occurrences DESC, last_seen_at DESC);

        CREATE TRIGGER tg_search_zero_results_updated_at
            BEFORE UPDATE ON search_zero_results
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- cron_schedules (admin-managed periodic tasks) --------------------
    op.execute(
        """
        CREATE TABLE cron_schedules (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            slug            text NOT NULL UNIQUE,
            name            jsonb NOT NULL DEFAULT '{}'::jsonb,
            expression      text NOT NULL,
            command         text NOT NULL,
            task_kind       text NOT NULL,
            is_active       boolean NOT NULL DEFAULT true,
            last_run_at     timestamptz,
            last_status     text,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            CHECK (slug ~ '^[a-z][a-z0-9_-]*$'),
            CHECK (length(expression) BETWEEN 1 AND 128),
            CHECK (length(command) BETWEEN 1 AND 512)
        );

        CREATE INDEX idx_cron_schedules_active
            ON cron_schedules(last_run_at) WHERE is_active;

        CREATE TRIGGER tg_cron_schedules_updated_at
            BEFORE UPDATE ON cron_schedules
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- cron_runs (execution history) ------------------------------------
    op.execute(
        """
        CREATE TABLE cron_runs (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            schedule_id     uuid NOT NULL REFERENCES cron_schedules(id) ON DELETE CASCADE,
            run_at          timestamptz NOT NULL DEFAULT now(),
            status          text NOT NULL
                CHECK (status IN ('started','done','failed','missed')),
            duration_ms     int CHECK (duration_ms IS NULL OR duration_ms >= 0),
            error           text,
            created_at      timestamptz NOT NULL DEFAULT now()
        );

        CREATE INDEX idx_cron_runs_schedule
            ON cron_runs (schedule_id, run_at DESC);
        CREATE INDEX idx_cron_runs_failed
            ON cron_runs (run_at DESC) WHERE status IN ('failed','missed');
        """
    )

    # --- background_jobs (generic admin-visible job mirror) ---------------
    op.execute(
        """
        CREATE TABLE background_jobs (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            kind            text NOT NULL,
            payload         jsonb NOT NULL DEFAULT '{}'::jsonb,
            status          text NOT NULL DEFAULT 'queued'
                CHECK (status IN ('queued','running','done','failed','cancelled')),
            attempts        int  NOT NULL DEFAULT 0 CHECK (attempts >= 0),
            requested_at    timestamptz NOT NULL DEFAULT now(),
            started_at      timestamptz,
            finished_at     timestamptz,
            worker_id       text,
            error           text,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            CHECK (finished_at IS NULL OR started_at IS NULL OR finished_at >= started_at)
        );

        CREATE INDEX idx_background_jobs_pending
            ON background_jobs (status, requested_at)
            WHERE status IN ('queued','running');
        CREATE INDEX idx_background_jobs_kind
            ON background_jobs (kind, status);

        CREATE TRIGGER tg_background_jobs_updated_at
            BEFORE UPDATE ON background_jobs
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- job_retries (append-only retry history) --------------------------
    op.execute(
        """
        CREATE TABLE job_retries (
            job_id          uuid NOT NULL REFERENCES background_jobs(id) ON DELETE CASCADE,
            attempt         smallint NOT NULL CHECK (attempt > 0),
            attempted_at    timestamptz NOT NULL DEFAULT now(),
            error           text,
            PRIMARY KEY (job_id, attempt)
        );

        CREATE INDEX idx_job_retries_recent
            ON job_retries (attempted_at DESC);
        """
    )

    # --- celery_tasks_mirror (durable mirror of Redis broker state) -------
    # id is the Celery task UUID-as-string (Celery doesn't always emit a
    # parseable UUID). We accept text so we never lose visibility.
    op.execute(
        """
        CREATE TABLE celery_tasks_mirror (
            id              text PRIMARY KEY,
            name            text NOT NULL,
            args            jsonb NOT NULL DEFAULT '[]'::jsonb,
            kwargs          jsonb NOT NULL DEFAULT '{}'::jsonb,
            status          text NOT NULL DEFAULT 'PENDING',
            started_at      timestamptz,
            finished_at     timestamptz,
            result          jsonb,
            error           text,
            worker_id       text,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            CHECK (finished_at IS NULL OR started_at IS NULL OR finished_at >= started_at)
        );

        CREATE INDEX idx_celery_tasks_mirror_status
            ON celery_tasks_mirror (status, created_at DESC);
        CREATE INDEX idx_celery_tasks_mirror_name
            ON celery_tasks_mirror (name, status);

        CREATE TRIGGER tg_celery_tasks_mirror_updated_at
            BEFORE UPDATE ON celery_tasks_mirror
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE celery_tasks_mirror IS
            'Durable mirror of in-flight Celery tasks per Agent 7 §11. Redis is '
            'the broker; this table is the admin-visible projection.';
        """
    )

    # --- analytics_events_raw (RANGE daily, short-TTL Postgres sink) ------
    op.execute(
        """
        CREATE TABLE analytics_events_raw (
            id              uuid NOT NULL DEFAULT gen_uuid_v7(),
            tenant_id       uuid NOT NULL,
            user_id         uuid,
            residency_region text,
            session_id      uuid,
            event_name      text NOT NULL,
            properties      jsonb NOT NULL DEFAULT '{}'::jsonb,
            page_url        text,
            user_agent      text,
            occurred_at     timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (id, occurred_at),
            CHECK (residency_region IS NULL OR residency_region IN ('uz','eu','us','global')),
            CHECK (length(event_name) BETWEEN 1 AND 128)
        ) PARTITION BY RANGE (occurred_at);

        CREATE INDEX idx_analytics_events_raw_tenant
            ON analytics_events_raw (tenant_id, occurred_at DESC);
        CREATE INDEX idx_analytics_events_raw_user
            ON analytics_events_raw (user_id, occurred_at DESC)
            WHERE user_id IS NOT NULL;
        CREATE INDEX idx_analytics_events_raw_name
            ON analytics_events_raw (event_name, occurred_at DESC);
        CREATE INDEX idx_analytics_events_raw_session
            ON analytics_events_raw (session_id, occurred_at)
            WHERE session_id IS NOT NULL;

        COMMENT ON TABLE analytics_events_raw IS
            'Short-TTL Postgres sink before ClickHouse ingest per Agent 7 §2.8. '
            'Daily partitions; old partitions detached + dropped after 7 days.';
        """
    )
    for offset in range(-7, 8):
        d = today + timedelta(days=offset)
        d_next = d + timedelta(days=1)
        suffix = d.strftime("%Y%m%d")
        op.execute(
            f"""
            CREATE TABLE analytics_events_raw_{suffix}
                PARTITION OF analytics_events_raw
                FOR VALUES FROM ('{d.isoformat()}') TO ('{d_next.isoformat()}');
            """
        )

    # --- analytics_sessions (computed session boundaries) -----------------
    op.execute(
        """
        CREATE TABLE analytics_sessions (
            session_id          uuid PRIMARY KEY,
            user_id             uuid,
            residency_region    text,
            started_at          timestamptz NOT NULL,
            ended_at            timestamptz,
            last_event_at       timestamptz NOT NULL,
            page_views          int NOT NULL DEFAULT 0 CHECK (page_views >= 0),
            duration_ms         int CHECK (duration_ms IS NULL OR duration_ms >= 0),
            country_code        char(2),
            referrer            text,
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now(),
            CHECK (residency_region IS NULL OR residency_region IN ('uz','eu','us','global')),
            CHECK (ended_at IS NULL OR ended_at >= started_at)
        );

        CREATE INDEX idx_analytics_sessions_user
            ON analytics_sessions (user_id, started_at DESC)
            WHERE user_id IS NOT NULL;
        CREATE INDEX idx_analytics_sessions_started
            ON analytics_sessions (started_at DESC);

        CREATE TRIGGER tg_analytics_sessions_updated_at
            BEFORE UPDATE ON analytics_sessions
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- incidents (production incidents log) -----------------------------
    op.execute(
        """
        CREATE TABLE incidents (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            slug            text NOT NULL UNIQUE,
            title           text NOT NULL,
            severity        text NOT NULL
                CHECK (severity IN ('info','low','medium','high','critical')),
            status          text NOT NULL DEFAULT 'open'
                CHECK (status IN ('open','mitigating','resolved','postmortem')),
            summary         text,
            started_at      timestamptz NOT NULL DEFAULT now(),
            mitigated_at    timestamptz,
            resolved_at     timestamptz,
            postmortem_url  text,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            CHECK (slug ~ '^[a-z0-9][a-z0-9_-]*$'),
            CHECK (length(title) BETWEEN 1 AND 256),
            CHECK (mitigated_at IS NULL OR mitigated_at >= started_at),
            CHECK (resolved_at  IS NULL OR resolved_at  >= started_at)
        );

        CREATE INDEX idx_incidents_open
            ON incidents (severity, started_at DESC)
            WHERE status IN ('open','mitigating');

        CREATE TRIGGER tg_incidents_updated_at
            BEFORE UPDATE ON incidents
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- release_versions (deploy registry) -------------------------------
    op.execute(
        """
        CREATE TABLE release_versions (
            service         text NOT NULL,
            version         text NOT NULL,
            commit_sha      text NOT NULL,
            released_at     timestamptz NOT NULL DEFAULT now(),
            released_by     uuid,
            notes           text,
            PRIMARY KEY (service, version),
            CHECK (length(service) BETWEEN 1 AND 64),
            CHECK (length(version) BETWEEN 1 AND 64),
            CHECK (commit_sha ~ '^[0-9a-f]{7,40}$')
        );

        CREATE INDEX idx_release_versions_service_released
            ON release_versions (service, released_at DESC);
        """
    )

    # --- feature_flag_evaluations (RANGE-partitioned DAILY, sampled audit)
    op.execute(
        """
        CREATE TABLE feature_flag_evaluations (
            id                  uuid NOT NULL DEFAULT gen_uuid_v7(),
            user_id             uuid,
            residency_region    text,
            flag_key            text NOT NULL,
            evaluated_to        text NOT NULL,
            decision_reason     text,
            evaluated_at        timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (id, evaluated_at),
            CHECK (residency_region IS NULL OR residency_region IN ('uz','eu','us','global')),
            CHECK (length(flag_key) BETWEEN 1 AND 128)
        ) PARTITION BY RANGE (evaluated_at);

        CREATE INDEX idx_feature_flag_eval_flag
            ON feature_flag_evaluations (flag_key, evaluated_at DESC);
        CREATE INDEX idx_feature_flag_eval_user
            ON feature_flag_evaluations (user_id, evaluated_at DESC)
            WHERE user_id IS NOT NULL;

        COMMENT ON TABLE feature_flag_evaluations IS
            'Sampled audit per Agent 7 §2.10. Daily partitions, sampling ratio '
            'is set per-flag in feature_flags.config.';
        """
    )
    for offset in range(-3, 4):
        d = today + timedelta(days=offset)
        d_next = d + timedelta(days=1)
        suffix = d.strftime("%Y%m%d")
        op.execute(
            f"""
            CREATE TABLE feature_flag_evaluations_{suffix}
                PARTITION OF feature_flag_evaluations
                FOR VALUES FROM ('{d.isoformat()}') TO ('{d_next.isoformat()}');
            """
        )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS feature_flag_evaluations CASCADE;")
    op.execute("DROP TABLE IF EXISTS release_versions CASCADE;")
    op.execute("DROP TABLE IF EXISTS incidents CASCADE;")
    op.execute("DROP TABLE IF EXISTS analytics_sessions CASCADE;")
    op.execute("DROP TABLE IF EXISTS analytics_events_raw CASCADE;")
    op.execute("DROP TABLE IF EXISTS celery_tasks_mirror CASCADE;")
    op.execute("DROP TABLE IF EXISTS job_retries CASCADE;")
    op.execute("DROP TABLE IF EXISTS background_jobs CASCADE;")
    op.execute("DROP TABLE IF EXISTS cron_runs CASCADE;")
    op.execute("DROP TABLE IF EXISTS cron_schedules CASCADE;")
    op.execute("DROP TABLE IF EXISTS search_zero_results CASCADE;")
    op.execute("DROP TABLE IF EXISTS search_query_log CASCADE;")
    op.execute("DROP TABLE IF EXISTS search_indexing_jobs CASCADE;")
    op.execute("DROP TABLE IF EXISTS search_index_mappings CASCADE;")
