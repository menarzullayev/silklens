# 08 — Performance & Reliability Architecture

> **Agent:** 8 / 8 — Performance & Reliability Architect
> **Scope:** Cross-cutting design for partitioning, replication, caching, indexes, hot/cold storage, HA, DR, offline-sync conflicts, multi-region future, migration safety.
> **Status:** v1.0 — 2026-05-18
> **Audience:** Advises Agents 1-7. Every schema/feature decision must respect the invariants in this document.

---

## 1. Domain Analysis — Performance as a Cross-Cutting Constraint

SilkLens is not a "regular CRUD" product. It is the intersection of four high-cardinality, append-heavy workloads stitched into one platform:

1. **A geo-spatial discovery engine** (every heritage view, GPS ping, AR session is a write).
2. **An AI inference funnel** (every camera capture produces a vision call, a vector embedding, a token-usage record, often a TTS file).
3. **A social/gamification layer** (XP increments, leaderboards, badges, friend feeds — write-amplified by fan-out).
4. **A monetization & audit substrate** (payments, entitlements, GDPR/UZ audit log — every write needs durability + immutability).

These workloads have radically different access patterns. Treating them as one Postgres schema with one set of indexes and one replica strategy guarantees brownouts by month 6. The Roadmap targets are explicit: **1M users at month 12, 10M+ users in the "Titan" phase, 500k+ heritage objects, 200 languages, <500ms API, <0.1% crash rate, 99.9% uptime** — and Project-Decisions §15 demands the system be DB-engine-pluggable, §34 demands local-first CRDT sync, §7 demands offline-first.

Therefore Agent 8 treats **performance as a property of the architecture, not of the code**. We commit to invariants that every other agent must respect:

| Invariant | Why |
|---|---|
| **No FK across a future shard boundary** | Citus / logical sharding requires shard-local FKs only. |
| **All hot tables are partitioned from day one** (even when small) | `ALTER TABLE … PARTITION BY` is impossible without rewriting; designing for it on day one is free. |
| **All time-series writes use BRIN, never B-tree on `created_at`** | A 10B-row B-tree on `created_at` is 200GB+. A BRIN is ~30MB. |
| **All primary keys are ULID/UUIDv7 (time-sortable)** | Monotonic-ish PKs keep B-tree page locality, enable range-scan optimizations, and survive sharding. UUIDv4 destroys cache locality. |
| **Reads default to a replica; writes default to primary; read-your-writes is solved by LSN-tracking, not by routing everything to primary** | Otherwise the primary becomes the bottleneck at ~50k QPS. |
| **No application logic in DB triggers for hot paths** (use logical replication → outbox bus per Agent 7) | Triggers serialize writes and hide latency. |
| **Every write that touches money or entitlements has an idempotency key** | At-least-once delivery is the only realistic guarantee from any network. |
| **All timestamps are UTC `timestamptz`; partition boundaries are UTC** | Time-zone-aware partitioning is a footgun at multi-region. |
| **A schema change that takes a lock for more than 30s is not allowed in CI** | We use expand-contract; long backfills run via `pg_cron` in batches. |

Performance is also a **product feature**: a 2s recognition latency in the Roadmap KPI is the difference between "magic" and "broken". The same fanout that powers gamification (leaderboards) is also the same fanout that destroys p99 latency if cached badly. Every layer (L1/L2/L3 cache, replicas, partitions, vector index) exists to defend a specific p99 budget. Section 5 names each budget explicitly.

---

## 2. Scale Projections

All numbers assume the Roadmap targets and conservative per-user activity (5 heritage views/day for free user, 25/day for premium, 10% premium ratio). "Bytes" = approximate on-disk including indexes & TOAST, not WAL.

| Table | 6 mo (100k users) | 1 yr (1M users) | 3 yr (5M users) | 5 yr (10M users) |
|---|---|---|---|---|
| `users` | 100k rows / 200 MB | 1M / 2 GB | 5M / 10 GB | 10M / 20 GB |
| `heritage_objects` | 50k / 2 GB (rich JSONB) | 500k / 20 GB | 2M / 80 GB | 5M / 200 GB |
| `heritage_views` (event) | 90M / 30 GB | 1.8B / 600 GB | 27B / 9 TB | 90B / 30 TB |
| `ai_generations` | 15M / 25 GB (incl. prompts) | 300M / 500 GB | 4.5B / 7.5 TB | 15B / 25 TB |
| `embeddings` (1536-dim fp16) | 200k / 0.6 GB | 2M / 6 GB | 20M / 60 GB | 100M / 300 GB |
| `audit_log` | 50M / 25 GB | 1B / 500 GB | 15B / 7.5 TB | 50B / 25 TB |
| `event_log` (outbox/CDC) | 200M / 60 GB | 4B / 1.2 TB | 60B / 18 TB | 200B / 60 TB |
| `push_deliveries` | 30M / 9 GB | 600M / 180 GB | 9B / 2.7 TB | 30B / 9 TB |
| `ai_token_usage` | 20M / 4 GB | 400M / 80 GB | 6B / 1.2 TB | 20B / 4 TB |
| `xp_events` | 50M / 10 GB | 1B / 200 GB | 15B / 3 TB | 50B / 10 TB |
| `ugc_photos` | 1M / 0.4 GB (DB rows; media in MinIO) | 20M / 8 GB | 300M / 120 GB | 1B / 400 GB |
| `subscriptions` + `payments` | 50k / 50 MB | 600k / 600 MB | 4M / 4 GB | 10M / 10 GB |

**Implications:**
- The DB stays *manageable* (single primary + replicas) up to **~year 2 / 2M users / ~5 TB hot data**. After that, Citus / logical sharding is no longer optional.
- `audit_log` + `event_log` + `heritage_views` together dominate WAL volume (~80%). They are the partitioning-must-haves.
- `embeddings` at 100M × 1536 dims × fp16 = 300 GB is the *upper* useful size for a single HNSW index. Beyond that we shard the vector store by tenant_id or by spatial bucket.

---

## 3. Partitioning Strategy

