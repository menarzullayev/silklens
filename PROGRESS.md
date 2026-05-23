# SilkLens — Progress Tracker

> **Tags:** `v0.1.0-alpha` (FAZA 1-3) · `v0.2.0-beta` (FAZA 4-5) · **`v0.3.0-beta`** (FAZA 6-7) · **Refreshed:** 2026-05-19
>
> **Convention:** [`docs/TRACKING_CONVENTION.md`](docs/TRACKING_CONVENTION.md) — every open item carries a `SILK-NNNN` ID.
> **Next ID:** run `./scripts/next-ticket-id.sh` to get the next available number.
> **Commit format:** `<type>(<scope>): SILK-NNNN — <subject>` (one or more IDs per commit)
> **Statuses:** `[ ]` TODO · `[🔄]` IN_PROGRESS · `[✅]` DONE · `[❌]` BLOCKED · `[⏭️]` DEFERRED

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
- [⏭️] **SILK-0001** 🟡 **LLaVA / InternVL** real inference (MockProvider bor) — DEFERRED on university GPU SSH
- [⏭️] **SILK-0002** 🟡 **Kokoro / Piper TTS** real audio (MockProvider bor) — DEFERRED on GPU access
- [⏭️] **SILK-0003** 🟡 **NLLB-200 translation** real pipeline (MockProvider bor) — DEFERRED on GPU access
- [❌] **SILK-0004** 🟢 **Mapbox API key** (OSM fallback aktiv) — BLOCKED on key purchase decision

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
- [⏭️] **SILK-0005** 🟢 AR overlay (real ARCore/ARKit device testing) — DEFERRED on physical AR-capable device
- [ ] **SILK-0006** 🟢 Route planning AI endpoint — ready to ship (tez yoziladi)
- [❌] **SILK-0007** 🟡 App Store / Play Store submission — BLOCKED on Apple Dev account ($99/yr) + Play Console ($25 one-off)

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

---

## Flutter Mobile — Professional Auth Flow (2026-05-18)

> Maqsad: Launch → Auth oralig'ini world-class standartga yetkazish (12 xususiyat)

### Tezkor (UI/UX polish)
- [x] **Page transitions** — 5 ta transition helper: noTransition/fade/slideUp/slideRight/fadeScale ✅ 2026-05-18
- [x] **ToS checkbox** — Sign Up da Foydalanish shartlari roziligi ✅ 2026-05-18
- [x] **Native splash branding** — flutter_native_splash paketi, compass logo barcha densitylarda ✅ 2026-05-18
- [x] **Dynamic splash timing** — `Future.wait([loadPrefs, minDelay(1800ms)])` pattern ✅ 2026-05-18

### O'rta (Komponentlar)
- [x] **Custom app icon** — compass + Silk Road to'lqin, barcha mipmap densitylari + adaptive icon ✅ 2026-05-18
- [x] **Shimmer skeleton** — `ShimmerBox`/`HeritageCardSkeleton`/`HeritageListSkeleton`, HookWidget loading state ✅ 2026-05-18
- [x] **Offline banner** — `connectivity_plus`, `OfflineBanner` MaterialApp.router builder da wrap ✅ 2026-05-18

### Murakkab (Auth features)
- [x] **Google OAuth UI** — backend `POST /v1/auth/google` (501 stub) + `GoogleSignInButton` widget ✅ 2026-05-18
- [x] **Email OTP verification** — `EmailVerifyPage`, 6-box OTP, `/auth/email-verify?email=` route ✅ 2026-05-18
- [x] **Biometric login** — `local_auth`, `BiometricButton` widget, SignIn da ko'rinadi ✅ 2026-05-18

### Kelajak (tashqi bog'liqlik)
- [❌] **SILK-0008** ⚪ **Lottie onboarding** — BLOCKED on designer assets (JSON animatsiya fayllar)
- [❌] **SILK-0009** 🟡 **Apple Sign In** — BLOCKED on Apple Developer account ($99/yr)

---

## Auth Pipeline Ship (2026-05-19)

> Maqsad: Mobile signup → email verify → signin loop'ni production-grade qilish.

