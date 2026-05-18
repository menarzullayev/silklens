# SilkLens — Progress Tracker

> **Sizning ko'zingiz uchun.** Bu fayl `HANDOFF.md` dan ko'ra qisqaroq — har bir item checkbox bilan.
> Last refresh: 2026-05-18 · Last commit: `0391819`

## Qayerda kuzata olasiz

| Joy | Nima ko'rasiz | Yangilanish |
|---|---|---|
| 📋 **`PROGRESS.md`** (bu fayl) | Yuqori darajadagi checklist | Har commit'da |
| 📘 **`docs/HANDOFF.md`** | Texnik tafsilotlar, keyingi qadamlar, deferred decisions | Har milestone'da |
| 🔗 **GitHub commits** — https://github.com/menarzullayev/silklens/commits/main | Har bir o'zgarish full diff bilan | Real vaqtda |
| 🟢 **`pytest` (lokal)** | 51/51 yashil | Har sessiyada |

---

## FAZA 1 — Launch (Hafta 1-2)

### Hafta 1 — Foundation

- [x] Monorepo struktura + Clean Architecture layout
- [x] Docker Compose stack (Postgres+pgvector / Redis / MinIO / Elasticsearch / Redpanda) — 5/5 healthy
- [x] FastAPI service skeleton + `/health`, `/ready`, `/version`
- [x] Alembic + UUIDv7 funksiyasi (migration 0001)
- [x] 4 ta ADR (monorepo, Postgres SoR, Clean Arch, UUIDv7)
- [x] pytest infrastructure + ruff + mypy konfiguratsiya
- [x] `.env.example` + Makefile + Dockerfile (multi-stage)
- [x] Memory saqlash (9 fayl `~/.claude/projects/.../memory/`)

### Hafta 2 — Foundation migrations (9 dona)

- [x] 0001 — extensions + UUIDv7
- [x] 0002 — tenants + branding + domains (white-label foundation)
- [x] 0003 — system_settings + feature_flags + controlled_vocabularies (7 vocab, 17 terms seeded)
- [x] 0004 — users + user_profiles (residency-partitioned: uz/eu/us/global)
- [x] 0005 — oauth_providers + identities + emails + phones (7 providers seeded)
- [x] 0006 — RBAC: 23 permissions + 5 roles + `app.has_permission()` function
- [x] 0007 — audit_log (Merkle-anchored) + `app.audit()` HMAC hash-chain
- [x] 0008 — event_bus: outbox + log + 17 event types + `app.emit_event()`
- [x] 0009 — sessions + refresh_tokens + device_fingerprints
- [x] 0010 — heritage_objects + aliases + revisions (bi-temporal)
- [x] 0011 — heritage_facts + provenance (fact-level confidence)
- [ ] 0012 — geographic_admin_levels (ltree) + historical_periods
- [ ] 0013 — architectural_styles + dynasties
- [ ] 0014 — heritage_relationships (part_of, near, restored_from)
- [ ] 0015 — heritage_movable_ext + heritage_intangible_ext

### Hafta 2 — Backend services

- [x] Identity domain (entities, errors, protocols, service)
- [x] Argon2id password hasher
- [x] JWT issuer (HS256, access 15min, refresh 30d, family rotation)
- [x] SqlUserRepository + SqlSessionRepository
- [x] `POST /v1/auth/register` (auto-login + 201)
- [x] `POST /v1/auth/login`
- [x] `POST /v1/auth/refresh` (replay defence revokes family)
- [x] `POST /v1/auth/logout`
- [x] `GET /v1/auth/me` (protected)
- [x] `BearerContextMiddleware` decodes Bearer → AuthContext
- [x] `require_user` + `require_permission(slug)` deps
- [x] Heritage domain (entities, errors, repository protocol, service)
- [x] SqlHeritageRepository (emits `heritage.created.v1`)
- [x] `GET /v1/heritage` (filter + paginate, public)
- [x] `GET /v1/heritage/{pub_id}` (public)
- [x] `POST /v1/heritage` (RBAC-gated: `heritage:create`)
- [ ] `PATCH /v1/heritage/{pub_id}` (heritage:update)
- [ ] `DELETE /v1/heritage/{pub_id}` (heritage:delete soft-delete)
- [ ] `POST /v1/heritage/{pub_id}/aliases`
- [ ] Heritage moderation workflow (draft → review → published)
- [ ] OAuth start/callback (Google + Apple + Telegram)
- [ ] Audit middleware (auto-wrap all privileged routes)

