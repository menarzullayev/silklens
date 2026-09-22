# 03 — AI, Embeddings, RAG, Inference & AI Observability

> **Agent 3 — AI & Vector Infrastructure Architect**
> **Domain:** Production-grade database architecture for the AI substrate that powers SilkLens — vision recognition, TTS, translation, semantic/RAG search, recommendations, moderation, observability, cost attribution, and future fine-tuning.
> **Stack:** PostgreSQL 16 + `pgvector` 0.7+ (HNSW), Redis 7 (hot cache), Celery 5 (broker = Redis, results = PG), MinIO (artifacts), OpenTelemetry (traces), Prometheus + Grafana (metrics).
> **Scale targets:** 500K vectors at launch → 50M by FAZA 7 (global dataset). p95 vision recognition < 2s, p95 semantic search < 150ms.

---

## 1. Domain Analysis — The AI Substrate as a First-Class System

SilkLens is, structurally, an **AI-native platform**. According to Project-Decisions §51 the AI agents perform 99% of execution; according to §5, §6, §42 the project never commits to a single model and instead operates a **benchmark-driven, admin-switchable model registry** with fallback chains. According to Roadmap FAZA 4 and FAZA 7 we will run model benchmarks and eventually fine-tune a SilkLens-specific model. This makes the AI layer not a feature — it is the load-bearing substrate of every user-visible capability: camera recognition, audio guides, content boost, multilingual translation, AR chat, recommendations, moderation, anti-fraud.

This forces three architectural commitments that drive the entire schema below:

**(A) Provider abstraction — never store “GPT-4V said …” — store `(provider_id, model_id, version_id) said …`.**
Every concrete capability is expressed as a **Provider** interface: `VisionProvider`, `TTSProvider`, `LLMProvider`, `TranslationProvider`, `EmbeddingProvider`, `ModerationProvider`. The DB layer mirrors this with `ai_providers` (LLaVA-local / Anthropic-API / OpenAI / Google-Vision / NLLB-local / DeepL / ElevenLabs / Kokoro-local) and `ai_models` (capability-scoped registry). Because the admin panel must switch models in one click (Decisions §5, §15), every generation row carries a *resolved* `model_version_id` so historical artifacts are reproducible even after the active model changes.

**(B) Multi-model coexistence — many embedding spaces simultaneously.**
CLIP-image (vision) produces 768-D vectors. multilingual-e5-large produces 1024-D. NLLB encoder produces 1024-D but in a different space. A SilkLens fine-tuned model in FAZA 7 will produce its own dimension. These vectors are **non-interchangeable** — a cosine distance between a CLIP embedding and an e5 embedding is meaningless. The schema therefore physically separates embedding tables **per model family and dimension** (`embeddings_heritage_clip_768`, `embeddings_heritage_e5_1024`, etc.) rather than one polymorphic table — see §5 for the trade-off analysis.

**(C) Everything is auditable, reproducible, and billable.**
Every AI call produces a row in `ai_generations` linked to: input hash (for cache), prompt-template version, resolved model version, token counts, latency, cost (USD micro-cents), success/failure, moderation verdict, OpenTelemetry trace ID, and user/B2B attribution. This makes three things possible at once: (1) Project-Decisions §17 B2B cost attribution / B2G grant reporting; (2) FAZA 7 fine-tuning — every approved generation with positive user feedback becomes labelled training data; (3) AI observability — drift, regression, and cost-per-feature dashboards.

The result is a substrate where adding a new provider (a future GPT-5 vision, Gemini 3, a custom SilkLens-VLM) is a *configuration* event, not a refactor. Removing a provider deprecates a `model_version_id` and triggers regeneration jobs for affected embeddings, with old generations kept immutable for audit.

---

## 2. Entity Discovery Report

Discovered entities (28 tables), grouped by sub-domain:

### Model & Provider Registry (admin-managed)
1. **`ai_providers`** — registered providers (LLaVA-local, Anthropic, OpenAI, Google-Vision, DeepL, ElevenLabs, NLLB-local, Kokoro-local, Piper-local, internal).
2. **`ai_models`** — capability-scoped models (`vision`, `llm`, `tts`, `translation`, `embedding-text`, `embedding-image`, `moderation`, `reranker`, `ocr`).
3. **`ai_model_versions`** — concrete versions with parameters, dimension, cost-per-1k-tokens, GPU/CPU resource cost, deprecation status.
4. **`ai_model_benchmarks`** — admin-run benchmarks (per Decisions §5): accuracy %, latency p50/p95, RAM/VRAM, cost. Drives model selection UI.
5. **`ai_fallback_chains`** — admin-configured ordered chain per task type (`vision_recognition` → LLaVA → Google-Vision → GPT-4V).
6. **`ai_rate_limits`** — per-provider quota (requests/min, tokens/day, monthly cap).

### Prompts (versioned + A/B)
7. **`prompt_templates`** — logical templates (`heritage_describe`, `chat_qa`, `route_plan`, `moderation_check`).
8. **`prompt_template_versions`** — immutable versions (rendered Jinja, system prompt, variables, expected output schema).
9. **`prompt_template_variants`** — A/B variants pinned to one version (e.g. `concise` vs `narrative`).
10. **`prompt_template_experiments`** — experiment definitions: variant weights, target metric, status.

### Vectors & RAG
11. **`embeddings_heritage_<model>_<dim>`** — per-heritage vectors (e.g. `embeddings_heritage_e5_1024`, `embeddings_heritage_clip_768`). Multiple tables, one per (model-family, dim).
12. **`embeddings_media_clip_768`** — image embeddings for user-uploaded & curated photos.
13. **`embeddings_user_content_e5_1024`** — UGC text (reviews, comments) embeddings.
14. **`embeddings_queries_e5_1024`** — user query embeddings (search bar, AI chat) for recommendation seeds.
15. **`embedding_chunks`** — RAG corpus chunks (long heritage descriptions, Wikipedia imports, expert notes) — separated because chunks have lifecycle independent of source rows.
16. **`embedding_regeneration_jobs`** — bookkeeping for re-embedding when a model version is upgraded or deprecated.

### Inference & Generations
17. **`ai_inference_jobs`** — async job queue mirror (Celery): vision recognize, TTS gen, translation, batch embedding. Idempotency key, retries, DLQ pointer.
18. **`ai_generations`** — every prompt → output log. Immutable audit row.
19. **`ai_cache`** — deduplication: `(input_hash, model_version_id, params_hash) → output_ref`. TTL + invalidation.
20. **`ai_perceptual_hash_index`** — pHash/dHash index for "same image → same recognition" cache lookup.

### Translation
21. **`ai_translation_memory`** — segment-level TM: `(source_lang, target_lang, source_hash) → translation, BLEU, model_version_id, approved_by`.
22. **`ai_translation_jobs`** — batch translation orchestration (e.g. "translate 5k heritage descriptions into Arabic").

### Moderation & Safety
23. **`ai_moderation_results`** — NSFW/spam/hate/violence/fake-geotag classification per artifact (media, UGC, AI output).
24. **`ai_safety_incidents`** — confirmed safety events (linked to user trust, ban pipeline).
25. **`ai_prompt_injection_log`** — detected injection attempts in chat / search.