We use **PostgreSQL native declarative partitioning** + **`pg_partman`** (for automated rolling partition creation) + **`pg_cron`** (for drop-old-partition jobs and batched backfills). Citus is intentionally **deferred** — it stays compatible with native partitions, so we lose nothing by waiting.

### 3.1 Per-table partitioning matrix

| Table | Partition strategy | Key | Sub-partition | Retention | Rationale |
|---|---|---|---|---|---|
| `heritage_views` | **RANGE monthly** | `viewed_at` (UTC) | none | 24 months hot, then archive | Append-only event; queries are time-bounded (last 7d, last 30d). BRIN ideal. |
| `ai_generations` | **RANGE monthly** | `created_at` | HASH on `user_id` (8 ways) per partition | 12 months hot | Heavy write + heavy read by user; per-month + per-user shard prevents single hot partition. |
| `embeddings` | **HASH** | `entity_id` (64 ways) | none | forever (no time decay) | Vector index rebuild cost scales with rows-per-partition. HNSW per-shard. |
| `audit_log` | **RANGE monthly** | `occurred_at` | LIST on `tenant_id` per partition (white-label) | 7 years legal hold, S3 Glacier after 90d | Compliance write-once; per-tenant isolation also satisfies §15 multi-DB. |
| `event_log` (outbox) | **RANGE daily** | `created_at` | none | 7 days hot, drop after consumers caught up | High-volume CDC; daily granularity makes drop cheap. |
| `push_deliveries` | **RANGE monthly** | `created_at` | HASH on `user_id` (8) | 90 days | Status flip writes (queued→sent→delivered→opened); per-user sub-shard for fanout queries. |
| `ai_token_usage` | **RANGE monthly** | `occurred_at` | none | 36 months (billing audit) | Finance-critical, append-only. |
| `xp_events` | **RANGE monthly** | `occurred_at` | HASH on `user_id` (16) | 24 months, then sum → `xp_snapshots` | Hot per-user write; aggregates roll up to `xp_snapshots`. |
| `heritage_objects` | **LIST on `tenant_id`** | `tenant_id` | none | forever | Multi-tenant / white-label isolation (Project-Decisions §50). Default tenant = `silklens`. |
| `users` | **HASH** | `id` (32 ways) | none | forever | Future sharding readiness; native HASH partition is the shard-key carrier. |
| `notification_inbox` | **RANGE monthly** | `created_at` | HASH on `user_id` (8) | 90 days | Same pattern as push. |
| `ugc_photos` | **RANGE monthly** | `uploaded_at` | none | forever (with cold tier) | Moderation queue queries are time-bounded; old approved photos move to cold. |
| `chat_messages` (AI chat) | **RANGE monthly** | `created_at` | HASH on `conversation_id` (8) | 12 months | Conversation locality + time pruning. |
| `travel_journals` | **HASH** | `user_id` (32) | none | forever | Per-user offline-sync (CRDT root); shard-aligned. |

### 3.2 Concrete DDL — canonical examples

```sql
-- 3.2.1 RANGE monthly with HASH sub-partition (heaviest pattern)
CREATE TABLE ai_generations (
    id              UUID            NOT NULL DEFAULT uuid_generate_v7(),
    user_id         UUID            NOT NULL,
    created_at      TIMESTAMPTZ     NOT NULL,
    model           TEXT            NOT NULL,
    input_tokens    INT             NOT NULL,
    output_tokens   INT             NOT NULL,
    cost_micros     BIGINT          NOT NULL,
    request_hash    BYTEA           NOT NULL,         -- for AI cache
    response_jsonb  JSONB,
    PRIMARY KEY (created_at, id)                      -- partition key MUST be in PK
) PARTITION BY RANGE (created_at);

-- one month → 8 hash sub-shards
CREATE TABLE ai_generations_2026_05 PARTITION OF ai_generations
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01')
    PARTITION BY HASH (user_id);

CREATE TABLE ai_generations_2026_05_h0 PARTITION OF ai_generations_2026_05
    FOR VALUES WITH (MODULUS 8, REMAINDER 0);
-- ... h1..h7

-- 3.2.2 HASH-only (entity-keyed, no time decay)
CREATE TABLE embeddings (
    entity_id   UUID    NOT NULL,
    entity_type TEXT    NOT NULL,
    model       TEXT    NOT NULL,
    vector      vector(1536) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (entity_id, model)
) PARTITION BY HASH (entity_id);
-- 64 shards: embeddings_h00 .. embeddings_h63

-- 3.2.3 LIST on tenant_id (white-label isolation)
CREATE TABLE heritage_objects (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    tenant_id   TEXT NOT NULL DEFAULT 'silklens',
    /* ... */
) PARTITION BY LIST (tenant_id);

CREATE TABLE heritage_objects_silklens PARTITION OF heritage_objects FOR VALUES IN ('silklens');
CREATE TABLE heritage_objects_default  PARTITION OF heritage_objects DEFAULT;
```

### 3.3 Automation

- `pg_partman.create_parent('public.heritage_views', 'viewed_at', 'native', 'monthly', p_premake := 6)` → maintains 6 future months pre-created.
- `pg_cron` runs nightly: `SELECT partman.run_maintenance();` → creates new, detaches old.
- Detached partitions go through a 7-day "warm shelf" (still queryable, on slower disk) before being exported to S3 Glacier via `pg_dump --table` and dropped.
- A partition is **never dropped** until: (a) it is older than retention; (b) it is backed up to S3 with checksum; (c) it has been detached (not dropped) for ≥7 days.

---

## 4. Index Strategy Catalog

Every secondary index is listed once below with its justification. **Adding an index that is not in this catalog requires an ADR.** Total index footprint must be tracked in Grafana; alert if any single table's index size exceeds its heap size.

### 4.1 Index taxonomy

