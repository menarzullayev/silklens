# SilkLens — Session Handoff

> **Last updated:** 2026-05-18 · Last commit: `b4cdc76`
> Keep this file current at the end of every session. It is the entry point for the next agent or developer to pick up without re-reading the entire transcript.

---

## Where we are right now

**Active FAZA:** FAZA 1 — Hafta 1 (foundation week)
**Status:** ✅ Foundation shipped and verified. ⏳ Domain migrations begin next.

### What is done and verified

- ✅ Monorepo layout established per [ADR-0001](adr/0001-monorepo-layout.md)
- ✅ Docker stack (Postgres 16+pgvector, Redis 7, MinIO, Elasticsearch 8.15, Redpanda 24.2) — `docker compose -f infra/docker/docker-compose.yml ps` shows 5/5 healthy
- ✅ Ports: Postgres `5434`, Redis `6381`, MinIO `9000/9001`, Elasticsearch `9200`, Redpanda `19092` (offset from defaults to avoid clashes with co-located projects on this host)
- ✅ FastAPI service skeleton with Clean Architecture per [ADR-0003](adr/0003-clean-architecture-layers.md)
- ✅ `/health`, `/ready`, `/version` endpoints — verified live with `curl`
- ✅ Migration `0001_extensions_uuidv7` applied; round-trip downgrade-upgrade green
- ✅ `gen_uuid_v7()` SQL function per [ADR-0004](adr/0004-uuidv7-primary-keys.md) — version 7 nibble and time-ordering both tested
- ✅ pytest **7/7 green** (2 unit + 5 integration)
- ✅ ruff lint + format clean
- ✅ Architecture docs (`docs/architecture/`) — ~11,000 lines, ~328 tables across 8 specialist designs + master synthesis (committed previously, `2ddd78e`)

### What is NOT yet done (next pickups in priority order)

1. **Migrations 0002–0010 — core foundation tables** (per [ADR-0001](adr/0001-monorepo-layout.md) + master architecture §4 cross-agent contracts):
   - `tenants` (default tenant seeded with id `00000000-0000-0000-0000-000000000001`)
   - `users` partitioned by `residency_region` LIST per Agent 2 architecture
   - `system_settings` (admin-managed runtime config rows)
   - `feature_flags`
   - `audit_log` partitioned monthly + `audit_anchors` (Merkle daily roots)
   - `event_outbox` + `event_log` daily partitioned
   - `controlled_vocabularies` + `vocabulary_terms` + `taxonomy_nodes`
   - `oauth_providers` (admin registry)
2. **Per-domain migrations** for the remaining ~280 tables — 8 domains, each owning its own `alembic/versions/` revisions.
3. **Identity / auth service** — register, login, OAuth (Google + Apple + Telegram), JWT issue/refresh, RBAC middleware, audit-log writer wrapping `app.audit(...)`.
4. **Heritage CRUD** — minimal endpoint surface to ship FAZA 2 obida-tanish dependency.
5. **GitHub Actions CI** — lint + test + build + Trivy/Bandit security scan.
6. **Flutter mobile skeleton** — Clean Architecture, Riverpod, Go Router, Isar.
7. **Admin panel skeleton** — Next.js 14 + shadcn/ui.

---

## How to resume work

```bash
# 1. Boot infra
cd /home/nsn/Workspace/silklens
make dev
make ps                    # confirm 5/5 healthy

# 2. Activate API venv
cd services/api
source .venv/bin/activate

# 3. Verify green baseline before touching anything
pytest -q                  # expect 7/7
ruff check src tests       # expect clean
alembic upgrade head       # idempotent

# 4. Generate next migration scaffold
alembic revision -m "your description"
# Edit the generated file under alembic/versions/

# 5. Apply and test
alembic upgrade head
pytest -q
```

---

## How to add a new bounded-context migration

Architecture says migrations are hand-authored (not autogenerate) because we use PG features Alembic can't infer: RLS, partitions, GIN/GiST/HNSW indexes, partial indexes, EXCLUDE constraints, CHECK constraints with subqueries, custom enums via `controlled_vocabularies`.

1. **Read first:** the relevant `docs/architecture/0N-*.md` for that domain, plus `00-MASTER-ARCHITECTURE.md` §4 (cross-agent contracts) and Appendix B.
2. **Naming:** `YYYYMMDD_NNNN_short_description.py` (ISO date + zero-padded sequence).
3. **Use `gen_uuid_v7()` for every PK default.**
4. **Every PII table must declare `residency_region` and partition on it** per [ADR-0002](adr/0002-postgres-as-system-of-record.md).
5. **Every tenant-bearing table must enable RLS** in the same migration that creates it; a follow-up migration adding RLS is too easy to forget.
6. **Write an integration test in `tests/`** asserting at least: table exists, indexes exist, FK constraints are correct, default values fire.
7. **Run downgrade-upgrade** round-trip locally before committing.

---

## Open architectural questions (deferred decisions)

Tracked here so we don't lose them. Promote to ADR when decided.

- **HMAC key custody for audit chain** ([ADR-pending]) — `audit_hmac_key` is currently a dev env var. Production needs HSM/KMS. Decide before the first prod-bound RLS audit.
- **Apple Hide-My-Email forwarding** — affects `user_emails.primary` semantics in identity domain. Needs concrete handling before launching Apple auth.
- **Photogrammetry GPU contention** — single RTX 4090 hosts vision + TTS + embeddings + 3D processing. Project-Decisions §29 promises AR; we may need cloud RealityCapture surge contract. Budget unresolved.
- **Per-jurisdiction PD law conflicts** — Uzbek PD law may require processing (not just storage) on Uzbek soil; conflicts with global AI provider routing. Legal review needed before FAZA 4 launch.

---

## Cross-session memory pointer

Long-running project context lives at:
```
/home/nsn/.claude/projects/-home-nsn-Workspace-silklens/memory/MEMORY.md
```
Read it first in any new session. The MEMORY.md is an index; specific facts are in sibling files (user profile, feedback, project notes, references).

---

## Repository

- GitHub: https://github.com/menarzullayev/silklens
- Branch: `main` (direct push during pre-launch; will switch to GitFlow once a team forms or v0.1.0-alpha tags)
- CI: not yet wired (pickup #5 above)