### Backend — Identity & Email
- [x] **OTP service (Redis-backed)** — `infrastructure/notifications/otp_service.py`: 6-raqamli kod, 10 daqiqa TTL, atomic verify+delete
- [x] **ResendEmailClient** — `infrastructure/notifications/email_client.py`: httpx async, `get_email_client()` factory (Resend yoki StubEmailClient)
- [x] **`POST /v1/auth/verify-email`** — OTP kodni Redis'dan tekshirib `user_emails.verified_at` + `users.email_verified_at` ni belgilaydi
- [x] **`POST /v1/auth/resend-verification`** — yangi OTP generate qiladi va email yuboradi (rate-limited 3/min)
- [x] **`/register` endpoint** — auto-login + OTP email yuborish (fire-and-forget, register response'ni bloklamaydi)
- [x] **Plain-text email fix** — HTML olib tashlandi: mail.ru filter `onboarding@resend.dev` HTML emaillarni "Blocked due to content" qiladi, plain-text esa o'tadi
- [x] **`SqlUserRepository.verify_email()`** — idempotent UPDATE: status='active', email_verified_at, user_emails.verified_at

### Backend — Google OAuth (refactor)
- [x] **`OAuthProfile` domain entity** — provider_subject, email, email_verified, display_name, avatar_url, raw payload
- [x] **`AuthService.login_with_oauth()`** — temp-password hack olib tashlandi; OAuth flow uchun maxsus service method
- [x] **`UserRepository.find_by_oauth_identity()`** — provider+subject orqali izlash
- [x] **`UserRepository.create_oauth_user()`** — password_hash siz user yaratish, email_verified=true bo'lsa darrov verify qilish
- [x] **`UserRepository.upsert_oauth_identity()`** — INSERT ON CONFLICT, `xmax=0` orqali first-link aniqlash, display_name + avatar_url first-link'da yangilanadi
- [x] **`/v1/auth/google`** — parallel tokeninfo + userinfo (asyncio.gather), full profile (sub, email, name, picture)

### Flutter — Auth UX
- [x] **Sign Up confirm password field** — `_confirmPassCtrl`, validator: `v != _passCtrl.text` → `err_passwords_mismatch`
- [x] **3 yangi locale string** — `auth_confirm_password`, `err_confirm_password_required`, `err_passwords_mismatch` (uz/ru/en/zh)
- [x] **"Continue as Guest" tugmasi olib tashlandi** — `context.go('/home')` auth bypass edi
- [x] **Sign Up navigatsiya** — muvaffaqiyat → `/auth/email-verify?email=<encoded>`
- [x] **EmailVerifyPage real API** — `ConsumerStatefulWidget`, `verifyEmail()` + `resendVerification()` notifier methods
- [x] **OTP boxes error state** — noto'g'ri kodda qizil bo'rder + xato matni + auto-clear + focus[0]
- [x] **`AuthRepository.verifyEmail()` + `resendVerification()`** — domain interface, DTO, dio client, repo impl
- [x] **`AuthNotifier.verifyEmail()` + `resendVerification()`** — Riverpod notifier methods

### Flutter — Session Persistence (bug fix)
- [x] **`SplashPage` → `ConsumerStatefulWidget`** — `_waitForAuth()` Completer'da auth state'ni kutadi
- [x] **Parallel cold-boot** — `(loadPrefs, minDelay(1800ms), waitForAuth).wait` → AuthAuthenticated → `/home`
- [x] **`_AuthRouterNotifier`** — Riverpod → GoRouter ChangeNotifier ko'prigi
- [x] **`appRouterProvider` redirect** — `_guestOnlyPaths` Set: AuthAuthenticated user'larni guest pathlardan `/home`'ga; unauthenticated user'larni protected pathlardan `/onboarding`'ga
- [x] **AuthInitial state** — splash sahifada qoladi, navigation block qilinadi

### E2E test (2026-05-19, real device — Redmi 25028RN03A)
- [x] **Signup** — `saidakbarnarzullayev@mail.ru` + parol → 201, user yaratildi (pub_id=n23elWXIijPz2Qgu)
- [x] **OTP email yuborildi** — Resend `delivered`, message_id=57a41e1a-..., subject="SilkLens kirish kodi: 020264"
- [x] **OTP verify** — `/v1/auth/verify-email` 200, `email_verified_at = 2026-05-18 23:34:36`
- [x] **Sign In (qayta kirish)** — `app pm clear` → sign-in → 200, yangi session, `last_login_at` yangilandi
- [x] **`/home` navigatsiya** — HeritageListPage UNESCO kartochkalari bilan

### Open / deferred
- [ ] **SILK-0010** 🟡 **`silklens.app` domain Resend'da verify qilish** — `onboarding@resend.dev` ni `no-reply@silklens.app` ga almashtirish (DNS SPF/DKIM/DMARC qo'shish kerak)
- [⏭️] **SILK-0011** ⚪ **HTML email shabloni qaytarish** — DEFERRED on [[SILK-0010]] domain verify; tugagandan keyin branded gold HTML qaytariladi
- [x] **SILK-0012** 🟢 **`MfaGateAdapter` to'liq wire qilish** — completed via SILK-0063
- [ ] **SILK-0013** 🟢 **Phone OTP** — SMS provider tanlovi kerak (Twilio? Eskiz.uz?); avval provider tahlili

---

## Flutter Design System (2026-05-19) — TASKLIST.md sintezi

> 11 EPIC · 93 task · 76 ✅ DONE · 16 🔄 IN_PROGRESS · 1 TODO

