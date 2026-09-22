# SilkLens — Master Database & Domain Architecture

> **Version 1.0** · 2026-05-18 · Synthesized from 8 parallel specialist-agent designs
> Roadmap: [`Roadmap.md`](../../Roadmap.md) · Decisions: [`Project-Decisions.md`](../../Project-Decisions.md)

This master document consolidates the eight per-domain designs into a single source of truth, resolves cross-domain dependencies, and answers the 20 required architecture questions from the design brief. It is intentionally **opinionated** — every default below was chosen by Staff+ reasoning against the philosophy in `Project-Decisions.md` (maximal · dynamic · professional).

---

## 0. Executive Summary

SilkLens is a global, AI-native, offline-first, white-label-ready cultural-heritage platform targeting **10M+ users, 500K+ heritage objects, 200 languages**. The architecture is built around eight independently-designed but tightly-contracted domains, materialized in PostgreSQL 16 + pgvector with Redis, Elasticsearch, MinIO, Kafka/Redpanda, ClickHouse, and Celery surrounding it.

**Headline numbers across all eight domains:**

| Domain | Tables | Key invention |
|---|---:|---|
| 1. Core Heritage Domain | 38 | Bi-temporal fact-level provenance with confidence scoring |
| 2. Identity, RBAC, GDPR | 35 | Tamper-evident audit chain anchored to S3 Object Lock + git |
| 3. AI & Vector Infrastructure | ~31 (+ 6–10 embedding partitions) | Per-`(target, model_family, dim)` embedding tables, pHash dedup |
| 4. Media & Storage | 30 | Ed25519-signed offline bundles, perceptual-hash bucket-prefix |
| 5. Social, Gamification, UGC | 51 | XP-as-ledger, whale-user pull-fanout, shadow sock-puppet damping |
| 6. Monetization & Enterprise | 96 | RLS multi-tenancy, double-entry deferred-revenue ledger, sealed-bid auctions |
| 7. Infra, Analytics, Events | 47 | Outbox/log separation, 200-language ES tiering |
| 8. Performance & Reliability | cross-cutting | Per-table partitioning matrix, CRDT typing per entity |
| **TOTAL** | **~328 tables** | |

---

## 1. Domain Analysis (Cross-Cutting)

SilkLens domain is unusual along five axes that drive every architectural choice:

1. **AI-first, not AI-bolted-on.** Every read of a heritage record can return AI-generated content (audio guide, chat answer, recommendation). Every write goes through AI moderation. Cost, latency, drift, and safety are first-class observable metrics, not afterthoughts.
2. **Offline-first by mandate, not as a fallback.** Tourists in Samarkand or Kashgar have no roaming. The mobile client owns truth for user-private state (drafts, preferences, in-progress journals) and reconciles via CRDT; the server owns truth for shared state (subscriptions, payments, leaderboards) and pushes deltas.
3. **Dynamic everything — admin panel is the load-bearing operator surface.** App name, branding, pricing per region, AI model selection, fallback chains, moderation policy, feature flags — all admin-configurable at runtime. The DB schema mirrors that: vocabularies, plans, prompts, badges, and policies are *rows*, not code.
4. **Multi-tenant white-label from day one.** `tenant_id` propagates through every monetizable table; RLS enforces isolation. A reseller can be onboarded in 5 minutes with no code change.
5. **Cultural-political sensitivity.** Heritage attribution is contested (Nizami, Crimea, Parthenon). The schema captures per-fact provenance and confidence; it does not pretend to a single ground truth. Per-jurisdiction rendering policies belong in the presentation layer but are powered by data this layer captures.

These axes show up as recurring patterns: append-only event logs, idempotency keys on every write, admin-managed vocabularies for what would otherwise be enums, and CRDT or LWW typing per entity made explicit in §11.

---

## 2. Entity Discovery Report — Cross-Domain Highlights

The eight per-domain reports collectively identify 60+ entities that the roadmap did not name explicitly. The top 12 most consequential discoveries:

| Entity | Domain | Why it matters |
|---|---|---|
| `heritage_facts` (predicate-object-source-confidence quintuples) | 1 | Lets `heritage_objects` denormalize "winning" facts while keeping provenance auditable. |
| `heritage_revisions` (bi-temporal) | 1 | Rollback + per-fact change history; pairs with `heritage_provenance`. |
| `controlled_vocabularies` + `vocabulary_terms` + `taxonomy_nodes` | 1 | Adds new heritage kinds / styles / facets with zero DDL. |
| `audit_anchors` (daily Merkle roots) | 2 | Tamper-evidence: malicious DBA cannot silently truncate `audit_log`. |
| `residency_region` LIST-partition column on PII tables | 2 | Uzbek PD-law data residency at storage layer, not policy. |
| `oauth_providers` (catalog) vs `user_identities` (binding) | 2 | Admin can toggle Facebook on/off without a deploy. |
| Per-`(target, model_family, dim)` embedding tables | 3 | Allows simultaneous CLIP-image + multilingual-e5-text indexes with different dims. |
| `embedding_regeneration_jobs` | 3 | Model upgrades become bookkeeping, not month-long ad-hoc backfills. |
| `media_perceptual_hashes.bucket_16` | 4 | Sub-O(N) near-duplicate search in vanilla Postgres. |
| `offline_bundle_signatures` (Ed25519) | 4 | Rooted devices cannot substitute malicious bundles. |
| `xp_events` (append-only ledger) + `xp_balances` (materialized) | 5 | Financial-grade XP economy with clawback semantics. |
| `whale_users` + hybrid push/pull fanout | 5 | Celebrity creators don't cause 2M-row write storms. |
| `exchange_rate_snapshots` (per-charge) | 6 | Reproducible multi-currency revenue accounting. |
| `deferred_revenue_schedule` + `revenue_recognition_ledger` | 6 | Audit-grade GAAP/IFRS from day one. |
| `event_outbox` (transient queue) vs `event_log` (immutable history) | 7 | Anti-pattern avoidance: outbox is *not* a log. |
| `search_index_mappings.tier` (first-class vs ICU-generic) | 7 | 200 languages without 200 hand-tuned ES analyzers. |
| `celery_tasks_mirror` | 7 | Postgres is the system of record, not Redis. |

Every other "obvious" entity (users, heritages, media, payments) is also fully specified in the corresponding per-domain file.

---

## 3. Full Database Architecture — Where to Read

The 20 required output sections are answered across the eight documents below; this master is the **index + cross-reference layer**. For each section a reader of this document should know exactly where to go.

| Required output | Primary doc | Secondary refs |
|---|---|---|
| 3. Full DB Architecture | All 8 | — |
| 4. Table-by-table spec | 01–07 | 08 for partitioning |
| 5. Relationship map | 01 §4 | All `cross-agent deps` sections |
| 6. Index strategy | 08 §4 | Each domain doc's own indexes |
| 7. Vector search design | 03 §5–§7 | 08 §3, §4 (HNSW partition) |
| 8. Multilingual content | 01 §5, 03 §10, 07 §8–§9 | — |
| 9. Offline-first data | 04 §8, 08 §11 | 02 §11 for residency |
| 10. Event & analytics | 07 §4–§10 | 02 §6 audit boundary |
| 11. Security & compliance | 02 entire | 03 §12, 06 §11, 08 §12 |
| 12. Scaling strategy | 08 entire | per-domain risk sections |
| 13. Future migration | 08 §13 | 03 §6 embedding regen |
| 14. High-risk areas | §13 below | every domain's Risks section |
| 15. Microservice boundaries | §14 below | — |
| 16. Postgres extensions | 08 §14 | 03 (pgvector), 04 (pgcrypto), 01 (postgis, ltree) |
| 17. Caching strategy | 08 §5 | 06 §5 entitlement cache |
| 18. Data retention | 02 §6 (GDPR), 08 §8 (tier) | 04 §5 (MinIO lifecycle) |
| 19. Backup & restore | 08 §10 | — |
| 20. Final recommendations | §15 below | — |

---

## 4. Relationship Map — Cross-Domain Edges

```
                        ┌──────────────────────────────┐
                        │  Agent 2: Identity / Tenancy │
                        │  users • tenants • residency │
                        └───────┬──────────────────────┘
                                │  user_id, tenant_id, trust_score
       ┌────────────────────────┼────────────────────────┐
       ▼                        ▼                        ▼
┌─────────────┐         ┌────────────────┐       ┌──────────────┐
│ Agent 1     │         │ Agent 5 Social │       │ Agent 6 $$$  │
│ Heritage    │◄────────┤ UGC / Gamif    │       │ Subs / B2B   │
│ Geo / Time  │ heritage│ reviews/journals│       │ tenant RLS   │
└────┬────────┘  _id    └─────┬──────────┘       └───┬──────────┘
     │                        │                      │
     │ heritage_id            │ media_id             │ ai_cost_ledger
     ▼                        ▼                      ▼ entitlements
┌─────────────┐         ┌──────────────┐       ┌──────────────┐
│ Agent 3 AI  │◄────────┤ Agent 4 Media│       │ Agent 7 Bus  │
│ Embed/Cache │ pHash   │ Storage/CDN  │──────►│ Events/Notif │
└─────┬───────┘ media_id└──────┬───────┘ events │ Search/Push  │
      │                        │                └──────┬───────┘
      │ ai_moderation          │ offline bundles       │ analytics
      └────────────┬───────────┴───────────────────────┘
                   ▼
              ┌────────────────────────────────┐
              │ Agent 8: Performance / SRE     │
              │ partitions • CRDT • shards     │
              │ caching • HA • DR              │
              └────────────────────────────────┘
                       (cross-cutting)
```

