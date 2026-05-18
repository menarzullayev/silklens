"""ai_providers / ai_models / ai_model_versions / ai_fallback_chains / prompt_templates

Per Agent 3 (03-ai-vector-infra.md §§3.1-3.10) + MASTER §6:

The AI substrate is provider-abstracted. Every concrete capability (vision,
text, tts, translation, embedding) is resolved at call time through a
``(provider, model, model_version)`` triple. Admins can switch the active
model with one click; every historical generation row carries the resolved
model_version so artifacts remain reproducible after a swap.

This migration lands the *admin-managed registry* — no vectors, no runtime
logs (those land in 0031/0032). It also seeds the canonical set of providers
and models referenced across docs/architecture and Project-Decisions §§5, 6, 42.

Tables (7):
    ai_providers, ai_models, ai_model_versions,
    ai_fallback_chains, ai_fallback_chain_steps,
    prompt_templates, prompt_template_versions.

Revision ID: 0030_ai_registry
Revises: 0023_offline_bundles
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0030_ai_registry"
down_revision: str | Sequence[str] | None = "0023_offline_bundles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- ai_providers ------------------------------------------------------
    op.execute(
        """
        CREATE TABLE ai_providers (
            id                      uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            slug                    text NOT NULL UNIQUE,
            name                    jsonb NOT NULL DEFAULT '{}'::jsonb,
            kind                    text NOT NULL
                CHECK (kind IN ('local_gpu','cloud_api')),
            base_url                text,
            supports_streaming      boolean NOT NULL DEFAULT false,
            requires_credit_card    boolean NOT NULL DEFAULT false,
            status                  text NOT NULL DEFAULT 'active'
                CHECK (status IN ('active','disabled','deprecated')),
            metadata                jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at              timestamptz NOT NULL DEFAULT now(),
            updated_at              timestamptz NOT NULL DEFAULT now(),
            CHECK (slug ~ '^[a-z0-9][a-z0-9_-]*$')
        );

        CREATE INDEX idx_ai_providers_kind
            ON ai_providers(kind) WHERE status = 'active';
        CREATE INDEX idx_ai_providers_status
            ON ai_providers(status);

        CREATE TRIGGER tg_ai_providers_updated_at
            BEFORE UPDATE ON ai_providers
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE ai_providers IS
            'Admin-managed catalog of AI providers (Agent 3 §3.1). '
            'Adding a new model vendor is a row insert, not a deploy.';
        """
    )

    # --- ai_models ---------------------------------------------------------
    op.execute(
        """
        CREATE TABLE ai_models (
            id                          uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            slug                        text NOT NULL UNIQUE,
            provider_id                 uuid NOT NULL REFERENCES ai_providers(id) ON DELETE RESTRICT,
            name                        jsonb NOT NULL DEFAULT '{}'::jsonb,
            task_type                   text NOT NULL
                CHECK (task_type IN ('vision','text','tts','translation','embedding','asr','moderation')),
            modality                    text[] NOT NULL DEFAULT ARRAY[]::text[],
            context_window              int,
            max_output_tokens           int,
            supports_tools              boolean NOT NULL DEFAULT false,
            supports_streaming          boolean NOT NULL DEFAULT false,
            cost_per_1k_input_tokens    numeric(10,6),
            cost_per_1k_output_tokens   numeric(10,6),
            is_enabled                  boolean NOT NULL DEFAULT true,
            sort_order                  int NOT NULL DEFAULT 100,
            metadata                    jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at                  timestamptz NOT NULL DEFAULT now(),
            updated_at                  timestamptz NOT NULL DEFAULT now(),
            CHECK (slug ~ '^[a-z0-9][a-z0-9._-]*$'),
            CHECK (context_window IS NULL OR context_window > 0),
            CHECK (max_output_tokens IS NULL OR max_output_tokens > 0)
        );

        CREATE INDEX idx_ai_models_provider
            ON ai_models(provider_id) WHERE is_enabled;
        CREATE INDEX idx_ai_models_task
            ON ai_models(task_type, sort_order) WHERE is_enabled;

        CREATE TRIGGER tg_ai_models_updated_at
            BEFORE UPDATE ON ai_models
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE ai_models IS
            'Capability-scoped model catalog (Agent 3 §3.2). One row per logical model; '
            'concrete weight versions live in ai_model_versions.';
        """
    )

    # --- ai_model_versions -------------------------------------------------
    # Embedding-family rows set ``dimensions`` so embedding tables can sanity-
    # check vector width; LLM rows leave it NULL.
    op.execute(
        """
        CREATE TABLE ai_model_versions (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            model_id        uuid NOT NULL REFERENCES ai_models(id) ON DELETE CASCADE,
            version         text NOT NULL,
            dimensions      int,
            is_current      boolean NOT NULL DEFAULT false,
            released_at     timestamptz,
            deprecated_at   timestamptz,
            artifact_uri    text,
            artifact_sha256 text,
            metadata        jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            UNIQUE (model_id, version),
            CHECK (dimensions IS NULL OR dimensions BETWEEN 32 AND 4096),
            CHECK (deprecated_at IS NULL OR released_at IS NULL OR deprecated_at >= released_at)
        );

        -- At most one current version per model.
        CREATE UNIQUE INDEX uq_ai_model_versions_current
            ON ai_model_versions (model_id)
            WHERE is_current;

        CREATE INDEX idx_ai_model_versions_model
            ON ai_model_versions(model_id);

        CREATE TRIGGER tg_ai_model_versions_updated_at
            BEFORE UPDATE ON ai_model_versions
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON COLUMN ai_model_versions.is_current IS
            'Exactly zero or one current version per model (partial unique index). '
            'Flipping this triggers an embedding_regeneration_job for affected tables.';
        """
    )

    # --- ai_fallback_chains + ai_fallback_chain_steps ----------------------
    op.execute(
        """
        CREATE TABLE ai_fallback_chains (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            slug            text NOT NULL UNIQUE,
            task_type       text NOT NULL
                CHECK (task_type IN ('vision','text','tts','translation','embedding','asr','moderation')),
            name            jsonb NOT NULL DEFAULT '{}'::jsonb,
            is_active       boolean NOT NULL DEFAULT true,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            CHECK (slug ~ '^[a-z0-9][a-z0-9_-]*$')
        );

        CREATE INDEX idx_ai_fallback_chains_task
            ON ai_fallback_chains(task_type) WHERE is_active;

        CREATE TRIGGER tg_ai_fallback_chains_updated_at
            BEFORE UPDATE ON ai_fallback_chains
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        CREATE TABLE ai_fallback_chain_steps (
            id                  uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            chain_id            uuid NOT NULL REFERENCES ai_fallback_chains(id) ON DELETE CASCADE,
            step_order          int NOT NULL,
            model_id            uuid NOT NULL REFERENCES ai_models(id) ON DELETE RESTRICT,
            max_latency_ms      int,
            max_cost_per_call   numeric(12,8),
            conditions          jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now(),
            UNIQUE (chain_id, step_order),
            CHECK (step_order >= 1),
            CHECK (max_latency_ms IS NULL OR max_latency_ms > 0)
        );

        CREATE INDEX idx_ai_fallback_chain_steps_chain
            ON ai_fallback_chain_steps(chain_id, step_order);

        CREATE TRIGGER tg_ai_fallback_chain_steps_updated_at
            BEFORE UPDATE ON ai_fallback_chain_steps
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE ai_fallback_chains IS
            'Ordered fallback chain per task type (Agent 3 §3.5). The resolver walks '
            'steps in step_order, skipping any whose conditions are unmet.';
        """
    )

    # --- prompt_templates + prompt_template_versions -----------------------
    op.execute(
        """
        CREATE TABLE prompt_templates (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            slug            text NOT NULL UNIQUE,
            name            jsonb NOT NULL DEFAULT '{}'::jsonb,
            system_prompt   text,
            user_template   text NOT NULL,
            output_schema   jsonb,
            task_type       text NOT NULL
                CHECK (task_type IN ('vision','text','tts','translation','embedding','asr','moderation')),
            is_active       boolean NOT NULL DEFAULT true,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            CHECK (slug ~ '^[a-z0-9][a-z0-9_-]*$')
        );

        CREATE INDEX idx_prompt_templates_task
            ON prompt_templates(task_type) WHERE is_active;

        CREATE TRIGGER tg_prompt_templates_updated_at
            BEFORE UPDATE ON prompt_templates
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        CREATE TABLE prompt_template_versions (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            template_id     uuid NOT NULL REFERENCES prompt_templates(id) ON DELETE CASCADE,
            version         int NOT NULL,
            system_prompt   text,
            user_template   text NOT NULL,
            output_schema   jsonb,
            created_by      uuid,
            created_at      timestamptz NOT NULL DEFAULT now(),
            deprecated_at   timestamptz,
            UNIQUE (template_id, version),
            CHECK (version >= 1)
        );

        CREATE INDEX idx_prompt_template_versions_template
            ON prompt_template_versions(template_id, version DESC);

        COMMENT ON TABLE prompt_template_versions IS
            'Immutable historical versions of a prompt template (Agent 3 §3.8). '
            'ai_generations rows reference a specific version for reproducibility.';
        """
    )

    # --- Seed providers (Decisions §5 / §6 / §42) --------------------------
    op.execute(
        """
        INSERT INTO ai_providers (slug, name, kind, base_url, supports_streaming, requires_credit_card, status) VALUES
            ('anthropic',
                '{"en":"Anthropic"}'::jsonb,
                'cloud_api', 'https://api.anthropic.com', true, true, 'active'),
            ('openai',
                '{"en":"OpenAI"}'::jsonb,
                'cloud_api', 'https://api.openai.com', true, true, 'active'),
            ('google',
                '{"en":"Google AI (Vision / Translate)"}'::jsonb,
                'cloud_api', 'https://vision.googleapis.com', false, true, 'active'),
            ('meta',
                '{"en":"Meta LLaVA (local GPU)"}'::jsonb,
                'local_gpu', NULL, true, false, 'active'),
            ('deepl',
                '{"en":"DeepL Translator"}'::jsonb,
                'cloud_api', 'https://api.deepl.com', false, true, 'active'),
            ('kokoro_local',
                '{"en":"Kokoro TTS (local)"}'::jsonb,
                'local_gpu', NULL, true, false, 'active'),
            ('piper_local',
                '{"en":"Piper TTS (local CPU)"}'::jsonb,
                'local_gpu', NULL, true, false, 'active'),
            ('nllb_local',
                '{"en":"NLLB translator (local)"}'::jsonb,
                'local_gpu', NULL, false, false, 'active'),
            ('elevenlabs',
                '{"en":"ElevenLabs TTS"}'::jsonb,
                'cloud_api', 'https://api.elevenlabs.io', true, true, 'active'),
            ('mistral_local',
                '{"en":"Mistral / Mixtral (local GPU)"}'::jsonb,
                'local_gpu', NULL, true, false, 'active');
        """
    )

    # --- Seed models (Decisions §5 vision benchmark; §6 TTS; §42 translation) ---
    # cost values are USD per 1k tokens for chat models; vision/tts/translation
    # rows leave the per-1k columns NULL — they're priced per-image or per-second.
    op.execute(
        """
        INSERT INTO ai_models (
            slug, provider_id, name, task_type, modality,
            context_window, max_output_tokens,
            supports_tools, supports_streaming,
            cost_per_1k_input_tokens, cost_per_1k_output_tokens,
            is_enabled, sort_order
        ) VALUES
            -- Anthropic Claude family
            ('claude-opus-4-7',
                (SELECT id FROM ai_providers WHERE slug='anthropic'),
                '{"en":"Claude Opus 4.7"}'::jsonb,
                'text', ARRAY['text','vision'],
                200000, 8192, true, true, 0.015, 0.075, true, 10),
            ('claude-sonnet-4-6',
                (SELECT id FROM ai_providers WHERE slug='anthropic'),
                '{"en":"Claude Sonnet 4.6"}'::jsonb,
                'text', ARRAY['text','vision'],
                200000, 8192, true, true, 0.003, 0.015, true, 20),
            ('claude-haiku-4-5-20251001',
                (SELECT id FROM ai_providers WHERE slug='anthropic'),
                '{"en":"Claude Haiku 4.5 (2025-10-01)"}'::jsonb,
                'text', ARRAY['text','vision'],
                200000, 8192, true, true, 0.00025, 0.00125, true, 30),

            -- OpenAI
            ('gpt-4o',
                (SELECT id FROM ai_providers WHERE slug='openai'),
                '{"en":"GPT-4o"}'::jsonb,
                'text', ARRAY['text','vision'],
                128000, 4096, true, true, 0.005, 0.015, true, 40),
            ('gpt-4o-mini',
                (SELECT id FROM ai_providers WHERE slug='openai'),
                '{"en":"GPT-4o mini"}'::jsonb,
                'text', ARRAY['text','vision'],
                128000, 4096, true, true, 0.00015, 0.0006, true, 50),

            -- Local vision (Decisions §5 vision benchmark candidates)
            ('llava-1.6-34b',
                (SELECT id FROM ai_providers WHERE slug='meta'),
                '{"en":"LLaVA 1.6 (34B)"}'::jsonb,
                'vision', ARRAY['image','text'],
                4096, 1024, false, true, NULL, NULL, true, 60),
            ('llava-1.6-vicuna-7b',
                (SELECT id FROM ai_providers WHERE slug='meta'),
                '{"en":"LLaVA 1.6 Vicuna (7B)"}'::jsonb,
                'vision', ARRAY['image','text'],
                4096, 1024, false, true, NULL, NULL, true, 70),
            ('internvl-2-26b',
                (SELECT id FROM ai_providers WHERE slug='meta'),
                '{"en":"InternVL 2 (26B)"}'::jsonb,
                'vision', ARRAY['image','text'],
                8192, 2048, false, false, NULL, NULL, true, 80),

            -- TTS (Decisions §6)
            ('kokoro-82m',
                (SELECT id FROM ai_providers WHERE slug='kokoro_local'),
                '{"en":"Kokoro 82M TTS"}'::jsonb,
                'tts', ARRAY['text','audio'],
                NULL, NULL, false, true, NULL, NULL, true, 90),
            ('piper-uz-female',
                (SELECT id FROM ai_providers WHERE slug='piper_local'),
                '{"en":"Piper Uzbek female"}'::jsonb,
                'tts', ARRAY['text','audio'],
                NULL, NULL, false, false, NULL, NULL, true, 100),

            -- Translation (Decisions §42)
            ('nllb-200-distilled-600m',
                (SELECT id FROM ai_providers WHERE slug='nllb_local'),
                '{"en":"NLLB-200 distilled (600M)"}'::jsonb,
                'translation', ARRAY['text'],
                1024, 1024, false, false, NULL, NULL, true, 110),
            ('nllb-200-3.3b',
                (SELECT id FROM ai_providers WHERE slug='nllb_local'),
                '{"en":"NLLB-200 (3.3B)"}'::jsonb,
                'translation', ARRAY['text'],
                1024, 1024, false, false, NULL, NULL, true, 120),

            -- Embeddings (text + multimodal)
            ('text-embedding-3-small',
                (SELECT id FROM ai_providers WHERE slug='openai'),
                '{"en":"OpenAI text-embedding-3 small"}'::jsonb,
                'embedding', ARRAY['text'],
                8192, NULL, false, false, 0.00002, NULL, true, 130),
            ('text-embedding-3-large',
                (SELECT id FROM ai_providers WHERE slug='openai'),
                '{"en":"OpenAI text-embedding-3 large"}'::jsonb,
                'embedding', ARRAY['text'],
                8192, NULL, false, false, 0.00013, NULL, true, 140),
            ('multilingual-e5-large',
                (SELECT id FROM ai_providers WHERE slug='meta'),
                '{"en":"multilingual-e5-large"}'::jsonb,
                'embedding', ARRAY['text'],
                512, NULL, false, false, NULL, NULL, true, 150),
            ('clip-vit-large-patch14',
                (SELECT id FROM ai_providers WHERE slug='meta'),
                '{"en":"CLIP ViT-L/14"}'::jsonb,
                'embedding', ARRAY['image','text'],
                77, NULL, false, false, NULL, NULL, true, 160);
        """
    )

    # --- Seed initial model versions (mark embedding models current) -------
    # Embedding ones carry ``dimensions`` so 0031 can wire HNSW to a known dim.
    op.execute(
        """
        INSERT INTO ai_model_versions (model_id, version, dimensions, is_current, released_at) VALUES
            ((SELECT id FROM ai_models WHERE slug='multilingual-e5-large'),
                'v1.0', 1024, true, now()),
            ((SELECT id FROM ai_models WHERE slug='clip-vit-large-patch14'),
                'v1.0', 768, true, now()),
            ((SELECT id FROM ai_models WHERE slug='text-embedding-3-small'),
                '2024-09-15', 1536, false, now()),
            ((SELECT id FROM ai_models WHERE slug='text-embedding-3-large'),
                '2024-09-15', 3072, false, now()),
            ((SELECT id FROM ai_models WHERE slug='claude-opus-4-7'),
                '20250101', NULL, true, now()),
            ((SELECT id FROM ai_models WHERE slug='claude-sonnet-4-6'),
                '20250101', NULL, true, now()),
            ((SELECT id FROM ai_models WHERE slug='claude-haiku-4-5-20251001'),
                '20251001', NULL, true, now()),
            ((SELECT id FROM ai_models WHERE slug='gpt-4o'),
                '2024-08-06', NULL, true, now()),
            ((SELECT id FROM ai_models WHERE slug='gpt-4o-mini'),
                '2024-07-18', NULL, true, now()),
            ((SELECT id FROM ai_models WHERE slug='llava-1.6-34b'),
                'q4_K_M', NULL, true, now()),
            ((SELECT id FROM ai_models WHERE slug='llava-1.6-vicuna-7b'),
                'q4_K_M', NULL, true, now()),
            ((SELECT id FROM ai_models WHERE slug='internvl-2-26b'),
                'q4_K_M', NULL, true, now()),
            ((SELECT id FROM ai_models WHERE slug='kokoro-82m'),
                'v0.19', NULL, true, now()),
            ((SELECT id FROM ai_models WHERE slug='piper-uz-female'),
                'v1.0', NULL, true, now()),
            ((SELECT id FROM ai_models WHERE slug='nllb-200-distilled-600m'),
                'v1.0', NULL, true, now()),
            ((SELECT id FROM ai_models WHERE slug='nllb-200-3.3b'),
                'v1.0', NULL, true, now());
        """
    )

    # --- Seed fallback chains ---------------------------------------------
    op.execute(
        """
        INSERT INTO ai_fallback_chains (slug, task_type, name, is_active) VALUES
            ('vision_default',      'vision',
                '{"en":"Vision recognition default"}'::jsonb,      true),
            ('tts_default',         'tts',
                '{"en":"Text-to-speech default"}'::jsonb,           true),
            ('translation_default', 'translation',
                '{"en":"Translation default"}'::jsonb,              true),
            ('chat_default',        'text',
                '{"en":"Chat / LLM default"}'::jsonb,               true);

        -- vision_default: llava-34b → google vision (gpt-4o vision proxy) → gpt-4o
        INSERT INTO ai_fallback_chain_steps (chain_id, step_order, model_id, max_latency_ms, conditions) VALUES
            ((SELECT id FROM ai_fallback_chains WHERE slug='vision_default'), 1,
                (SELECT id FROM ai_models WHERE slug='llava-1.6-34b'),  3000, '{}'::jsonb),
            ((SELECT id FROM ai_fallback_chains WHERE slug='vision_default'), 2,
                (SELECT id FROM ai_models WHERE slug='internvl-2-26b'), 4000, '{"on":"error"}'::jsonb),
            ((SELECT id FROM ai_fallback_chains WHERE slug='vision_default'), 3,
                (SELECT id FROM ai_models WHERE slug='gpt-4o'),         6000, '{"on":"error"}'::jsonb);

        -- tts_default: kokoro → piper → elevenlabs
        INSERT INTO ai_fallback_chain_steps (chain_id, step_order, model_id, max_latency_ms, conditions) VALUES
            ((SELECT id FROM ai_fallback_chains WHERE slug='tts_default'), 1,
                (SELECT id FROM ai_models WHERE slug='kokoro-82m'),      1500, '{}'::jsonb),
            ((SELECT id FROM ai_fallback_chains WHERE slug='tts_default'), 2,
                (SELECT id FROM ai_models WHERE slug='piper-uz-female'), 1000, '{"on":"error"}'::jsonb);

        -- translation_default: nllb-distilled → nllb-3.3b → deepl-proxy (claude haiku stand-in until DeepL model row exists)
        INSERT INTO ai_fallback_chain_steps (chain_id, step_order, model_id, max_latency_ms, conditions) VALUES
            ((SELECT id FROM ai_fallback_chains WHERE slug='translation_default'), 1,
                (SELECT id FROM ai_models WHERE slug='nllb-200-distilled-600m'), 800, '{}'::jsonb),
            ((SELECT id FROM ai_fallback_chains WHERE slug='translation_default'), 2,
                (SELECT id FROM ai_models WHERE slug='nllb-200-3.3b'),           1500,
                jsonb_build_object('on','low_confidence','threshold',0.6)),
            ((SELECT id FROM ai_fallback_chains WHERE slug='translation_default'), 3,
                (SELECT id FROM ai_models WHERE slug='claude-haiku-4-5-20251001'), 2000, '{"on":"error"}'::jsonb);

        -- chat_default: opus → sonnet → gpt-4o
        INSERT INTO ai_fallback_chain_steps (chain_id, step_order, model_id, max_latency_ms, conditions) VALUES
            ((SELECT id FROM ai_fallback_chains WHERE slug='chat_default'), 1,
                (SELECT id FROM ai_models WHERE slug='claude-opus-4-7'),   8000, '{}'::jsonb),
            ((SELECT id FROM ai_fallback_chains WHERE slug='chat_default'), 2,
                (SELECT id FROM ai_models WHERE slug='claude-sonnet-4-6'), 6000, '{"on":"error"}'::jsonb),
            ((SELECT id FROM ai_fallback_chains WHERE slug='chat_default'), 3,
                (SELECT id FROM ai_models WHERE slug='gpt-4o'),            6000, '{"on":"error"}'::jsonb);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS prompt_template_versions CASCADE;")
    op.execute("DROP TABLE IF EXISTS prompt_templates CASCADE;")
    op.execute("DROP TABLE IF EXISTS ai_fallback_chain_steps CASCADE;")
    op.execute("DROP TABLE IF EXISTS ai_fallback_chains CASCADE;")
    op.execute("DROP TABLE IF EXISTS ai_model_versions CASCADE;")
    op.execute("DROP TABLE IF EXISTS ai_models CASCADE;")
    op.execute("DROP TABLE IF EXISTS ai_providers CASCADE;")