| Type | Use | Tables |
|---|---|---|
| **B-tree** | exact-match, range on selective cols | PKs, FKs, `email`, `slug`, status enums |
| **B-tree partial** | filtered queries; cuts index size 10-100× | `active=true`, `deleted_at IS NULL`, `status='pending'` |
| **B-tree expression** | computed predicates | `lower(email)`, `date_trunc('day', created_at)` |
| **BRIN** | append-only time-series | every `*_log`, `heritage_views.viewed_at`, `event_log.created_at` |
| **GIN** | JSONB containment, arrays, tsvector | `heritage_objects.tags`, full-text search columns |
| **GiST** | geometry, ranges, exclusion | `heritage_objects.location` (PostGIS), `subscriptions.valid_during` |
| **SP-GiST** | non-balanced trees, geohash | rarely — defer |
| **HNSW (pgvector)** | ANN search | `embeddings.vector` |
| **Hash** | equality only, smaller than B-tree | mostly avoided — B-tree is good enough now |

### 4.2 Catalog by table (curated, not exhaustive)

```
users
  - pk_users                        B-tree     (id)                     [implicit via PK]
  - ux_users_email_lower            B-tree UNIQUE  (lower(email)) WHERE deleted_at IS NULL
  - ix_users_phone                  B-tree     (phone_e164) WHERE phone_e164 IS NOT NULL
  - ix_users_created_at_brin        BRIN       (created_at)
  - ix_users_tenant                 B-tree     (tenant_id) WHERE tenant_id <> 'silklens'

heritage_objects
  - pk                              B-tree     (tenant_id, id)
  - ix_heritage_location_gist       GiST       (location)                  -- PostGIS
  - ix_heritage_h3_cell             B-tree     (h3_cell_r8)                -- Uber H3 for fast geo-bucketing
  - ix_heritage_tags_gin            GIN        (tags jsonb_path_ops)
  - ix_heritage_search_tsv          GIN        (search_tsv)                -- tsvector multi-lang
  - ix_heritage_status_partial      B-tree     (status) WHERE status='published'
  - ix_heritage_country_category    B-tree     (country_code, category)
  - ix_heritage_updated_at_brin     BRIN       (updated_at)

heritage_views (partitioned monthly)
  - pk                              B-tree     (viewed_at, id)
  - ix_views_user_brin              BRIN       (user_id)                  -- per-partition
  - ix_views_heritage_brin          BRIN       (heritage_id)              -- per-partition
  - ix_views_viewed_at_brin         BRIN       (viewed_at) pages_per_range=32
  -- NO B-tree on user_id at scale; aggregate via materialized rollups instead

embeddings (partitioned hash 64)
  - pk                              B-tree     (entity_id, model)
  - ix_emb_hnsw                     HNSW       (vector vector_cosine_ops) m=16, ef_construction=64
  -- HNSW built per-partition; total memory = 64 × per-shard; reindex one shard at a time

audit_log (partitioned monthly + tenant)
  - pk                              B-tree     (occurred_at, id)
  - ix_audit_actor_brin             BRIN       (actor_id)
  - ix_audit_entity                 B-tree     (entity_type, entity_id, occurred_at DESC)
  - ix_audit_action                 B-tree     (action) WHERE action IN ('delete','export','login_failed')

event_log (outbox, partitioned daily)
  - pk                              B-tree     (created_at, id)
  - ix_event_unpublished_partial    B-tree     (created_at) WHERE published_at IS NULL
  -- partial index stays tiny because rows graduate to "published" quickly

push_deliveries
  - pk                              B-tree     (created_at, id)
  - ix_push_user_status             B-tree     (user_id, status) WHERE status IN ('queued','retrying')
  - ix_push_dedupe                  B-tree UNIQUE (idempotency_key)
  - ix_push_brin                    BRIN       (created_at)

ai_token_usage
  - pk                              B-tree     (occurred_at, id)
  - ix_tokenusage_user_month        B-tree     (user_id, occurred_at)     -- billing rollups
  - ix_tokenusage_model             B-tree     (model, occurred_at)

xp_events
  - pk                              B-tree     (occurred_at, id)
  - ix_xp_user_brin                 BRIN       (user_id)
  -- xp_snapshots holds the materialized current value per user (B-tree on user_id)

subscriptions
  - ux_sub_user_active              B-tree UNIQUE (user_id) WHERE status='active'
  - ix_sub_valid_gist               GiST       (valid_during)             -- tstzrange
  - ix_sub_renewal                  B-tree     (next_renewal_at) WHERE status='active'

payments
  - pk                              B-tree     (created_at, id)
  - ux_payment_idempotency          B-tree UNIQUE (idempotency_key)
  - ix_payment_user                 B-tree     (user_id, created_at DESC)

travel_journals (CRDT)
  - pk                              B-tree     (user_id, journal_id)
  - ix_journal_updated              B-tree     (user_id, hlc_timestamp DESC)

chat_messages
  - ix_chat_conv                    B-tree     (conversation_id, created_at)
  - ix_chat_search                  GIN        (search_tsv) WHERE deleted_at IS NULL
```

**Index rules of thumb encoded as CI checks (per the policy in Sec. 13):**
1. No new B-tree on a `*_log` or `*_event` table's timestamp column — always BRIN.
2. No new index unless its expected scan / write ratio in `pg_stat_user_indexes` would be > 5:1.
3. Drop any index that shows 0 scans for 30 days in production (alert quarterly).
4. Composite index column order: equality first, then range; never reverse.

---

## 5. Caching Layers (L1 / L2 / L3)

```
        ┌──────────────────────────┐
Request │ FastAPI worker process    │
        │                           │
        │ L1: in-proc LRU (cachetools)
        │   - plan_features          (300s TTL,  10k entries)
        │   - entitlements_by_user   (60s,        50k)
        │   - feature_flags          (15s,         1k)
        │   - tenant_branding        (120s,        1k)
        └──────┬───────────────────┘
               │ miss
        ┌──────▼───────────────────┐
        │ L2: Redis (cluster mode) │
        │   - session:<sid>             1h sliding
        │   - user:<uid>:profile        15m
        │   - heritage:<id>:detail:<lang>  6h
        │   - heritage:hot:<country>    materialized list, 5m
        │   - leaderboard:<scope>:<period>  Redis ZSET, refreshed by stream
        │   - ai:cache:<hash>           7d (image-hash → result)
        │   - tts:cache:<hash>          forever (text-hash → minio URL)
        │   - rate:<uid>:<bucket>       60s windows
        │   - sync:lsn:<uid>            5m   (read-your-writes LSN)
        │   - lock:<key>                Redlock for cross-worker mutexes
        └──────┬───────────────────┘
               │ miss
        ┌──────▼───────────────────┐
        │ L3: PostgreSQL (primary  │
        │     or read replica)     │
        └──────────────────────────┘
```