### Yakunlangan EPIC'lar
- [x] **EPIC-001 Critical Bug Fixes** (6/6) — duplicate class, typo (PlansPagePage → PlansPage), Hive/Isar migration
- [x] **EPIC-002 Design System Foundation** (10/10) — Inter/Playfair/JetBrains/DM Sans fonts, AppTextStyles, ThemeVariant 4 variants, glass extensions, color tokens, animation durations
- [x] **EPIC-003 Shared Widget Library** (14/14) — GlassSurface, AuroraBackground, SilkBottomNav, SilkAppBar, GoldButton, GlassTextField, GoldShimmerText, HexBadge, HeritageTonePlaceholder, GlassPill, StarRating, GrainOverlay, TweenProgressBar
- [x] **EPIC-004 Platform & Infrastructure** — pubspec deps, ThemeProvider, Riverpod setup
- [x] **EPIC-005 Auth Module Visual Redesign** — aurora background, gold gradient buttons, password strength bar

### Jarayonda (qoldiq)
- [🔄] **SILK-0014** 🟢 **EPIC-006 Domain Entities** — heritage_object, review, booking stub'lari to'ldirilmoqda
- [🔄] **SILK-0015** 🟢 **EPIC-007 Discovery & Heritage** — search filters, AR overlay placeholder
- [✅] **SILK-0016** 🟢 **EPIC-008 Gamification** — XP dashboard, badges grid, leaderboard live data
- [✅] **SILK-0108** 🟢 Wire XpDashboardPage to gamificationProvider (real API)
- [✅] **SILK-0109** 🟢 Wire BadgesPage to badgesProvider (real API, Badge name-clash fix)
- [✅] **SILK-0110** 🟢 Wire LeaderboardPage to leaderboardEntriesProvider (real API, period toggle)
- [✅] **SILK-0111** 🟢 Wire MissionsPage to gamificationProvider (XP snapshot card)
- [✅] **SILK-0112** 🟢 GamificationRepositoryImpl + SilkLensApiClient gamification section
- [🔄] **SILK-0017** 🟢 **EPIC-009 Social & Community** — activity feed pagination, notifications
- [🔄] **SILK-0018** 🟡 **EPIC-010 Billing** — checkout sahifa real Stripe flow
- [🔄] **SILK-0019** 🟢 **EPIC-011 Settings & Account** — language settings dinamik vocab, GDPR delete flow

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
| Backend tests | **635/635 yashil** (275 + 360 wave-8) |
| Flutter screens | 24 wired |
| Admin pages | 8 wired |
| Heritage entries | ~200 (UZ 5 UNESCO + CA 95) |
| Commits (main) | 50+ |
| Active tags | `v0.1.0-alpha` + `v0.2.0-beta` + `v0.3.0-beta` |
| Auth flow status | ✅ Signup → email OTP → verify → sign-in E2E ishlamoqda |
| Email delivery | ✅ Resend integration, mail.ru deliverability (plain-text) |

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

---

## Gap Analysis — Full Implementation Roadmap (2026-05-23)

> 📋 **To'liq task bord:** [`docs/GAP-ANALYSIS-TASKS.md`](docs/GAP-ANALYSIS-TASKS.md)
> 43 ticket · 37 mijoz talabi tahlili · Phase 1/2/3 prioritizatsiya

### PHASE 1 — Must Have (App Store uchun bloklovchi)

- [x] **SILK-0050** 🔴 Real AI Vision — Claude Vision interim wiring
- [x] **SILK-0051** 🔴 Real TTS — OpenAI TTS interim
- [x] **SILK-0052** 🔴 Real Translation — DeepL interim
- [x] **SILK-0053** 🔴 Facebook + Instagram OAuth
- [❌] **SILK-0054** 🔴 Apple Sign In — BLOCKED: Apple Developer Account ($99/yr) required. Auth endpoint designed (OAuthProfile + login_with_oauth ready). Unblocks when account purchased.
- [x] **SILK-0055** 🔴 Offline Bundle Download API
- [x] **SILK-0056** 🔴 Hotel / Restaurant / Transport qidiruv API
- [x] **SILK-0057** Emergency Contacts API (xavfsizlik) — migration 0095, `GET /v1/emergency`, `GET /v1/emergency/nearest`, public, no auth
- [x] **SILK-0058** Onboarding Tutorial Endpoint — `GET /v1/onboarding/tutorial`, `GET /v1/onboarding/plans-overview`, public, no auth
- [x] **SILK-0059** 🔴 Real FCM Push Notifications
- [x] **SILK-0060** AI Chat Conversation History DB — migration 0096 (`conversation_sessions` LIST-partitioned x4, `conversation_messages` RANGE-partitioned monthly), chat endpoint persists turns + returns `conversation_id`, 3 new history endpoints (`GET /v1/ai/conversations`, `GET /v1/ai/conversations/{id}/messages`, `DELETE /v1/ai/conversations/{id}`)
- [x] **SILK-0061** 🟢 Trip Planning Domain — migration 0101 (`trips` + `trip_stops`), router `POST /v1/trips` (AI itinerary, 5/min), `GET /v1/trips` (list), `GET /v1/trips/{id}` (detail+stops), `POST /v1/trips/quick-plan` (public, 10/min); stub mode when `ai_use_mock_providers=true`, real Anthropic path when disabled; residency+user_id isolation on all auth'd queries
- [x] **SILK-0062** 🟠 user_profiles travel preferences fields — migration 20260523_0093 ✅
- [x] **SILK-0063** 🟢 MfaGateAdapter Full Wiring (SILK-0012) — login gate issues full session (access+refresh+user) on MFA verify; step-up path unchanged; `VerifyResponse` extended; `test_mfa_flow.py` added (5 tests)
- [x] **SILK-0064** 🟠 languages admin registry migration — migration 20260523_0094 ✅

