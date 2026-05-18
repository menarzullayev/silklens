# SilkLens — Progress Tracker

> **Tag:** `v0.1.0-alpha` · Last commit: `914cce0` · Refreshed: 2026-05-18

## Qayerda kuzata olasiz
- 📋 **`PROGRESS.md`** (bu fayl) — checklist
- 📘 **`docs/HANDOFF.md`** — texnik holat
- 🔗 **GitHub:** https://github.com/menarzullayev/silklens
- 🏷️ **Release:** https://github.com/menarzullayev/silklens/releases/tag/v0.1.0-alpha
- 🟢 **`pytest`:** 145/145 yashil

---

## FAZA 1 — Launch (Hafta 1-2)

### Foundation ✅
- [x] Monorepo + Clean Architecture
- [x] Docker stack 5/5 healthy
- [x] FastAPI + Alembic + UUIDv7
- [x] 4 ADRs
- [x] CI/CD: 3 GitHub Actions workflows

### Database migrations (13 fayl, 0001 → 0062) ✅
- [x] 0001 extensions + UUIDv7
- [x] 0002 tenants + branding + domains
- [x] 0003 system_settings + feature_flags + controlled_vocabularies (17 seeded)
- [x] 0004 users + user_profiles (residency-partitioned)
- [x] 0005 oauth_providers + identities + emails + phones (7 providers)
- [x] 0006 RBAC: 23 perms + 5 roles + `app.has_permission()`
- [x] 0007 audit_log (HMAC chain) + `app.audit()`
- [x] 0008 event_bus: outbox + log + 17+14 event types
- [x] 0009 sessions + refresh_tokens + device_fingerprints
- [x] 0010 heritage_objects + aliases + revisions (bi-temporal triggers)
- [x] 0011 heritage_facts + provenance (7 sources)
- [x] 0012 geography: countries (49) + cities (9) + admin_levels (ltree)
- [x] 0013 taxonomies: historical_periods (18) + styles (8) + dynasties (8)
- [x] 0014 heritage_relations + unesco_inscriptions (5 UZ) + events
- [x] 0015 heritage_indexes + tsvector search_vector
- [x] 0020 media_assets + variants + storage_locations
- [x] 0021 media_pipeline: presets + jobs + lifecycle + signed_url_grants
- [x] 0022 media_licensing: 10 license types + DMCA
- [x] 0023 offline_bundles: Ed25519-signed
- [x] 0030 ai_registry: 10 providers + 16 models + 4 fallback chains
- [x] 0031 embeddings: per-(target,model,dim) tables + 5 HNSW indexes
- [x] 0032 ai_runtime: generations + jobs + cache + token_usage + cost_ledger
- [x] 0033 ai_safety_and_tm: translation_memory + prompt_injection_log
- [x] 0040 social_graph: follows + friendships + activity feed
- [x] 0041 reviews_and_ugc: multi-dim ratings + ltree comments + reactions
- [x] 0042 gamification: badges (12) + xp_events ledger + levels (5) + leaderboards
- [x] 0043 moderation_pipeline: queue + actions + reports + sockpuppet graph
- [x] 0050 products_pricing: 15 currencies + 7 zones + 9 features
- [x] 0051 subscriptions: state machine + dunning
- [x] 0052 payments_invoicing: idempotent webhooks + SLN-YYYY invoice trigger
- [x] 0053 b2b_enterprise: listings + sealed-bid auctions + API keys + affiliates
- [x] 0054 rls_tenancy: 81 RLS policies + helper functions
- [x] 0060 notifications: templates + push + email/SMS + webhooks_outbound
- [x] 0061 search_jobs: search index sync + cron + analytics sink
- [x] 0062 security_patches: has_permission deleted_at + audit fallback removal + missing events

**Total: ~220 jadval, 8 funksiya, 81 RLS policy, ~75 seed-data row**

### Backend services ✅
- [x] Identity domain (entities, errors, repositories, service, infrastructure)
- [x] Auth flow: register/login/refresh/logout/me (Argon2id + JWT HS256 + family rotation)
- [x] BearerContextMiddleware + require_permission factory
- [x] TenantContextMiddleware (RLS enforcement)
- [x] Heritage CRUD: list/get/create/update/delete/aliases/revisions/transitions
- [x] Media: upload/get/signed-url/delete (MinIO integration + BOLA-safe)
- [x] AI service: recognize/chat/translate/tts/search + admin (Mock + Anthropic providers)
- [x] Social: follow/friend/block/feed (hybrid pull/push fanout)
- [x] Reviews + UGC: multi-dim ratings + threaded comments + reactions
- [x] Gamification: XP ledger + badges + streaks + leaderboards
- [x] Billing: subscriptions + payments + invoices + webhooks (MockProvider + shared-secret gate)
- [x] Notifications: templates + push devices + preferences + quiet hours
- [x] Admin: tenants/branding/system-settings/feature-flags/ai-models endpoints
- [x] Public meta: /branding /vocab

**75+ endpoints, 145/145 tests green**

### Frontend ✅
- [x] Flutter mobile (`apps/mobile/`): 24 ekran wired
  - Auth: splash, onboarding, sign-in/up/forgot
  - Heritage: list, detail, search, saved (filter+pagination+offline cache)
  - Camera: Shazam-style capture + recognition flow
  - Map: flutter_map OSM/Mapbox with marker preview
  - Chat: AI bubbles + TTS playback
  - Profile: 5-tab activity/saved/reviews/friends/settings
  - Gamification: XP card, streak, badges grid, leaderboard
  - Billing: plans, checkout, manage sub, invoices
  - Clean Architecture enforced; 4 ARB locales (uz/en/ru/zh)