### Hafta 2 — Frontend skeletons

- [x] Flutter (`apps/mobile/`) — Clean Arch + Riverpod + Go Router + Isar + 4 ARB locales + HLC CRDT util
- [x] Admin panel (`apps/admin/`) — Next.js 14 + shadcn/ui + 12 routes + NextAuth v5 stub + PermissionGuard
- [ ] Flutter — kamera moduli (FAZA 2)
- [ ] Flutter — xarita integratsiyasi (FAZA 2)
- [ ] Flutter — onboarding "Shazam style" ekran
- [ ] Admin — OpenAPI types regeneratsiya (heritage endpoint live bo'lganda)
- [ ] Admin — branding sahifasi backend bilan ulanishi

### Hafta 2 — CI/CD

- [x] `.github/workflows/ci.yml` — 7 jobs (lint, test, migrations round-trip, mobile, admin)
- [x] `.github/workflows/security.yml` — Trivy + Bandit + CodeQL
- [x] `.github/workflows/release.yml` — Docker→GHCR, mobile artifacts, auto-changelog
- [ ] CI hozircha PR ochilganda ishlamaganga o'xshaydi — birinchi PR'dan keyin testlash

### Hafta 2 — Tests

- [x] 7 unit + 44 integration = **51/51 yashil**
- [x] Migration round-trip: downgrade base → upgrade head clean
- [x] Live curl tests: register → /me → 403 RBAC → public list
- [ ] Load test (k6) — 10K parallel users (FAZA 4)
- [ ] Flutter widget tests beyond skeleton
- [ ] Admin Playwright tests beyond smoke

---

## FAZA 2 — Boost (Hafta 3-4)

> Roadmap: kamera tanish + xarita + audio guide + offline rejim

- [ ] Media migrations (0020+) — `media_assets`, variants, transcoding jobs, perceptual hashes
- [ ] MinIO bucket provisioning + signed URLs
- [ ] AI domain migrations (0030+) — `ai_models`, `ai_providers`, embeddings tables, RAG chunks
- [ ] pgvector HNSW indexes
- [ ] Vision recognition endpoint (`POST /v1/recognize`)
- [ ] LLaVA / InternVL local benchmark
- [ ] Audio guide generation (Kokoro TTS)
- [ ] NLLB-200 translation pipeline
- [ ] Flutter camera screen + recognition flow
- [ ] Mapbox/OpenStreetMap integration
- [ ] Offline bundle generation (Ed25519 signed)

---

## FAZA 3-12 — Roadmap

[`Roadmap.md`](Roadmap.md) — 12 faza, 12 oy. Hozircha FAZA 1 da emas, deyarli yarmida.

---

## Bu sessiya yutuqlari (commit `0391819`)

| Metrika | Qiymat |
|---|---|
| Yangi migrations | 2 (0010, 0011) |
| Yangi tables | ~8 (heritage_objects, aliases, revisions, facts, provenance, fact_provenance + 2 trigger functions) |
| Yangi domains | 1 (heritage) + auth middleware |
| Yangi endpoints | 5 (`/me`, `/logout`, GET heritage list, GET heritage one, POST heritage) |
| Yangi tests | 18 (7 middleware + 11 heritage) |
| Test holati | **51/51 yashil** |
| Lint | ruff + format toza |
| Round-trip | downgrade base ↔ upgrade head clean |

---

## Statistika (jami)

| Metrika | Qiymat |
|---|---|
| Migration | 11 ta (0001-0011) |
| DB tables | ~70 ta |
| Endpoint | 10 ta |
| Test | 51/51 yashil |
| Architecture docs | ~11,000 qator |
| Backend code | ~5,500 qator |
| Frontend skeletons | Flutter (~3K) + Admin (~2K) |
| Commits | 14 ta (main'da) |
| ADRs | 4 ta |