### Cost, Usage, Observability
26. **`ai_token_usage`** — **partitioned by day** (range partition). Per (user_id|b2b_id, model_version_id, day) input/output tokens, cost.
27. **`ai_cost_ledger`** — daily roll-up + B2B billing source-of-truth (linked to billing in Agent 6's domain).
28. **`ai_drift_metrics`** — daily drift signals: input-distribution KL-divergence, output-distribution shift, confidence-score drop.

### Recommendation & Feedback
29. **`ai_recommendation_state`** — per-user precomputed recs: item vector centroid, last-update, decay.
30. **`ai_user_item_interactions`** — implicit & explicit signals (view, dwell, like, save, share) for CF.
31. **`ai_feedback`** — thumbs up/down/edit/report on AI outputs — becomes fine-tuning labels (FAZA 7).

*Final count: 31 logical tables (embedding tables expand to ~4–8 physical tables — see §5).*

---

## 3. Full Table-by-Table Specification

> **Conventions:** All PKs are `BIGINT GENERATED ALWAYS AS IDENTITY` unless noted. All tables have `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`, `updated_at TIMESTAMPTZ` with trigger. Soft-delete via `deleted_at TIMESTAMPTZ` only where audit demands it (registry tables, generations are *never* deleted, only `status='archived'`).
> **Cross-agent FK contracts** are marked `FK→Agent N` and finalised in §14.

### 3.1 `ai_providers`

```sql
CREATE TABLE ai_providers (
  id            BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  code          TEXT NOT NULL UNIQUE,        -- 'anthropic', 'openai', 'llava_local', 'nllb_local', 'elevenlabs', 'google_vision', 'deepl', 'kokoro_local'
  display_name  TEXT NOT NULL,
  kind          TEXT NOT NULL CHECK (kind IN ('local_gpu','local_cpu','cloud_api','hybrid')),
  base_url      TEXT,                        -- NULL for local
  auth_kind     TEXT NOT NULL CHECK (auth_kind IN ('none','api_key','oauth','mtls')),
  credential_ref TEXT,                       -- pointer to secret manager (Vault/SOPS); never plaintext
  is_enabled    BOOLEAN NOT NULL DEFAULT TRUE,
  health_status TEXT NOT NULL DEFAULT 'unknown' CHECK (health_status IN ('healthy','degraded','down','unknown')),
  last_health_check_at TIMESTAMPTZ,
  metadata      JSONB NOT NULL DEFAULT '{}', -- {region, sla, data_residency}
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ
);
CREATE INDEX idx_ai_providers_enabled ON ai_providers(is_enabled) WHERE is_enabled = TRUE;
```

### 3.2 `ai_models`

```sql
CREATE TABLE ai_models (
  id            BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  provider_id   BIGINT NOT NULL REFERENCES ai_providers(id) ON DELETE RESTRICT,
  code          TEXT NOT NULL,               -- 'llava-1.6-34b','claude-sonnet-4.7','nllb-200-3.3B','clip-vit-l-14','multilingual-e5-large'
  capability    TEXT NOT NULL CHECK (capability IN (
                  'vision_recognition','vision_caption','llm_chat','llm_completion',
                  'tts','translation','embedding_text','embedding_image',
                  'moderation_image','moderation_text','reranker','ocr','speech_to_text')),
  modality_in   TEXT[] NOT NULL,             -- {'image'}, {'text'}, {'image','text'}
  modality_out  TEXT[] NOT NULL,
  is_default_for_capability BOOLEAN NOT NULL DEFAULT FALSE,
  metadata      JSONB NOT NULL DEFAULT '{}',
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (provider_id, code)
);
CREATE UNIQUE INDEX uq_ai_models_default_per_capability
  ON ai_models(capability) WHERE is_default_for_capability = TRUE;
CREATE INDEX idx_ai_models_capability ON ai_models(capability);
```

### 3.3 `ai_model_versions`

```sql
CREATE TABLE ai_model_versions (
  id              BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  model_id        BIGINT NOT NULL REFERENCES ai_models(id) ON DELETE RESTRICT,
  version         TEXT NOT NULL,             -- 'v2024-09-15', '1.6.34b-q4', 'sha:abcdef'
  released_at     TIMESTAMPTZ NOT NULL,
  deprecated_at   TIMESTAMPTZ,
  -- Embedding-specific (NULL otherwise)
  embedding_dim         INT,
  embedding_normalized  BOOLEAN,             -- L2-normalised on output?
  embedding_distance    TEXT CHECK (embedding_distance IN ('cosine','l2','ip')),
  -- Cost & perf
  cost_input_per_1k_micro_usd  BIGINT NOT NULL DEFAULT 0, -- micro-cents per 1k input tokens
  cost_output_per_1k_micro_usd BIGINT NOT NULL DEFAULT 0,
  cost_per_image_micro_usd     BIGINT NOT NULL DEFAULT 0,
  cost_per_second_audio_micro_usd BIGINT NOT NULL DEFAULT 0,
  context_window  INT,
  max_output_tokens INT,
  default_params  JSONB NOT NULL DEFAULT '{}', -- {temperature, top_p, ...}
  resource_profile JSONB NOT NULL DEFAULT '{}', -- {vram_gb, ram_gb, gpu_class}
  artifact_uri    TEXT,                       -- minio://models/llava-1.6-34b-q4.gguf
  artifact_sha256 TEXT,
  status          TEXT NOT NULL DEFAULT 'active'
                  CHECK (status IN ('active','staging','deprecated','archived','failed')),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (model_id, version),
  CHECK ( (embedding_dim IS NULL) OR (embedding_dim BETWEEN 32 AND 4096) )
);
CREATE INDEX idx_amv_active ON ai_model_versions(model_id, status) WHERE status IN ('active','staging');
```

### 3.4 `ai_model_benchmarks` (Decisions §5)

```sql
CREATE TABLE ai_model_benchmarks (
  id                  BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  model_version_id    BIGINT NOT NULL REFERENCES ai_model_versions(id) ON DELETE CASCADE,
  benchmark_suite     TEXT NOT NULL,         -- 'silklens_heritage_v1','uzbek_monuments_50','tts_quality_v2'
  dataset_size        INT NOT NULL,
  accuracy            NUMERIC(5,4),          -- 0.0000–1.0000
  precision_score     NUMERIC(5,4),
  recall_score        NUMERIC(5,4),
  f1_score            NUMERIC(5,4),
  bleu_score          NUMERIC(5,4),          -- translation
  mos_score           NUMERIC(4,2),          -- TTS Mean Opinion Score
  latency_p50_ms      INT,
  latency_p95_ms      INT,
  latency_p99_ms      INT,
  cost_per_request_micro_usd BIGINT,
  vram_peak_mb        INT,
  ran_by_admin_id     BIGINT,                -- FK→Agent 2 (admin user)
  ran_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
  notes               TEXT,
  metadata            JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX idx_amb_suite_recent ON ai_model_benchmarks(benchmark_suite, ran_at DESC);
CREATE INDEX idx_amb_model_recent ON ai_model_benchmarks(model_version_id, ran_at DESC);
```

### 3.5 `ai_fallback_chains`

```sql
CREATE TABLE ai_fallback_chains (
  id            BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  task_code     TEXT NOT NULL,               -- 'vision_recognition','tts','translation','chat'
  position      INT  NOT NULL,               -- 1 = primary, 2 = fallback, ...
  model_version_id BIGINT NOT NULL REFERENCES ai_model_versions(id) ON DELETE RESTRICT,
  trigger_condition JSONB NOT NULL DEFAULT '{}', -- {on:'error'|'timeout'|'low_confidence', threshold: 0.6}
  is_enabled    BOOLEAN NOT NULL DEFAULT TRUE,
  region        TEXT,                        -- NULL = global; 'UZ', 'CN', 'EU' for geo-routing
  created_by_admin_id BIGINT,                -- FK→Agent 2
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (task_code, position, region)
);
CREATE INDEX idx_afc_lookup ON ai_fallback_chains(task_code, is_enabled, region, position);
```

### 3.6 `ai_rate_limits`

```sql
CREATE TABLE ai_rate_limits (
  id            BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  provider_id   BIGINT NOT NULL REFERENCES ai_providers(id) ON DELETE CASCADE,
  model_id      BIGINT REFERENCES ai_models(id) ON DELETE CASCADE, -- NULL = applies to provider
  scope         TEXT NOT NULL CHECK (scope IN ('global','per_user','per_b2b','per_ip')),
  window_kind   TEXT NOT NULL CHECK (window_kind IN ('minute','hour','day','month')),
  max_requests  INT,
  max_tokens    BIGINT,
  max_cost_micro_usd BIGINT,
  is_enabled    BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX idx_arl_lookup ON ai_rate_limits(provider_id, model_id, scope) WHERE is_enabled;
```

### 3.7 `prompt_templates`

```sql
CREATE TABLE prompt_templates (
  id            BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  code          TEXT NOT NULL UNIQUE,        -- 'heritage_describe','chat_qa','moderation_image'
  category      TEXT NOT NULL,               -- 'content','chat','moderation','rag','tool_call'
  description   TEXT,
  current_version_id BIGINT,                 -- FK to prompt_template_versions; nullable to avoid circular
  owner_admin_id BIGINT,                     -- FK→Agent 2
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 3.8 `prompt_template_versions`

```sql
CREATE TABLE prompt_template_versions (
  id              BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  template_id     BIGINT NOT NULL REFERENCES prompt_templates(id) ON DELETE CASCADE,
  version         INT NOT NULL,
  system_prompt   TEXT,
  user_prompt_template TEXT NOT NULL,        -- Jinja2
  expected_schema JSONB,                     -- JSON-Schema for structured output validation
  variables       JSONB NOT NULL DEFAULT '[]', -- [{name,type,required}]
  default_model_version_id BIGINT REFERENCES ai_model_versions(id),
  default_params  JSONB NOT NULL DEFAULT '{}',
  prompt_hash     TEXT NOT NULL,             -- sha256 of (system + user_template) — cache keying
  is_published    BOOLEAN NOT NULL DEFAULT FALSE,
  changelog       TEXT,
  created_by_admin_id BIGINT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (template_id, version)
);
ALTER TABLE prompt_templates
  ADD CONSTRAINT fk_pt_current_version FOREIGN KEY (current_version_id)
  REFERENCES prompt_template_versions(id) DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX idx_ptv_hash ON prompt_template_versions(prompt_hash);
```

### 3.9 `prompt_template_variants` (A/B)

```sql
CREATE TABLE prompt_template_variants (
  id            BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  version_id    BIGINT NOT NULL REFERENCES prompt_template_versions(id) ON DELETE CASCADE,
  variant_code  TEXT NOT NULL,               -- 'concise','narrative','poetic'
  prompt_override JSONB NOT NULL,            -- patch on top of version
  weight        INT  NOT NULL DEFAULT 1 CHECK (weight >= 0),
  is_enabled    BOOLEAN NOT NULL DEFAULT TRUE,
  UNIQUE (version_id, variant_code)
);
```

### 3.10 `prompt_template_experiments`

```sql
CREATE TABLE prompt_template_experiments (
  id               BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  template_id      BIGINT NOT NULL REFERENCES prompt_templates(id),
  experiment_code  TEXT NOT NULL UNIQUE,
  status           TEXT NOT NULL CHECK (status IN ('draft','running','paused','completed','archived')),
  variant_ids      BIGINT[] NOT NULL,
  target_metric    TEXT NOT NULL,            -- 'user_thumbs_up_rate','latency','cost'
  started_at       TIMESTAMPTZ,
  ended_at         TIMESTAMPTZ,
  winner_variant_id BIGINT REFERENCES prompt_template_variants(id),
  result_summary   JSONB
);
```

### 3.11 Embedding tables — pattern

> One physical table per `(target_kind, model_family, dimension)`. See §5 for justification.

```sql
-- Example: heritage embeddings via multilingual-e5-large (1024-D, cosine, normalized)
CREATE TABLE embeddings_heritage_e5_1024 (
  id                BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  heritage_id       BIGINT NOT NULL,                       -- FK→Agent 1 (heritages.id)
  model_version_id  BIGINT NOT NULL REFERENCES ai_model_versions(id) ON DELETE RESTRICT,
  language          CHAR(2) NOT NULL,                      -- 'uz','ru','en','zh' — embeddings are per-language
  source_field      TEXT NOT NULL,                         -- 'description','short_description','tags_concat'
  source_hash       TEXT NOT NULL,                         -- sha256 of source text — regen trigger
  embedding         vector(1024) NOT NULL,
  norm              REAL,                                  -- pre-computed L2 norm (sanity)
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (heritage_id, model_version_id, language, source_field)
);

-- HNSW index — cosine; m=16, ef_construction=200 baseline (see §4)
CREATE INDEX idx_eh_e5_1024_hnsw
  ON embeddings_heritage_e5_1024
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 200);