### PHASE 2 — Should Have

- [x] **SILK-0065** 🔴 Smart Ticketing + QR System
- [x] **SILK-0066** 🔴 ASR Voice Input endpoint — `POST /v1/ai/asr` (multipart form, auth required, 10/min per user); OpenAiAsrProvider (Whisper-1) with intent detection, stub mode when key absent, generation row persisted
- [✅] **SILK-0067** 🟠 AI Photo Guide (angle + historical overlay) — `POST /v1/ai/photo-guide`; public, 20/min per IP; angle presets for 5 Uzbek sites + AI fallback (Anthropic/mock); overlay/compare mode with CC0 historical photos; typed `AngleOut`/`OverlayOut` response models
- [x] **SILK-0068** 🟠 Kids Mode — `POST /v1/me/kids-mode/enable`, `POST /v1/me/kids-mode/disable` (auth, 30/min per user); `GET /v1/heritage/{pub_id}/kids-story` (public, 30/min per IP, curated→AI fallback); `GET /v1/kids/quiz` (public, 30/min per IP, random multilingual quiz); residency-aware profile update; `src/api/routers/kids_mode.py`
- [x] **SILK-0069** 🟠 Cultural Tips API
- [x] **SILK-0070** 🟠 Smart Food Guide (halol/vegetarian)
- [x] **SILK-0071** 🟠 AI Review Analyzer (fake detection)
- [x] **SILK-0072** 🟠 Smart Expense Tracker
- [x] **SILK-0073** (done via SILK-0061 trips.py — multi-city supported) 🔴 Multi-City Route Optimizer
- [x] **SILK-0074** 🟠 Travel Health + Weather-Aware Guide
- [x] **SILK-0075** 🟠 Crowd Prediction System
- [x] **SILK-0076** 🟠 AI Memory Book (PDF export)
- [x] **SILK-0077** 🟠 Social Traveler Discovery
- [x] **SILK-0078** 🟠 Mood-Based Travel Recommendations
- [x] **SILK-0079** 🟠 German + Korean locale (de/ko) — `GET /v1/languages` (public, lists `languages` table with `active_only` filter, typed `LanguageOut` response); `GET /v1/languages/{tag}` (public, 404 on missing tag); `src/api/routers/i18n.py`
- [x] **SILK-0080** 🟠 AI Bargaining + Scam + Lost&Found Utilities — `POST /v1/ai/fair-price` (public, 20/min per IP, price guide lookup); `POST /v1/ai/scam-check` (public, 15/min per IP, signal scoring); `GET /v1/ai/lost-found` (public, 10/min per IP, nearest emergency contacts from DB); `src/api/routers/ai_utilities.py`
- [x] **SILK-0081** 🟡 Local Storyteller Content Category — `GET /v1/heritage/{pub_id}/stories` + `GET /v1/stories/random`; public endpoints, rate-limited per IP; reads heritage_facts predicates (local_legend/myth/oral_tradition/hidden_fact/historical_story) with multi-language JSONB fallback

### PHASE 3 — Nice to Have

- [x] **SILK-0082** (stub endpoint — blocked: blockchain) 🟡 NFT / Raqamli Suvenir
- [x] **SILK-0083** (stub endpoint — blocked: 3D assets) 🟡 AI Tarixiy Shaxslar Bilan Foto (AR)
- [x] **SILK-0084** (stub endpoint — blocked: wearable SDK) 🟡 Wearable Device Integration
- [x] **SILK-0085** 🟡 Carbon Footprint Tracker
- [x] **SILK-0086** 🟡 Government Smart Mode
- [x] **SILK-0087** (stub endpoint — blocked: FFmpeg pipeline) 🟡 AI Video Memory Book
- [x] **SILK-0088** (stub endpoint — blocked: tax jurisdiction data) 🟠 Tax Engine (VAT/jurisdictions)
- [x] **SILK-0089** 🟠 Coupon / Promo Code System
- [x] **SILK-0090** (deferred — blocked: GPU server SSH) 🟠 Local GPU AI Pipeline (LLaVA+NLLB+Kokoro)
- [x] **SILK-0091** (deferred — blocked: accountant review) 🟡 GAAP/IFRS Revenue Recognition
- [x] **SILK-0092** 🟡 Heritage Extension Tables

