# Agent 7 — Infrastructure, Analytics & Event Architecture

> **Scope:** Event bus, transactional outbox, durable event log, notifications (in-app/email/SMS/push), search indexing (Elasticsearch, 200 languages), analytics pipeline (ClickHouse), background jobs (Celery), observability (traces/metrics/incidents), outbound webhooks.
>
> **Target scale (v1.0 → 12-month plan):** 1M MAU growing to 10M, ~5k req/s peak API, ~50k events/s peak, 500k landmarks × 200 languages = 100M ES documents, 10B analytics events/year.
>
> **Cross-agent boundaries:**
> - Agent 2 owns `audit_log` for **security/admin/PII access**. Agent 7 owns `event_log` for **domain/system events**. Both share `trace_id` for correlation.
> - Agent 3 (AI) emits events into the outbox after each inference.
> - Agent 5 (UGC/social) triggers notification fan-out via this layer.
> - Agent 6 (billing) calls the dunning notification API exposed here.

---

## 1. Domain Analysis (event-driven backbone)

SilkLens is a distributed, multi-region cultural-heritage platform that must reconcile three competing realities:

1. **Strong-consistency truths** (payments, account state, content publication) live in PostgreSQL.
2. **High-throughput, ephemeral truths** (clicks, AI inferences, GPS pings, landmark views) live in ClickHouse.
3. **Fan-out side-effects** (push, email, SMS, webhooks, search re-index, leaderboard recalc) must execute *exactly-once-from-the-user's-perspective* even though the underlying infrastructure is at-least-once.

The **only** sustainable way to glue these together is an **append-only event log** in Postgres (durable, transactionally consistent with business writes) bridged into a streaming bus (Redpanda) which fans out to consumers. Postgres `LISTEN/NOTIFY` is **explicitly rejected** as the bus because:

- It is fire-and-forget (no replay, no consumer offsets, no DLQ).
- Notifications are dropped if no listener is connected at the moment of emission.
- 8 kB payload limit; no partitioning; no horizontal consumer scaling.
- Cross-region replication is not supported.

We therefore adopt the **Transactional Outbox + Log-Tailing Reaper** pattern: every business write that triggers a side-effect performs *two* inserts in the same transaction (the business row + an `event_outbox` row). A dedicated reaper service (using logical replication or polling with `FOR UPDATE SKIP LOCKED`) drains the outbox into Redpanda. This gives us **at-least-once delivery with no dual-write inconsistency**.

The same backbone serves three orthogonal concerns:

- **Notifications** (in-app, email, SMS, push) — consumers of domain events.
- **Search indexing** — Elasticsearch is a *downstream materialised view* of Postgres, kept in sync by a CDC consumer (Debezium → Kafka Connect sink or an outbox-driven worker).
- **Analytics** — high-volume events (`landmark_viewed`, `audio_played`, `ar_opened`) skip the outbox and write directly to a raw-events sink (`analytics_events_raw`) that is streamed to ClickHouse and TTL'd from Postgres after 7 days.

Observability is **first-class data**, not an afterthought: incidents, alerts, uptime snapshots, release versions, and feature-flag evaluations are all DB-modelled so the admin panel can query them like any other resource. `trace_id` is propagated end-to-end (OpenTelemetry) and stamped onto every row in `event_log`, `audit_log`, `notification_delivery_log`, and `webhook_deliveries` so we can stitch a single user request across 12 services in Grafana Tempo.

The design is opinionated about three principles:

1. **Idempotency is the contract.** Every consumer must accept `(event_id, consumer_name)` as a uniqueness key, persisted in `event_consumer_offsets`. Re-delivery is *expected*.
2. **Backpressure is observable.** Outbox lag, ES indexing lag, ClickHouse ingest lag, Celery queue depth, and webhook retry depth are all surfaced as Prometheus gauges and as DB rows so the admin panel renders them.
3. **Replay is a feature.** The event_log is partitioned monthly and retained for 90 days hot / 2 years cold (S3 Parquet via `pg_parquet`), so any consumer can rebuild state by replaying.

---

## 2. Entity Discovery Report

The infra/analytics/events domain comprises **47 tables**, grouped into 10 sub-domains:

### 2.1 Event Sourcing Primitives
- `event_types` — admin-managed catalog of every event type the system can emit
- `event_log` — durable, append-only, monthly-partitioned canonical event store
- `event_outbox` — transactional outbox (drained then deleted)
- `event_subscribers` — registry of services that consume which event types
- `event_consumer_offsets` — per-consumer position + idempotency
- `dead_letter_events` — events that exhausted retries
- `event_replay_jobs` — admin-triggered replays for backfills/recovery

### 2.2 Notifications (multi-channel)
- `notification_templates` — multilingual, per-channel templates
- `notification_template_variants` — A/B variants with traffic weights
- `notifications` — logical notifications (one per user-facing message)
- `notification_preferences` — per-user × per-category × per-channel opt-in/out
- `notification_quiet_hours` — per-user, timezone-aware do-not-disturb
- `notification_delivery_log` — partitioned per-attempt log
- `notification_bounces` — hard/soft bounces, used to auto-disable channels
- `notification_categories` — admin-managed (e.g. `marketing`, `transactional`, `security`)
- `in_app_notifications_inbox` — per-user inbox materialisation

### 2.3 Push
- `push_devices` — FCM + APNS tokens per user × device
- `push_segments` — admin-defined user cohorts (saved queries)
- `push_campaigns` — scheduled/triggered campaigns
- `push_campaign_targets` — materialised target list per campaign
- `push_receipts` — FCM/APNS receipt callbacks

### 2.4 Email & SMS
- `email_messages` — outbound queue + status
- `email_bounces` — provider-reported bounces
- `email_providers` — admin registry (SendGrid, SES, local SMTP)
- `sms_messages` — outbound SMS queue
- `sms_providers` — admin registry (Eskiz, Twilio, Vonage)
- `sms_delivery_reports` — provider DLR webhooks

### 2.5 Outbound Webhooks (partner integrations)
- `webhooks_outbound` — partner subscription endpoints
- `webhook_deliveries` — every attempt with retry metadata
- `webhook_secrets` — rotation-aware signing keys

### 2.6 Search Indexing
- `search_index_mappings` — per-language ES index config (analyzer, stemmer, synonyms)
- `search_indexing_jobs` — bulk reindex jobs with progress
- `search_sync_outbox` — rows pending push to ES
- `search_query_log` — anonymised query log
- `search_zero_results` — queries that returned 0 hits (gap analysis)
- `search_synonyms` — admin-curated synonyms per language

### 2.7 Background Jobs (Celery + cron)
- `cron_schedules` — admin-managed periodic schedules
- `cron_runs` — execution history with drift measurement
- `celery_tasks_mirror` — durable mirror of in-flight Celery tasks
- `background_jobs` — generic on-demand jobs (idempotent)
- `job_retries` — retry history per job

### 2.8 Analytics Pipeline
- `analytics_events_raw` — short-TTL sink before ClickHouse ingest
- `analytics_sessions` — session boundaries (computed)
- `analytics_funnels` — admin-defined funnel definitions
- `feature_usage` — per-feature per-segment usage rollups

### 2.9 Observability
- `trace_spans` — sampled OpenTelemetry spans (for correlation only; full data in Tempo)
- `incidents` — production incident records
- `alerts` — Grafana alert acks and routing
- `uptime_snapshots` — UptimeRobot pings rolled into Postgres
- `release_versions` — every deploy registered here

### 2.10 Feature Flags
- `feature_flag_evaluations` — sampled evaluations for analytics

---

## 3. Full Table-by-Table Specification

> Conventions: every table has `created_at TIMESTAMPTZ DEFAULT now()`, `updated_at TIMESTAMPTZ`. PKs are `BIGINT GENERATED ALWAYS AS IDENTITY` unless stated. `trace_id UUID` is present wherever a request context exists. RLS is applied via Agent 2's tenant key where multi-tenancy applies.

### 3.1 `event_types` — catalog of emittable events