-- Filter-aware indexes for hybrid search
CREATE INDEX idx_eh_e5_lang ON embeddings_heritage_e5_1024(language);
CREATE INDEX idx_eh_e5_heritage ON embeddings_heritage_e5_1024(heritage_id);
CREATE INDEX idx_eh_e5_model ON embeddings_heritage_e5_1024(model_version_id);

-- Partial HNSW per active model (recall stays high; index small)
CREATE INDEX idx_eh_e5_active_hnsw
  ON embeddings_heritage_e5_1024
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 200)
  WHERE model_version_id = 17;  -- active model — recreated via migration on model switch
```

Analogous tables: `embeddings_heritage_clip_768`, `embeddings_media_clip_768`, `embeddings_user_content_e5_1024`, `embeddings_queries_e5_1024`.

### 3.12 `embedding_chunks` (RAG)

```sql
CREATE TABLE embedding_chunks (
  id                 BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  corpus             TEXT NOT NULL,           -- 'heritage_long','wikipedia_uz','expert_notes','unesco_pdf'
  source_kind        TEXT NOT NULL,           -- 'heritage','media','external_doc','b2b_content'
  source_id          BIGINT,                  -- heritage_id / media_id / doc_id
  source_url         TEXT,
  language           CHAR(2) NOT NULL,
  chunk_index        INT NOT NULL,
  chunk_text         TEXT NOT NULL,
  token_count        INT NOT NULL,
  char_start         INT,
  char_end           INT,
  overlap_prev       INT NOT NULL DEFAULT 0,
  overlap_next       INT NOT NULL DEFAULT 0,
  -- metadata for filtered retrieval
  heritage_id        BIGINT,                  -- FK→Agent 1, optional
  period             TEXT,                    -- 'antique','medieval','timurid','modern' — for time-filtered RAG
  region_code        TEXT,                    -- ISO 3166-2 e.g. 'UZ-SA'
  tags               TEXT[] NOT NULL DEFAULT '{}',
  confidence_score   NUMERIC(5,4),
  -- vector
  embedding_e5_1024  vector(1024),
  model_version_id   BIGINT NOT NULL REFERENCES ai_model_versions(id),
  source_hash        TEXT NOT NULL,
  -- full-text for hybrid
  tsv                tsvector GENERATED ALWAYS AS (to_tsvector('simple', chunk_text)) STORED,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (corpus, source_kind, source_id, chunk_index, model_version_id, language)
);

CREATE INDEX idx_ec_hnsw
  ON embedding_chunks USING hnsw (embedding_e5_1024 vector_cosine_ops)
  WITH (m = 16, ef_construction = 200);