### 5.1 Naming convention

`<domain>:<entity>:<id>[:<variant>]` — colon-separated, lowercase, no spaces.
- Variants encode language (`:en`), version (`:v3`), or scope (`:weekly:2026w20`).
- Cluster-safe hash tags around the *partition* component: `leaderboard:{global}:weekly` keeps a set on one shard.

### 5.2 TTL policy

| Class | TTL | Invalidation |
|---|---|---|
| Static config (plans, flags) | 15-300s | event-driven via outbox bus (Agent 7) |
| User-owned (profile, entitlements) | 60s-15m | invalidate on write + TTL fallback |
| Hot reads (heritage detail) | 6h | event-bus on edit; stale-while-revalidate |
| Computed aggregates (leaderboards) | refreshed every 60s by background worker; cache itself has no TTL |
| AI cache | 7d default, 30d if expert-validated | manual flush on model upgrade |
| TTS cache | forever; pointers only, blobs in MinIO | manual on voice change |
| Sessions | 1h sliding, 30d max | explicit logout |

### 5.3 Invalidation strategy — event-driven, not poll

Writes to authoritative state emit a CDC event via the outbox (`event_log` table). A `cache-invalidator` consumer subscribes and runs `DEL`/`UNLINK` against Redis. Two invariants:

1. **The write is the source of truth, the cache is the optimization** — we never block a write on cache success. If invalidation lags, TTL catches up.
2. **Stale-while-revalidate by default** — on miss we return the stale value (if any) and trigger a background refill. p99 stays flat during cache churn.

### 5.4 Latency budgets per layer

| Hop | Budget | Notes |
|---|---|---|
| L1 hit | < 0.1 ms | in-process |
| L2 hit | 0.5-2 ms | Redis same-AZ |
| L3 indexed point read | 2-8 ms | from replica |
| L3 vector ANN (HNSW, k=10) | 5-30 ms | per-shard |
| End-to-end p99 API | < 500 ms (Roadmap KPI) | leaves ~450 ms for app logic + AI |

---

## 6. Read / Write Scaling

### 6.1 Topology

```
                         ┌────────────────────┐
                         │   pgbouncer (HA)   │  transaction-mode pool
                         │   pool_size=200    │
                         └────┬───────────┬───┘
                              │           │
                       writes │           │ reads
                              ▼           ▼
                ┌──────────────────┐   ┌──────────────────┐
                │  Primary (sync   │   │  Replica pool    │
                │  + async repls)  │   │  (HAProxy LB)    │
                └────────┬─────────┘   └────────┬─────────┘
                         │                      ▲
              streaming repl (sync to R1,       │
              async to R2..Rn)                  │
                         │                      │
                         ├──────────────────────┘
                         │
                  ┌──────▼──────┐  ┌────────────┐
                  │ R1 (sync,   │  │ R2..Rn     │
                  │ same DC)    │  │ async      │
                  └─────────────┘  └────────────┘
```

- **Single writer**, **N read replicas**. R1 is synchronous (zero-data-loss). R2..Rn are async.
- **pgbouncer in transaction mode** in front of every Postgres node. `default_pool_size=200`, `max_client_conn=10_000`. Application uses short-lived transactions only; no prepared statements (transaction-mode incompatible) unless we move that workload to session-mode on a separate pool.
- **Timeouts** (set per-role):
  - `statement_timeout = 30s` for app role
  - `idle_in_transaction_session_timeout = 60s`
  - `lock_timeout = 5s`
  - `tcp_keepalives_idle = 60`

### 6.2 Read-your-writes guarantee

After a write, the app captures `pg_current_wal_lsn()` and stores it as `sync:lsn:<uid>` in Redis (5-minute TTL). Subsequent reads in the same user session:

1. Hit a replica.
2. Before returning, compare replica `pg_last_wal_replay_lsn()` to the stashed LSN.
3. If replica is behind → either (a) retry on next replica, or (b) fall back to primary.

This is cheaper than session-pinning (which collapses our replica fan-out for chatty users).

### 6.3 Connection budget

- Backend pods: ~200 × 5 connections to pgbouncer = 1000 client conns
- Pgbouncer → Postgres: 200 server conns (matches `max_connections=300` on Postgres with headroom).
- AI workers, Celery workers each get their **own** pgbouncer pool — don't share with API.

### 6.4 Workload separation

- `analytics_*` role → routed exclusively to a dedicated reporting replica with `hot_standby_feedback=off` and aggressive `vacuum_defer_cleanup_age`. Long queries OK there.
- `admin_*` role → routed to primary (consistency matters for admin panel writes).
- `mobile_*` role → routed to nearest replica, falls back to primary on LSN miss.

---

## 7. Sharding Readiness (Citus / logical, future)

We commit to **shard-readiness now**, **shard-execution later** (target trigger: ~5M users or ~5 TB hot data). What we do today so the future migration is mechanical:

### Rule 1 — Natural shard key per table is fixed now

| Domain | Shard key | Reasoning |
|---|---|---|
| User-centric (profile, prefs, journals, xp, devices) | `user_id` | Locality of per-user fanout. |
| Heritage-centric (objects, media, translations) | `heritage_id` | Read-heavy; locality of detail joins. |
| Tenant-centric (white-label tables) | `tenant_id` | Hard multi-tenant isolation (LIST partition is a stepping stone). |
| Events (views, ai_generations) | `user_id` | Already HASH sub-partitioned by user_id (Sec. 3). |

### Rule 2 — No FK across shard boundaries

If `heritage_views.user_id → users.id` will cross shards under user-id sharding (because views are also user-keyed, this one is fine), we keep it. But:
- `heritage_views.heritage_id → heritage_objects.id` would be cross-shard. **Drop it.** Enforce in app + nightly reconciliation job.
- All "reference" tables (`countries`, `languages`, `plans`, `feature_flags`) are **distributed reference tables** — replicated to every shard. They are small (<10 MB).