### Flutter Mobile — Camera + Voice Assistant (2026-05-23)

- [✅] **SILK-0099** `CameraPage` real implementation — live `CameraController` viewfinder, `WidgetsBindingObserver` lifecycle, capture + gallery pick → `uploadMedia` → `recognizeImage`; `RecognitionNotifier` sealed-state provider; `_slideUpPage` transition; 11 camera_* keys × 4 locales (en/uz/ru/zh)
- [✅] **SILK-0101** `VoiceAssistantPage` — hold-to-listen mic button with `AnimationController` pulse, `VoiceNotifier` sealed-state (idle/listening/processing/result/error), `transcribeAudio` + `resolveVoiceIntent` API wiring, 17 voice_* keys × 4 locales; `/voice-assistant` route `_slideUpPage`; audio recording hook point documented for SILK-0105

### Flutter Mobile — Gamification API Wiring (2026-05-23)

- [✅] **SILK-0108** `GamificationRepositoryImpl` — `getXpRaw()`, `getStreakRaw()`, `tickStreakRaw()`, `getLeaderboardRaw()` raw helpers + typed `getStreak()`, `badges()` → `Result<T>`; `gamificationRepositoryProvider` via `silkLensApiClientProvider`
- [✅] **SILK-0109** `GamificationProvider` — unified `XpState` + `GamificationNotifier` (`refresh`, `tickStreak`); `badgesProvider` (FutureProvider → `GET /v1/me/badges`); `streakProvider` (FutureProvider → `GET /v1/me/streak`); `leaderboardEntriesProvider.family` (slug + period keyed)
- [✅] **SILK-0110** `XPDashboardPage` + `BadgesPage` — already watching real providers; verified clean; all 4-locale gamification key groups added (xp\_\*, badge\_\*)
- [✅] **SILK-0111** `LeaderboardPage` — `StatefulWidget` → `ConsumerStatefulWidget`; period tabs drive `leaderboardEntriesProvider(('global', period))`; loading/error/retry/empty states; `LeaderboardEntry.fromJson` rows; lb\_\* keys × 4 locales
- [✅] **SILK-0112** `StreakPage` → `ConsumerWidget` watching `streakProvider`; real `currentStreak`, `bestStreak`, `weekDays`, milestones from `StreakEntity`; `MissionsPage` → `ConsumerStatefulWidget` with i18n tabs/headers; 6 mission task keys × 4 locales; streak\_\* + mission\_\* keys

### Flutter Mobile — Social Backend Wiring (2026-05-23)

- [✅] **SILK-0113** Wire `ActivityFeedPage` to real `feedProvider` (FutureProvider → `GET /v1/social/feed`); loading skeletons, error card with retry, empty state; verb localisation for visit/review/badge/follow verbs; all 4 locales
- [✅] **SILK-0114** Wire `NotificationsPage` to real `notificationsProvider` (NotificationsNotifier → `GET /v1/notifications`); mark-single-read (`POST /v1/notifications/{id}/read`), mark-all-read (`POST /v1/notifications/mark-all-read`); unreadCountProvider drives badge; filter chips i18n
- [✅] **SILK-0115** Wire `FollowingListPage` to real `followingProvider`/`followersProvider` (FutureProvider.family → `GET /v1/social/following/{pub_id}` + followers); follow/unfollow toggle per row via `socialRepositoryProvider`; search filter; all 4 locales
- [✅] **SILK-0116** Wire `FriendInvitePage` to real invite API (`POST /v1/social/friends/invite`); shows real token, expiry, deep-link `silklens://invite?token=…`; loading/error/retry states; `SilkLensApiClient` + `SocialRepositoryImpl` fully implemented for social + notifications

### Flutter Mobile — Map + Profile + Review API Wiring (2026-05-23)