- [x] Admin panel (`apps/admin/`): 8 sahifa wired
  - Dashboard, Heritage CRUD (5-tab detail), Tenants, Branding,
    Settings, Feature flags, AI models, Moderation placeholder
  - NextAuth v5 silent refresh
  - 8 Playwright tests
  - RBAC PermissionGuard aligned with backend

### Wave 4 — Review + Critical fixes ✅
- [x] Code review: 3 Critical + 6 High + 7 Medium + 6 Low → docs/code-review-2026-05-18.md
- [x] Security review: 4 Critical + 5 High + 6 Medium + 8 Low → docs/security-review-2026-05-18.md
- [x] Fixed CRIT-1/SEC-006: TenantContextMiddleware (RLS now enforced)
- [x] Fixed CRIT-2/SEC-012: atomic refresh-token rotation
- [x] Fixed CRIT-3/SEC-001: webhook shared-secret + provider allow-list
- [x] Fixed SEC-002: audit HMAC fallback constant removed
- [x] Fixed SEC-003: media GET tenant filter (BOLA)
- [x] Fixed SEC-004: refresh-token HMAC (not bare SHA)
- [x] Fixed SEC-007: openapi.json gated by env != 'prod'
- [x] Fixed SEC-008: has_permission requires deleted_at IS NULL
- [x] Fixed HIGH-1: heritage get_by_pub_id deleted_at filter

### Tag ✅
- [x] `v0.1.0-alpha` released

---

## FAZA 2 — Boost (Hafta 3-4)

> **Status:** ~85% scaffolded, AI integration deferred to FAZA 4 (real GPU server work)

- [x] Camera UI (Flutter screen wired to /v1/ai/recognize)
- [x] Vector search backend (pgvector HNSW)
- [x] Map screen wired (flutter_map OSM)
- [x] Heritage detail page + multi-language UI
- [x] Offline mode v1 (Isar cache + heritage list)
- [x] UGC: photo upload, reviews, ratings (backend + Flutter)
- [x] Push notification scaffolding (FCM stub)
- [x] Admin: heritage CRUD UI
- [ ] **REAL LLaVA / InternVL benchmark on GPU server** (MockProvider in place)
- [ ] **REAL Kokoro / Piper TTS on GPU server** (MockProvider in place)
- [ ] **REAL NLLB-200 translation pipeline** (MockProvider in place)
- [ ] Heritage bulk import (Wikidata SPARQL → Postgres)
- [ ] Real-device camera testing
- [ ] Mapbox API key wiring (OSM fallback active)

---

## FAZA 3 — Spark (Hafta 5-6)

> **Status:** ~70% scaffolded, hardware-dependent features deferred

- [x] AI Chat backend (/v1/ai/chat + Flutter ChatPage)
- [x] Gamification UI (XP, badges, streaks, leaderboard)
- [x] Social features (follow, friends, feed)
- [x] B2B listings backend (Auctions + featured slots)
- [x] B2B admin endpoints
- [x] Freemium plan structure + entitlements
- [ ] AR overlay (deferred — needs real device + ARCore/ARKit testing)
- [ ] Historical AR reconstruction (deferred)
- [ ] Route planning AI endpoint
- [ ] Turn-by-turn navigation (Flutter)
- [ ] Hotel/restaurant integration UI (Booking.com / Yandex)
- [ ] Group travel real-time channels (WebSocket)
- [ ] App Store / Play Store submission (deferred — needs Apple dev account)

---

## Statistika (jami)

| Metrika | Qiymat |
|---|---|
| Migration files | 28 ta (0001-0062) |
| DB tables | ~220 |
| RLS policies | 81 |
| SQL functions | 8 (gen_uuid_v7, has_permission, audit, emit_event, set_tenant_context, …) |
| Backend endpoints | 75+ |
| Backend tests | **145/145 yashil** |
| Backend code | ~12,000+ qator (services/api/src) |
| Flutter screens | 24 wired |
| Flutter tests | 16 widget + unit |
| Admin pages | 8 wired |
| Admin tests | 8 Playwright |
| Architecture docs | ~11,000 qator (9 fayl docs/architecture/) |
| ADRs | 4 |
| Commits | 25+ (main'da) |
| Tags | v0.1.0-alpha |

---

## v0.1.0-alpha → v0.2.0-beta gacha qoldi

**Production hardening (FAZA 4 work):**
- Rate limiting (slowapi + Redis) on auth routes
- MIME magic-byte validation on media uploads
- Real provider integrations: Stripe + Apple IAP + Google IAP + Stripe webhook signature
- Real AI models on GPU server: LLaVA/InternVL benchmark, Kokoro/Piper TTS, NLLB-200
- Anthropic SDK opt-in for prod (ANTHROPIC_API_KEY)
- KMS for audit HMAC key + Stripe secret
- MFA / WebAuthn
- OAuth Google/Apple/Telegram start/callback wiring
- Atomic XP idempotency via `INSERT ON CONFLICT DO NOTHING RETURNING`
- Extract AiRepository (ADR-0003 cleanup)
- Replace bare `assert` with explicit raise
- AR module on real iOS/Android devices
- Wikidata SPARQL ingestion job
- Mapbox API key
- Load testing (k6) — 10K parallel users
- App Store + Play Store submission