**Key edges resolved in this master:**

- Every domain's `created_by/updated_by/deleted_by` columns reference `users(id)` from Agent 2 (Agent 2 §11).
- Every monetizable table carries `tenant_id` from Agent 6 (Agent 6 §4).
- Every embedding-bearing table FKs to its owning row (heritage / media / user-content) — Agent 3 §15.
- Every UGC table FKs to `users(id)` AND consults Agent 2's `user_trust_scores` snapshot at submit time (Agent 5).
- Every payment write uses idempotency keys ≥30 days (Agent 8 §13, Agent 6 §7).
- Every domain's events go through Agent 7's outbox; nothing bypasses it (Agent 7 §5).
- Every audit-bearing write goes through `app.audit(...)` SQL function from Agent 2 (Agent 2 cross-agent contract).

---

## 5. Index Strategy — Consolidated Catalog

See `08-performance-reliability.md §4` for the full catalog. Quick orientation:

| Index type | Where it lives | Rationale |
|---|---|---|
| **B-tree** | Every PK + every FK + every (created_at) on append-only tables | Default; cheap with UUIDv7 monotonicity. |
| **GIN** | jsonb columns (heritage `properties`, audit `details`); tsvector (search); arrays | Search and faceted queries. |
| **GiST** | `geography(Point, 4326)` columns; tstzrange for valid-time | Geo proximity + temporal overlap. |
| **BRIN** | Append-only event tables partitioned by month (`audit_log`, `event_log`, `xp_events`, `heritage_views`, `ai_generations`) | 1000× smaller than B-tree on time-correlated data. |
| **HNSW (pgvector)** | All `embeddings_*` tables, partial by `model_version_id` | Sub-millisecond ANN. |
| **Partial** | `WHERE deleted_at IS NULL` on soft-delete tables; `WHERE status = 'pending'` on moderation queues | Skip cold rows. |
| **Expression** | `lower(email)`, `digest(content, 'sha256')`, `extract(epoch FROM created_at)` | Functional uniqueness + fast filters. |
| **Unique partial** | `(user_id) WHERE is_primary` on phones/emails/payment-methods | Enforce "only one primary" without trigger. |

PK choice across the board: **UUIDv7 (or ULID)** to preserve B-tree locality on append-heavy tables. Never UUIDv4 on hot tables. Agent 8 §7.

---

## 6. Vector Search Design — How the Search Box Actually Works

Synthesized from Agent 3 §5–§8 and Agent 7 §8:

```
              user query "blue-tiled madrasa Samarkand 15th century"
                                 │
                                 ▼
        ┌────────── Query Understanding (Agent 3) ───────────┐
        │  • language detect  • intent classify              │
        │  • named-entity extract → heritage / period / style│
        │  • build filter predicates + free-text residual    │
        └────────┬─────────────────────────────────┬─────────┘
                 │                                 │
                 ▼                                 ▼
       ┌─────────────────┐                ┌────────────────────┐
       │ Postgres        │                │ Elasticsearch      │
       │ pgvector HNSW   │                │ tier-1 lang index  │
       │ filtered by     │                │ BM25 + analyzers   │
       │ partition on    │                │ + synonyms         │
       │ model_version_id│                │                    │
       └────────┬────────┘                └──────────┬─────────┘
                │                                    │
                │       ┌────────────────────┐       │
                └──────►│ Reciprocal Rank    │◄──────┘
                        │ Fusion (RRF) k=60  │
                        └──────────┬─────────┘
                                   ▼
                        ┌────────────────────┐
                        │ Rerank top 50 with │
                        │ cross-encoder      │
                        │ (admin-configurable│
                        │  via prompt_templ.)│
                        └──────────┬─────────┘
                                   ▼
                          final 10 results
```

**Per-model embedding tables** (Agent 3 §5):
- `embeddings_heritage_text_e5_1024` — multilingual-e5-large, 1024 dims, cosine
- `embeddings_heritage_image_clip_768` — CLIP-ViT-L, 768 dims, cosine
- `embeddings_media_image_clip_768` — same model, different target
- `embeddings_chunks_text_e5_1024` — RAG chunks
- `embeddings_user_query_e5_1024` — for recommendation cold-start