CREATE INDEX idx_ec_tsv ON embedding_chunks USING GIN (tsv);
CREATE INDEX idx_ec_filter ON embedding_chunks(language, corpus, region_code, period);
CREATE INDEX idx_ec_heritage ON embedding_chunks(heritage_id) WHERE heritage_id IS NOT NULL;
CREATE INDEX idx_ec_tags ON embedding_chunks USING GIN (tags);
```

### 3.13 `embedding_regeneration_jobs`

```sql
CREATE TABLE embedding_regeneration_jobs (
  id                  BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  target_table        TEXT NOT NULL,         -- 'embeddings_heritage_e5_1024'
  reason              TEXT NOT NULL CHECK (reason IN
                       ('model_upgrade','source_changed','dim_change','quality_drift','backfill','manual')),
  from_model_version_id BIGINT REFERENCES ai_model_versions(id),
  to_model_version_id   BIGINT NOT NULL REFERENCES ai_model_versions(id),
  filter_predicate    JSONB,                 -- e.g. {language:'uz'} for partial regen
  total_rows          BIGINT,
  processed_rows      BIGINT NOT NULL DEFAULT 0,
  failed_rows         BIGINT NOT NULL DEFAULT 0,
  status              TEXT NOT NULL DEFAULT 'pending'
                      CHECK (status IN ('pending','running','paused','completed','failed','cancelled')),
  started_at          TIMESTAMPTZ,
  finished_at         TIMESTAMPTZ,
  last_heartbeat_at   TIMESTAMPTZ,
  triggered_by_admin_id BIGINT,
  notes               TEXT,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_erj_active ON embedding_regeneration_jobs(status) WHERE status IN ('pending','running');
```

### 3.14 `ai_inference_jobs`

```sql
CREATE TABLE ai_inference_jobs (
  id                  BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  celery_task_id      UUID UNIQUE,                          -- Celery task UUID
  idempotency_key     TEXT NOT NULL UNIQUE,                 -- sha256(input + model + params + user_id?)
  task_kind           TEXT NOT NULL CHECK (task_kind IN
                       ('vision_recognize','vision_caption','tts','translation','embed_text',
                        'embed_image','chat_completion','moderation_image','moderation_text',
                        'ocr','rag_query','batch_embed')),
  requested_model_version_id BIGINT REFERENCES ai_model_versions(id),
  resolved_model_version_id  BIGINT REFERENCES ai_model_versions(id), -- after fallback resolution
  fallback_chain_id   BIGINT REFERENCES ai_fallback_chains(id),
  fallback_position   INT NOT NULL DEFAULT 1,
  prompt_template_version_id BIGINT REFERENCES prompt_template_versions(id),
  prompt_variant_id   BIGINT REFERENCES prompt_template_variants(id),
  input_ref           TEXT,                                  -- minio://… for binary; or inline JSONB
  input_inline        JSONB,
  input_hash          TEXT NOT NULL,
  params              JSONB NOT NULL DEFAULT '{}',
  -- attribution
  user_id             BIGINT,                                -- FK→Agent 2
  b2b_partner_id      BIGINT,                                -- FK→Agent 6
  origin              TEXT NOT NULL,                         -- 'mobile_app','admin_panel','batch_import','b2b_api'
  -- state
  status              TEXT NOT NULL DEFAULT 'queued' CHECK (status IN
                       ('queued','running','succeeded','failed','retrying','dead_letter','cancelled')),
  priority            SMALLINT NOT NULL DEFAULT 5 CHECK (priority BETWEEN 1 AND 9),
  attempts            INT NOT NULL DEFAULT 0,
  max_attempts        INT NOT NULL DEFAULT 3,
  next_retry_at       TIMESTAMPTZ,
  -- timing
  enqueued_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  started_at          TIMESTAMPTZ,
  finished_at         TIMESTAMPTZ,
  -- result
  output_ref          TEXT,                                  -- minio:// for binary
  output_inline       JSONB,
  output_hash         TEXT,
  error_kind          TEXT,
  error_message       TEXT,
  trace_id            TEXT,                                  -- OpenTelemetry
  span_id             TEXT,
  parent_job_id       BIGINT REFERENCES ai_inference_jobs(id) -- for retries / fallback chains
);
CREATE INDEX idx_aij_status ON ai_inference_jobs(status, priority, enqueued_at)
  WHERE status IN ('queued','retrying');
CREATE INDEX idx_aij_user ON ai_inference_jobs(user_id, enqueued_at DESC);
CREATE INDEX idx_aij_b2b ON ai_inference_jobs(b2b_partner_id, enqueued_at DESC);
CREATE INDEX idx_aij_kind_time ON ai_inference_jobs(task_kind, enqueued_at DESC);
CREATE INDEX idx_aij_trace ON ai_inference_jobs(trace_id);
```

### 3.15 `ai_generations`

```sql
CREATE TABLE ai_generations (
  id                  BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  inference_job_id    BIGINT REFERENCES ai_inference_jobs(id) ON DELETE SET NULL,
  model_version_id    BIGINT NOT NULL REFERENCES ai_model_versions(id),
  prompt_template_version_id BIGINT REFERENCES prompt_template_versions(id),
  prompt_variant_id   BIGINT REFERENCES prompt_template_variants(id),
  capability          TEXT NOT NULL,
  -- caching keys
  input_hash          TEXT NOT NULL,
  params_hash         TEXT NOT NULL,
  cache_key           TEXT NOT NULL,                          -- composite hash
  cache_hit           BOOLEAN NOT NULL DEFAULT FALSE,
  -- content
  input_preview       TEXT,                                   -- truncated, for debugging only
  output_ref          TEXT,
  output_inline       JSONB,
  output_text         TEXT,                                   -- shortcut for text outputs
  confidence_score    NUMERIC(5,4),
  -- moderation link (mandatory for user-visible outputs)
  moderation_id       BIGINT,                                 -- forward FK to ai_moderation_results
  moderation_verdict  TEXT CHECK (moderation_verdict IN ('clean','flagged','blocked','pending')),
  -- usage
  tokens_input        INT,
  tokens_output       INT,
  images_processed    INT,
  audio_seconds       NUMERIC(8,2),
  cost_micro_usd      BIGINT NOT NULL DEFAULT 0,
  latency_ms          INT,
  -- attribution
  user_id             BIGINT,                                 -- FK→Agent 2
  b2b_partner_id      BIGINT,                                 -- FK→Agent 6
  -- audit
  trace_id            TEXT,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  -- training data eligibility (FAZA 7)
  training_eligible   BOOLEAN NOT NULL DEFAULT FALSE,
  training_label      TEXT
);
CREATE INDEX idx_ag_cache ON ai_generations(cache_key);
CREATE INDEX idx_ag_user_recent ON ai_generations(user_id, created_at DESC);
CREATE INDEX idx_ag_model_recent ON ai_generations(model_version_id, created_at DESC);
CREATE INDEX idx_ag_capability_day ON ai_generations(capability, created_at DESC);
CREATE INDEX idx_ag_training ON ai_generations(capability, created_at DESC) WHERE training_eligible = TRUE;
```

> `ai_generations` is **append-only**; protected by `BEFORE UPDATE` trigger that rejects all mutation except moderation backfill within 24h.

### 3.16 `ai_cache`

```sql
CREATE TABLE ai_cache (
  cache_key           TEXT PRIMARY KEY,                       -- sha256(input_hash + model_version_id + params_hash + prompt_version_id)
  model_version_id    BIGINT NOT NULL REFERENCES ai_model_versions(id) ON DELETE CASCADE,
  capability          TEXT NOT NULL,
  output_ref          TEXT,
  output_inline       JSONB,
  output_text         TEXT,
  generation_id       BIGINT REFERENCES ai_generations(id),
  hit_count           BIGINT NOT NULL DEFAULT 0,
  last_hit_at         TIMESTAMPTZ,
  expires_at          TIMESTAMPTZ,                            -- NULL = never expires until model deprecation
  size_bytes          INT,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_ac_model ON ai_cache(model_version_id);
CREATE INDEX idx_ac_expires ON ai_cache(expires_at) WHERE expires_at IS NOT NULL;
```

> Redis mirrors hot keys (LRU, ~10GB). PostgreSQL is the source of truth and survives Redis flush.

### 3.17 `ai_perceptual_hash_index`

```sql
CREATE TABLE ai_perceptual_hash_index (
  id                  BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  phash               BIT(64) NOT NULL,                       -- pHash (64-bit)
  dhash               BIT(64),
  ahash               BIT(64),
  media_id            BIGINT,                                 -- FK→Agent 4
  heritage_id         BIGINT,                                 -- FK→Agent 1 (canonical match)
  generation_id       BIGINT REFERENCES ai_generations(id),
  source              TEXT NOT NULL,                          -- 'curated','ugc','b2b'
  confidence          NUMERIC(5,4),
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Hamming-distance search via bktree extension OR pg_bigm; baseline: simple equality + bucketed search
CREATE INDEX idx_aphi_phash_bucket ON ai_perceptual_hash_index((substring(phash::text, 1, 16)));
CREATE INDEX idx_aphi_heritage ON ai_perceptual_hash_index(heritage_id);
```

### 3.18 `ai_translation_memory`

```sql
CREATE TABLE ai_translation_memory (
  id                  BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  source_lang         CHAR(2) NOT NULL,
  target_lang         CHAR(2) NOT NULL,
  source_text         TEXT NOT NULL,
  source_hash         TEXT NOT NULL,                          -- sha256(source_text)
  target_text         TEXT NOT NULL,
  domain              TEXT,                                   -- 'heritage','ui','legal','b2b'
  segment_kind        TEXT NOT NULL CHECK (segment_kind IN ('term','phrase','sentence','paragraph')),
  bleu_score          NUMERIC(5,4),
  comet_score         NUMERIC(5,4),
  confidence_score    NUMERIC(5,4),
  model_version_id    BIGINT REFERENCES ai_model_versions(id),
  approved_by_admin_id BIGINT,
  approved_at         TIMESTAMPTZ,
  status              TEXT NOT NULL DEFAULT 'pending'
                      CHECK (status IN ('pending','auto_approved','approved','rejected','superseded')),
  -- vector for fuzzy match (LaBSE / multilingual-e5)
  source_embedding    vector(1024),
  hit_count           BIGINT NOT NULL DEFAULT 0,
  last_hit_at         TIMESTAMPTZ,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (source_lang, target_lang, source_hash, domain)
);
CREATE INDEX idx_atm_lookup ON ai_translation_memory(source_lang, target_lang, source_hash);
CREATE INDEX idx_atm_status ON ai_translation_memory(status) WHERE status IN ('pending','auto_approved');
CREATE INDEX idx_atm_hnsw ON ai_translation_memory
  USING hnsw (source_embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 200);
```

### 3.19 `ai_translation_jobs`

```sql
CREATE TABLE ai_translation_jobs (
  id                  BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  job_code            TEXT NOT NULL UNIQUE,
  source_lang         CHAR(2) NOT NULL,
  target_langs        CHAR(2)[] NOT NULL,
  scope               JSONB NOT NULL,                         -- {kind:'heritage', filter:{country:'UZ'}}
  model_version_id    BIGINT NOT NULL REFERENCES ai_model_versions(id),
  fallback_chain_id   BIGINT REFERENCES ai_fallback_chains(id),
  total_segments      BIGINT,
  processed_segments  BIGINT NOT NULL DEFAULT 0,
  tm_hit_segments     BIGINT NOT NULL DEFAULT 0,
  failed_segments     BIGINT NOT NULL DEFAULT 0,
  status              TEXT NOT NULL DEFAULT 'pending',
  started_at          TIMESTAMPTZ,
  finished_at         TIMESTAMPTZ,
  triggered_by_admin_id BIGINT,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 3.20 `ai_moderation_results`

```sql
CREATE TABLE ai_moderation_results (
  id                  BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  target_kind         TEXT NOT NULL CHECK (target_kind IN
                       ('user_media','user_review','user_comment','ai_generation','heritage_content','b2b_listing')),
  target_id           BIGINT NOT NULL,                        -- polymorphic; resolved via target_kind
  generation_id       BIGINT REFERENCES ai_generations(id),   -- if moderating an AI output
  model_version_id    BIGINT NOT NULL REFERENCES ai_model_versions(id),
  -- scores (0.0–1.0)
  nsfw_score          NUMERIC(5,4),
  violence_score      NUMERIC(5,4),
  hate_score          NUMERIC(5,4),
  spam_score          NUMERIC(5,4),
  fake_geotag_score   NUMERIC(5,4),
  copyright_risk_score NUMERIC(5,4),
  prompt_injection_score NUMERIC(5,4),
  -- verdict
  verdict             TEXT NOT NULL CHECK (verdict IN ('clean','flagged','blocked','quarantine')),
  verdict_reason      TEXT[],
  threshold_set_id    BIGINT,                                 -- references admin-managed threshold config
  -- review pipeline
  requires_human_review BOOLEAN NOT NULL DEFAULT FALSE,
  reviewed_by_admin_id BIGINT,
  reviewed_at         TIMESTAMPTZ,
  final_verdict       TEXT,
  -- linkage
  user_id             BIGINT,                                 -- FK→Agent 2 (content author / generation requester)
  raw_response        JSONB,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_amr_target ON ai_moderation_results(target_kind, target_id);
CREATE INDEX idx_amr_pending_review ON ai_moderation_results(verdict, requires_human_review)
  WHERE requires_human_review = TRUE AND reviewed_at IS NULL;
CREATE INDEX idx_amr_user ON ai_moderation_results(user_id, created_at DESC);
```

### 3.21 `ai_safety_incidents`

```sql
CREATE TABLE ai_safety_incidents (
  id                  BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  incident_kind       TEXT NOT NULL,                          -- 'csam','violence','hate','self_harm','copyright','impersonation'
  severity            SMALLINT NOT NULL CHECK (severity BETWEEN 1 AND 5),
  user_id             BIGINT,                                 -- FK→Agent 2
  moderation_id       BIGINT REFERENCES ai_moderation_results(id),
  generation_id       BIGINT REFERENCES ai_generations(id),
  action_taken        TEXT,                                   -- 'content_removed','user_warned','user_banned','reported_authority'
  reported_externally BOOLEAN NOT NULL DEFAULT FALSE,
  notes               TEXT,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_asi_user ON ai_safety_incidents(user_id, created_at DESC);
```

### 3.22 `ai_prompt_injection_log`

```sql
CREATE TABLE ai_prompt_injection_log (
  id                  BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  inference_job_id    BIGINT REFERENCES ai_inference_jobs(id),
  user_id             BIGINT,
  signal_kind         TEXT NOT NULL,                          -- 'role_override','system_prompt_leak','jailbreak_pattern','sql_in_text'
  pattern_id          TEXT,                                   -- pointer to detection rule registry
  confidence          NUMERIC(5,4),
  raw_input_preview   TEXT,
  blocked             BOOLEAN NOT NULL DEFAULT FALSE,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_apil_user_recent ON ai_prompt_injection_log(user_id, created_at DESC);
```

### 3.23 `ai_token_usage` (partitioned)

```sql
CREATE TABLE ai_token_usage (
  id                  BIGINT GENERATED ALWAYS AS IDENTITY,
  usage_day           DATE NOT NULL,
  user_id             BIGINT,
  b2b_partner_id      BIGINT,
  model_version_id    BIGINT NOT NULL,
  capability          TEXT NOT NULL,
  tokens_input        BIGINT NOT NULL DEFAULT 0,
  tokens_output       BIGINT NOT NULL DEFAULT 0,
  images_processed    BIGINT NOT NULL DEFAULT 0,
  audio_seconds       NUMERIC(12,2) NOT NULL DEFAULT 0,
  request_count       BIGINT NOT NULL DEFAULT 0,
  success_count       BIGINT NOT NULL DEFAULT 0,
  failure_count       BIGINT NOT NULL DEFAULT 0,
  cost_micro_usd      BIGINT NOT NULL DEFAULT 0,
  PRIMARY KEY (usage_day, id)
) PARTITION BY RANGE (usage_day);

-- Monthly partitions, created by pg_partman
-- e.g. ai_token_usage_2026_05, ai_token_usage_2026_06 ...
CREATE INDEX idx_atu_user_day ON ai_token_usage(user_id, usage_day);
CREATE INDEX idx_atu_b2b_day ON ai_token_usage(b2b_partner_id, usage_day);
CREATE INDEX idx_atu_model_day ON ai_token_usage(model_version_id, usage_day);
```

### 3.24 `ai_cost_ledger`

```sql
CREATE TABLE ai_cost_ledger (
  id                  BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  ledger_date         DATE NOT NULL,
  account_kind        TEXT NOT NULL CHECK (account_kind IN ('user','b2b','b2g','platform','grant')),
  account_id          BIGINT,                                 -- user_id / b2b_partner_id / NULL for platform
  model_version_id    BIGINT REFERENCES ai_model_versions(id),
  capability          TEXT,
  gross_cost_micro_usd BIGINT NOT NULL DEFAULT 0,
  billable_cost_micro_usd BIGINT NOT NULL DEFAULT 0,           -- after subsidies / free-tier
  currency            CHAR(3) NOT NULL DEFAULT 'USD',
  fx_rate_to_usd      NUMERIC(20,10) NOT NULL DEFAULT 1,
  notes               TEXT,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (ledger_date, account_kind, account_id, model_version_id, capability)
);
CREATE INDEX idx_acl_billing ON ai_cost_ledger(account_kind, account_id, ledger_date);
```

> `ai_cost_ledger` is **consumed by Agent 6 (billing)** as the source-of-truth for B2B invoicing.

### 3.25 `ai_drift_metrics`

```sql
CREATE TABLE ai_drift_metrics (
  id                  BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  measured_day        DATE NOT NULL,
  model_version_id    BIGINT NOT NULL REFERENCES ai_model_versions(id),
  capability          TEXT NOT NULL,
  -- input drift
  input_kl_divergence NUMERIC(10,6),                          -- vs 30-day baseline distribution
  input_distribution_summary JSONB,
  -- output drift
  avg_confidence      NUMERIC(5,4),
  avg_confidence_delta NUMERIC(5,4),                          -- vs baseline
  output_length_p50   INT,
  output_length_p95   INT,
  -- quality proxy
  user_thumbs_up_rate NUMERIC(5,4),
  user_thumbs_down_rate NUMERIC(5,4),
  edit_rate           NUMERIC(5,4),
  -- performance
  latency_p50_ms      INT,
  latency_p95_ms      INT,
  latency_p99_ms      INT,
  failure_rate        NUMERIC(5,4),
  alert_triggered     BOOLEAN NOT NULL DEFAULT FALSE,
  alert_kind          TEXT,
  UNIQUE (measured_day, model_version_id, capability)
);
CREATE INDEX idx_adm_alerts ON ai_drift_metrics(alert_triggered, measured_day DESC) WHERE alert_triggered;
```

### 3.26 `ai_recommendation_state`

```sql
CREATE TABLE ai_recommendation_state (
  user_id             BIGINT PRIMARY KEY,                     -- FK→Agent 2
  taste_vector_e5_1024 vector(1024),                          -- centroid of last-N interactions
  taste_vector_clip_768 vector(768),                          -- visual taste
  last_recomputed_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  interaction_count   BIGINT NOT NULL DEFAULT 0,
  decay_half_life_days INT NOT NULL DEFAULT 30,
  region_affinity     JSONB NOT NULL DEFAULT '{}',            -- {'UZ-SA':0.4,'UZ-BU':0.3,...}
  category_affinity   JSONB NOT NULL DEFAULT '{}',            -- {'mosque':0.6,'archeology':0.2,...}
  language_pref       CHAR(2)[],
  cold_start          BOOLEAN NOT NULL DEFAULT TRUE,
  metadata            JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX idx_ars_taste_e5
  ON ai_recommendation_state USING hnsw (taste_vector_e5_1024 vector_cosine_ops)
  WITH (m = 16, ef_construction = 200);
```

### 3.27 `ai_user_item_interactions`

```sql
CREATE TABLE ai_user_item_interactions (
  id                  BIGINT GENERATED ALWAYS AS IDENTITY,
  user_id             BIGINT NOT NULL,
  item_kind           TEXT NOT NULL CHECK (item_kind IN ('heritage','media','route','b2b_listing')),
  item_id             BIGINT NOT NULL,
  signal_kind         TEXT NOT NULL CHECK (signal_kind IN
                       ('view','dwell','like','save','share','complete','skip','negative')),
  weight              NUMERIC(6,3) NOT NULL DEFAULT 1,
  context             JSONB,                                  -- {device, lang, region}
  occurred_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (occurred_at, id)
) PARTITION BY RANGE (occurred_at);
CREATE INDEX idx_auii_user_recent ON ai_user_item_interactions(user_id, occurred_at DESC);
CREATE INDEX idx_auii_item ON ai_user_item_interactions(item_kind, item_id, occurred_at DESC);
```

### 3.28 `ai_feedback`

```sql
CREATE TABLE ai_feedback (
  id                  BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  generation_id       BIGINT NOT NULL REFERENCES ai_generations(id) ON DELETE CASCADE,
  user_id             BIGINT,                                 -- FK→Agent 2
  signal              TEXT NOT NULL CHECK (signal IN ('thumbs_up','thumbs_down','edit','report','share')),
  rating              SMALLINT CHECK (rating BETWEEN 1 AND 5),
  edited_output       TEXT,                                   -- user-corrected → high-value fine-tuning data
  report_reason       TEXT,
  context             JSONB,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_af_gen ON ai_feedback(generation_id);
CREATE INDEX idx_af_user ON ai_feedback(user_id, created_at DESC);
CREATE INDEX idx_af_training_signal ON ai_feedback(signal) WHERE signal IN ('edit','thumbs_up');
```

---

## 4. pgvector Index Strategy

### 4.1 HNSW vs IVFFlat — the call

| Criterion | HNSW | IVFFlat |
|---|---|---|
| Build time | Slow (O(N log N), bulk requires `maintenance_work_mem` ≥ 4GB) | Fast |
| Query latency | **Excellent, stable** | Good but degrades with skewed clusters |
| Recall @ 0.95 | **Yes, tunable via `ef_search`** | Requires high `probes` (cost) |
| Update friendly | **Yes** (incremental) | Index requires retraining as data grows |
| Memory | Higher (~1.5× IVFFlat) | Lower |
| Filter combinations | **Better with partial indexes** | Worse |

**Decision: HNSW everywhere.** SilkLens is read-heavy, latency-sensitive (Roadmap: API < 500ms), continuously growing (UGC + global dataset). IVFFlat's retraining cost on a 50M-vector table is prohibitive.

### 4.2 Parameter tuning per table

| Table | `m` | `ef_construction` | `ef_search` (runtime) | Distance | Target recall@10 |
|---|---|---|---|---|---|
| `embeddings_heritage_e5_1024` | 16 | 200 | 80 | cosine | 0.97 |
| `embeddings_heritage_clip_768` | 16 | 200 | 80 | cosine | 0.97 |
| `embeddings_media_clip_768` (large, hot) | **24** | 300 | 100 | cosine | 0.98 |
| `embedding_chunks` (RAG, recall-critical) | **32** | 400 | 150 | cosine | 0.99 |
| `embeddings_queries_e5_1024` (short-lived, recall less critical) | 12 | 100 | 50 | cosine | 0.93 |
| `ai_recommendation_state` | 16 | 200 | 80 | cosine | 0.97 |
| `ai_translation_memory` | 16 | 200 | 100 | cosine | 0.98 |

`ef_search` is set **per-query** in the worker: `SET LOCAL hnsw.ef_search = 80;`. The admin panel can override per-task in `ai_fallback_chains.trigger_condition`.

### 4.3 Hybrid search (vector + tsvector via RRF)

```sql
WITH semantic AS (
  SELECT id, 1.0 / (60 + RANK() OVER (ORDER BY embedding <=> $query_vec)) AS rrf
  FROM embedding_chunks
  WHERE language = $lang AND model_version_id = $active_id
  ORDER BY embedding <=> $query_vec
  LIMIT 50
),
lexical AS (
  SELECT id, 1.0 / (60 + RANK() OVER (ORDER BY ts_rank_cd(tsv, plainto_tsquery($lang, $q)) DESC)) AS rrf
  FROM embedding_chunks
  WHERE tsv @@ plainto_tsquery($lang, $q)
  LIMIT 50
)
SELECT id, SUM(rrf) AS score
FROM (SELECT * FROM semantic UNION ALL SELECT * FROM lexical) u
GROUP BY id ORDER BY score DESC LIMIT 10;
```

A second-stage reranker (Cohere Rerank or BAAI/bge-reranker-large local) is invoked on top-50 via a `reranker` capability model — also logged to `ai_generations` for cost attribution.

### 4.4 Reindex plan at scale

- Use `CREATE INDEX CONCURRENTLY` for any reindex; never block writes.
- For very large tables (>10M rows), use **partial indexes per active `model_version_id`**: when the active model rotates, build the new partial index concurrently, swap via `ALTER … RENAME`, drop old after grace period.
- Maintenance window: nightly `REINDEX INDEX CONCURRENTLY` per shard on a rotation. Drift > 5% recall (measured against ground-truth set) triggers a forced reindex.

---

## 5. Multi-Model Embedding Architecture

**Choice: separate physical table per (target_kind, model_family, dimension).** Naming: `embeddings_<target>_<model>_<dim>`.

### Rationale (vs. one polymorphic table with `vector(N)` per row + `model_id`)

| Concern | Polymorphic single table | Separate tables (chosen) |
|---|---|---|
| Variable dim | pgvector requires fixed-dim column → not possible without `vector` per row or JSONB (kills HNSW) | Native fixed-dim columns, HNSW works |
| Index strategy | Cannot index a column whose dim varies; have to maintain N partial indexes anyway | One HNSW per table, clean |
| Query plan | Forced runtime filter on `model_id` before vector op → bad cardinality estimates | Direct table = perfect plan |
| Operational | Drop one model = mass DELETE on huge table (vacuum storm) | `DROP TABLE` of dead model — instant |
| Cross-model joins | Trivially possible (UNION via heritage_id) | Same — no loss |
| Schema cost | Lower (one table) | Higher (~6–10 tables) — mitigated by templated migration |

**Conclusion:** Separate tables. We accept the schema-count cost (managed via Alembic migration templates) in exchange for correct HNSW, clean planner, painless model retirement.

### Active models at launch (FAZA 1–2)

| Target | Model | Dim | Table |
|---|---|---|---|
| heritage description | multilingual-e5-large | 1024 | `embeddings_heritage_e5_1024` |
| heritage image (cover) | CLIP-ViT-L/14 | 768 | `embeddings_heritage_clip_768` |
| media (photos) | CLIP-ViT-L/14 | 768 | `embeddings_media_clip_768` |
| UGC text | multilingual-e5-large | 1024 | `embeddings_user_content_e5_1024` |
| user queries | multilingual-e5-base | 768 | `embeddings_queries_e5_768` |
| RAG chunks | multilingual-e5-large | 1024 | `embedding_chunks.embedding_e5_1024` |

### Adding a future model (e.g. SilkLens-VLM, FAZA 7, dim 1536)

1. Admin registers in `ai_model_versions` (dim=1536, status='staging').
2. Migration creates `embeddings_heritage_silklens_1536` table + HNSW index.
3. `embedding_regeneration_jobs` row created, Celery workers backfill.
4. On reaching N% coverage, admin sets new model as default; old table remains until traffic drains.
5. Old table deprecated → archived (export to MinIO) → dropped.

---

## 6. RAG Chunking

### Chunking strategy per content kind

| Source kind | Chunk size (tokens) | Overlap | Splitter | Notes |
|---|---|---|---|---|
| Heritage long description | 400 | 80 | Recursive (paragraph → sentence) | Preserve `period`, `region_code` in every chunk |
| Wikipedia article | 512 | 100 | Section-aware (h2 / h3) | Section title prepended to chunk text |
| Expert notes (PDF / DOCX) | 350 | 75 | Layout-aware via `unstructured.io` | Tables → markdown; figures → caption-only |
| UNESCO PDFs | 512 | 100 | Page-then-paragraph | Page number stored in `metadata` |
| B2B listing | 256 | 50 | Single-pass | Short content |
| Audio guide script | 400 | 80 | Sentence | Carries `tts_voice` for round-trip |

Every chunk row carries: `source_url`, `language`, `heritage_id`, `period`, `region_code`, `tags`, `confidence_score`, `chunk_index`, `char_start`, `char_end`. Filtered retrieval is index-supported (`idx_ec_filter`).

### Reembedding policy

- `source_hash` changes → chunk row re-embedded in place (idempotent upsert).
- Model upgrade → `embedding_regeneration_jobs` walks the table by primary key in batches of 1000.
- Language added (Decisions §42) → new chunk rows are created (chunks are language-scoped).

---

## 7. Inference Pipeline

### 7.1 Celery topology

```
queues:
  ai.vision.realtime       priority=9   workers=GPU      concurrency=2      max_runtime=10s
  ai.vision.batch          priority=4   workers=GPU      concurrency=4      max_runtime=120s
  ai.tts                   priority=6   workers=GPU      concurrency=2      max_runtime=60s
  ai.translation           priority=5   workers=GPU+CPU  concurrency=8      max_runtime=30s
  ai.embedding.text        priority=5   workers=GPU      concurrency=16     batch=32
  ai.embedding.image       priority=5   workers=GPU      concurrency=8      batch=16
  ai.chat                  priority=7   workers=API      concurrency=32     max_runtime=60s
  ai.moderation            priority=8   workers=GPU      concurrency=8      max_runtime=10s
  ai.rag                   priority=6   workers=CPU      concurrency=16     max_runtime=15s
  ai.batch_long            priority=2   workers=GPU      concurrency=1      max_runtime=3600s
  ai.dead_letter           manual replay only
```

### 7.2 Job lifecycle

```
client request
   │  computes idempotency_key = sha256(input_hash + model_resolved + params + user_scope)
   ▼
INSERT ai_inference_jobs (status='queued') — UNIQUE on idempotency_key returns existing row if dup
   │
   ▼
Celery picks up → SET status='running', started_at=now(), trace_id from OTel
   │
   ├── try resolved_model_version_id
   │     ├── success → status='succeeded', write ai_generations, ai_cache, ai_token_usage roll-up
   │     ├── timeout/error → status='retrying', schedule next attempt, next_retry_at = now + 2^attempt seconds
   │     └── exceeded max_attempts → walk ai_fallback_chains.position+1
   │           ├── fallback succeeded → status='succeeded', parent_job_id = original
   │           └── all fallbacks exhausted → status='dead_letter'
   ▼
post-success hooks:
   • mandatory moderation for user-visible outputs (chained job)
   • ai_token_usage upsert (current-day partition)
   • OTel span closed; metrics emitted
```

### 7.3 Idempotency & retry semantics

- `idempotency_key` is UNIQUE → duplicate user request short-circuits to the existing job result (no double-cost).
- Transient errors (network, 429, GPU OOM) → exponential backoff with jitter, max 3 attempts.
- Permanent errors (4xx schema, content-policy block) → no retry, straight to `failed` and surface to client.
- DLQ is `status='dead_letter'`; replayable via admin panel after fix.

---

## 8. AI Cache & Deduplication

### 8.1 Keying

```
cache_key = sha256(
  input_canonical_hash      // for images: perceptual hash; for text: trimmed+normalised sha256
  + ':' + model_version_id
  + ':' + params_hash         // sha256(sorted JSON of params: temp, top_p, voice_id, lang_pair)
  + ':' + prompt_template_version_id  // 0 if N/A
)
```

For images, `input_canonical_hash` uses **pHash (64-bit)** rather than file sha256 — so the same monument photographed twice (slightly different framing, exposure) hits the same cache entry. Threshold: Hamming distance ≤ 5 against `ai_perceptual_hash_index`.

### 8.2 Tiering

- **L1 — Redis** (hot, 10GB, LRU): keyed by `cache_key`, value = compact JSON / blob pointer. TTL = 7 days.
- **L2 — PostgreSQL `ai_cache`**: persistent, survives Redis flush.
- **L3 — MinIO** (artifacts): TTS audio, large JSON outputs; `output_ref` points here.

### 8.3 Invalidation

- Model version `status='deprecated'` → background job deletes rows from `ai_cache WHERE model_version_id = X` and corresponding Redis keys.
- Prompt template version retired → cache rows referencing that prompt version are purged.
- Source content changed (heritage description edited by admin) → cache for downstream generations using that heritage as context is invalidated via tag-based purge (tags stored on `ai_generations` for traceability).

---

## 9. AI Observability

### 9.1 Metrics tables

- `ai_drift_metrics` — daily roll-up per (model, capability).
- `ai_token_usage` — daily partition, the cardinal feed for Grafana.
- `ai_inference_jobs` — recent rows feed real-time p50/p95/p99 via materialised view refreshed every 60s:

```sql
CREATE MATERIALIZED VIEW mv_ai_perf_5m AS
SELECT
  resolved_model_version_id,
  task_kind,
  date_trunc('minute', finished_at) AS bucket,
  count(*) FILTER (WHERE status='succeeded') AS ok,
  count(*) FILTER (WHERE status IN ('failed','dead_letter')) AS err,
  percentile_disc(0.5)  WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM finished_at-started_at)*1000) AS p50_ms,
  percentile_disc(0.95) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM finished_at-started_at)*1000) AS p95_ms,
  percentile_disc(0.99) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM finished_at-started_at)*1000) AS p99_ms,
  sum(coalesce(cost_micro_usd,0)) AS cost_micro_usd
FROM ai_inference_jobs
WHERE finished_at > now() - interval '6 hours'
GROUP BY 1,2,3;
CREATE UNIQUE INDEX ON mv_ai_perf_5m (resolved_model_version_id, task_kind, bucket);
```

### 9.2 Drift detection

- **Input drift**: nightly job computes KL-divergence of input embedding distribution vs 30-day baseline → `ai_drift_metrics.input_kl_divergence`. Threshold > 0.15 → alert.
- **Output drift**: average confidence delta > 0.05 or avg output length shift > 25% → alert.
- **Quality proxy**: thumbs-up rate drop > 10 percentage points over 7 days → alert.
- All alerts go to `ai_drift_metrics.alert_triggered` and into Grafana via Alertmanager.

### 9.3 OpenTelemetry contract

Every inference job emits a span tree:
```
silklens.ai.inference (parent)
  ├── ai.cache_lookup
  ├── ai.provider_call(provider=anthropic,model=claude-sonnet-4.7)
  ├── ai.moderation_check
  └── ai.persist
```
`trace_id` is stored on `ai_inference_jobs` and `ai_generations` for cross-system join (logs ⇄ DB ⇄ Grafana).

---

## 10. Translation Memory

### 10.1 Lookup pipeline (Decisions §42)

```
1. exact match: SELECT … WHERE source_lang, target_lang, source_hash
2. fuzzy match: HNSW on source_embedding (cosine), threshold ≥ 0.92 similarity
3. NLLB-200 local generation
4. If BLEU/COMET below threshold → DeepL fallback
5. If still low → Google Translate fallback
6. UPSERT into ai_translation_memory with model_version_id, scores
```

### 10.2 Approval flow

- BLEU ≥ 0.80 (auto): `status='auto_approved'` → live.
- 0.50–0.80: `status='pending'` → admin review queue.
- < 0.50: blocked, requires human.

Admin edits in panel write to TM directly with `status='approved'` and `approved_by_admin_id` — these become the highest-priority training data for FAZA 7 fine-tune (§13).

---

## 11. Recommendation Engine

### 11.1 Hybrid model

```
final_score(user, item) =
    α · cosine(taste_vector, item_vector)            // content-based
  + β · CF_score(user, item)                          // collaborative
  + γ · popularity_decay(item)                        // global signal
  + δ · region_affinity(user, item.region)
  + ε · category_affinity(user, item.category)
```

Coefficients α…ε are admin-tunable in a config row; A/B-tested via `prompt_template_experiments`-style mechanism.

### 11.2 Taste vector update

A streaming worker consumes `ai_user_item_interactions` (Redis stream mirror), updates `ai_recommendation_state.taste_vector_e5_1024` via exponential moving average:

```
taste_new = (1 - λ) * taste_old + λ * item_embedding * signal_weight
```

`λ` derived from `decay_half_life_days`. Cold-start uses category/region affinity until `interaction_count > 10`.

### 11.3 CF table

`ai_user_item_interactions` is partitioned monthly. ALS-style CF runs nightly on the last 90 days into a separate `ai_cf_factors` table (user_factor vector, item_factor vector) — not detailed here but mirrors `ai_recommendation_state` shape.

---

## 12. AI Safety & Moderation

### 12.1 Mandatory moderation paths

| Artifact | Moderation kind | Blocking? |
|---|---|---|
| User-uploaded photo | NSFW + violence + fake-geotag | Yes (Decisions §11) |
| User review/comment | Spam + hate + advertisement | Yes |
| AI-generated heritage description | Hallucination check + safety | Block if `verdict='blocked'` |
| AI chat response | Safety + prompt-injection back-reflection | Block if `verdict='blocked'` |
| B2B listing | Spam + copyright | Yes |

### 12.2 Threshold management

Admin-managed `moderation_threshold_sets` (referenced by `ai_moderation_results.threshold_set_id`) — per Decisions §11 thresholds are dynamic. Examples:

```json
{
  "nsfw":          { "block": 0.85, "flag": 0.60 },
  "violence":      { "block": 0.80, "flag": 0.55 },
  "fake_geotag":   { "block": 0.90, "flag": 0.70 },
  "prompt_injection": { "block": 0.75, "flag": 0.50 }
}
```

### 12.3 User trust linkage

Moderation outcomes feed `users.trust_score` (Agent 2's domain) via daily aggregation. Three confirmed safety incidents → automatic ban pipeline.

### 12.4 Prompt-injection detection

`ai_prompt_injection_log` is populated by:
- regex/rule-based prefilter (system-prompt leak patterns, role overrides),
- model-based classifier (small distilled model running on every chat input),
- output back-reflection (does the response contain system prompt fragments?).

Confirmed injections → safety incident + block + log to user trust.

---

## 13. Future Fine-Tuning Dataset (FAZA 7)

Per Roadmap FAZA 7 a SilkLens-specific model will be fine-tuned. The schema captures training data **continuously from day one**:

### 13.1 Training-eligible signals

A nightly job sets `ai_generations.training_eligible = TRUE` when:
- moderation `verdict = 'clean'`, AND
- at least one of:
  - `ai_feedback.signal = 'thumbs_up'` from a trusted user (trust_score ≥ T),
  - `ai_feedback.signal = 'edit'` (the edited output is the gold label),
  - admin manually approved the output via `ai_translation_memory.status='approved'` (translations),
  - user dwell-time on the heritage page exceeds median × 1.5 (passive positive signal).

### 13.2 Curated export

`ai_training_export_jobs` (added as needed) snapshots eligible rows to MinIO in HuggingFace `datasets` format. Each export is reproducible because every row carries `model_version_id` + `prompt_template_version_id`, allowing precise filtering ("only outputs from Claude Sonnet 4.7 with prompt v12").

### 13.3 Privacy

- User PII (emails, names) is stripped at export time via a documented redaction pipeline.
- Per Decisions §36 (GDPR), users can request deletion → their generations are flagged `training_eligible=FALSE` and excluded from future exports; already-exported snapshots are retained for legal model audit but flagged.

---

## 14. Risks & Open Questions

### 14.1 Top operational risks

1. **HNSW reindex on 50M+ vectors blocks `maintenance_work_mem` for hours.**
   *Mitigation:* partial indexes per `model_version_id` so the active-model index stays small; pre-sized `maintenance_work_mem` (≥ 8GB) on a dedicated reindex follower; reindex during off-peak window with `CONCURRENTLY`.

2. **GPU saturation on RTX 4090 — single point of contention.**
   *Mitigation:* per-queue concurrency limits (§7.1); priority-queue starvation guard; admin can flip fallback chain to cloud API with one click (Decisions §5); plan for second GPU node in FAZA 5.

3. **Cost runaway via prompt-injection or recursive AI chat.**
   *Mitigation:* `ai_rate_limits` per-user; `ai_cost_ledger` hard caps; circuit breaker that disables paid providers when daily budget exceeded.

4. **Cache poisoning via near-duplicate perceptual hash collisions.**
   *Mitigation:* Hamming threshold tuned conservatively (≤ 5); secondary verification by feature embedding similarity > 0.95; manual purge path for admin.

5. **Multi-model embedding fragmentation — operational sprawl as table count grows.**
   *Mitigation:* templated migrations (Alembic generator from `(target, model, dim)` triple); enforced naming convention; deprecation tooling that audits unused tables monthly.

6. **Translation memory drift — old TM rows from inferior model linger and lower quality.**
   *Mitigation:* TM rows track `model_version_id`; admin panel can mass-supersede rows from a deprecated model; background re-translation job for high-traffic segments.

7. **Recommendation cold start.**
   *Mitigation:* region+category affinity + content-based vector similarity carries new users for the first ~10 interactions; explicit onboarding preferences (Decisions §22).

8. **`ai_generations` table grows unboundedly (~10M rows/day at scale).**
   *Mitigation:* range-partition by `created_at` monthly (same pattern as `ai_token_usage`); tier-archive partitions older than 18 months to Parquet on MinIO; keep `ai_cost_ledger` hot.

### 14.2 Open questions for the team

- **Q1.** Do we run pgvector on the same PG cluster as transactional data, or on a dedicated read-replica with logical replication? *Recommendation:* dedicated read-replica from FAZA 4 onward, primary writes go through a coordinator that fans out.
- **Q2.** Should `embedding_chunks` move to a dedicated PG cluster once it crosses 100M rows, or to a specialised store (Qdrant, Milvus)? *Recommendation:* stay on pgvector until 100M, decision point at FAZA 6.
- **Q3.** Reranker model — local (BGE) vs cloud (Cohere)? Benchmark in FAZA 4 alongside vision/TTS benchmarks (Decisions §5 framework reused).
- **Q4.** TM fuzzy match — segment-level vector OR sentence-piece overlap? Pilot both in FAZA 2.
- **Q5.** Feedback loop on auto-approved translations — currently auto-approve at BLEU ≥ 0.80, but should we require N user-views without complaint before locking? *Open.*
- **Q6.** GDPR right-to-be-forgotten interaction with `ai_generations` immutability — define a tombstone protocol that nullifies PII fields without breaking referential integrity.

---

## 15. Cross-Agent Dependency Contracts

| Field | Source agent | Consumer (this agent) |
|---|---|---|
| `heritages.id` (BIGINT) | **Agent 1** | `embeddings_heritage_*`, `embedding_chunks`, `ai_perceptual_hash_index`, `ai_moderation_results` |
| `users.id`, `users.trust_score` | **Agent 2** | `ai_generations`, `ai_token_usage`, `ai_feedback`, `ai_user_item_interactions`, `ai_recommendation_state`, `ai_safety_incidents` |
| `media.id` | **Agent 4** | `embeddings_media_*`, `ai_perceptual_hash_index`, `ai_moderation_results` |
| `b2b_partners.id` | **Agent 6** | `ai_token_usage`, `ai_cost_ledger`, `ai_inference_jobs` |
| `admin_users.id` | **Agent 2** | `ai_fallback_chains`, `prompt_templates`, `ai_model_benchmarks`, `embedding_regeneration_jobs`, `ai_translation_memory` |

**Outputs this agent provides to others:**
- `ai_cost_ledger` → **Agent 6 (billing)** for B2B invoicing.
- `ai_moderation_results` → **Agent 2 (trust)** for user trust scoring and ban pipeline.
- `ai_recommendation_state` → **Agent 1 (heritage UX)** for personalised feeds.
- `ai_translation_memory` → **Agent 1 (content)** for multilingual rendering.
- `embeddings_*` → all agents needing semantic search APIs.

---

*End of document — Agent 3.*
