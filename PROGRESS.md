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
- [ ] **SILK-0012** 🟢 **`MfaGateAdapter` to'liq wire qilish** — login flow'da MFA challenge integration
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
- [🔄] **SILK-0016** 🟢 **EPIC-008 Gamification** — XP dashboard, badges grid, leaderboard live data
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
| Mapbox API key | API key kerak |
| WebAuthn real device | Browser + authenticator kerak |
