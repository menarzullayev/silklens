# SilkLens — Session Handoff (Foundation Snapshot)

> ⚠️ **This document is a historical foundation snapshot from FAZA-1.**
> For current project status, **see [`/PROGRESS.md`](../PROGRESS.md)** — single source of truth.
>
> Body below preserves architectural decisions, port assignments, and migration details from the early build phase. It is useful as onboarding/reference material, **not** as live status.

---

## Snapshot — FAZA 1 Hafta 2 (2026-05-18)

**Status at snapshot:** ✅ Foundation + frontends + CI + auth (incl. middleware) + heritage CRUD all shipped.
**Snapshot frozen at:** commit `0391819` — `feat(faza-1): auth middleware + heritage CRUD end-to-end`

For everything after this snapshot (FAZA 2-7, wave-8, auth pipeline ship 2026-05-19) → **`/PROGRESS.md`**.

---

## Where we WERE at the time of snapshot

**Active FAZA:** FAZA 1 — Hafta 2
**Status:** ✅ Foundation + frontends + CI + **auth (incl. middleware)** + **heritage CRUD** all shipped. ⏳ AI vector + media services next.

### Latest milestone

**Heritage CRUD live + Auth middleware** (this session):
- `GET /v1/heritage` (public, filterable: kind / country / status / search, paginated)
- `GET /v1/heritage/{pub_id}` (public, 404 on unknown)
- `POST /v1/heritage` (`heritage:create` permission required, returns 201 with new pub_id)
- `GET /v1/auth/me` (protected — returns AuthContext)
- `POST /v1/auth/logout` (protected — revokes session + refresh family)
- `BearerContextMiddleware` decodes `Authorization: Bearer …` into `request.state.auth`
- `require_user` + `require_permission(slug)` FastAPI dependencies; the latter calls `app.has_permission()` SQL function
- Migration 0010 (`heritage_objects`/`heritage_aliases`/`heritage_revisions` w/ BEFORE-bump + AFTER-log triggers) + 0011 (`heritage_facts`/`heritage_provenance`/`fact_provenance` w/ winning-fact unique index)
- Domain layer (entities/errors/repository protocol/service) + SqlHeritageRepository emitting `heritage.created.v1` into event_outbox
- **51/51 pytest green** (33 prior + 7 middleware + 11 heritage); ruff lint + format clean
- Round-trip downgrade-to-base + upgrade-to-head verified clean across all 11 migrations

### Prior milestone — Auth service core (`0a045bd`)

- `POST /v1/auth/register`, `/login`, `/refresh` (Argon2id + JWT HS256 + refresh family rotation w/ replay defence)
- Clean Architecture layers: domain → infrastructure → api

### What is done and verified

**Infrastructure & Foundation:**
- ✅ Monorepo layout — [ADR-0001](adr/0001-monorepo-layout.md)
- ✅ Docker stack (Postgres 16+pgvector, Redis 7, MinIO, Elasticsearch 8.15, Redpanda 24.2) — `make ps` shows 5/5 healthy
- ✅ Ports: Postgres `5434`, Redis `6381`, MinIO `9000/9001`, Elasticsearch `9200`, Redpanda `19092` (offset from defaults to avoid clashes with co-located stacks)
- ✅ FastAPI Clean Architecture skeleton ([ADR-0003](adr/0003-clean-architecture-layers.md))
- ✅ `/health`, `/ready`, `/version` endpoints — live and tested

**Database (9 migrations applied + round-trip verified):**