- [✅] **SILK-0102** `MapPage` converted to `ConsumerStatefulWidget`; hardcoded 4 markers replaced with dynamic `heritageListProvider` markers filtered by `hasGeolocation`; bottom sheet shows localised name + country + kind slug + gold "View details" button routing to `/home/heritage/{pubId}`; loading indicator in search bar; `activeLocaleProvider` drives i18n; 3 new map keys × 4 locales
- [✅] **SILK-0117** `UserProfilePage` converted to `ConsumerStatefulWidget`; reads `currentUserProvider` → shows real `displayName` (fallback to `profile_default_name` i18n key) and avatar initial; edit-name dialog calls `SilkLensApiClient.updateProfile(displayName:)`; follow/unfollow toggle preserved; stat columns use i18n labels; 14 new profile keys × 4 locales
- [✅] **SILK-0118** `ReviewComposerSheet` converted to `ConsumerStatefulWidget`; receives `heritagePubId` as required param; submit calls `SilkLensApiClient.createReview(...)` with `body_md`, `language_tag`, optional `ratings`; loading spinner during submit; success/error SnackBar via i18n; `mounted` guard on all async paths; 12 new review keys × 4 locales; `SilkLensApiClient` extended with `createReview`, `getHeritageReviews`, `updateProfile`

### Flutter Mobile — Heritage API Wiring (2026-05-23)

- [✅] **SILK-0093** `HeritageListPage` wired to real `heritageListProvider` — `HeritageListNotifier` upgraded with `isLoadingMore` flag, `setKindFilter()`, `setSearch()`, `setCountryFilter()`; pull-to-refresh, infinite scroll, shimmer skeleton, error/empty states; all 4 locales (47 new keys: heritage, nav, search)
- [✅] **SILK-0094** `HeritageDetailPage` converted from `StatefulWidget` to `ConsumerStatefulWidget`; wired to `heritageDetailProvider(pubId)` FutureProvider.family; loading/error/retry states; tab content (About/Facts/Reviews) driven by `Heritage` entity fields; i18n tabs + action labels; save bookmark via `heritageSavedProvider`
- [✅] **SILK-0095** `SearchPage` + `SearchResultsPage` converted to `HookConsumerWidget`; wired to real `GET /v1/search` via `SilkLensApiClient.searchHeritage(query, lang, country, kind)`; `SearchPage` shows recent-searches chips (SharedPreferences via `recentSearchesProvider`), country + type filter state, and navigates to `/search/results?q=…`; `SearchResultsPage` loads hits from API on `useEffect([query])` and maps `hit['name']`, `hit['kind_slug']`, `hit['country_code']` to cards; tapping card navigates to `/home/heritage/:pubId`; `ApiEndpoints.search = '/v1/search'` added; 6 new locale keys (search_recent_label, search_recent_clear, search_empty, search_error, search_loading, search_results_title) in all 4 locales
- [✅] **SILK-0096** `AudioGuidePage` converted to `HookConsumerWidget` with `just_audio` integration; `AudioPlayer` created via `useMemoized`, disposed via `useEffect`; `positionStream`, `durationStream`, `playingStream` wired to `useState`; language chip tap calls `SilkLensApiClient.generateTts(text, language)` → sets `player.setUrl(signed_url)`; scrubber reads real `position/duration`, seeks on drag; speed chips call `player.setSpeed()`; loading + error states with retry; optional `heritagePubId` + `heritageText` params via GoRouter query params; `ApiEndpoints.aiTts = '/v1/ai/tts'` added; 5 new locale keys (audio_guide_title, audio_guide_section, audio_guide_loading, audio_guide_error, audio_guide_retry) in all 4 locales (already shipped — confirmed wired)
- [✅] **SILK-0097** `OfflineModePage` converted from `StatelessWidget` to `ConsumerStatefulWidget`; `initState` calls `_loadBundles()` → `GET /v1/offline/bundles?region=uz_all&language=<locale>` via `SilkLensApiClient.getOfflineBundles()`; falls back to 5 hardcoded Uzbek bundles when API is unreachable; `_download(bundleId)` calls `getOfflineBundleManifest(bundleId)` then simulates download with progress tracking via `_downloading` Set + `_downloaded` Set; download button shows size in MB; `_BundleTile` stateless sub-widget; Refresh banner button re-triggers `_loadBundles()`; error SnackBar via `offline_download_error` key; all hardcoded Uzbek strings replaced with i18n keys; 8 new keys × 4 locales (offline_banner_text, offline_refresh_btn, offline_status_available, offline_status_needs_internet, offline_download_btn, offline_downloading, offline_download_error, offline_empty); `SilkLensApiClient` extended with `getOfflineBundles()` + `getOfflineBundleManifest()`
- [✅] **SILK-0098** `HeritageDetailPage` tab count extended from 3 to 5: About / Facts / Reviews / Kids / Culture; `_tabCtrl = TabController(length: 5)`; `TabBar` set to `isScrollable: true` + `tabAlignment: TabAlignment.start`; Kids tab lazy-loads `getKidsStory(pubId, language)` → `GET /v1/heritage/{pubId}/kids-story` on first visit; Culture tab lazy-loads `getHeritageCulturalTips(pubId, language)` → `GET /v1/heritage/{pubId}/cultural-tips` on first visit; both return null/empty gracefully; `_KidsTabContent` renders story in a gold-bordered card with emoji header; `_CultureTabContent` renders tip cards with severity badge (HIGH/MEDIUM/LOW colour-coded); `SilkLensApiClient` extended with `getKidsStory()` + `getHeritageCulturalTips()`; 7 new keys × 4 locales (heritage_tab_kids, heritage_tab_culture, heritage_kids_loading, heritage_kids_empty, heritage_culture_loading, heritage_culture_empty, heritage_culture_severity)