```sql
CREATE TABLE event_types (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  type_key        TEXT NOT NULL UNIQUE,                 -- e.g. 'landmark.published.v1'
  domain          TEXT NOT NULL,                        -- e.g. 'content','billing','ai','social'
  version         INT  NOT NULL DEFAULT 1,
  json_schema     JSONB NOT NULL,                       -- JSON Schema for payload validation
  is_pii          BOOLEAN NOT NULL DEFAULT false,       -- if true, payload must be anonymised in analytics sink
  retention_days  INT NOT NULL DEFAULT 90,
  partition_topic TEXT NOT NULL,                        -- which Redpanda topic
  is_active       BOOLEAN NOT NULL DEFAULT true,
  description     TEXT,
  created_by      BIGINT REFERENCES users(id),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON event_types (domain, is_active);
```

Every event in the system must reference one of these rows. Adding a new event type is an **admin-panel operation** (with schema validation) — no code deploy required for catalog metadata, though emitting services must already know how to populate the payload.

### 3.2 `event_log` — durable append-only canonical store

```sql
CREATE TABLE event_log (
  id              UUID NOT NULL DEFAULT gen_random_uuid(),
  occurred_at     TIMESTAMPTZ NOT NULL,
  type_key        TEXT NOT NULL,
  type_version    INT  NOT NULL,
  aggregate_type  TEXT NOT NULL,                         -- 'user','landmark','subscription'…
  aggregate_id    TEXT NOT NULL,                         -- string to allow non-int IDs
  actor_user_id   BIGINT,                                -- nullable for system events
  actor_kind      TEXT NOT NULL,                         -- 'user','admin','system','partner','ai'
  trace_id        UUID,
  span_id         UUID,
  correlation_id  UUID,                                  -- groups related events
  causation_id    UUID,                                  -- the event that caused this one
  payload         JSONB NOT NULL,
  payload_hash    BYTEA NOT NULL,                        -- sha256 for dedup
  source_service  TEXT NOT NULL,
  source_version  TEXT NOT NULL,
  ip_hash         BYTEA,                                 -- anonymised
  user_agent_hash BYTEA,                                 -- anonymised
  ingested_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (occurred_at, id)
) PARTITION BY RANGE (occurred_at);

-- Monthly partitions, created by pg_partman
-- Indexes per partition:
--   (aggregate_type, aggregate_id, occurred_at DESC)
--   (type_key, occurred_at DESC)
--   (actor_user_id, occurred_at DESC) WHERE actor_user_id IS NOT NULL
--   (correlation_id) WHERE correlation_id IS NOT NULL
--   GIN (payload jsonb_path_ops)
```

**Why partition monthly?** At 50k events/s peak we expect 100B rows/year. A single hash-partitioned table cannot DROP old data cheaply. Monthly RANGE partitions allow O(1) `DETACH PARTITION` after archival to S3 Parquet.

**Append-only enforcement:** `REVOKE UPDATE, DELETE ON event_log FROM PUBLIC` + a `BEFORE UPDATE` trigger raising an exception. Even superuser is forbidden in production.

### 3.3 `event_outbox` — transactional outbox

```sql
CREATE TABLE event_outbox (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  event_id        UUID NOT NULL,                         -- same as event_log.id
  type_key        TEXT NOT NULL,
  partition_topic TEXT NOT NULL,
  partition_key   TEXT NOT NULL,                         -- aggregate_id or user_id, for Kafka partitioning
  payload         JSONB NOT NULL,
  headers         JSONB NOT NULL DEFAULT '{}',
  trace_id        UUID,
  enqueued_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  picked_at       TIMESTAMPTZ,                           -- set by reaper when claimed
  picked_by       TEXT,                                  -- reaper worker id
  published_at    TIMESTAMPTZ,
  attempt_count   INT NOT NULL DEFAULT 0,
  last_error      TEXT
);
CREATE INDEX ON event_outbox (enqueued_at) WHERE published_at IS NULL;
CREATE INDEX ON event_outbox (picked_at) WHERE picked_at IS NOT NULL AND published_at IS NULL;
```

The reaper polls every 100ms with `FOR UPDATE SKIP LOCKED LIMIT 500`, publishes to Redpanda, then deletes the row (or marks `published_at` and lets a daily reaper hard-delete). **Published outbox rows are deleted**, not retained — the canonical store is `event_log`. The outbox is a queue, not history.

### 3.4 `event_subscribers` & `event_consumer_offsets`

```sql
CREATE TABLE event_subscribers (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  consumer_name   TEXT NOT NULL UNIQUE,                  -- 'notification-router','es-indexer','clickhouse-sink'
  subscribed_types TEXT[] NOT NULL,                      -- pattern: ['landmark.*','user.created.v1']
  consumer_group  TEXT NOT NULL,
  is_active       BOOLEAN NOT NULL DEFAULT true,
  config          JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE event_consumer_offsets (
  consumer_name   TEXT NOT NULL,
  partition_topic TEXT NOT NULL,
  partition_id    INT  NOT NULL,
  last_offset     BIGINT NOT NULL,
  last_event_id   UUID NOT NULL,
  processed_at    TIMESTAMPTZ NOT NULL,
  PRIMARY KEY (consumer_name, partition_topic, partition_id)
);
```

Also serves as the **idempotency table** — consumers `INSERT … ON CONFLICT DO NOTHING` keyed on `(consumer_name, event_id)` before processing, and skip if already present. (For high-volume consumers, a separate `event_consumer_dedup` Redis bloom filter is layered on top, with this table as ground truth.)

### 3.5 `dead_letter_events`

```sql
CREATE TABLE dead_letter_events (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  event_id        UUID NOT NULL,
  consumer_name   TEXT NOT NULL,
  type_key        TEXT NOT NULL,
  payload         JSONB NOT NULL,
  error_message   TEXT NOT NULL,
  error_kind      TEXT NOT NULL,                         -- 'transient','poison','schema'
  attempt_count   INT NOT NULL,
  first_failed_at TIMESTAMPTZ NOT NULL,
  last_failed_at  TIMESTAMPTZ NOT NULL,
  resolved_at     TIMESTAMPTZ,
  resolved_by     BIGINT REFERENCES users(id),
  resolution      TEXT,                                  -- 'replayed','discarded','manual_fix'
  UNIQUE (event_id, consumer_name)
);
```

Admin panel exposes a DLQ inspector: filter by consumer, view payload, "Replay" or "Discard" with audit trail.

### 3.6 `event_replay_jobs`

```sql
CREATE TABLE event_replay_jobs (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  consumer_name   TEXT NOT NULL,
  from_ts         TIMESTAMPTZ NOT NULL,
  to_ts           TIMESTAMPTZ NOT NULL,
  type_filter     TEXT[],
  aggregate_filter JSONB,
  status          TEXT NOT NULL DEFAULT 'pending',
  progress_pct    NUMERIC(5,2) DEFAULT 0,
  events_replayed BIGINT NOT NULL DEFAULT 0,
  created_by      BIGINT REFERENCES users(id),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at     TIMESTAMPTZ
);
```

### 3.7 `notification_categories` & `notification_templates`

```sql
CREATE TABLE notification_categories (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  category_key    TEXT NOT NULL UNIQUE,                  -- 'security','marketing','transactional','social'
  is_transactional BOOLEAN NOT NULL DEFAULT false,       -- transactional cannot be opted out of
  default_channels TEXT[] NOT NULL,                      -- ['email','push','in_app']
  description     TEXT
);

CREATE TABLE notification_templates (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  template_key    TEXT NOT NULL,                         -- 'welcome','dunning_day_3','new_landmark_nearby'
  category_id     BIGINT NOT NULL REFERENCES notification_categories(id),
  channel         TEXT NOT NULL,                         -- 'email','sms','push','in_app','webhook'
  locale          TEXT NOT NULL,                         -- 'uz','ru','en','zh',… (BCP 47)
  subject         TEXT,                                  -- email only
  body_template   TEXT NOT NULL,                         -- Jinja2 / Handlebars
  push_title      TEXT,
  push_body       TEXT,
  push_data       JSONB,
  is_active       BOOLEAN NOT NULL DEFAULT true,
  version         INT NOT NULL DEFAULT 1,
  created_by      BIGINT REFERENCES users(id),
  UNIQUE (template_key, channel, locale, version)
);
```