| # | Migration | What it lands |
|---|---|---|
| 0001 | extensions_uuidv7 | pgcrypto, pg_trgm, citext, ltree, vector, btree_gist + `gen_uuid_v7()` ([ADR-0004](adr/0004-uuidv7-primary-keys.md)) |
| 0002 | tenants_branding | `tenants`, `tenant_branding`, `tenant_domains` + default tenant seeded |
| 0003 | admin_config | `system_settings`, `feature_flags`, `controlled_vocabularies`, `vocabulary_terms` + 7 vocabs + 9 heritage_kinds + 4 languages + 4 residency_regions |
| 0004 | users | `users` + `user_profiles` partitioned by `LIST(residency_region)` into `_uz/_eu/_us/_global` + system_actor user seeded |
| 0005 | oauth_identities | `oauth_providers` (admin catalog), `oauth_provider_secrets` (privilege isolation), `user_identities`, `user_emails`, `user_phones` + 7 providers seeded |
| 0006 | rbac | `permissions`, `roles`, `role_permissions`, `user_roles` (residency-partitioned), `app.has_permission()` + 23 perms + 5 roles + super_admin granted to system_actor |
| 0007 | audit_log | `audit.audit_log` (RANGE-partitioned monthly), `audit.audit_anchors` (Merkle roots), `app.audit()` with HMAC hash-chain |
| 0008 | event_bus | `event_types` catalog, `event_outbox` (transactional, transient), `event_log` (immutable, daily-partitioned), `app.emit_event()` + 17 events seeded |
| 0009 | sessions | `device_fingerprints`, `sessions`, `refresh_tokens` (residency-partitioned, family-rotated) |

**Test suite:**
- ✅ pytest **23/23 green** (2 unit + 21 integration including hash-chain assertion, event-name rejection, partition checks, RBAC behaviour)
- ✅ ruff lint + format clean
- ✅ Round-trip `alembic downgrade base` → `alembic upgrade head` clean

**Frontend skeletons (parallel-agent output):**
- ✅ `apps/mobile/` — Flutter + Riverpod + Go Router 14 + Isar + dio/retrofit, Clean Architecture, 4 ARB locales, dynamic theme tokens, HLC utility for CRDT sync
- ✅ `apps/admin/` — Next.js 14 + shadcn/ui + TypeScript strict + next-intl, 9 dashboard routes, NextAuth v5 stub, PermissionGuard mirroring server RBAC, Playwright smoke test

**CI/CD:**
- ✅ `.github/workflows/ci.yml` — 7 jobs with paths-filter routing
- ✅ `.github/workflows/security.yml` — Trivy + Bandit + CodeQL matrix
- ✅ `.github/workflows/release.yml` — semver-tag-driven build of API Docker → GHCR + mobile artifacts + admin build + auto-changelog

**Documentation:**
- 4 ADRs ([0001](adr/0001-monorepo-layout.md), [0002](adr/0002-postgres-as-system-of-record.md), [0003](adr/0003-clean-architecture-layers.md), [0004](adr/0004-uuidv7-primary-keys.md))
- 8-domain architecture (~11,000 lines, ~328 tables) under `docs/architecture/` — committed at `2ddd78e`

### What is NOT yet done (next pickups in priority order)

1. **Auth follow-ups still pending:**
   - OAuth start/callback for Google + Apple + Telegram (providers seeded, secrets+endpoints config remaining)
   - Audit middleware wrapping privileged routes to call `app.audit(...)` automatically (currently only emit_event is wired into heritage create)
   - MFA / WebAuthn (deferred per HANDOFF deferred decisions)
2. **Heritage follow-ups:**
   - `PATCH /v1/heritage/{pub_id}` and soft-delete with `heritage:update` / `heritage:delete` perms
   - `heritage:moderate` workflow (status transitions draft → review → published)
   - Fact-resolver background job that computes winning facts from `heritage_facts` rows back into `heritage_objects` denormalized columns
   - Aliases endpoint (`POST /v1/heritage/{pub_id}/aliases`)
3. **Heritage migrations beyond 0011** — geographic hierarchy (`geographic_admin_levels` with ltree), historical periods, architectural styles, full Agent 1 §3 catalog (~25 more tables).
   - `heritage_objects` (root polymorphic table) + `heritage_facts` (provenance-tagged claims) + `heritage_revisions` (bi-temporal) + `heritage_aliases`
   - `geographic_admin_levels` (ltree) + `historical_periods` + `architectural_styles`
   - At minimum `GET /v1/heritage`, `GET /v1/heritage/{pub_id}`, `POST /v1/heritage` (with `heritage:create` permission), search via Elasticsearch tier-1 index