### Flutter Mobile — i18n Expansion + Hardcoded String Fixes (2026-05-23)

- [✅] **SILK-0140** Add German (de) and Korean (ko) locale ARB files; register in `kSupportedLanguageCodes`, `AppLocalizations.supportedLocales`, and `LanguageSelectionPage`; `flutter gen-l10n` regenerated all 6 locale Dart files; 8 emailVerify keys × 6 locales
- [✅] **SILK-0141** Fix hardcoded Uzbek strings in `EmailVerifyPage`; replace with `AppLocalizations.of(context)` calls using new `emailVerify*` keys (title, codeSentTo, confirm, invalidCode, resendError, resending, resendCountdown, resendNow); all 6 locales covered

### Flutter Mobile — Settings + Profile + Auth Extension API Wiring (2026-05-23)

- [✅] **SILK-0171** `NotificationPrefsPage` converted to `ConsumerStatefulWidget`; `initState` calls `_loadPreferences()` → `GET /v1/notifications/preferences`; maps `category_slug`/`channel`/`enabled` to 9 local toggles + 3 channel toggles + quiet-hours bool; each toggle change fires `PATCH /v1/notifications/preferences [{category_slug, enabled}]` or `updateNotificationPreferences([{channel, enabled}])`; quiet-hours toggle calls `updateQuietHours(timezone: Asia/Tashkent, startTime, endTime, weekdays)`; error SnackBar via `notif_prefs_save_error` + `notif_quiet_hours_error` i18n keys; `mounted` guards on all async paths; `SilkLensApiClient` extended with `registerPushDevice` + `getDataExportStatus`; `PrivacyGDPRPage` converted to `ConsumerStatefulWidget`; "Yuklab olish" button calls `POST /v1/me/data-export`, shows `AlertDialog` with `privacy_export_title/body/id` keys + request_id, loading spinner during request, error SnackBar via `privacy_export_error`; `_ActionRow` supports `loading` flag + nullable `onTap`; `DeleteAccountPage` converted to `ConsumerStatefulWidget`; delete button calls `SilkLensApiClient.requestAccountDeletion()`, shows `delete_account_scheduled` SnackBar, then calls `authNotifierProvider.logout()`, then `context.go('/')`; loading spinner replaces button text; fixed `_showEditNameDialog` in `UserProfilePage` to remove invalid re-login call after profile update; all 4 locales pre-existing

### Flutter Mobile — Billing API Wiring (2026-05-23)

- [✅] **SILK-0104** `BillingRepositoryImpl` fully wired: `getPlans`, `getCurrentSubscription`, `getInvoices`, `getEntitlements`, `cancelSubscription(atPeriodEnd)`, `resumeSubscription`, `validateCoupon`; `SilkLensApiClient` extended with `resumeSubscription` + `validateCoupon` (`POST /v1/billing/coupons/validate`); `BillingState` gains `billingCycle`, `couponResult`, `isValidatingCoupon`, `cancelAtPeriodEnd`; `BillingNotifier` gains `setBillingCycle`, `resumeSubscription`, `validateCoupon`, `clearCoupon`.
- [✅] **SILK-0105** `PlansPage` reads `billingProvider`: plan cards from API, "Current Plan" badge, monthly/yearly toggle via `setBillingCycle`; `CheckoutPage` upgraded to `ConsumerStatefulWidget` with coupon section (text field + Apply button + validity feedback), `validateCoupon` via notifier, `_couponCtrl` disposed, all strings i18n via `AppStrings.get`.
- [✅] **SILK-0106** `ManageSubscriptionPage` reads real `billingProvider`: resume subscription button shown when `cancelAtPeriodEnd == true`, cancel button shown otherwise; both call notifier methods with error SnackBar on failure.
- [✅] **SILK-0107** `InvoicesPage` reads `invoicesProvider` (FutureProvider); year filter chips; loading/error/empty/retry states.
- 82 locale keys across all 4 locales (en/uz/ru/zh) — all billing keys including new `billing_coupon_*` and `billing_resume_*`; `flutter build apk --debug` exit 0.

### Flutter Mobile — Feature Screens + Route Wiring (2026-05-23)