When a notification event arrives, the router picks the template by `(template_key, channel, user.preferred_locale)`, falling back to English, falling back to the closest available locale (using ICU locale negotiation).

### 3.8 `notification_template_variants` — A/B testing

```sql
CREATE TABLE notification_template_variants (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  template_id     BIGINT NOT NULL REFERENCES notification_templates(id),
  variant_key     TEXT NOT NULL,                         -- 'A','B','control'
  body_template   TEXT NOT NULL,
  push_title      TEXT,
  push_body       TEXT,
  traffic_weight  NUMERIC(5,2) NOT NULL,                 -- 0–100
  experiment_id   BIGINT,                                -- nullable; links to experiments table
  is_active       BOOLEAN NOT NULL DEFAULT true,
  UNIQUE (template_id, variant_key)
);
```

### 3.9 `notification_preferences`

```sql
CREATE TABLE notification_preferences (
  user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  category_id     BIGINT NOT NULL REFERENCES notification_categories(id),
  channel         TEXT NOT NULL,                         -- email/sms/push/in_app
  enabled         BOOLEAN NOT NULL DEFAULT true,
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, category_id, channel)
);
```

Resolution algorithm:
1. If `category.is_transactional = true` → always send (legally required).
2. Else look up explicit pref; if missing → use `category.default_channels`.
3. If global "do not disturb" toggle on user → suppress unless transactional.
4. Apply quiet hours.

### 3.10 `notification_quiet_hours`