Each table has its own HNSW index (m=16, ef_construction=200) and is partitioned by `entity_id` HASH(64). Reindex is online via Agent 8 §13's expand-contract pattern: new `model_version_id` populates a partial index `WHERE model_version_id = 'new'`, then swap.

---

## 7. Multilingual Content Strategy — 200 Languages, One Schema

Synthesized from Agent 1 §5, Agent 3 §10, Agent 7 §8–§9.

**Translatable text fields use jsonb keyed by BCP-47:**
```sql
heritage_objects.name jsonb NOT NULL  -- {"uz": "Registon", "en": "Registan", "ru": "Регистан"}
heritage_objects.description_md jsonb NOT NULL
```
**Why jsonb beats side-table:** read locality (one row → all languages), simpler ORM, GIN-indexable, no JOIN N×200. Costs: harder to constrain length per language (use CHECK with `jsonb_each_text`) and translation memory must be a side table anyway. Agent 1 §5 picks jsonb with this reasoning.

**Translation pipeline** (Agent 3 §10):
```
source_text (uz) → NLLB-200 local → confidence (BLEU/COMET)
                                  ├── ≥ 0.85 → auto-publish, machine_translated=true
                                  ├── 0.50–0.85 → review queue, "MT, unreviewed" badge
                                  └── < 0.50  → manual translation required
                                  └── domain-loaded glossary applied first
                                  └── DeepL fallback when NLLB confidence low for top-20 languages
```

**Translation memory** (`ai_translation_memory`):
- Segment-level cache keyed by (source_hash, source_lang, target_lang, model_version)
- Fuzzy matching via trigram similarity for "this is 92% similar to a translated segment, reuse"
- Per Project-Decisions §42

**Elasticsearch tiering** (Agent 7 §8):
- **Tier-1 (top 20 languages):** dedicated index per language with stemmer + stopwords + synonyms
- **Tier-2 (long tail 180 languages):** one shared index with ICU analyzer + `locale` field
- Total index count ≈ 21, not 200 — keeps heap pressure manageable

---

## 8. Offline-First Data Strategy

Synthesized from Agent 4 §8 (bundles), Agent 8 §11 (sync conflicts), Agent 2 §11 (residency).

**Three layers of "offline":**

| Layer | Trigger | Authority |
|---|---|---|
| L1: Always-cached metadata | App launch | Server-pushed manifest |
| L2: Per-city / per-country **offline bundles** | User download (or auto for Premium) | Server-signed (Ed25519) zip with manifest |
| L3: Live AI / live chat / live payments | Online only | Server-only |

**Bundle versioning (Agent 4 §8):**
- `offline_bundles` row per `(region_id, language_set, version)`
- `offline_bundle_signatures` Ed25519 — app verifies before extraction
- Delta updates: client sends current version, server returns patch manifest
- Per-device tracking in `offline_bundle_downloads` to size CDN egress
- New heritage added in UZ → bundle version bumps → push notification → user opts to update

**Conflict resolution (Agent 8 §11), per entity type:**

| Entity | Conflict mode | CRDT type |
|---|---|---|
| `user_profile.display_name` | LWW with HLC timestamp | LWW-Register |
| `xp_balances.current_xp` | Server-authoritative (Agent 5 ledger) | — |
| `travel_journals.notes_md` | Collaborative text | RGA |
| `group_trip_items[]` | Set membership | OR-Set |
| `gamification.streak_count` | Counter | G-Counter |
| `subscriptions.*` | Server-only, never client-authoritative | — |
| `reviews.text` | Server with optimistic write | LWW + optimistic lock |
| `bookmarks[]` | Client-authoritative until next sync | OR-Set |

Hybrid Logical Clock (HLC) is generated client-side for ordering; server validates and overrides if drift > N minutes.

---

## 9. Event & Analytics Design

See Agent 7 §4–§10. Key contract:

```
domain table write
   │  (same transaction)
   ▼
event_outbox INSERT
   │
   ▼
outbox reaper (Celery worker)
   │
   ├──► Kafka/Redpanda topic <event_type>
   │       │
   │       ├──► event_log (immutable, partitioned)
   │       ├──► Elasticsearch indexer
   │       ├──► ClickHouse analytics sink
   │       ├──► Notification router (Agent 7 notif tables)
   │       ├──► Cache invalidator (Agent 8 §5)
   │       └──► partner webhooks (signed)
   │
   └──► outbox row DELETED on successful publish
```

Bus choice: **Redpanda** (Kafka-API compatible, no JVM, simpler ops, single-binary). Justified in Agent 7 §4.

CDC for analytics: **Debezium → Kafka → ClickHouse**. Postgres `wal_level=logical`. Replication slots managed in Agent 8.