**Generalized rule for Agents 1-7:** any FK whose two sides have different shard keys must be removed before launch. The schema reviewer (Agent 1) enforces.

### Rule 3 — Monotonic-ish PKs everywhere

ULID / UUIDv7 for all primary keys. We provide `uuid_generate_v7()` via a small C extension or the `pg_uuidv7` extension. **Never UUIDv4** for hot tables — random PKs destroy B-tree page locality and inflate WAL.

### Rule 4 — Application uses repository abstractions (per Project-Decisions §15)

`HeritageRepository`, `UserRepository`, etc. The routing logic (which shard?) lives inside one place. When Citus is enabled, we change the connection string and (mostly) we are done.

### Rule 5 — `CREATE EXTENSION citus;` is a no-op until we flip the switch

Until then, the same DDL works on plain Postgres. The hash-partitioned tables already encode the shard count; Citus will adopt them via `create_distributed_table(..., colocate_with => ...)`.

---

## 8. Hot / Warm / Cold / Archive Storage Tiers

```
HOT     (last 90 days, NVMe RAID10)
WARM    (90-365 days, SAS/SSD)
COLD    (1-3 years, slow SSD or large HDD)
ARCHIVE (3+ years, S3 Glacier / Glacier Deep)
```

### 8.1 Storage backing — Postgres tablespaces

```sql
CREATE TABLESPACE ts_hot  LOCATION '/mnt/nvme/pg';
CREATE TABLESPACE ts_warm LOCATION '/mnt/ssd/pg';
CREATE TABLESPACE ts_cold LOCATION '/mnt/hdd/pg';
```

`pg_partman` retention move-job nightly: detach partition → `ALTER TABLE … SET TABLESPACE` → continue queryable. Apps don't need to know.

### 8.2 Filesystem

- **ZFS** for the Postgres data directory. `recordsize=8K` (matches Postgres page), `compression=zstd-3` (typical 2-3× compression on JSONB/text), `atime=off`, `logbias=throughput` for WAL volume.
- **ext4** acceptable fallback; ZFS preferred for snapshot-based backups + cheap cloning of staging environments.

### 8.3 Media (MinIO / S3) tiers

- `media-hot` bucket → recent uploads, served via Cloudflare CDN
- `media-warm` → 30-day-old originals; thumbnails stay hot
- `media-archive` → moved to S3 Glacier after 365 days; cold restore is async (user sees "loading…" for archive restore, ≤4h)

### 8.4 Retention windows (default; per-tenant override via admin panel)

| Data class | Hot | Warm | Cold | Archive | Hard delete |
|---|---|---|---|---|---|
| `heritage_views` | 90d | 9 mo | 12 mo | 24+ mo | never (rolled up) |
| `ai_generations` (request/response bodies) | 30d | 6 mo | never stored full beyond 6mo; only summary | — | 12 mo |
| `audit_log` | 90d | 1 yr | 6 yr (Glacier) | — | never (legal hold) |
| `event_log` (outbox) | 7d | — | — | — | drop after consumers caught up |
| `push_deliveries` | 30d | 60d | — | — | 90d |
| `chat_messages` | 90d | 9 mo | — | — | 12 mo (or user-controlled) |
| `ugc_photos` (rows) | 1y | forever | — | — | on user delete |
| `xp_events` (granular) | 90d | 9 mo | — | — | 24 mo (snapshot replaces) |

### 8.5 GDPR right-to-be-forgotten

Tombstoning: a delete request enters `gdpr_deletion_queue`. A background job walks the partitioned tables, deletes / nulls by user_id, and writes a single `audit_log` row recording the cryptographic hash of the deleted-user-id (so we can prove compliance without retaining PII).

---

## 9. High Availability & Replication

### 9.1 Topology

- **3-node Postgres cluster** managed by **Patroni** + **etcd** (3 nodes for quorum).
- **1 synchronous replica** (`synchronous_standby_names = 'ANY 1 (replica1, replica2)'`) for zero-data-loss on commit.
- **2-3 async replicas** for read scaling and reporting.
- **Cross-region async replica** (target Phase 5+) seeds the future EU/US region.

### 9.2 Failover procedure (Patroni-driven)

