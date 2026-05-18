# ADR 0002 — PostgreSQL is the system of record; everything else is derived

- **Status:** Accepted
- **Date:** 2026-05-18

## Context

The architecture pulls in pgvector (embeddings), Redis (cache/leaderboards), Elasticsearch (search), ClickHouse (analytics), MinIO (blobs), and Redpanda (events). Project-Decisions §15 mentions "multi-database" but in a way that frames each store as serving a specific purpose, not as a parallel source of truth.

A naive read of "multi-DB architecture" risks dual-write problems: a heritage update goes to Postgres and Elasticsearch in parallel, one succeeds, the other fails, and the system diverges. Every dual-write team has the same scar.

## Decision

**PostgreSQL 16 (with pgvector and PostGIS extensions) is the single source of truth.** Every other store is a derived projection:

| Store | Role | Refreshed by |
|---|---|---|
| Redis | Cache (sessions, hot reads, leaderboards) | TTL + event-driven invalidation |
| Elasticsearch | Search index, per-language analyzers | CDC (Debezium) from Postgres WAL |
| ClickHouse | OLAP analytics warehouse | Kafka stream sourced from event_log |
| MinIO | Blob storage (media, offline bundles) | Direct writes; metadata mirrored in Postgres |
| Redpanda (Kafka API) | Event bus | Transactional outbox from Postgres |
| In-process LRU | Hot config (entitlements, feature flags) | Event invalidation |

Writes go to Postgres + outbox in the **same transaction**. A worker drains the outbox to Redpanda. Downstream consumers (ES indexer, ClickHouse sink, cache invalidator, partner webhooks) consume from Redpanda.

The "one-click DB switch" requirement from Project-Decisions §15 is satisfied via the Repository pattern at the service boundary — services depend on `interfaces.HeritageRepository`, not on `PostgresHeritageRepository` — but the default implementation is and remains Postgres.

## Consequences

**Positive:**

- No dual-write divergence. Every consumer derives from one log of facts.
- Disaster recovery is one PITR drill, not five.
- We can replay history into any new derived store without re-deriving from a soup of unrelated systems.
- AI agents reason about one ground-truth schema, not many.

**Negative:**

- All write traffic funnels through one Postgres primary. Replicas absorb read load; sharding is a future concern (Agent 8 §7 keeps the option open).
- A complete Postgres outage stops new writes (acceptable: HA replicas + 1-minute RPO mitigate).

## Alternatives considered

- **MongoDB / DynamoDB as primary** — schema-less appeal, but loses transactional outbox correctness and complicates joins. Rejected.
- **Event-sourcing-first** (Kafka as primary) — extreme operational complexity for our team size (1 human + AI agents). Rejected for now; we can layer event sourcing on top of Postgres event_log without flipping the source of truth.
- **Postgres + Cassandra split** — premature optimization. Rejected.