---

## 10. Security & Compliance Design

Cross-domain references:
- Agent 2 entire: identity, RBAC/ABAC, GDPR workflows, audit Merkle anchors, residency.
- Agent 3 §12: AI safety, prompt-injection signals, NSFW classification.
- Agent 4 §11: license & attribution, DMCA, EXIF privacy stripping.
- Agent 6 §11: PCI DSS scope reduction via Stripe, IAP receipt validation, B2B KYC.
- Agent 8 §12: PII residency, multi-region routing.

**Top-level security invariants enforced in schema:**
1. Every PII-bearing table has RLS enabled by default (CI gate blocks merges that disable it).
2. `users.residency_region` LIST-partitions all PII children to the correct tablespace (`ts_uz` / `ts_eu` / `ts_us` / `ts_global`).
3. `audit_log` is APPEND-ONLY (role-level revoke of UPDATE/DELETE) and hash-chained per row + daily Merkle anchor published to S3 Object Lock + git.
4. Passwords use Argon2id (not bcrypt — bcrypt mentioned in some agents was a slip; Argon2id is the modern recommendation; Agent 2's `password_hashes.algorithm` column enforces the choice at the row level).
5. Idempotency keys live ≥30 days on payment paths (Agent 6 §7, Agent 8 §13).
6. PCI DSS: SilkLens never stores PAN; only Stripe tokens. Apple/Google IAP tokens go to provider-specific receipt store, not main DB.
7. GDPR deletion: 30-day grace window, then cascade-anonymize (not hard-delete on audit-bearing rows; replace with `__deleted__` tombstone preserving FK).
8. Prompt injection: every chat input is scored by Agent 3's `ai_prompt_injection_log`; trust score penalized on repeat offenses.

---

## 11. Scaling Strategy

See Agent 8 entire. Quick reference matrix:

| Table family | Partition by | Cache layer | Shard key (future) |
|---|---|---|---|
| `users` & PII children | `residency_region` (LIST) | Redis (session, hot profile) | `user_id` |
| `heritage_objects` | none (slow growth) | Redis hot detail | `heritage_id` |
| `heritage_views` | `viewed_at` (RANGE monthly) | — | `heritage_id` |
| `embeddings_*` | `entity_id` (HASH 64) | — | `entity_id` |
| `ai_generations` | `created_at` (RANGE monthly) × `user_id` (HASH 8 sub-partition) | — | `user_id` |
| `audit_log` | `created_at` (RANGE monthly) × `tenant_id` (LIST) | — | `tenant_id` |
| `event_log` | `created_at` (RANGE daily) | — | `event_type` |
| `xp_events` | `created_at` (RANGE monthly) | — | `user_id` |
| `notification_delivery_log` | `created_at` (RANGE weekly) | — | `user_id` |
| `payments`, `subscriptions` | none (low volume), idempotent | Entitlement cache (Redis) | `tenant_id` |

**Caching layers (Agent 8 §5):**
- **L1 in-process** (FastAPI LRU, 30-second TTL): plan_features, feature_flags, entitlements, vocabulary lookups
- **L2 Redis** (TTL varies): sessions (12h), hot heritage detail (5min), leaderboards (live sorted-set), AI cache (24h), translation memory (forever until model bump)
- **L3 Postgres** (materialized views): `xp_balances`, `heritage_aggregate_stats`, `tenant_revenue_snapshots` — refreshed by Celery beat

Cache invalidation channel: **Agent 7's event bus**. Subscribers listen to `entitlement.changed`, `heritage.updated`, `xp.delta`, etc.

---

## 12. Future Migration Considerations

From Agent 8 §13:

- **Expand-contract** for every schema change: `ADD COLUMN ... NULL` → backfill in batches via `pg_cron` → `SET NOT NULL` → app reads new column → drop old column in next release.
- **No FK across future shard boundaries.** If `user_id` is a future shard key, do not place FK from `payments.user_id` to a table that lives in a different shard family. Reconciliation jobs validate referential integrity asynchronously.
- **UUIDv7 / ULID** PKs everywhere. Migration off UUIDv4 in any prototype tables before launch.
- **Citus path open** but not adopted at launch. Single-writer Postgres + read replicas suffices to 1M MAU; Citus consideration triggered at sustained >5K writes/s on a single hot table.
- **Backwards-compatible API:** `/api/v1` lives forever; `/api/v2` parallel; mobile sets `X-Min-API-Version` header to opt-in to deprecation timelines.

---

## 13. High-Risk Areas (Consolidated)

The top 15 risks across all eight domains, ranked by blast radius:

| # | Risk | Domain | Mitigation |
|---|---|---|---|
| 1 | HNSW reindex on 50M+ vectors blocks writes | 3, 8 | Partial indexes per `model_version_id`; shadow-index swap; consider dedicated vector store (Milvus/Qdrant) at >100M |
| 2 | GDPR right-to-be-forgotten conflicts with UZ/B2G legal-hold on audit_log | 2, 8 | Hash-only retention: store HMAC of PII fields after deletion, recoverable only with court-ordered key release |
| 3 | RLS policy gap leaks one tenant's revenue to another | 6, 2 | CI gate fails any PR adding a `tenant_id` table without `ENABLE ROW LEVEL SECURITY` + matching policy |
| 4 | IAP receipt validation race conditions; Apple/Google subs not portable to Stripe | 6 | Apple ASN webhook + idempotent state machine; explicit user warning in upgrade flow |
| 5 | Celebrity whale fanout cascade | 5 | Hybrid pull/push fanout, `whale_users` flag at 5K followers (admin-tunable) |
| 6 | Cultural-context moderation false positives | 5, 3 | `moderation_policies` keyed on `region_id`; human-cultural lane; AI never auto-rejects on cultural axis |
| 7 | GPU saturation on single RTX 4090 | 3 | Per-queue Celery concurrency limits; admin-flippable cloud fallback chains; surge pricing for partner traffic |
| 8 | `event_log` growth (36 TB/year @ 10M MAU) | 7, 8 | Daily partitions, Parquet export to MinIO at 90d, S3 Glacier at 1y |
| 9 | Perceptual-hash search degrades at 10M+ assets | 4 | Bucket-prefix works to ~5M; external Milvus/Qdrant binary-vector ANN beyond |
| 10 | Audit Merkle anchor key custody — single point of forgery | 2 | HSM/KMS for signing key; quorum of 3 officers for rotation |
| 11 | `pg_partman`/`pg_cron` failure → writes fail at month boundary | 8 | Dead-man-switch alert: future partition must exist 7d ahead; alert if `pg_partman` hasn't run in 24h |
| 12 | Politically-disputed heritage attribution | 1 | Per-fact provenance is the schema-level answer; presentation layer chooses what to show |
| 13 | B2B auction collusion via shell accounts | 6 | KYC + tax-ID + payout-fingerprint clustering + manual review gate above $X bid |
| 14 | Country-scale offline bundles exceed 10 GB | 4 | Per-region splits, premium-gate large assets, on-demand stream-in for non-essential media |
| 15 | DST / timezone bugs in quiet-hours and streak calculation | 5, 7 | Always store IANA tz on user; compute "today" at delivery time, not enqueue time |

Per-domain `Risks & Open Questions` sections in each file enumerate the long tail.

---

## 14. Recommended Microservice Boundaries

The roadmap calls for a Docker-first deploy with future Kubernetes. The schema design is microservice-ready but does not force microservices. Recommended **modular monolith** for FAZA 1–4, splitting later only where contention forces it.

**Bounded contexts (each is a module today, a service tomorrow):**

| Context | Owns tables from | First split when |
|---|---|---|
| `identity` | Agent 2 | First B2B SSO integration |
| `heritage` | Agent 1 | >50K writes/day on heritage edits |
| `media` | Agent 4 | First photogrammetry GPU contention |
| `ai-orchestration` | Agent 3 | Multi-region AI routing |
| `social` | Agent 5 | Activity-feed write storm |
| `billing` | Agent 6 | First B2G contract requiring audit-isolated infra |
| `notifications` | Agent 7 (notifications subset) | Push delivery > 10M/day |
| `search` | Agent 7 (search subset) | ES cluster needs dedicated team |
| `analytics` | Agent 7 (analytics subset) + ClickHouse | First data-science user |
| `admin` | Cross-cutting admin UI | Permanent cross-cutter; stays a service from the start |

The **outbox + event bus** is the seam along which splits happen. Anything currently a domain event already crosses the future boundary correctly.

---

## 15. Suggested PostgreSQL Extensions

From Agent 8 §14 (versions targeting Postgres 16):

| Extension | Purpose | Required at launch? |
|---|---|---|
| `pgvector` ≥ 0.7 | Vector embeddings + HNSW | YES |
| `postgis` ≥ 3.4 | Geography / proximity | YES |
| `pg_trgm` | Trigram fuzzy match for translation memory + search suggest | YES |
| `pgcrypto` | gen_random_uuid, HMAC for audit chain, password hashing helpers | YES |
| `pg_stat_statements` | Slow query alerting | YES |
| `pg_partman` ≥ 5 | Automatic partition maintenance | YES |
| `pg_cron` | In-database cron (partition creation, materialized view refresh) | YES |
| `ltree` | Threaded comments, taxonomy hierarchy | YES |
| `citext` | Case-insensitive emails | YES |
| `unaccent` | Diacritic-insensitive search | YES |
| `hll` | Approximate distinct counts in analytics | Recommended |
| `pg_repack` | Online table reorg | Recommended |
| `pgaudit` | Compliance-grade audit (companion to our custom chain) | Recommended |
| `pg_jsonschema` or `pg_jsonb_schema` | jsonb validation for translatable columns | Recommended |
| `wal2json` / `pgoutput` | Logical replication for Debezium CDC | YES |
| `pg_uuidv7` (or app-side ULID) | Monotonic UUIDs | YES (or app-generated) |
| `Citus` | Future horizontal sharding | NO at launch |

---

## 16. Caching Strategy

See §11 above and Agent 8 §5.

**Naming convention** (mandatory):
```
sl:<env>:<domain>:<entity>:<id>[:<variant>]    # singular
sl:<env>:<domain>:<entity>:<id>:children       # collection
sl:<env>:lb:<scope>:<period>                   # leaderboard
sl:<env>:ai:<model>:<input_hash>               # AI cache
sl:<env>:entitlement:<user_id>                 # hot lookup
```

**TTL defaults:**

| Data | TTL | Invalidation channel |
|---|---|---|
| Session | 12h | logout / revoke |
| Hot heritage detail | 5m | `heritage.updated` event |
| Heritage list page | 30s | timer |
| Entitlements | 5m + push invalidate | `entitlement.changed` |
| AI cache (deterministic prompts) | 24h | model_version bump |
| Translation memory | ∞ | model_version bump |
| Leaderboard top-100 | live (sorted set) | per-event update |
| Search suggestions | 1h | nightly rebuild |
| Tenant branding | 5m | `tenant.branding.changed` |

---

## 17. Data Retention Strategy

| Table family | Retention | Tier path |
|---|---|---|
| `users` (active) | Forever | Hot |
| `users` (deleted) | Anonymize at +30d, tombstone forever | Hot |
| `audit_log` | 12m hot, 36m warm, then Parquet to MinIO forever | Hot → Warm → Cold |
| `event_log` | 90d Postgres, then Parquet to MinIO 1y, then Glacier | Hot → Cold → Archive |
| `ai_generations` | 90d for free tier, 12m for premium, then summary stats only | Hot → Warm → Aggregate |
| `notification_delivery_log` | 30d | Drop |
| `analytics_events_raw` | 7d in Postgres, streamed to ClickHouse forever | Hot → Warehouse |
| `media_assets` (UGC, deleted) | 30d soft, then hard-delete from MinIO; thumbnails retained 90d for moderation | Hot → Drop |
| `xp_events` | 12m hot, then rollup to `xp_balances` snapshots | Hot → Aggregate |
| `payments`, `invoices` | Forever (legal) | Hot → Warm |

Per-region overrides (UZ PD law, EU GDPR Article 17) take precedence per `users.residency_region`. Implemented via per-partition retention policy in Agent 8 §8.

---

## 18. Backup & Restore Strategy

From Agent 8 §10:

- **PITR** via WAL archive to S3 (or self-hosted MinIO with versioning + lifecycle).
- **Base backups:** nightly via `pgBackRest` or `barman`.
- **Logical backups:** nightly `pg_dump` per schema; long-term retention 12 months.
- **Replication:**
  - 1 synchronous standby (zero-data-loss writes)
  - 2 async replicas (read scaling)
  - 1 delayed replica (24h delay; ransomware recovery)
- **RPO:** ≤ 1 minute (WAL shipping every 60s)
- **RTO:** ≤ 15 minutes (Patroni failover; DNS / pgbouncer reload)
- **Restore drills:** quarterly; tabletop monthly.
- **Cross-region:** at FAZA 6, second region async-replicated; promote-to-primary tested annually.

---

## 19. Final Improvement Recommendations

Beyond what each domain agent recommended, this synthesis layer adds:

1. **Adopt an ADR (Architecture Decision Record) discipline from day one.** Every decision in this stack — jsonb-vs-side-table for i18n, RLS-vs-schema multi-tenancy, Redpanda-vs-Kafka, UUIDv7 — has a real trade-off. Capture each in `docs/adr/NNNN-decision.md`. Two-page max each.

2. **Build the admin panel against the same API that mobile uses.** No "admin-only" endpoints with bypassed auth; admin is a role, not an architecture. This forces the API to actually support all admin use cases instead of growing a side door.

3. **Wire AI cost attribution end-to-end on day one** (Agent 3 `ai_cost_ledger` → Agent 6 `enterprise.api_usage_records`). The B2B revenue story dies if we can't bill back AI costs at API maturity. Cheaper to build now than retrofit at FAZA 5.

4. **CRDT typing is part of the schema, not application code.** Add a `crdt_kind` column on tables that participate in offline sync. Reject writes that don't honor the CRDT contract at API boundary.

5. **The 200-language story must not be a marketing claim.** Per Agent 7 §8, only the top 20 get first-class search treatment. Be honest in the UI about which languages are "machine-translated, unreviewed" — Agent 3 §10's confidence badge belongs on every screen.

6. **CI must enforce schema invariants:**
   - Every table with `tenant_id` has RLS + policy
   - Every table with PII has `residency_region` partition key
   - Every payment-path table has unique idempotency key index
   - Every event-emitting write goes through outbox (linter on raw `NOTIFY`)
   - Every PK is UUIDv7 or ULID (linter on `gen_random_uuid()` in migrations)

7. **The white-label story changes infra economics.** If we onboard 50 white-label tenants in year 1, we are running 50 logical databases on one physical primary. Cap connections per tenant, monitor noisy neighbors via `pg_stat_statements` group-by `tenant_id`.

8. **Plan the "Wikidata firehose" before FAZA 5.** The roadmap says 500K heritage objects globally. A Wikidata SPARQL + Wikimedia Commons ingestion pipeline at that scale will be its own multi-week project. Allocate Agent 4 + Agent 1 engineering time in FAZA 4.

9. **Observability dashboards belong in the same repo as code.** Grafana JSON, Prometheus alert rules, and Postgres slow-query budgets live in `infra/observability/` and are PR-reviewed like code.

10. **A "production readiness review" gate before each FAZA cuts launch risk.** Checklist enforced: indexes profiled, partitions provisioned 90d ahead, RLS audited, cache TTLs justified, GDPR deletion verified end-to-end.

---

## Appendix A — Per-Agent Files

| # | Agent | File | Lines |
|---|---|---|---:|
| 0 | Master synthesis | [`00-MASTER-ARCHITECTURE.md`](00-MASTER-ARCHITECTURE.md) | this file |
| 1 | Core Domain | [`01-core-domain.md`](01-core-domain.md) | 1,567 |
| 2 | Identity, RBAC, GDPR | [`02-identity-rbac-gdpr.md`](02-identity-rbac-gdpr.md) | 1,306 |
| 3 | AI & Vector | [`03-ai-vector-infra.md`](03-ai-vector-infra.md) | 1,255 |
| 4 | Media & Storage | [`04-media-storage.md`](04-media-storage.md) | 1,071 |
| 5 | Social, Gamification, UGC | [`05-social-gamification-ugc.md`](05-social-gamification-ugc.md) | 1,506 |
| 6 | Monetization & Enterprise | [`06-monetization-enterprise.md`](06-monetization-enterprise.md) | 2,150 |
| 7 | Infra, Analytics, Events | [`07-infra-analytics-events.md`](07-infra-analytics-events.md) | 1,382 |
| 8 | Performance & Reliability | [`08-performance-reliability.md`](08-performance-reliability.md) | 800 |
| | **Total** | | **~11,000 + master** |

## Appendix B — Cross-Agent Contracts (Quick Reference)

Anything one agent expects another to provide. Disagreements between agents are resolved here; later docs defer.

- **Everywhere → Agent 2 `users(id) uuid`** for `created_by/updated_by/deleted_by` (NULL allowed for system actors → use service-account user row).
- **Everywhere → Agent 6 `tenants(id) uuid`** for white-label isolation. Default tenant = `'00000000-0000-0000-0000-000000000001'` for single-tenant deploys.
- **Agent 2 → Everyone:** SQL function `app.audit(action, entity_type, entity_id, before jsonb, after jsonb)` is the only path to `audit_log`.
- **Agent 7 → Everyone:** `INSERT INTO event_outbox(...)` is the only path to event publishing.
- **Agent 3 → Agent 1, 4, 5:** consumes `heritage_id`, `media_id`, `user_content_id`; produces `embeddings_*`, `ai_moderation_results`.
- **Agent 8 → Everyone:** partition key choices listed in §11 are binding; CI gate enforces.
- **Agent 6 → Agent 3:** consumes `ai_cost_ledger` for enterprise API billing.
- **Agent 5 → Agent 7:** `notification_triggers_map` declares which events fire which channels.
- **Agent 4 → Agent 8:** offline bundle signing key custody owned by Agent 8 (KMS / HSM tier).

---

*End of master architecture v1.0. Each per-agent file is self-contained at the level of full DDL. This master is the index, the cross-walk, and the integrated 20-question answer.*