1. Patroni detects primary unhealthy (configurable threshold, default 10s).
2. Patroni elects the most-caught-up sync replica.
3. New primary promoted; HAProxy / Patroni REST API exposes the new endpoint.
4. Pgbouncer is restarted (or uses Patroni's `pg_rewind`-aware reload) → client connections reconnect.
5. Failover SLA: **30-60 seconds**. Reads continue throughout (replicas keep serving).

### 9.3 Replication slots

- One **physical replication slot** per replica (`replication1`, `replication2`, …) so WAL is retained even if a replica is offline briefly.
- **Cap WAL retention** with `max_slot_wal_keep_size = 100GB` — otherwise a dead replica fills the primary's disk.
- Monitor `pg_replication_slots.confirmed_flush_lsn` lag; alert at >1 GB or >5 minutes.

### 9.4 Logical replication

- Used for **CDC to downstream consumers** (Elasticsearch indexer, analytics ClickHouse, event bus). Logical slots are tracked separately and never block physical recovery.
- Used for **zero-downtime major-version upgrades** (e.g., Postgres 17 → 18): set up new cluster as logical subscriber, cut over, drop old.

### 9.5 Connection-level HA

- pgbouncer runs as a sidecar pair fronted by a Linux IPVS / keepalived VIP, or by Kubernetes service + readiness probe. App talks to a stable virtual endpoint.

---

## 10. Disaster Recovery (RPO 1 min, RTO 15 min)

### 10.1 PITR via WAL archive

- `archive_mode = on`, `archive_command = pgbackrest archive-push %p` (or wal-g).
- WAL archive destination: **S3 (server-side encrypted, versioned, cross-region replicated)**.
- Base backups: **daily full** + **6-hourly differentials** (pgBackRest).
- Verification: a **restore drill quarterly** into a sandbox cluster; sign-off recorded as ADR.

### 10.2 Logical / dump backups

- Nightly `pg_dump --format=custom` of small-but-critical metadata tables (`plans`, `tenants`, `feature_flags`, `users` schema-only). Cheap insurance against logical corruption that PITR can't isolate.
- Stored in a separate AWS account / region (defends against credential compromise blast radius).

### 10.3 RPO / RTO targets

| Scenario | RPO | RTO | Mechanism |
|---|---|---|---|
| Primary node failure (HW) | 0 (sync replica) | 30-60 s | Patroni failover |
| AZ outage | <30 s | 5 min | promote cross-AZ replica |
| DC outage | ≤1 min | ≤15 min | promote cross-region replica + DNS swing |
| Logical corruption / bad migration | ≤5 min | ≤30 min | PITR to T-1 |
| Ransomware / S3 wipe | hours | hours | restore from cross-account immutable backup |

### 10.4 Backup integrity

- Every backup verified by automated restore-and-checksum job in the sandbox cluster (`pg_dump | sha256sum` + row counts vs source). Alert on any drift.
- Backups encrypted at rest with a KMS key separate from prod app keys.

---

## 11. Offline-First Sync & Conflict Resolution (Project-Decisions §7, §34)

### 11.1 Entity classification

Every entity is assigned exactly one **authority class**:

| Class | Definition | Examples |
|---|---|---|
| **Server-authoritative** | Server is the only truth; client only reads. Conflict resolution: server always wins. | `subscriptions`, `payments`, `entitlements`, `plans`, `pricing`, `feature_flags`, `heritage_objects`, `audit_log`, `ai_token_usage`, `leaderboards` |
| **Client-authoritative** | Client is the truth; server stores latest received. Conflict resolution: client always wins (LWW with client HLC). | `user_preferences` (UI theme, language), `local_drafts`, `recently_viewed_local`, `download_queue` |
| **CRDT** | Both can write; merged deterministically. | `travel_journals` (RGA text + LWW metadata), `bookmarks` (OR-Set), `xp_total` (G-Counter), `friend_list` (OR-Set), `group_trip_items` (OR-Set + LWW-Register), `profile_fields` (LWW-Register per-field), `tags_on_photo` (OR-Set) |

### 11.2 CRDT type per field

| Entity / Field | CRDT | Notes |
|---|---|---|
| `xp_total` | **G-Counter** per device-id; server sums | Increments only; survives offline; no negative. |
| `streak_days` | **PN-Counter** | Can decrement on reset. |
| `profile.{display_name, bio, avatar_url, ...}` | **LWW-Register** per field, HLC-timestamped | Field-level, not row-level — one device editing bio doesn't clobber another editing avatar. |
| `bookmarks` | **OR-Set** (Observed-Remove) | Add/remove without resurrection bug. |
| `friend_list` | **OR-Set** | Same. |
| `travel_journal.entries[i].title` | LWW-Register | One title per entry. |
| `travel_journal.entries[i].body` | **RGA (Replicated Growable Array)** of characters | Collaborative rich text — concurrent edits merge without lost characters. |
| `group_trip.items` | **OR-Set of item IDs** + LWW for each item's fields | Add/remove items + edit fields. |
| `photo.tags` | **OR-Set of tag strings** | |
| `heritage_review.rating` | **LWW-Register** | One reviewer, last write wins. |

### 11.3 Clocks

- **Hybrid Logical Clock (HLC)** in the client + server. 64-bit: 48 bits physical ms + 16 bits logical counter.
- Each write carries `(hlc_ts, device_id, user_id)`. Server's clock advances `max(local, incoming) + 1`.
- HLCs are monotonic per device but converge across devices, giving us total order without requiring synchronized clocks.

### 11.4 Sync protocol

1. **Push** — client sends batched ops since last `last_pushed_hlc`. Server accepts/rejects per-op (server-authoritative entities can reject).
2. **Pull** — client requests ops since `last_pulled_hlc`. Server streams.
3. **Conflict detection** — only matters for CRDT entities; resolution is deterministic by CRDT semantics.
4. **Transport** — HTTPS for bulk sync; **WebSocket** for live updates while online.

### 11.5 Storage on device (Flutter)

- **Isar** (per Roadmap) holds local state.
- Each CRDT entity has an `ops` table (the local op log) + a materialized "current view" for fast reads.
- On reconnect, ops are flushed to server. Server returns merged state; client materializes.

### 11.6 Sync edge cases

- **Clock skew**: HLC handles it (uses logical counter to break ties).
- **Conflicting server-authoritative writes**: server rejects with `409`, client must reload state.
- **Long-offline device returns weeks later**: pull is bounded by `last_pulled_hlc`; if the gap is too large (e.g., op log was pruned), we fall back to a **full snapshot + reset HLC**.
- **Multi-device same user concurrent edit**: HLC + per-field LWW means worst case is one field's last-50ms-edit gets overwritten — acceptable.

---

## 12. Multi-Region Future

### 12.1 Target topology (Phase 5+ / Year 2)

```
UZ-PRIMARY (Tashkent)        EU-SECONDARY (Frankfurt)      US-SECONDARY (Virginia)
  ┌─────────────────┐           ┌─────────────────┐           ┌─────────────────┐
  │ Postgres primary │           │ async replica   │           │ async replica   │
  │ + sync replica   │           │ + read endpoint │           │ + read endpoint │
  │ Redis (master)   │           │ Redis (regional)│           │ Redis (regional)│
  │ MinIO            │           │ S3 (mirrored)   │           │ S3 (mirrored)   │
  └─────────────────┘           └─────────────────┘           └─────────────────┘
```

### 12.2 Routing rules

- **Reads**: nearest region, replica-first.
- **Writes**: routed to UZ-PRIMARY initially (single-writer). Latency budget: EU→UZ ~80ms, US→UZ ~150ms. Acceptable for non-realtime writes; gamification writes (XP) are batched on-device anyway.
- **Cross-region active-active writes** are *out of scope* for Year 1-2. When demanded, options are: (a) Citus multi-coordinator, (b) per-region tenancy (heritage objects regional-owned), (c) per-region user pinning. We document but defer.

### 12.3 Read-locality optimizations

- Heritage detail cache (L2 Redis) replicated regionally — populated lazily from L3 on first miss.
- Static config (plans, branding) pushed to all regions via CDN + Redis pub/sub.
- Leaderboards: regional partial leaderboards + nightly global merge. Eventual consistency with explicit "global" vs "regional" tab.

### 12.4 PII residency (per Agent 2 / GDPR / UZ law)

- EU users' PII (defined per Agent 2) stored only in EU region.
- UZ users' PII stored only in UZ region.
- This is enforced by **tenant + residency tagging** on the user row + at the application routing layer. PII columns are **not** part of cross-region replicated tables; only pseudonymous IDs replicate.
- Audit-log entries pertaining to a user follow that user's residency.

### 12.5 Sync lag SLOs

- Async replication target: < 2s p95, < 10s p99.
- If lag exceeds 30s → page on-call; if > 5 min → escalate, consider regional failover.

---

## 13. Migration Safety — Zero-Downtime Schema Changes

### 13.1 Expand-Contract pattern (mandatory for all schema changes)

```
1. EXPAND   — add new column / table / index NULLable, no app reads it yet
2. BACKFILL — batched, throttled, via pg_cron (every 10s, 1000 rows/batch)
3. DUAL-WRITE — app writes to old AND new
4. DUAL-READ — app reads new with fallback to old (canary)
5. CUT      — app reads only new
6. CONTRACT — drop old column / table / index
```

Each step is a separate deployable. Steps may live in production for days — that is fine.

### 13.2 Lock-avoidance recipes

| Goal | Wrong way (locks) | Right way (lock-free) |
|---|---|---|
| Add column with default | `ADD COLUMN x INT NOT NULL DEFAULT 0` (PG ≥11 is fast for constant defaults — still verify) | Add NULLable → backfill → set NOT NULL with `NOT VALID` + `VALIDATE CONSTRAINT` |
| Add index | `CREATE INDEX` (locks writes) | `CREATE INDEX CONCURRENTLY` + retry-on-failure script |
| Add FK | `ADD CONSTRAINT ... REFERENCES` (full scan + lock) | `ADD CONSTRAINT ... NOT VALID` → `VALIDATE CONSTRAINT` (no lock) |
| Rename column | `RENAME COLUMN` (catalog lock, may stall) | Add new → dual-write → migrate readers → drop old |
| Change column type | `ALTER COLUMN … TYPE` (rewrites table) | Add new typed column → backfill → swap |
| Drop column | `DROP COLUMN` (instant in PG, but breaks queries) | Stop reading → drop |
| Re-partition | impossible in-place | Create new parent, dual-write, swap with `ALTER TABLE … ATTACH PARTITION` |

### 13.3 Long-running backfills

- Always batched. Pattern:
  ```sql
  -- runs every 10s via pg_cron
  WITH next AS (
      SELECT id FROM source WHERE migrated_at IS NULL
      ORDER BY id LIMIT 1000 FOR UPDATE SKIP LOCKED
  )
  UPDATE source SET … , migrated_at = now()
  WHERE id IN (SELECT id FROM next);
  ```
- Throttle on replica lag — pause if `pg_last_wal_replay_lsn` lag > 30s.

### 13.4 API versioning compatibility

- API contracts (per Agent 3) live longer than the underlying schema. We expose `/v1` and `/v2` simultaneously during any breaking change; old clients keep working.

### 13.5 Statement timeout for migrations

- Migration role bypasses the 30s `statement_timeout` (separate role: `migrator`). But each individual migration step still must be < 30s on production data, OR be implemented as a batched backfill.

### 13.6 CI guardrails

- Lint Alembic migrations with `squawk` (or equivalent) — reject anti-patterns at PR time.
- Apply each migration to a production-sized shadow DB before merge; fail if any statement takes > 30s on a single transaction.

---

## 14. Recommended Postgres Extensions

| Extension | Version | Purpose | Notes |
|---|---|---|---|
| `pgvector` | ≥ 0.7 | embeddings, HNSW ANN | Per-shard HNSW. |
| `postgis` | ≥ 3.4 | geometry, GiST | For `heritage_objects.location`. |
| `pg_partman` | ≥ 5.0 | automated partition mgmt | Schedule via pg_cron. |
| `pg_cron` | ≥ 1.6 | in-DB scheduled jobs | Batched backfills, partition maintenance, retention. |
| `pg_stat_statements` | bundled | query stats | **Always on** in prod. |
| `auto_explain` | bundled | log slow plans | `log_min_duration=500ms`. |
| `pg_trgm` | bundled | trigram fuzzy text | Search fallback / typo tolerance. |
| `pgcrypto` | bundled | crypto primitives | Hash IDs, encrypt PII at rest. |
| `uuid-ossp` / `pg_uuidv7` | bundled / 1.x | ULID/UUIDv7 generation | Monotonic PKs. |
| `pg_repack` | ≥ 1.5 | online table rewrite | Reclaim bloat without downtime. |
| `pg_buffercache` | bundled | inspect shared_buffers | Diagnostics. |
| `pg_visibility` | bundled | inspect VM | Vacuum diagnostics. |
| `hypopg` | ≥ 1.4 | hypothetical indexes | Index design without locks. |
| `pg_hint_plan` | optional | force plans on regressions | Use sparingly, document each hint. |
| `citus` | ≥ 12 | future sharding | **Deferred** — install only when triggered. |
| `timescaledb` | optional | alternative time-series | We use native partitioning + BRIN; TSDB only if hypertable features prove necessary. |
| `wal2json` / `pgoutput` | bundled | logical decoding | For CDC to ES / ClickHouse / event bus. |

---

## 15. Observability & Slow-Query Detection

### 15.1 Postgres metrics (Prometheus via postgres_exporter + custom queries)

- Per-table: row count, dead tuples %, index hit ratio, seq vs index scan ratio
- Per-query (pg_stat_statements): total_time, mean_time, p95 (computed), calls, rows
- Replication: WAL bytes/sec, replication lag bytes & seconds per replica
- Locks: long-running, blocking chains
- Connections: per-role, per-pool
- Cache: shared_buffers hit ratio (target > 99% for hot tables)
- Vacuum / autovacuum: bloat %, last_vacuum age
- Partitions: row count per partition, age, tablespace usage

### 15.2 Slow query regression detection

Nightly job snapshots `pg_stat_statements`; diffs against last week. Alert on:
- New query with `mean_time > 200ms`
- Existing query whose `mean_time` increased > 50% week-over-week
- Any query whose `rows / calls > 10000` (probable missing LIMIT/index)

### 15.3 Tracing

- OpenTelemetry SDK in FastAPI; spans cover: HTTP → route → cache lookup → DB query → external API (AI, payments) → cache write.
- Trace exemplars linked from Prometheus metrics (jump from "p99 high" to a real trace).

### 15.4 Dashboards (Grafana)

Per the Roadmap monitoring section, but with additions:
- "Hot Partition" dashboard — top 10 partitions by write rate
- "Index Bloat" dashboard — indexes with > 30% bloat
- "Replication" dashboard — lag, WAL retention, slot health
- "Cache Tier" dashboard — L1/L2/L3 hit ratios end-to-end
- "Vector ANN" dashboard — HNSW per-shard query latency, recall sample

### 15.5 SLOs (formal)

| SLO | Target | Error budget |
|---|---|---|
| API availability | 99.9% / 30d | 43.2 min/month |
| API p95 latency | < 500 ms | 5% of requests over budget |
| DB primary availability | 99.95% / 30d | 21.6 min/month |
| Replication lag p95 | < 5 s | 5% of samples over |
| Backup success rate | 100% / 30d | 0 (page immediately) |

---

## 16. Risks & Open Questions

### 16.1 Top reliability risks

1. **HNSW reindex at 50M+ vectors.** HNSW rebuilds block writes on the partition; even per-shard (64 shards) this can be hours per shard. Mitigations: (a) build a parallel shadow index in a tablespace, then atomically `ALTER INDEX … RENAME`; (b) move embeddings to a dedicated vector store (Qdrant / Milvus) if HNSW reindex becomes a recurring crisis; (c) keep embeddings reproducible (same input → same vector) so we can rebuild from source if needed.

2. **`audit_log` retention vs legal hold conflict.** GDPR right-to-be-forgotten requires deletion within 30 days; UZ + financial audit law may require 6+ years. Resolved via **hash-only retention** for "forgotten" users (we keep the audit row with user_id replaced by a one-way hash, satisfying both regimes). Needs sign-off from Agent 2.

3. **Multi-region sync lag during traffic spikes.** Leaderboards across regions may show inconsistent rankings during high write bursts. We label "Global" leaderboard with an "as of HH:MM UTC" timestamp; weekly leaderboards are computed off the primary at top-of-hour to avoid drift surprises.

4. **`pg_partman` + `pg_cron` interaction failures.** If pg_cron stops, partitions stop being created → writes start failing at month boundary. Mitigation: dead-man-switch alert on "future months pre-created < 3".

5. **Idempotency-key TTL vs replay attacks.** If we expire idempotency keys at 24h, a delayed-but-valid retry can double-charge. We keep payment idempotency keys for 30 days minimum + use a per-payment-method dedupe constraint.

6. **WAL volume blowout from outbox.** `event_log` at 4B rows/year produces enormous WAL. We use **unlogged tables for the in-flight portion** and only persist consumed-checkpoint rows; logical decoding goes via a separate publication.

7. **Connection-pool exhaustion under thundering herd** (e.g., a viral push notification). Mitigations: pgbouncer rate-limits, per-role pools, app-layer circuit breakers.

### 16.2 Open questions for cross-agent review

1. **Agent 1 (data model):** are there entities we've classified as server-authoritative that should actually be CRDT (e.g., `bookmarks` if user can bookmark from web + mobile simultaneously)?
2. **Agent 2 (security/privacy):** which exact columns count as PII for residency? Need a published list to implement column-level partitioning.
3. **Agent 5 (AI):** does the AI cache key include user_id (per-user personalization) or is it purely content-hashed? Affects cache size by 100×.
4. **Agent 6 (payments):** confirm idempotency key longevity (we propose 30 days) and whether retries cross day boundaries are expected.
5. **Agent 7 (events):** is the outbox the *only* CDC source, or do we also tap logical decoding directly for ES indexing? Both is fine, but the contract needs naming.

### 16.3 Tripwires (auto-alerts that force a re-evaluation of this doc)

- Any single partition > 200 GB
- Any HNSW shard > 5 GB
- Replication lag p99 > 30 s for 1 hour
- pg_stat_statements: any single query > 5% of total DB time
- Connection pool wait time p99 > 100 ms
- Hot table row count crosses 1B (triggers "consider sharding now" ADR)

---

## Appendix A — Cross-Cutting Directives to Agents 1-7

| To | Directive |
|---|---|
| **Agent 1 (Data Model)** | All PKs are ULID/UUIDv7. No FK across the shard-key boundaries listed in §7. Every hot table partitioned per §3. PII columns flagged with a `residency` tag. |
| **Agent 2 (Security/Privacy)** | Define the exhaustive PII column list. Validate the hash-on-forget approach in §16.1.2. Confirm KMS key separation for backups. |
| **Agent 3 (API)** | Every write endpoint accepts `Idempotency-Key` header. Every list endpoint paginates by `(created_at, id)` keyset, not OFFSET. Read endpoints accept `Cache-Control: stale-if-error`. API versioned per §13.4. |
| **Agent 4 (Mobile / Flutter)** | Use HLC clocks per §11.3. CRDT classification per §11.1 is binding. Implement LSN-stash for read-your-writes per §6.2. |
| **Agent 5 (AI)** | AI cache key contract per §16.2.3. TTS cache forever, but stable hashing. Vector writes go through the embedding partitioner (hash mod 64). |
| **Agent 6 (Payments / Monetization)** | Idempotency keys live 30 days minimum. All payment writes are server-authoritative (§11.1). Audit-log every payment state transition. |
| **Agent 7 (Events / Outbox)** | Outbox is the *one* invalidation channel for L2 cache (§5.3). `event_log` partitioned daily, drained continuously, no triggers on hot tables. |

---

*Document owner: Agent 8 (Performance & Reliability) | Version 1.0 | 2026-05-18*
