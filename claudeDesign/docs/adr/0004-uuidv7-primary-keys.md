# ADR 0004 — UUIDv7 (time-ordered) primary keys on every table

- **Status:** Accepted
- **Date:** 2026-05-18

## Context

Agent 8 §7 of the master architecture mandates "ULID/UUIDv7 PKs everywhere; never UUIDv4 on hot tables (destroys B-tree locality)." We need to make this concrete before any migration is written.

UUIDv4 is random and inflates B-tree page splits on every insert; this is a documented pathology at scale. UUIDv7 (RFC 9562, 2024) interleaves a Unix-ms timestamp into the front of the UUID, restoring monotonicity while preserving global uniqueness. ULID is equivalent in spirit. PostgreSQL 17 has native `uuidv7()` but we target Postgres 16 for the launch window.

## Decision

Every table's primary key is `id uuid PRIMARY KEY DEFAULT gen_uuid_v7()` where `gen_uuid_v7()` is a project-supplied SQL function (definition in migration `0001_extensions_and_uuidv7.sql`). When PostgreSQL 17 is widely available we will swap the function body for the native call without changing the table schema.

Function definition (canonical):

```sql
CREATE OR REPLACE FUNCTION gen_uuid_v7() RETURNS uuid AS $$
DECLARE
    unix_ts_ms bytea;
    uuid_bytes bytea;
BEGIN
    unix_ts_ms = substring(int8send((extract(epoch from clock_timestamp()) * 1000)::bigint) from 3);
    uuid_bytes = unix_ts_ms || gen_random_bytes(10);
    -- Set version (7) in the 7th byte
    uuid_bytes = set_byte(uuid_bytes, 6, (b'01110000'::bit(8) | (get_byte(uuid_bytes, 6)::bit(8) & b'00001111'::bit(8)))::int);
    -- Set variant (10xxxxxx) in the 9th byte
    uuid_bytes = set_byte(uuid_bytes, 8, (b'10000000'::bit(8) | (get_byte(uuid_bytes, 8)::bit(8) & b'00111111'::bit(8)))::int);
    RETURN encode(uuid_bytes, 'hex')::uuid;
END;
$$ LANGUAGE plpgsql VOLATILE;
```

Two clarifications:

1. **Public-facing identifiers** (`pub_id`) for heritage objects, users, etc. may use a shorter base58 encoding for URLs (Agent 1 §3). These are separate columns; `id` remains UUID for joins.
2. **Composite keys** are permitted only where the row truly is a many-to-many edge (e.g. `(user_id, badge_id)`); even then we add a surrogate `id uuid` if the row will ever be referenced elsewhere.

## Consequences

**Positive:**

- B-tree locality preserved on heavy-insert tables (audit_log, event_log, xp_events).
- Distributed systems remain ID-conflict-free.
- Sharding by `id` later is straightforward (timestamp prefix gives natural shard bands).

**Negative:**

- Until Postgres 17 we depend on a project-supplied function; tested in migration 0001.
- A small (~10 ns) per-insert cost vs `gen_random_uuid()`; negligible.

## Alternatives considered

- **bigserial / bigint** — leaks information (count of inserts), poor for global systems, breaks future sharding. Rejected.
- **ULID** — equivalent; UUIDv7 picked because it's now an RFC standard.
- **Snowflake IDs** — needs coordination service; we don't have one. Rejected.
- **gen_random_uuid()** — rejected per Agent 8 §7.