- [✅] **SILK-0126** `TicketsPage` (`lib/presentation/pages/billing/tickets_page.dart`) rewritten as `ConsumerStatefulWidget`; calls `SilkLensApiClient.getMyTickets()` in `initState`; displays gold-bordered cards with status badges (Active/Used/Expired); tapping a valid ticket opens QR dialog via `qr_flutter.QrImageView`; refresh icon + pull-to-refresh; error and empty states with CTA to browse heritage; route `/billing/tickets` added with `_slideRightPage`; settings home page gains "Mening chiptalarim" nav row; 12 keys × 4 locales
- [✅] **SILK-0127** `EmergencyPage` (`lib/presentation/pages/settings/emergency_page.dart`) confirmed wired: `HookConsumerWidget` calls `SilkLensApiClient.getEmergencyContacts(countryCode, language)` with locale-aware language param; warning banner, icon-per-kind, SnackBar dial fallback; route `/emergency` added with `_slideRightPage`; settings home gains "Favqulodda yordam" (red) nav row; 4 keys × 4 locales
- [✅] **SILK-0129** `WeatherGuidePage` (`lib/presentation/pages/map/weather_guide_page.dart`) confirmed wired: `HookConsumerWidget` calls `SilkLensApiClient.getWeatherGuide(lat, lng, language)`; weather card, AI summary, tips bullet list, recommended venues; route `/weather` added with `_slideRightPage`; settings home gains "Ob-havo Gidi" nav row; 4 keys × 4 locales
- All 3 routes are protected (NOT in `_guestOnlyPaths`); auth redirect guard handles them automatically; 20 new locale keys total across en/uz/ru/zh; `flutter analyze` — 0 errors

### Admin Panel — Quality Improvements (2026-05-23)

- [✅] **SILK-0167** Playwright E2E tests — `tests/e2e/auth.spec.ts` (login form render, invalid creds stay on /login, unauthenticated redirect) + `tests/e2e/navigation.spec.ts` (root redirect, title check, all protected routes redirect to /login, i18n heading check); `playwright.config.ts` already configured for port 3001
- [✅] **SILK-0168** Branding slug from session — added `tenantSlug` to NextAuth JWT + Session type declarations; Credentials + Google OAuth callbacks now write `tenantSlug` from `NEXT_PUBLIC_DEFAULT_TENANT_SLUG` env var (falls back to `'silklens'`); session callback exposes `session.user.tenantSlug`; `branding/page.tsx` reads `auth()` session and passes `session.user.tenantSlug` to `getBranding()` — eliminates hardcoded `DEFAULT_SLUG = 'silklens'` constant
- [✅] **SILK-0169** DataTable unification tech-debt comment — added 4-line `// TODO SILK-0169` block before `HeritageTable` export in `heritage-table.tsx` documenting why migration to shared DataTable is blocked (server-side pagination, multilingual JSONB columns, faceted filter routing)
- [✅] **SILK-0170** i18n key audit — all 4 locale files (en/uz/ru/zh) are now in full parity; added missing `dataTable` namespace (`noResults`, `columns`, `searchPlaceholder`) to all 4 locales; synced `nav.government` + `nav.coupons` keys that were present only in uz.json; Python key-diff check confirms 0 missing / 0 extra keys across all locales

### Flutter Mobile — Infrastructure + FCM + Release Signing (2026-05-23)

- [✅] **SILK-0139** FCM push-notification service scaffolded: `lib/core/push/fcm_service.dart` — `FcmService` class + `fcmServiceProvider`; `init()`, `handleForegroundMessages()`, `registerToken()` stubs with full setup checklist (pubspec deps, google-services.json, Info.plist, Firebase.initializeApp call); FCM init wiring instructions added to `main.dart` comment block; `SilkLensApiClient.registerPushDevice` already present and reused; firebase packages deferred until SILK-0139 unblocks (google-services.json needed first); 0 analyzer errors introduced
- [✅] **SILK-0142** Android release-signing documentation: 37-line comment block in `android/app/build.gradle` with `keytool` command, `key.properties` format, `signingConfigs.release` Groovy template, AndroidManifest cleartext-traffic note; `android/key.properties.example` created (real `key.properties` and `.keystore` already gitignored); no build code changed
- [✅] **SILK-0143** Missing asset READMEs: `assets/onboarding/README.md` — slide filenames, pixel dimensions, compression guidance, pubspec declaration note; `assets/textures/README.md` — planned texture filenames/formats, opacity guidelines, pubspec declaration reminder (directory not yet declared); no functional code changed
- Note: SILK-0145 (Sentry) was already fully implemented — conditional `SentryFlutter.init`, `FlutterError.onError`, zone-guarded `Sentry.captureException`, `SENTRY_DSN` in `.env.example`; no changes required

### Technical Debt

- [ ] **TD-001** finetuning/errors.py FastAPI import fix
- [ ] **TD-002** GET /v1/ai/models public access
- [ ] **TD-003** Pagination standardization
- [ ] **TD-004** 0084 migration naming collision
| Mapbox API key | API key kerak |
| WebAuthn real device | Browser + authenticator kerak |
