# SilkLens — Progress Tracker

> **Tags:** `v0.1.0-alpha` (FAZA 1-3) · **`v0.2.0-beta`** (FAZA 4-5) · **Last commit:** `20954bb` · **Refreshed:** 2026-05-18

## Kuzatuv joylari

| Joy | Nima ko'rasiz | Yangilanish |
|---|---|---|
| 📋 **`PROGRESS.md`** (bu fayl) | Yuqori darajadagi checklist | Har sessiyada |
| 📘 **`docs/HANDOFF.md`** | Texnik holat + keyingi qadamlar | Har milestone'da |
| 🔗 **GitHub commits** — https://github.com/menarzullayev/silklens/commits/main | Har o'zgarish | Real vaqtda |
| 🟢 **`pytest`:** `make api-test` | 275/275 yashil | Har push'da |
| 🔄 **CI/CD:** GitHub Actions | Avtomatik lint + test | Har push'da |

---

## Pre-push hook (yangi!)

Har `git push`'dan oldin lokal tekshiruv ishlaydi:
```bash
make install-hooks  # birinchi marta o'rnatish
git push            # hook avtomatik: ruff + pytest → fail bo'lsa push to'xtaydi
git push --no-verify  # emergency bypass
```

---

## FAZA 1 — Launch (Hafta 1-2) ✅ TUGADI

### Foundation
- [x] Monorepo + Clean Architecture
- [x] Docker stack 5/5 healthy (Postgres+pgvector, Redis, MinIO, Elasticsearch, Redpanda)
- [x] FastAPI skeleton + Alembic + UUIDv7 gen function
- [x] 5 ADR (monorepo, Postgres SoR, Clean Arch, UUIDv7, provider-switching)
- [x] 3 GitHub Actions workflows (CI, security, release)
- [x] Pre-push git hook (`scripts/hooks/pre-push`)

### Database (migrations 0001-0062, 13 fayl)
- [x] 0001 extensions + UUIDv7
- [x] 0002 tenants + branding + white-label
- [x] 0003 system_settings + feature_flags + controlled_vocabularies
- [x] 0004 users + user_profiles (residency-partitioned)
- [x] 0005 oauth_providers + identities + emails + phones
- [x] 0006 RBAC: permissions + roles + `app.has_permission()`
- [x] 0007 audit_log (HMAC chain) + `app.audit()`
- [x] 0008 event_bus: outbox + log + event_types
- [x] 0009 sessions + refresh_tokens + device_fingerprints
- [x] 0010 heritage_objects + aliases + revisions (bi-temporal)
- [x] 0011 heritage_facts + provenance
- [x] 0062 security_patches: has_permission deleted_at, audit HMAC mandatory

### Backend services (75+ endpoint)
- [x] Auth: register/login/refresh/logout/me (Argon2id + JWT + family rotation)
- [x] BearerContextMiddleware + TenantContextMiddleware (RLS)
- [x] Heritage CRUD: list/get/create/update/delete/aliases/revisions/transitions (RBAC)
- [x] Media: upload/get/signed-url/delete (MinIO + BOLA-safe)
- [x] Social: follow/friend/block/feed (whale-aware fanout)
- [x] Reviews + UGC: ratings/comments/reactions/reports
- [x] Gamification: XP ledger/badges/streaks/leaderboards (atomic idempotency)
- [x] Billing: subs/payments/invoices/webhooks (MockProvider + shared-secret)
- [x] Notifications: templates/push/email/SMS/preferences
- [x] Admin: tenants/branding/settings/feature-flags/ai-models
- [x] Compliance: GDPR export/deletion/anonymization + cookie consent
- [x] Search: Elasticsearch multi-language + vector search
- [x] Reseller: white-label onboarding + B2G tier

### Frontend skeletons
- [x] Flutter (`apps/mobile/`): 24 ekran wired (auth, heritage, camera, map, chat, gamification, billing...)
- [x] Admin panel (`apps/admin/`): 8 sahifa wired (Next.js + shadcn/ui + NextAuth v5)

---

## FAZA 2 — Boost (Hafta 3-4) ✅ ~85% TUGADI

### Backend (fully scaffolded)
- [x] Vision recognition endpoint (`POST /v1/ai/recognize`) — MockProvider
- [x] TTS generation (`POST /v1/ai/tts`) — MockProvider
- [x] Translation memory + pipeline — MockProvider
- [x] pgvector HNSW embeddings — 5 indexes provisioned
- [x] Wikidata SPARQL ingestion (`POST /v1/admin/ingestion/wikidata`)
- [x] Elasticsearch indexer (5-language tiered) + admin rebuild
- [x] Offline bundle infrastructure (Ed25519-signed)
- [x] Media upload pipeline (MIME magic-byte validated)
- [x] Offline mode: Isar cache wired in Flutter
- [x] UGC: review/rating/photo APIs wired

### Deferred (real GPU server kerak)
- [ ] **LLaVA / InternVL** real inference (MockProvider bor)
- [ ] **Kokoro / Piper TTS** real audio (MockProvider bor)
- [ ] **NLLB-200 translation** real pipeline (MockProvider bor)
- [ ] **Mapbox API key** (OSM fallback aktiv)