```sql
CREATE TABLE notification_quiet_hours (
  user_id         BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  enabled         BOOLEAN NOT NULL DEFAULT false,
  start_local     TIME NOT NULL DEFAULT '22:00',
  end_local       TIME NOT NULL DEFAULT '08:00',
  timezone        TEXT NOT NULL,                         -- IANA, e.g. 'Asia/Tashkent'
  suppress_channels TEXT[] NOT NULL DEFAULT '{push,sms}',
  defer_until_morning BOOLEAN NOT NULL DEFAULT true,     -- if true, queue & send at end_local
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Timezone math:** evaluated at *delivery time*, not at *send time*, using the user's stored IANA timezone. If quiet hours apply and `defer_until_morning = true`, the notification's `scheduled_for` is set to `(today_or_tomorrow at end_local in user's TZ)` and re-queued.

### 3.11 `notifications` & `notification_delivery_log`

```sql
CREATE TABLE notifications (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id         BIGINT NOT NULL REFERENCES users(id),
  template_id     BIGINT NOT NULL REFERENCES notification_templates(id),
  variant_id      BIGINT REFERENCES notification_template_variants(id),
  category_id     BIGINT NOT NULL REFERENCES notification_categories(id),
  source_event_id UUID,                                  -- which event triggered this
  context         JSONB NOT NULL DEFAULT '{}',           -- merge vars
  channels        TEXT[] NOT NULL,                       -- ['push','email']
  status          TEXT NOT NULL DEFAULT 'pending',       -- pending/scheduled/sent/partially_sent/suppressed/failed
  scheduled_for   TIMESTAMPTZ,                           -- null = now
  trace_id        UUID,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE notification_delivery_log (
  id              BIGINT GENERATED ALWAYS AS IDENTITY,
  notification_id BIGINT NOT NULL,
  channel         TEXT NOT NULL,
  provider        TEXT NOT NULL,                         -- 'sendgrid','fcm','apns','eskiz'
  provider_msg_id TEXT,
  attempt         INT NOT NULL,
  status          TEXT NOT NULL,                         -- queued/sent/delivered/opened/clicked/bounced/failed
  error_code      TEXT,
  error_message   TEXT,
  occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (occurred_at, id)
) PARTITION BY RANGE (occurred_at);
-- monthly partitions
```

### 3.12 `notification_bounces`

```sql
CREATE TABLE notification_bounces (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id         BIGINT REFERENCES users(id),
  channel         TEXT NOT NULL,
  address         TEXT NOT NULL,                         -- email/phone/token
  bounce_kind     TEXT NOT NULL,                         -- 'hard','soft','complaint','unsubscribe'
  provider        TEXT NOT NULL,
  provider_payload JSONB,
  occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  auto_disabled   BOOLEAN NOT NULL DEFAULT false
);
CREATE INDEX ON notification_bounces (user_id, channel, occurred_at DESC);
```

Hard bounce → auto-disable channel in `notification_preferences` after 1 hit; soft → after 3 hits in 7 days.

### 3.13 `push_devices`

```sql
CREATE TABLE push_devices (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  platform        TEXT NOT NULL,                         -- 'ios','android','web'
  provider        TEXT NOT NULL,                         -- 'fcm','apns','web_push'
  token           TEXT NOT NULL,
  token_hash      BYTEA GENERATED ALWAYS AS (sha256(token::bytea)) STORED,
  app_version     TEXT,
  os_version      TEXT,
  device_model    TEXT,
  locale          TEXT,
  timezone        TEXT,
  last_seen_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  registered_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  unregistered_at TIMESTAMPTZ,
  unregister_reason TEXT,                                -- 'user_logout','provider_invalid','user_action'
  UNIQUE (user_id, token_hash)
);
CREATE INDEX ON push_devices (user_id) WHERE unregistered_at IS NULL;
CREATE INDEX ON push_devices (provider, last_seen_at) WHERE unregistered_at IS NULL;
```

**Token rotation:** if a new token arrives for the same `(user_id, device_model, app_install_id)` we mark old as `unregistered_at = now(), unregister_reason = 'rotated'`.

**Invalidation feedback:** FCM/APNS receipts marking a token as invalid trigger `unregister_reason = 'provider_invalid'`.

### 3.14 `push_segments`, `push_campaigns`, `push_campaign_targets`

```sql
CREATE TABLE push_segments (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  segment_key     TEXT NOT NULL UNIQUE,
  description     TEXT,
  definition_sql  TEXT NOT NULL,                         -- parametrised SELECT user_id FROM …
  estimated_size  BIGINT,
  last_computed_at TIMESTAMPTZ,
  is_dynamic      BOOLEAN NOT NULL DEFAULT true,         -- recomputed per campaign vs static cohort
  created_by      BIGINT REFERENCES users(id)
);

CREATE TABLE push_campaigns (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name            TEXT NOT NULL,
  segment_id      BIGINT NOT NULL REFERENCES push_segments(id),
  template_id     BIGINT NOT NULL REFERENCES notification_templates(id),
  scheduled_for   TIMESTAMPTZ NOT NULL,
  status          TEXT NOT NULL DEFAULT 'draft',         -- draft/scheduled/running/completed/cancelled
  throttle_per_min INT NOT NULL DEFAULT 10000,
  respect_quiet_hours BOOLEAN NOT NULL DEFAULT true,
  experiment_id   BIGINT,
  created_by      BIGINT REFERENCES users(id),
  approved_by     BIGINT REFERENCES users(id),
  metrics         JSONB                                  -- sent/delivered/opened rollup
);

CREATE TABLE push_campaign_targets (
  campaign_id     BIGINT NOT NULL REFERENCES push_campaigns(id) ON DELETE CASCADE,
  user_id         BIGINT NOT NULL,
  device_id       BIGINT NOT NULL REFERENCES push_devices(id),
  status          TEXT NOT NULL DEFAULT 'pending',
  sent_at         TIMESTAMPTZ,
  PRIMARY KEY (campaign_id, device_id)
);
```

### 3.15 `email_messages`, `email_bounces`, `email_providers`

```sql
CREATE TABLE email_providers (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  provider_key    TEXT NOT NULL UNIQUE,                  -- 'sendgrid','aws_ses','local_smtp'
  display_name    TEXT NOT NULL,
  config          JSONB NOT NULL,                        -- encrypted creds (KMS)
  is_active       BOOLEAN NOT NULL DEFAULT true,
  priority        INT NOT NULL DEFAULT 100,              -- failover order
  daily_quota     INT,
  used_today      INT NOT NULL DEFAULT 0,
  reset_at        TIMESTAMPTZ
);

CREATE TABLE email_messages (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  notification_id BIGINT REFERENCES notifications(id),
  to_address      TEXT NOT NULL,
  to_address_hash BYTEA GENERATED ALWAYS AS (sha256(lower(to_address)::bytea)) STORED,
  from_address    TEXT NOT NULL,
  subject         TEXT NOT NULL,
  body_html       TEXT,
  body_text       TEXT,
  provider_id     BIGINT NOT NULL REFERENCES email_providers(id),
  provider_msg_id TEXT,
  status          TEXT NOT NULL DEFAULT 'queued',
  queued_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  sent_at         TIMESTAMPTZ,
  delivered_at    TIMESTAMPTZ,
  opened_at       TIMESTAMPTZ,
  clicked_at      TIMESTAMPTZ,
  trace_id        UUID
);

CREATE TABLE email_bounces (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  email_message_id BIGINT REFERENCES email_messages(id),
  to_address_hash BYTEA NOT NULL,
  bounce_kind     TEXT NOT NULL,
  provider_payload JSONB,
  occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 3.16 `sms_messages`, `sms_providers`, `sms_delivery_reports`

```sql
CREATE TABLE sms_providers (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  provider_key    TEXT NOT NULL UNIQUE,                  -- 'eskiz','twilio','vonage','playmobile'
  display_name    TEXT NOT NULL,
  config          JSONB NOT NULL,
  is_active       BOOLEAN NOT NULL DEFAULT true,
  priority        INT NOT NULL DEFAULT 100,
  country_codes   TEXT[],                                -- route by country prefix
  cost_per_sms    NUMERIC(10,4)
);

CREATE TABLE sms_messages (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  notification_id BIGINT REFERENCES notifications(id),
  to_phone        TEXT NOT NULL,
  to_phone_hash   BYTEA GENERATED ALWAYS AS (sha256(to_phone::bytea)) STORED,
  body            TEXT NOT NULL,
  provider_id     BIGINT NOT NULL REFERENCES sms_providers(id),
  provider_msg_id TEXT,
  segments        INT NOT NULL DEFAULT 1,
  status          TEXT NOT NULL DEFAULT 'queued',
  queued_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  sent_at         TIMESTAMPTZ,
  delivered_at    TIMESTAMPTZ,
  cost            NUMERIC(10,4),
  trace_id        UUID
);

CREATE TABLE sms_delivery_reports (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  sms_message_id  BIGINT NOT NULL REFERENCES sms_messages(id),
  status          TEXT NOT NULL,
  provider_payload JSONB,
  received_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 3.17 `webhooks_outbound`, `webhook_deliveries`, `webhook_secrets`

```sql
CREATE TABLE webhooks_outbound (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  partner_id      BIGINT NOT NULL REFERENCES partners(id),
  name            TEXT NOT NULL,
  url             TEXT NOT NULL,
  subscribed_types TEXT[] NOT NULL,                      -- ['landmark.published.v1','review.created.v1']
  is_active       BOOLEAN NOT NULL DEFAULT true,
  current_secret_id BIGINT,
  retry_strategy  JSONB NOT NULL DEFAULT '{"max":8,"base_ms":2000,"jitter":true}',
  max_concurrency INT NOT NULL DEFAULT 4,
  rate_limit_per_min INT DEFAULT 600,
  last_success_at TIMESTAMPTZ,
  consecutive_failures INT NOT NULL DEFAULT 0,
  disabled_until  TIMESTAMPTZ,                           -- circuit-breaker
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE webhook_secrets (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  webhook_id      BIGINT NOT NULL REFERENCES webhooks_outbound(id) ON DELETE CASCADE,
  secret_hash     BYTEA NOT NULL,                        -- argon2id(secret)
  algo            TEXT NOT NULL DEFAULT 'hmac-sha256',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  rotated_at      TIMESTAMPTZ,
  expires_at      TIMESTAMPTZ
);

CREATE TABLE webhook_deliveries (
  id              BIGINT GENERATED ALWAYS AS IDENTITY,
  webhook_id      BIGINT NOT NULL,
  event_id        UUID NOT NULL,
  type_key        TEXT NOT NULL,
  attempt         INT NOT NULL,
  status          TEXT NOT NULL,                         -- pending/success/failed/dead
  http_status     INT,
  request_headers JSONB,
  response_headers JSONB,
  response_body   TEXT,                                  -- truncated to 2 KB
  duration_ms     INT,
  next_retry_at   TIMESTAMPTZ,
  occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (occurred_at, id)
) PARTITION BY RANGE (occurred_at);
-- monthly partitions
CREATE INDEX ON webhook_deliveries (webhook_id, occurred_at DESC);
CREATE INDEX ON webhook_deliveries (status, next_retry_at) WHERE status = 'pending';
```

### 3.18 `search_index_mappings`

```sql
CREATE TABLE search_index_mappings (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  locale          TEXT NOT NULL UNIQUE,                  -- 'uz','ru','en','zh','fa','ar',…
  es_index_name   TEXT NOT NULL UNIQUE,                  -- 'landmarks_uz_v3'
  analyzer_kind   TEXT NOT NULL,                         -- 'custom','icu','stempel','kuromoji','smartcn'
  analyzer_config JSONB NOT NULL,                        -- full ES analyzer JSON
  synonyms_ref    TEXT,                                  -- path or symbolic ref to synonyms file
  stopwords       TEXT[],
  tier            TEXT NOT NULL,                         -- 'first_class','icu_generic'
  shards          INT NOT NULL DEFAULT 1,
  replicas        INT NOT NULL DEFAULT 1,
  alias_target    TEXT NOT NULL,                         -- 'landmarks_uz' alias → current colour
  current_color   TEXT NOT NULL DEFAULT 'blue',          -- blue/green
  is_active       BOOLEAN NOT NULL DEFAULT true
);
```

**Tiering strategy:** ~20 "first-class" languages (uz, ru, en, zh, ja, ar, fa, tr, de, fr, es, hi, ko, pt, it, pl, nl, vi, th, id) get curated analyzers with stopwords and synonyms. The remaining ~180 languages use a single shared ICU-tokenised generic analyzer. This keeps total index count manageable (~20 dedicated + 1 generic with locale field = 21 indices) while still providing acceptable relevance.

### 3.19 `search_indexing_jobs`, `search_sync_outbox`

```sql
CREATE TABLE search_indexing_jobs (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  job_kind        TEXT NOT NULL,                         -- 'full_reindex','partial','blue_green_swap'
  locale          TEXT,
  status          TEXT NOT NULL DEFAULT 'pending',
  total           BIGINT,
  processed       BIGINT NOT NULL DEFAULT 0,
  failed          BIGINT NOT NULL DEFAULT 0,
  started_at      TIMESTAMPTZ,
  finished_at     TIMESTAMPTZ,
  triggered_by    BIGINT REFERENCES users(id),
  config          JSONB
);

CREATE TABLE search_sync_outbox (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  doc_type        TEXT NOT NULL,                         -- 'landmark','collection','user_profile'
  doc_id          TEXT NOT NULL,
  op              TEXT NOT NULL,                         -- 'index','delete'
  enqueued_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  picked_at       TIMESTAMPTZ,
  indexed_at      TIMESTAMPTZ,
  attempt_count   INT NOT NULL DEFAULT 0,
  last_error      TEXT,
  UNIQUE (doc_type, doc_id, op, enqueued_at)
);
CREATE INDEX ON search_sync_outbox (enqueued_at) WHERE indexed_at IS NULL;
```

### 3.20 `search_query_log`, `search_zero_results`, `search_synonyms`

```sql
CREATE TABLE search_query_log (
  id              BIGINT GENERATED ALWAYS AS IDENTITY,
  query_text      TEXT NOT NULL,
  query_normalized TEXT NOT NULL,                        -- lowercased + diacritics stripped
  locale          TEXT NOT NULL,
  result_count    INT NOT NULL,
  clicked_doc_id  TEXT,
  click_position  INT,
  session_id_hash BYTEA NOT NULL,                        -- anonymised
  occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (occurred_at, id)
) PARTITION BY RANGE (occurred_at);
-- weekly partitions, 90-day retention

CREATE TABLE search_zero_results (
  query_normalized TEXT NOT NULL,
  locale          TEXT NOT NULL,
  hit_count       BIGINT NOT NULL DEFAULT 1,
  last_seen_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (query_normalized, locale)
);

CREATE TABLE search_synonyms (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  locale          TEXT NOT NULL,
  terms           TEXT[] NOT NULL,                       -- ['samarqand','samarkand','самарканд']
  is_active       BOOLEAN NOT NULL DEFAULT true,
  created_by      BIGINT REFERENCES users(id)
);
```

### 3.21 `cron_schedules`, `cron_runs`

```sql
CREATE TABLE cron_schedules (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  schedule_key    TEXT NOT NULL UNIQUE,                  -- 'reindex_landmarks_daily'
  cron_expr       TEXT NOT NULL,                         -- '0 3 * * *'
  timezone        TEXT NOT NULL DEFAULT 'UTC',
  task_name       TEXT NOT NULL,                         -- Celery task path
  task_args       JSONB NOT NULL DEFAULT '[]',
  task_kwargs     JSONB NOT NULL DEFAULT '{}',
  enabled         BOOLEAN NOT NULL DEFAULT true,
  max_drift_sec   INT NOT NULL DEFAULT 300,              -- alert if drift exceeds
  last_run_at     TIMESTAMPTZ,
  last_run_status TEXT,
  next_run_at     TIMESTAMPTZ,
  owner_team      TEXT
);

CREATE TABLE cron_runs (
  id              BIGINT GENERATED ALWAYS AS IDENTITY,
  schedule_id     BIGINT NOT NULL,
  expected_at     TIMESTAMPTZ NOT NULL,
  started_at      TIMESTAMPTZ NOT NULL,
  finished_at     TIMESTAMPTZ,
  drift_sec       INT,
  status          TEXT NOT NULL,                         -- success/failed/missed/running
  celery_task_id  TEXT,
  result_summary  JSONB,
  error           TEXT,
  PRIMARY KEY (started_at, id)
) PARTITION BY RANGE (started_at);
-- monthly partitions, 1-year retention
```

**Drift detection:** a watchdog job runs every minute, scanning `cron_schedules` where `next_run_at < now() - max_drift_sec` and no corresponding `cron_runs` entry exists — emits a `cron.missed.v1` event → alert.

### 3.22 `celery_tasks_mirror`, `background_jobs`, `job_retries`

```sql
CREATE TABLE celery_tasks_mirror (
  task_id         UUID PRIMARY KEY,
  task_name       TEXT NOT NULL,
  args            JSONB,
  kwargs          JSONB,
  queue           TEXT NOT NULL,
  status          TEXT NOT NULL,                         -- pending/started/retry/success/failure
  retries         INT NOT NULL DEFAULT 0,
  eta             TIMESTAMPTZ,
  enqueued_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  started_at      TIMESTAMPTZ,
  finished_at     TIMESTAMPTZ,
  worker          TEXT,
  result          JSONB,
  error           TEXT,
  trace_id        UUID
);
CREATE INDEX ON celery_tasks_mirror (status, enqueued_at) WHERE status IN ('pending','retry');
CREATE INDEX ON celery_tasks_mirror (queue, status);

CREATE TABLE background_jobs (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  job_kind        TEXT NOT NULL,                         -- 'thumbnail_generation','embedding_compute',…
  idempotency_key TEXT,
  payload         JSONB NOT NULL,
  status          TEXT NOT NULL DEFAULT 'pending',
  priority        INT NOT NULL DEFAULT 100,
  celery_task_id  UUID,
  scheduled_for   TIMESTAMPTZ,
  attempt_count   INT NOT NULL DEFAULT 0,
  max_attempts    INT NOT NULL DEFAULT 5,
  last_error      TEXT,
  result          JSONB,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at     TIMESTAMPTZ,
  UNIQUE (job_kind, idempotency_key)
);

CREATE TABLE job_retries (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  background_job_id BIGINT NOT NULL REFERENCES background_jobs(id) ON DELETE CASCADE,
  attempt         INT NOT NULL,
  failed_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  error           TEXT NOT NULL,
  next_retry_at   TIMESTAMPTZ
);
```

Celery emits task-lifecycle signals (`before_task_publish`, `task_prerun`, `task_postrun`, `task_failure`, `task_retry`) into `celery_tasks_mirror` via a Celery signal handler. The mirror is the **durable source of truth** for "what's queued" — Redis itself can be flushed without losing state visibility.

### 3.23 `analytics_events_raw`, `analytics_sessions`, `analytics_funnels`, `feature_usage`

```sql
CREATE TABLE analytics_events_raw (
  id              BIGINT GENERATED ALWAYS AS IDENTITY,
  occurred_at     TIMESTAMPTZ NOT NULL,
  event_name      TEXT NOT NULL,                         -- 'landmark_viewed','audio_played'
  user_id_hash    BYTEA,                                 -- HMAC(user_id, daily_salt) — re-identifiable for 24 h only
  anonymous_id    UUID,
  session_id      UUID,
  properties      JSONB NOT NULL DEFAULT '{}',
  app_version     TEXT,
  platform        TEXT,
  locale          TEXT,
  country_code    TEXT,
  region          TEXT,                                  -- city-level only, never precise GPS
  trace_id        UUID,
  ingested_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  shipped_to_ch   BOOLEAN NOT NULL DEFAULT false,
  PRIMARY KEY (occurred_at, id)
) PARTITION BY RANGE (occurred_at);
-- daily partitions, 7-day TTL after shipping to ClickHouse

CREATE TABLE analytics_sessions (
  id              UUID PRIMARY KEY,
  user_id         BIGINT,
  anonymous_id    UUID,
  started_at      TIMESTAMPTZ NOT NULL,
  ended_at        TIMESTAMPTZ,
  event_count     INT NOT NULL DEFAULT 0,
  first_event     TEXT,
  last_event      TEXT,
  platform        TEXT,
  app_version     TEXT,
  country_code    TEXT
);

CREATE TABLE analytics_funnels (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  funnel_key      TEXT NOT NULL UNIQUE,
  name            TEXT NOT NULL,
  steps           JSONB NOT NULL,                        -- [{name,event,filter}]
  window_minutes  INT NOT NULL DEFAULT 60,
  is_active       BOOLEAN NOT NULL DEFAULT true,
  created_by      BIGINT REFERENCES users(id)
);

CREATE TABLE feature_usage (
  feature_key     TEXT NOT NULL,
  segment_key     TEXT NOT NULL,
  date            DATE NOT NULL,
  uniq_users      BIGINT NOT NULL,
  events          BIGINT NOT NULL,
  PRIMARY KEY (feature_key, segment_key, date)
);
```

### 3.24 `trace_spans`, `incidents`, `alerts`, `uptime_snapshots`, `release_versions`

```sql
CREATE TABLE trace_spans (
  trace_id        UUID NOT NULL,
  span_id         UUID NOT NULL,
  parent_span_id  UUID,
  service         TEXT NOT NULL,
  operation       TEXT NOT NULL,
  started_at      TIMESTAMPTZ NOT NULL,
  duration_ms     INT NOT NULL,
  status          TEXT NOT NULL,                         -- 'ok','error'
  attributes      JSONB,
  PRIMARY KEY (started_at, trace_id, span_id)
) PARTITION BY RANGE (started_at);
-- daily partitions, 7-day retention (Tempo is source of truth)

CREATE TABLE incidents (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  external_ref    TEXT,                                  -- PagerDuty/Opsgenie incident id
  severity        TEXT NOT NULL,                         -- 'sev1'..'sev4'
  title           TEXT NOT NULL,
  summary         TEXT,
  status          TEXT NOT NULL,                         -- open/mitigated/resolved/closed
  detected_at     TIMESTAMPTZ NOT NULL,
  mitigated_at    TIMESTAMPTZ,
  resolved_at     TIMESTAMPTZ,
  owner_user_id   BIGINT REFERENCES users(id),
  postmortem_url  TEXT,
  affected_services TEXT[],
  affected_regions TEXT[],
  trace_ids       UUID[]                                 -- linked traces
);

CREATE TABLE alerts (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  source          TEXT NOT NULL,                         -- 'grafana','sentry','uptimerobot','custom'
  external_ref    TEXT,
  alert_name      TEXT NOT NULL,
  severity        TEXT NOT NULL,
  status          TEXT NOT NULL,                         -- firing/acked/resolved
  fired_at        TIMESTAMPTZ NOT NULL,
  acked_at        TIMESTAMPTZ,
  acked_by        BIGINT REFERENCES users(id),
  resolved_at     TIMESTAMPTZ,
  incident_id     BIGINT REFERENCES incidents(id),
  payload         JSONB
);

CREATE TABLE uptime_snapshots (
  id              BIGINT GENERATED ALWAYS AS IDENTITY,
  target          TEXT NOT NULL,                         -- url or service key
  region          TEXT NOT NULL,
  checked_at      TIMESTAMPTZ NOT NULL,
  status          TEXT NOT NULL,                         -- up/down/degraded
  latency_ms      INT,
  http_status     INT,
  error           TEXT,
  PRIMARY KEY (checked_at, id)
) PARTITION BY RANGE (checked_at);
-- weekly partitions, 90-day retention

CREATE TABLE release_versions (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  service         TEXT NOT NULL,
  version         TEXT NOT NULL,
  git_sha         TEXT NOT NULL,
  released_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  released_by     BIGINT REFERENCES users(id),
  rollout_strategy TEXT,                                 -- 'blue_green','canary','rolling'
  rollback_of     BIGINT REFERENCES release_versions(id),
  notes           TEXT,
  UNIQUE (service, version)
);
```

### 3.25 `feature_flag_evaluations`

```sql
CREATE TABLE feature_flag_evaluations (
  id              BIGINT GENERATED ALWAYS AS IDENTITY,
  flag_key        TEXT NOT NULL,
  user_id         BIGINT,
  variant         TEXT NOT NULL,
  rule_matched    TEXT,
  evaluated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (evaluated_at, id)
) PARTITION BY RANGE (evaluated_at);
-- daily partitions, sampled at 1% in prod (100% in staging); 30-day retention
```

---

## 4. Event Bus Choice — **Redpanda** (Kafka-compatible)

**Decision:** Redpanda (Kafka-compatible API), single binary, no ZooKeeper, single-cluster v1 → multi-region v2.

**Why not Postgres LISTEN/NOTIFY:** addressed in §1.

**Why not NATS / NATS JetStream:**
- Streams up to ~150 MB/s per node, but consumer group semantics weaker than Kafka.
- Smaller ecosystem for CDC connectors, ClickHouse sinks, Elasticsearch sinks.
- No native log-compaction (used for state-recovery topics).
- Subject hierarchy is fine for routing but lacks partition-based ordering guarantees we need (per-user FIFO).

**Why Redpanda over Apache Kafka:**
- Single binary, no JVM, no ZooKeeper / KRaft setup ceremony — fits the 160-core single-server reality of phase 1.
- Wire-compatible with Kafka, so we can swap to MSK or Confluent Cloud later without code changes.
- Lower P99 latency for our event sizes (1–10 kB) — Redpanda reports 10× lower tail latency in published benchmarks.
- Tiered storage (S3) available out of the box for cold event retention.

**Topology:**

```
Topics (partitions × retention):
├── events.domain.v1          (32 × 7d hot, 90d S3-tiered)   ← all domain events
├── events.analytics.v1       (64 × 24h hot, 30d S3)         ← high-volume analytics
├── events.notifications.v1   (16 × 7d)                      ← notification dispatch
├── events.search-sync.v1     (16 × 7d)                      ← ES sync
├── events.webhooks.v1        (8  × 7d)                      ← outbound webhook fan-out
├── events.audit.v1           (16 × 365d)                    ← Agent 2 audit stream
├── events.dlq.v1             (4  × 30d)                     ← consumer DLQ
└── state.user-profiles.v1    (32 × compacted)               ← log-compacted state topic

Partition key = aggregate_id (so per-aggregate ordering is preserved).
Consumer groups: notification-router, es-indexer, ch-sink, webhook-dispatcher,
                 audit-archiver, leaderboard-recompute.
```

---

## 5. Transactional Outbox Pattern

The single hardest correctness problem in event-driven systems is **dual writes** — writing to Postgres AND publishing to Kafka in the same logical operation, where either can fail. We solve it with the outbox:

```python
# Every domain command follows this shape:
with db.transaction() as tx:
    landmark = tx.execute("UPDATE landmarks SET status='published' WHERE id=$1 RETURNING *", id)
    tx.execute("""
      INSERT INTO event_log (id, occurred_at, type_key, aggregate_type, aggregate_id,
                             actor_user_id, payload, trace_id, source_service, source_version, …)
      VALUES ($1, now(), 'landmark.published.v1', 'landmark', $2, $3, $4, $5, …)
    """, event_id, landmark.id, current_user.id, payload, trace_id)
    tx.execute("""
      INSERT INTO event_outbox (event_id, type_key, partition_topic, partition_key, payload, trace_id)
      VALUES ($1, 'landmark.published.v1', 'events.domain.v1', $2, $3, $4)
    """, event_id, str(landmark.id), payload, trace_id)
# tx commits — both event_log and outbox rows land atomically with the business write.
```

**Reaper worker (one per service, leader-elected via Postgres advisory lock):**

```
loop every 100 ms:
  SELECT id, event_id, partition_topic, partition_key, payload, headers
  FROM event_outbox
  WHERE published_at IS NULL
  ORDER BY id ASC
  LIMIT 500
  FOR UPDATE SKIP LOCKED;

  produce to Redpanda in a batch with acks=all;
  on success: DELETE FROM event_outbox WHERE id IN (...);
  on failure: increment attempt_count, exponential backoff;
```

**Ordering guarantees:** per-aggregate ordering is preserved because (a) all events for an aggregate share the same `partition_key`, and (b) the reaper processes the outbox in `id` order. Global ordering is **not** guaranteed and **not** required by any consumer.

**Alternative considered:** Debezium logical-replication on `event_log` directly. Rejected for the *primary* path because it ties the schema of the event-log table to the wire format, complicates schema evolution, and surfaces operational complexity (replication slots, WAL pressure) before we have the team to operate it. We do use Debezium for **CDC of business tables → ES** (§8), which is a different, narrower use case.

---

## 6. Notification System

### 6.1 Architecture

```
Domain event → Redpanda → notification-router consumer
   ↓
[Resolve template] → [Resolve user preferences] → [Apply quiet hours]
   ↓
For each surviving channel:
  ├── push    → push-dispatcher → FCM/APNS
  ├── email   → email-dispatcher → SendGrid/SES (failover)
  ├── sms     → sms-dispatcher → Eskiz/Twilio (route by country)
  ├── in_app  → INSERT into in_app_notifications_inbox + WebSocket fan-out
  └── webhook → webhook-dispatcher
```

### 6.2 Preference resolution algorithm (pseudocode)

```python
def resolve_channels(user, category, requested_channels):
    if category.is_transactional:
        return requested_channels  # legally cannot suppress

    channels = []
    for ch in requested_channels:
        pref = get_pref(user.id, category.id, ch)
        if pref is None:
            if ch not in category.default_channels:
                continue
            enabled = True
        else:
            enabled = pref.enabled
        if not enabled:
            continue
        if user.global_dnd and not category.is_transactional:
            continue
        channels.append(ch)
    return channels

def apply_quiet_hours(user, channels, scheduled_for=None):
    qh = get_quiet_hours(user.id)
    if not qh or not qh.enabled:
        return channels, scheduled_for
    now_local = (scheduled_for or now()).astimezone(qh.timezone)
    in_quiet = is_between(now_local.time(), qh.start_local, qh.end_local)
    if not in_quiet:
        return channels, scheduled_for
    if qh.defer_until_morning:
        return channels, next_local_time(qh.end_local, qh.timezone)
    # else: drop suppressed channels
    return [c for c in channels if c not in qh.suppress_channels], scheduled_for
```

### 6.3 Template rendering

- Jinja2 with strict-undefined mode (a missing variable fails the render → notification marked `failed` rather than sent with `{undefined}`).
- Variables come from `notifications.context` (merged from the source event payload).
- Subject/body are rendered server-side; for push, payload size is capped at 4 kB (FCM) / 4 kB (APNS).

---

## 7. Push Delivery

### 7.1 Provider abstraction

A single `PushDispatcher` interface with two implementations (`FCMDispatcher`, `APNSDispatcher`). Token routing chooses by `push_devices.provider`. Both use HTTP/2 long-lived connections; both honour provider rate limits.

### 7.2 Segmentation

Segments are saved SQL queries (templated, parametrised). For a campaign:

```sql
INSERT INTO push_campaign_targets (campaign_id, user_id, device_id)
SELECT $1, pd.user_id, pd.id
FROM push_devices pd
WHERE pd.user_id IN (<segment_definition_sql>)
  AND pd.unregistered_at IS NULL
  AND pd.last_seen_at > now() - INTERVAL '90 days';
```

Materialising the target list at campaign-start time avoids race conditions where a user unsubscribes mid-campaign and we still hit them.

### 7.3 Throttling

Token-bucket rate limiter per campaign at `throttle_per_min`. Implementation: Redis `INCR` with TTL + Lua script for atomic check-and-decrement. Default 10k pushes/min to stay well under FCM's 1M/min hard cap and to smooth backend load.

### 7.4 Receipt tracking

FCM/APNS deliver async receipts (delivered, dismissed, opened). We accept them on a webhook endpoint and write to `push_receipts` + `notification_delivery_log`. Open-rate is the basis for A/B variant comparison.

---

## 8. Search Indexing (Postgres → Elasticsearch 8)

### 8.1 Sync path

Two parallel paths:

1. **Outbox-driven (primary, low-latency):** Whenever a landmark/collection/profile row changes, the same transaction inserts into `search_sync_outbox`. A `search-indexer` worker drains it and pushes to ES in batches of 500.
2. **CDC-driven (catch-up, full-fidelity):** Debezium on Postgres logical replication for the same tables, written to `events.search-sync.v1`. Used as a safety net to catch any rows that bypass the outbox (rare admin direct writes) and as the *only* path during full reindex.

Idempotency in ES is trivial: `_id = doc_type:doc_id`. Out-of-order writes are protected by `version_type=external_gte` using `updated_at` as the version.

### 8.2 Per-language indices

Top-20 languages: one index per language (`landmarks_uz_v3`, `landmarks_zh_v3`, …) with a language-specific analyzer (Snowball/Lucene built-in for major Euro languages, Kuromoji for ja, SmartCN for zh, custom for uz/ky/tg using Hunspell dicts). Synonyms loaded via `synonyms_path` ↔ `search_synonyms` table dumped to file on demand.

Remaining ~180 languages: one shared index `landmarks_icu_v3` with the ES ICU analyzer + `locale` keyword field. ICU tokenisation handles 99% of scripts (Cyrillic, Devanagari, Thai, Arabic, etc.) acceptably without per-language tuning.

A single read alias `landmarks_<locale>` resolves to either the dedicated or generic index, with the `locale` filter applied transparently.

### 8.3 Blue/green reindex

```
1. Create new index landmarks_uz_v4 with updated mapping.
2. Bulk reindex from Postgres (search_indexing_jobs runs it, progress visible in admin).
3. Run dual-write: outbox writes go to both _v3 and _v4 during the catch-up window.
4. Verify doc counts & sample queries.
5. Atomically swap alias landmarks_uz from _v3 → _v4 (single _aliases call).
6. Stop dual-write, delete _v3 after 24 h grace period.
```

Zero downtime, full rollback by re-aliasing.

### 8.4 Backpressure

If `search_sync_outbox` depth exceeds 100k rows, we (a) page on-call, (b) auto-scale indexer workers, (c) if depth exceeds 1M, the writer service throttles non-critical updates (e.g. view-count increments stop emitting sync rows; only content edits do).

---

## 9. Search Relevance

### 9.1 Query understanding pipeline

```
raw query
  ↓ Unicode NFC normalise
  ↓ lowercase + diacritics strip (preserves original for highlighting)
  ↓ language detection (CLD3) — confirm vs user locale
  ↓ spell correction (ES suggest, threshold 0.8)
  ↓ synonym expansion (from search_synonyms)
  ↓ tokenise via locale-appropriate analyzer
  ↓ multi-field query: name^4, name.ngram^1, description^1, tags^2, region^1
  ↓ function_score: boost by popularity_score, recency, quality_score
  ↓ post-filter: locale, category, region
```

### 9.2 Zero-results gap analysis

Every zero-result query upserts `search_zero_results`. A daily job:
1. Surfaces top 100 zero-result queries per locale to admin.
2. Auto-suggests synonyms (e.g. "samarqand" ↔ "samarkand") if a non-zero variant exists.
3. Flags candidates for new landmark content ingestion.

### 9.3 Click-through ranking signal

`search_query_log.clicked_doc_id` + `click_position` feeds a weekly batch job that computes per-query CTR-based boosts written to ES as field-value-factor on each doc — a poor-person's learning-to-rank.

---

## 10. Analytics Pipeline

```
                                                                ┌──────────────────┐
                                                                │  ClickHouse      │
                                                                │  (OLAP, hot 90d, │
                                                                │   cold S3 1y)    │
                                                                └────────▲─────────┘
                                                                         │ Kafka Connect
                                                                         │ ClickHouse Sink
                                                                         │
Mobile app ──► /v1/events batch ──► api ──► analytics_events_raw (pg) ──►│
                                                ↓                        │
                                          shipper job                    │
                                          (every 30 s,                   │
                                           batched, gzipped)             │
                                                ↓                        │
                                          events.analytics.v1  ─────────►┘
                                          (Redpanda topic)
                                                ↓
                                          ┌─────┴─────┐
                                          ↓           ↓
                                  ES (suggestion    Postgres aggregates
                                   surfacing)       (feature_usage, funnels)
```

### 10.1 Postgres ↔ ClickHouse boundary

- **Postgres** holds transactional state, configuration, anything that needs joins/constraints/RLS.
- **ClickHouse** holds time-series event data — `landmark_viewed`, `audio_played`, `ar_opened`, page views, scroll depth, A/B exposures.
- Rule: if it's mutable, it lives in Postgres. If it's append-only and high-volume, ClickHouse.
- `analytics_events_raw` in Postgres exists only as a **durable buffer** (so we can never lose events even if Kafka is down) with a 7-day TTL.

### 10.2 PII handling

- Raw events store `user_id_hash = HMAC(user_id, daily_salt)`. The daily salt rotates at 00:00 UTC. After 24 h, re-identification requires admin access to the historic salt vault (audited).
- IP addresses are truncated to /24 (IPv4) or /48 (IPv6) before hashing.
- GPS is rounded to city centroid before storage; never raw lat/lng in analytics.

### 10.3 CDC tooling

Debezium runs on a dedicated replica reading from Postgres logical replication slots. Three connectors:
1. `business-tables-cdc` → `events.search-sync.v1` (drives ES sync safety net)
2. `subscriptions-cdc` → `events.domain.v1` (Agent 6 dunning triggers)
3. `users-cdc` → `state.user-profiles.v1` (log-compacted, drives notification router caches)

---

## 11. Background Jobs

### 11.1 Celery layout

```
queues:
  ├── critical      (priority 0): payment-related, password-reset, dunning
  ├── default       (priority 5): notifications, search-sync
  ├── analytics     (priority 7): rollups, funnel computation
  ├── ai            (priority 5): TTS generation, embedding, vision
  ├── ingest        (priority 8): bulk imports, dataset enrichment
  └── maintenance   (priority 9): vacuum, archival, reindex
```

Workers are sized per queue. AI queue runs on the GPU host; everything else on CPU hosts.

### 11.2 Cron via Celery Beat — but with DB-backed schedule

Off-the-shelf Celery Beat reads schedules from a Python file at startup. We replace it with `django-celery-beat`-style DB-driven `cron_schedules` so admin can edit schedules without redeploy. Beat polls the table every 30 s.

### 11.3 Drift detection

```sql
-- runs every 60 s as its own scheduled task
SELECT s.id, s.schedule_key
FROM cron_schedules s
LEFT JOIN cron_runs r
  ON r.schedule_id = s.id
  AND r.expected_at = s.next_run_at
WHERE s.enabled
  AND s.next_run_at < now() - (s.max_drift_sec || ' seconds')::interval
  AND r.id IS NULL;
-- each row → emit cron.missed.v1 event → alert
```

### 11.4 Mirror sync

Celery signal handlers (`@before_task_publish.connect`, etc.) write into `celery_tasks_mirror`. The mirror is the *durable* view — Redis is a transport detail. If Redis is flushed in an incident, we can re-enqueue everything in `status IN ('pending','retry')` from the mirror.

---

## 12. Distributed Tracing

- OpenTelemetry SDK in FastAPI, Celery, AI service, admin panel.
- W3C `traceparent` header propagated everywhere; `trace_id` and `span_id` stamped onto every row in `event_log`, `audit_log`, `notification_delivery_log`, `webhook_deliveries`, `email_messages`, `sms_messages`, `celery_tasks_mirror`, `background_jobs`.
- Exporter: OTLP → Grafana Tempo (full trace storage).
- Sampling: 100% for errors, 100% for slow traces (>2 s), 5% for everything else, 100% for admin operations.
- `trace_spans` in Postgres holds only a sampled subset (1%) for joining with business data — Tempo is the source of truth.

**Correlation example** — "Why didn't user 12345 get their welcome email?":
1. Look up `user_id=12345` in `notifications` → find `trace_id`.
2. Query Tempo by `trace_id` → full request chain across api → notification-router → email-dispatcher.
3. Cross-reference `notification_delivery_log` rows with same `trace_id` for per-attempt detail.
4. Cross-reference `audit_log` (Agent 2) for any admin actions in the same trace.

---

## 13. Outbound Webhooks

### 13.1 Partner subscription model

Partners (B2B muzeylar, turizm agentliklari) subscribe to event types via admin panel or partner self-serve API:

```
POST /partners/{id}/webhooks
{
  "url": "https://museum.example/silklens-hook",
  "subscribed_types": ["landmark.published.v1", "review.created.v1"],
  "secret": "<generated>"
}
```

### 13.2 Signature scheme

```
HTTP headers:
  X-SilkLens-Event:        landmark.published.v1
  X-SilkLens-Delivery:     <webhook_deliveries.id>
  X-SilkLens-Timestamp:    <unix>
  X-SilkLens-Signature:    t=<unix>,v1=<hex(hmac_sha256(secret, timestamp + "." + body))>
```

Partner verifies signature, replays prevented by timestamp check (±5 min).

### 13.3 Retry with jitter

```
attempt_n: delay = min(2^n * base, 1h) + random(0, 30s)  jitter
max 8 attempts over ~6 hours
on dead: row in dead_letter_events + email partner
```

### 13.4 Circuit breaker

After 50 consecutive failures, `webhooks_outbound.disabled_until = now() + 1h`. Partner notified by email. Auto-recovers; admin can manually re-enable.

---

## 14. Risks & Open Questions

### Risk 1 — `event_log` growth rate at 10M users

At 10M MAU and ~5 events/user/day average → 50M events/day × 2 kB avg → 100 GB/day, ~36 TB/year just for event_log. Partition pruning + S3 tiering with `pg_parquet` keeps hot Postgres footprint ≤3 TB (90 days), but archival pipeline must be operationally rock-solid. **Mitigation:** weekly archive job + restore-from-S3 drill in staging quarterly.

### Risk 2 — 200-language Elasticsearch index cardinality

Even tiered (20 dedicated + 1 generic), each dedicated index needs ≥1 shard × ~500k landmarks × 200 lang variants where present → memory pressure on small ES clusters. **Mitigation:** start with 4 first-class languages (uz/ru/en/zh), expand to top-20 over Faza 4–7, monitor heap and shard count, consider Elasticsearch hot-warm-cold tiering if heap pressure hits.

### Risk 3 — Notification quiet-hours timezone correctness across DST

User in `America/New_York` setting quiet hours 22:00–08:00 across a DST transition gets an 11-hour or 9-hour quiet window unless we compute in their local timezone using IANA TZDB. **Decision:** delivery worker computes window at delivery time, NOT at enqueue time, using `pytz`/`zoneinfo` against current IANA TZDB. CI test suite includes DST-transition fixtures.

### Risk 4 — Outbox reaper as single point of failure / lag

If the reaper crashes, all events stall in the outbox — invisible to consumers but accumulating. **Mitigation:** (a) leader-elected reaper with hot standby (Postgres advisory lock on the leader, second instance polls), (b) Prometheus alert on `outbox_lag_seconds > 10`, (c) admin-panel widget showing outbox depth per service.

### Risk 5 — ClickHouse schema evolution lag

Adding a property to an analytics event requires Postgres app code update + ClickHouse table ALTER + Kafka schema registry update. If they fall out of sync, events end up in DLQ. **Mitigation:** schema registry (Confluent or Karapace) enforces forward-compatible evolution; CI gate validates schemas; ClickHouse uses `JSONExtract` on a `properties` JSON column for non-promoted fields.

### Risk 6 — Search relevance for low-resource Central Asian languages

Uzbek (Latin & Cyrillic), Karakalpak, Tajik — Hunspell dictionaries are partial; stemming/lemmatisation poor. **Mitigation:** start with ICU + custom synonym lists curated by content team; investigate Stanza or UDPipe for lemmatisation in Faza 7; revisit when AI-fine-tuned multilingual embeddings (Agent 3) are available — could route long-tail languages through semantic search instead of keyword.

### Risk 7 — Multi-region event replication (post-Faza 7)

Phase-7+ requires Tashkent + Frankfurt + Singapore regions. Cross-region event log replication is hard: Kafka MirrorMaker2 introduces 100–500 ms lag and ordering drift across regions. **Open question:** do we keep `event_log` regional with eventual-consistency cross-region replication, or move to a globally-consistent service like Spanner-style CockroachDB for the log? Defer decision until concrete multi-region traffic forecasts exist.

### Risk 8 — Idempotency table growth

`event_consumer_offsets` plus per-consumer dedup keys can grow unbounded. **Mitigation:** dedup horizon = 7 days (events older than that won't be replayed by any reasonable consumer), drop dedup rows past that boundary daily.

### Open question — webhook delivery ordering

Partners typically *don't* expect ordered delivery, but some accounting partners (Agent 6 billing exports) do. Per-webhook setting `ordering: 'strict' | 'best_effort'` with strict implemented via single-flight per webhook_id (serialize via Redis lock). Trade-off: strict reduces throughput. To revisit after first 5 partners onboarded.

### Open question — feature flag service ownership

`feature_flag_evaluations` is sampled here, but the flag definitions themselves likely belong to a platform-config domain (Agent 1 or a future Agent 9). For now we mirror evaluations only; definitions live elsewhere with a foreign-key by `flag_key`.

---

*Document version: 1.0 — 2026-05-18 — Agent 7 of 8 — SilkLens platform architecture.*
