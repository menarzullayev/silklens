"""Fine-tuning dataset infrastructure — datasets, examples, jobs, evaluations.

FAZA 7 — Wave-8 Agent-6. Implements §13 of docs/architecture/03-ai-vector-infra.md.

Tables (4 new + 1 ALTER):
    finetuning_datasets       — dataset catalogue per tenant, purpose-tagged
    finetuning_examples       — individual training examples awaiting curation
    finetuning_jobs           — fine-tuning job submissions to providers
    finetuning_evaluations    — per-job metric snapshots (BLEU, ROUGE, human pref…)
    ai_feedback               — ALTER to add included_in_dataset_id FK column

Trigger:
    tg_ai_feedback_queue — auto-enqueues high-rated feedback (rating ≥ 4) into
    the heritage_qa_uz_en dataset as prompt_response examples.

Seeds 3 starter datasets:
    heritage_qa_uz_en           (heritage_qa / llm)
    cultural_classification_v1  (cultural_classification / vision)
    audio_guide_style_silk_road (audio_guide_style / tts)

Revision ID: 0090_finetuning_dataset
Revises: 0087_virtual_tours
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0090_finetuning_dataset"
down_revision: str | Sequence[str] | None = "0087_virtual_tours"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ====================================================================
    # finetuning_datasets — catalogue of labelled datasets per purpose
    # ====================================================================
    op.execute(
        """
        CREATE TABLE finetuning_datasets (
            id                  uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            tenant_id           uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            slug                text NOT NULL UNIQUE,
            name                jsonb NOT NULL DEFAULT '{}'::jsonb,
            description_md      text,
            purpose             text NOT NULL
                CHECK (purpose IN (
                    'heritage_qa',
                    'cultural_classification',
                    'translation_quality',
                    'audio_guide_style',
                    'moderation'
                )),
            target_model_kind   text NOT NULL
                CHECK (target_model_kind IN ('llm','vision','tts','translation','embedding')),
            status              text NOT NULL DEFAULT 'collecting'
                CHECK (status IN ('collecting','curating','ready','training','completed','archived')),
            example_count       int NOT NULL DEFAULT 0,
            min_quality_score   numeric(3,2) NOT NULL DEFAULT 0.80,
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now(),
            CHECK (min_quality_score BETWEEN 0 AND 1)
        );

        CREATE INDEX idx_finetuning_datasets_tenant
            ON finetuning_datasets(tenant_id, status);
        CREATE INDEX idx_finetuning_datasets_purpose
            ON finetuning_datasets(purpose, target_model_kind);

        CREATE TRIGGER tg_finetuning_datasets_updated_at
            BEFORE UPDATE ON finetuning_datasets
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE finetuning_datasets IS
            'Fine-tuning dataset catalogue (FAZA 7 §13). Each dataset collects '
            'approved examples for a specific task and model kind.';
        """
    )

    # ====================================================================
    # finetuning_examples — individual labelled training examples
    # ====================================================================
    op.execute(
        """
        CREATE TABLE finetuning_examples (
            id                  uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            dataset_id          uuid NOT NULL REFERENCES finetuning_datasets(id) ON DELETE CASCADE,
            kind                text NOT NULL
                CHECK (kind IN ('prompt_response','classification','conversation','preference')),
            input_text          text NOT NULL,
            output_text         text NOT NULL,
            input_metadata      jsonb NOT NULL DEFAULT '{}'::jsonb,
            output_metadata     jsonb NOT NULL DEFAULT '{}'::jsonb,
            quality_score       numeric(3,2),
            source_kind         text NOT NULL
                CHECK (source_kind IN ('manual','ai_approved','user_feedback','expert_review')),
            source_id           uuid,
            language_tag        text NOT NULL DEFAULT 'uz',
            is_approved         bool NOT NULL DEFAULT false,
            approved_by         uuid,
            approved_at         timestamptz,
            created_at          timestamptz NOT NULL DEFAULT now(),
            CHECK (quality_score IS NULL OR quality_score BETWEEN 0 AND 1),
            CHECK (approved_at IS NULL OR approved_by IS NOT NULL)
        );

        -- Primary access pattern: per-dataset approved examples sorted by quality
        CREATE INDEX idx_finetuning_examples_dataset_approved_quality
            ON finetuning_examples(dataset_id, is_approved, quality_score DESC);
        CREATE INDEX idx_finetuning_examples_pending
            ON finetuning_examples(dataset_id, created_at DESC)
            WHERE is_approved = false;
        CREATE INDEX idx_finetuning_examples_source
            ON finetuning_examples(source_kind, source_id)
            WHERE source_id IS NOT NULL;

        COMMENT ON TABLE finetuning_examples IS
            'Individual prompt/response or classification examples awaiting curation '
            '(FAZA 7 §13). Examples are auto-enqueued from high-rated ai_feedback via trigger.';
        """
    )

    # ====================================================================
    # finetuning_jobs — fine-tuning job submissions
    # ====================================================================
    op.execute(
        """
        CREATE TABLE finetuning_jobs (
            id                  uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            dataset_id          uuid NOT NULL REFERENCES finetuning_datasets(id) ON DELETE RESTRICT,
            provider            text NOT NULL
                CHECK (provider IN ('anthropic','openai','huggingface_local','mistral')),
            base_model_slug     text NOT NULL,
            job_kind            text NOT NULL
                CHECK (job_kind IN ('supervised','rlhf','dpo','lora_adapter')),
            status              text NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending','running','completed','failed','cancelled')),
            hyperparams         jsonb NOT NULL DEFAULT '{}'::jsonb,
            provider_job_id     text,
            started_at          timestamptz,
            finished_at         timestamptz,
            output_model_slug   text,
            eval_metrics        jsonb NOT NULL DEFAULT '{}'::jsonb,
            cost_usd            numeric(12,4),
            created_at          timestamptz NOT NULL DEFAULT now(),
            CHECK (finished_at IS NULL OR started_at IS NOT NULL),
            CHECK (cost_usd IS NULL OR cost_usd >= 0)
        );

        CREATE INDEX idx_finetuning_jobs_dataset
            ON finetuning_jobs(dataset_id, status);
        CREATE INDEX idx_finetuning_jobs_status_recent
            ON finetuning_jobs(status, created_at DESC)
            WHERE status IN ('pending','running');

        COMMENT ON TABLE finetuning_jobs IS
            'Fine-tuning job submissions (FAZA 7 §13). Actual provider API calls '
            'are deferred; this table tracks scaffolded + launched jobs.';
        """
    )

    # ====================================================================
    # finetuning_evaluations — per-job metric snapshots
    # ====================================================================
    op.execute(
        """
        CREATE TABLE finetuning_evaluations (
            id                  uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            job_id              uuid NOT NULL REFERENCES finetuning_jobs(id) ON DELETE CASCADE,
            eval_kind           text NOT NULL
                CHECK (eval_kind IN (
                    'bleu','rouge','human_preference','task_accuracy','perplexity'
                )),
            score               numeric(6,4) NOT NULL,
            benchmark_name      text NOT NULL,
            eval_dataset_size   int NOT NULL,
            created_at          timestamptz NOT NULL DEFAULT now(),
            CHECK (eval_dataset_size > 0)
        );

        CREATE INDEX idx_finetuning_evaluations_job
            ON finetuning_evaluations(job_id, eval_kind);

        COMMENT ON TABLE finetuning_evaluations IS
            'Post-training evaluation snapshots per job (FAZA 7 §13). '
            'Supports multiple eval kinds per job run.';
        """
    )

    # ====================================================================
    # ALTER ai_feedback — add dataset linkage column
    # ====================================================================
    op.execute(
        """
        ALTER TABLE ai_feedback
            ADD COLUMN included_in_dataset_id uuid
                REFERENCES finetuning_datasets(id) ON DELETE SET NULL;

        CREATE INDEX idx_ai_feedback_dataset
            ON ai_feedback(included_in_dataset_id)
            WHERE included_in_dataset_id IS NOT NULL;

        COMMENT ON COLUMN ai_feedback.included_in_dataset_id IS
            'Set when this feedback row was promoted to a finetuning_dataset. '
            'NULL = not yet curated. ON DELETE SET NULL keeps feedback history.';
        """
    )

    # ====================================================================
    # Seed 3 starter datasets using the default tenant
    # ====================================================================
    op.execute(
        """
        INSERT INTO finetuning_datasets
            (tenant_id, slug, name, description_md, purpose, target_model_kind, status)
        SELECT
            t.id,
            v.slug,
            v.name::jsonb,
            v.description_md,
            v.purpose,
            v.target_model_kind,
            'collecting'
        FROM tenants t
        CROSS JOIN (
            VALUES
            (
                'heritage_qa_uz_en',
                '{"uz":"Meros QA","en":"Heritage Q&A"}',
                'Question-answer pairs about Central Asian heritage objects. '
                'Primary source: high-rated ai_feedback rows auto-enqueued by trigger.',
                'heritage_qa',
                'llm'
            ),
            (
                'cultural_classification_v1',
                '{"uz":"Madaniy tasniflash v1","en":"Cultural Classification v1"}',
                'Image + label pairs for heritage object kind classification. '
                'Source: expert-reviewed media assets with confirmed heritage_kind tags.',
                'cultural_classification',
                'vision'
            ),
            (
                'audio_guide_style_silk_road',
                '{"uz":"Audio gid uslubi — Ipak yo''li","en":"Audio Guide Style — Silk Road"}',
                'Script/audio pairs in the preferred SilkLens narration style. '
                'Used to fine-tune TTS voice tone and pacing for heritage audio guides.',
                'audio_guide_style',
                'tts'
            )
        ) AS v(slug, name, description_md, purpose, target_model_kind)
        WHERE t.slug = 'default'
        ON CONFLICT (slug) DO NOTHING;
        """
    )

    # ====================================================================
    # Trigger: auto-queue high-rated ai_feedback into heritage_qa_uz_en
    # ====================================================================
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app.tg_auto_queue_finetuning() RETURNS trigger AS $$
        BEGIN
          IF NEW.rating >= 4 THEN
            INSERT INTO finetuning_examples
                (dataset_id, kind, input_text, output_text, source_kind, source_id, quality_score)
            SELECT
                d.id,
                'prompt_response',
                COALESCE(
                    (SELECT input_summary FROM ai_generations
                     WHERE id = NEW.generation_id
                     LIMIT 1),
                    ''
                ),
                COALESCE(
                    (SELECT output_text FROM ai_generations
                     WHERE id = NEW.generation_id
                     LIMIT 1),
                    ''
                ),
                'user_feedback',
                NEW.id,
                NEW.rating::numeric / 5
            FROM finetuning_datasets d
            WHERE d.slug = 'heritage_qa_uz_en'
            ON CONFLICT DO NOTHING;
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER tg_ai_feedback_queue
            AFTER INSERT ON ai_feedback
            FOR EACH ROW EXECUTE FUNCTION app.tg_auto_queue_finetuning();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS tg_ai_feedback_queue ON ai_feedback;")
    op.execute("DROP FUNCTION IF EXISTS app.tg_auto_queue_finetuning();")
    op.execute("ALTER TABLE ai_feedback DROP COLUMN IF EXISTS included_in_dataset_id;")
    op.execute("DROP TABLE IF EXISTS finetuning_evaluations CASCADE;")
    op.execute("DROP TABLE IF EXISTS finetuning_jobs CASCADE;")
    op.execute("DROP TABLE IF EXISTS finetuning_examples CASCADE;")
    op.execute("DROP TABLE IF EXISTS finetuning_datasets CASCADE;")