3. **Media service** — migrations 0040–0060 + MinIO bucket provisioning + signed-URL endpoint + transcoding pipeline scaffolding
4. **Remaining ~250 tables** across AI, social, monetization, infra-events (per per-domain `docs/architecture/0N-*.md`)
5. **Open ADRs to write:**
   - `0005-hmac-key-custody.md` (move from env to KMS before any prod RLS audit)
   - `0006-identity-merge-workflow.md` (Apple Hide-My-Email, dual-registration)
6. **First end-of-FAZA tag:** `v0.1.0-alpha` after auth + heritage CRUD ship and CI is green.

---

## How to resume work

```bash
# 1. Boot infra
cd /home/nsn/Workspace/silklens
make dev
make ps                                       # confirm 5/5 healthy

# 2. Activate API venv
cd services/api
source .venv/bin/activate

# 3. Verify green baseline
pytest -q                                     # expect 51/51
ruff check src tests                          # expect clean
alembic current                               # expect 0011_heritage_facts

# 4. Smoke-test the full flow
python -m src &                               # start the API (port 8000)
curl -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@silklens-test.com","password":"DemoPassword12345"}'
# → grab access_token, then:
curl http://localhost:8000/v1/auth/me \
  -H "Authorization: Bearer <access_token>"
curl http://localhost:8000/v1/heritage     # public list

# 5. Drop into the next FAZA — see "What is NOT yet done" above
```

---

## How to add a new bounded-context migration

1. **Read first:** the relevant `docs/architecture/0N-*.md` + `00-MASTER-ARCHITECTURE.md` §4 cross-agent contracts.
2. **File name:** `YYYYMMDD_NNNN_short_description.py` (next sequential — 0010 for heritage).
3. **PK default:** `gen_uuid_v7()`. **Never** `gen_random_uuid()` on hot tables.
4. **Partitioning rules (already in production):**
   - PII tables: `LIST(residency_region)` like users/sessions
   - Append-only event tables: `RANGE(created_at)` monthly or daily
   - Audit log: `RANGE` monthly
5. **Unique constraints on partitioned tables MUST include the partition key.** PostgreSQL requirement, learned the hard way in migration 0005.
6. **Use the helpers in `alembic/_helpers.py`** for `tg_set_updated_at()` trigger.
7. **Every write that mutates a domain entity must call** `app.audit(...)` and `app.emit_event(...)` in the same transaction. New event names must be inserted into `event_types` first.
8. **RLS** stays off until tenant_admin role assignments propagate (next migration after auth service ships).
9. **Test:** add at least one integration test in `tests/test_foundation_schema.py` (or a new file) asserting the table exists, expected indexes are present, seeded data is correct.
10. **Round-trip:** `alembic downgrade base && alembic upgrade head && pytest -q` before commit.

---

## Open architectural questions (deferred decisions)

- **HMAC key custody** for `app.audit()` — currently `SILKLENS_AUDIT_HMAC_KEY` env. Needs HSM/KMS before prod (ADR pending).
- **Apple Hide-My-Email** — affects `user_emails.is_forwarded` semantics; needs concrete handling before launching Apple auth.
- **Photogrammetry GPU contention** — single RTX 4090 hosts vision + TTS + embeddings + 3D. May need cloud RealityCapture surge contract.
- **Uzbek PD law on AI processing** — may require Uz-resident user inference to run only on Uz-soil GPUs; conflicts with global AI fallback.
- **RLS rollout strategy** — should we enable RLS table-by-table as roles get assigned, or all-at-once after a CI gate?

---

## Cross-session memory pointer

```
/home/nsn/.claude/projects/-home-nsn-Workspace-silklens/memory/MEMORY.md
```
Read first. Index → 9 specific memory files (user profile, feedback, project, references).

---

## Repository

- GitHub: https://github.com/menarzullayev/silklens
- Branch: `main` (direct push during pre-launch; GitFlow after `v0.1.0-alpha`)
- CI: ⏳ wired but will only start running once first PR opens against this branch with workflows on `main`. Next push to `main` after this commit will trigger.
- Latest commit: `7b86bee` (foundation milestone)
- Commits behind plan: 0