---

## FAZA 3 — Spark (Hafta 5-6) ✅ ~70% TUGADI

### Backend (fully scaffolded)
- [x] AI Chat (`POST /v1/ai/chat`) — Anthropic SDK (opt-in) + MockProvider
- [x] Gamification: full XP + badges + streaks (backend)
- [x] Social graph: follow/friend/feed
- [x] B2B listings + auctions + API keys
- [x] Billing: freemium plans + entitlements
- [x] Group travel schema (infra ready)

### Deferred
- [ ] AR overlay (real ARCore/ARKit device testing)
- [ ] Route planning AI endpoint (tez yoziladi)
- [ ] App Store / Play Store submission

---

## FAZA 4 — NOVA ✅ TUGADI (commit `a8cc54e`)

- [x] **Rate limiting**: slowapi + Redis, 8 endpoint gated, 423 lockout (SEC-005)
- [x] **Observability**: Sentry SDK, OpenTelemetry, 9 Prometheus metrics, 4 Grafana dashboards, 5 alert rules
- [x] **GDPR + UZ PD-law**: legal_documents, consent_records, gdpr_requests, anonymization, `app.anonymize_user()`
- [x] **Real Stripe provider**: PaymentIntent + webhook signature verification (Stripe-Signature)
- [x] **Anthropic SDK**: ephemeral prompt-cache, streaming, retry-with-backoff
- [x] **Elasticsearch**: 5-language tiered indexer + Wikidata SPARQL ingestion pipeline
- [x] **Code-quality sweep**: 13 review findings fixed (atomic XP, MIME validation, AiRepository extracted, asserts→RuntimeError, N+1, etc.)
- [x] **211 tests** (before FAZA 5 additions)

---

## FAZA 5 — TURBO ✅ TUGADI (commit `deaf0ff`)

- [x] **Central Asia heritage**: KZ 30, TJ 25, TM 20, KG 20 = 95 ta yodgorlik
  - 9 UNESCO inscription, 22 shahar, 49 mamlakat seeded
  - `central_asia` pricing zone ($1.99/oy, $19.99/yil)
  - KZT, TJS, TMT, KGS currencies
- [x] **Multi-currency payments**: Payme (JSON-RPC + Basic-Auth), Click (HMAC-SHA1), PayPal (signed-webhook)
  - Per-currency provider routing (UZS→payme, USD→stripe, fallback→mock)
  - ADR-0006: multi-currency routing decision
- [x] **White-label onboarding**: reseller_application + tenant_revenue_share + B2G partnerships
  - 5 MOU templates in docs/legal/mou-templates/
  - `POST /v1/reseller/applications` (public) + admin workflow
- [x] **MFA**: TOTP (pyotp) + WebAuthn (FIDO2) + backup codes + step-up auth
  - Login → MFA required → challenge → elevated JWT
  - `require_recent_mfa()` dependency wired to sensitive routes
- [x] **275 tests** yashil (consistent)

---

## CI/CD holati (GitHub Actions)

| Workflow | Status |
|---|---|
| CI (lint+test+migrations) | ✅ Yashil (Redis service + libmagic1 + ruff format) |
| Security (Trivy + Bandit + CodeQL) | 🟡 Trivy `@v0.28.0` → hali kechikish bo'lishi mumkin |
| Release (Docker → GHCR + mobile + admin) | ⏳ Versioned tag kerak |

---

## Jami statistika

| Metrika | Qiymat |
|---|---|
| Migration files | 28 ta (0001-0084) |
| DB tables | ~250+ |
| RLS policies | 81 |
| Backend endpoints | 100+ |
| Backend tests | **275/275 yashil** |
| Flutter screens | 24 wired |
| Admin pages | 8 wired |
| Heritage entries | ~200 (UZ 5 UNESCO + CA 95) |
| Commits (main) | 38+ |
| Active tags | `v0.1.0-alpha` + `v0.2.0-beta` |

---

## Keyingi FAZA-lar (FAZA 6-12)

| FAZA | Roadmap | Asosiy ish |
|---|---|---|
| **6 VELOCITY** | Ipak yo'li kengayishi | CN/IR/TR/IN 1200+ yodgorlik; UNESCO hamkorlik |
| **7 QUANTUM** | Evropa + global | IT/GR/EG/MA/JP; 50K+ yodgorlik; fine-tuning |
| **8-12** | HORIZON → APEX | 100K+ yodgorlik; VR/AR; IPO/acquisition |

---

## Nima bajarilmadi (FAZA 1-5 doirasida)

| Item | Sabab |
|---|---|
| Real LLaVA/Kokoro/NLLB | GPU server'ga SSH kerak (university server) |
| Real Stripe live keys | Merchant account kerak |
| App Store / Play Store | Apple Dev account + real device |
| AR overlay | Real ARCore/ARKit device |
| 200+ KZ / 150+ TJ yodgorlik | Wikidata ingestion pipeline bor, data curation kerak |
| Load test 10K users | k6 scripts yozilmagan |
| Mapbox API key | API key kerak |
| WebAuthn real device | Browser + authenticator kerak |
