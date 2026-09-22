# SilkLens — Master Design Briefing

> Generated: 2026-05-18 | Source: claudeDesign/* + PROGRESS.md + Project-Decisions.md + Roadmap.md

---

## 1. Executive Summary

SilkLens is an AI-powered global cultural heritage discovery platform that lets users point their smartphone camera at any monument, temple, ruin, or artwork and instantly receive multilingual context, an AI-narrated audio guide, and an AR overlay — all tied to a rich social and gamification layer. The platform launches on Flutter (iOS + Android simultaneously) with a FastAPI/PostgreSQL backend already carrying 100+ endpoints, 275 passing tests, and ~200 seeded heritage sites across Uzbekistan and Central Asia. SilkLens operates on a freemium model (B2C subscription + B2B white-label + B2G government contracts) managed entirely through a headless admin panel — nothing is hardcoded, every color, price, AI model, and screen label is runtime-configurable.

---

## 2. Target Audience

### Primary Personas

| Persona | Profile | Key Needs |
|---|---|---|
| **Xorijiy Turist** (Foreign Tourist) | Age 25-55, visits Samarkand/Bukhara/Khiva; may lack local SIM; has discretionary income | Instant recognition, offline maps, audio guide, multilingual UI |
| **Mahalliy Foydalanuvchi** (Local Uzbek) | Age 18-40, curious about national heritage; uses Android; price-sensitive | Uzbek language, low data usage, gamification, social sharing |
| **Cultural Enthusiast** | Global; uses travel apps like Google Arts & Culture, Atlas Obscura | Deep content, historical context, collection-building |
| **Academic / Researcher** | Universities, UNESCO affiliates | Verified data, citations, bulk export |
| **B2B Partner** | Hotels, tour agencies, museums | White-label API, featured listings, analytics |

### Geographic Sequence
Uzbekistan (launch) → Central Asia (KZ/TJ/TM/KG) → Silk Road corridor (CN/IR/TR/IN) → Europe (IT/GR/EG) → Global

---

## 3. Platform

| Attribute | Value |
|---|---|
| Framework | Flutter 3.24+ (Dart 3.5+) |
| Target OS | iOS 16+ and Android 10+ |
| Architecture | Clean Architecture — domain / data / presentation separation |
| State management | hooks_riverpod 2.5 |
| Navigation | go_router 14 with 5 custom transition types |
| Offline | Hive (local), Isar v4 planned for FAZA 6 |
| API client | Dio 5.4 with pretty_dio_logger |
| Maps | flutter_map 7 (OpenStreetMap) + Mapbox styling planned |
| AI integration | Camera, image_picker, just_audio; backend handles all inference |
| Auth extras | google_sign_in, local_auth (biometrics), flutter_stripe |
| Total wired screens | **24 screens** |
| Admin pages | 8 wired (Next.js + shadcn/ui) |

---

## 4. Current Design System

### Color Palette (extracted from live code)

| Role | Hex | Usage |
|---|---|---|
| **Deep Navy** | `#0D2337` | Primary background, status bar, nav bar |
| **Brand Blue** | `#1A3A5C` | Secondary background, card surfaces, brand color |
| **Accent Blue** | `#1E4976` | Gradient endpoint, hover states |
| **White** | `#FFFFFF` | Primary text, primary button fill |
| **White 65%** | `rgba(255,255,255,0.65)` | Tagline text, secondary labels |
| **White 55%** | `rgba(255,255,255,0.55)` | Tertiary text, placeholders |
| **White 45%** | `rgba(255,255,255,0.45)` | Borders, dividers |
| **White 18%** | `rgba(255,255,255,0.18)` | Logo container fill, glass surfaces |
| **White 8%** | `rgba(255,255,255,0.08)` | Subtle glow / shadow |

### Gradient (Splash & Auth screens)
```
LinearGradient: top→bottom
  #0D2337 (0%) → #1A3A5C (50%) → #0D2337 (100%)
```
Logo container uses a `RadialGradient`: `rgba(255,255,255,0.18)` → `rgba(255,255,255,0.06)`

### Typography
- **App name "SilkLens"**: 46sp, weight 800, letterSpacing 4 (splash); 34sp weight 800 letterSpacing 2 (auth)
- **Tagline**: 15sp, weight 400, letterSpacing 2, white 65%
- **Section heading**: 24sp bold
- **Body**: system default (font tokens planned — Inter via Google Fonts in FAZA 2+)
- **Button labels**: 16sp weight 700 (primary), weight 600 (secondary)
- **Caption/meta**: 14sp, grey

### Spacing
- Screen horizontal padding: **28dp**
- Button height: **54dp**
- Button border radius: **14dp**
- Logo circle (splash): **128dp**; (auth choice): **80dp**
- Standard gaps: 8 / 12 / 16 / 24 / 36dp

### Transitions (5 types wired in go_router)
1. `noTransition` — splash only
2. `fade` 300ms — language selection, onboarding
3. `slideUp + fade` — auth pages (sheet-like reveal)
4. `slideRight` 250ms — detail pages, forgot-password
5. `fadeScale` 400ms (scale 0.96→1.0) — home entry

### Navigation Pattern
Bottom navigation bar with camera centered (Shazam-style). Admin panel configurable.

---

## 5. All 24 Screens — Complete List

### Auth Flow (8 screens)
| # | Screen | Route | State |
|---|---|---|---|
| 1 | **Splash** | `/` | Animated logo + tagline; loads locale prefs; 1800ms min display |
| 2 | **Language Selection** | `/language` | First-run; pick from UZ/RU/EN/ZH; persists to SharedPreferences |
| 3 | **Onboarding** | `/onboarding` | Multi-step feature showcase (Lottie animations placeholder) |
| 4 | **Auth Choice** | `/auth/choice` | Sign In / Sign Up / Guest Continue; full dark gradient |
| 5 | **Sign In** | `/auth/sign-in` | Email+password; Google OAuth; biometric button; slideUp transition |
| 6 | **Sign Up** | `/auth/sign-up` | Email+password+ToS checkbox; full validation |
| 7 | **Forgot Password** | `/auth/forgot-password` | Email entry; send reset link |
| 8 | **Email Verify** | `/auth/email-verify?email=` | 6-box OTP input; resend timer |

### Main App (shell) — Bottom Navigation
| # | Screen | Route | State |
|---|---|---|---|
| 9 | **Home / Heritage List** | `/home` | Paginated card list; shimmer skeleton loading; offline banner |
| 10 | **Heritage Detail** | `/home/heritage/:pubId` | Hero image, markdown body, period label, location, audio guide, AI chat button |
| 11 | **Map** | `/map` | flutter_map; heritage pins; cluster markers; tap-to-preview |
| 12 | **Camera / Recognize** | `/camera` | Live preview; capture button; upload to API; recognition result overlay |
| 13 | **Heritage Search** | (heritage list inline) | Full-text + vector search; filters by kind/country |
| 14 | **Saved Heritage** | (profile tab) | Bookmarked items; offline-ready |

### Social & Profile (4 screens)
| # | Screen | Route | State |
|---|---|---|---|
| 15 | **My Profile** | `/profile` | Avatar, stats (visited/badges/XP), activity feed |
| 16 | **User Profile** | `/profile/:pubId` | Public view; follow button; visited map |
| 17 | **Review Composer** | (bottom sheet) | Rating sliders (architecture/preservation/accessibility/storytelling); photo attach |
| 18 | **Social Feed** | (home tab) | Friends' discoveries; reactions; share |

### Gamification (2 screens + 2 widgets)
| # | Screen | Route | State |
|---|---|---|---|
| 19 | **Badges** | `/badges` | Grid of earned/locked badges; progress rings |
| 20 | **Leaderboard** | `/leaderboard` | Weekly/monthly/friends tabs; rank chips |
| 21 | **Streak Widget** | (embedded) | Flame icon; consecutive days counter |
| 22 | **XP Card** | (embedded) | Level name + XP bar + next milestone |

### Billing (4 screens)
| # | Screen | Route | State |
|---|---|---|---|
| 23 | **Plans** | `/billing/plans` | Free vs Premium tiers; dynamic pricing from API; region-aware |
| 24 | **Checkout** | `/billing/checkout` | Stripe + Payme + Click payment flows |
| 25 | **Manage Subscription** | `/billing/manage` | Current plan; cancel; change; billing history |
| 26 | **Invoices** | `/billing/invoices` | Invoice list; PDF download |

### AI & Chat (1 screen)
| # | Screen | Route | State |
|---|---|---|---|
| 27 | **AI Chat** | `/chat` | Conversation with heritage context; Claude API backend; streaming |

---

## 6. User Journeys — 5 Key Flows

### Flow A: Onboarding (New User)
```
App Open → Splash (1.8s, animated logo)
         → Language Selection (first run only)
         → Onboarding (3 slides: Discover / Recognize / Explore)
         → Auth Choice
         → Sign Up (or Guest Continue)
         → Home
```
Key moments: compass logo animation, tagline fade-in, WOW moment deferred to first recognition.

### Flow B: Discover (Browse Heritage)
```
Home (Heritage List, shimmer → cards)
  → Filter by country / kind
  → Heritage Card tap
  → Heritage Detail
      ├── Scroll rich markdown description
      ├── Tap audio button → TTS plays
      ├── Tap map pin → Map focused on site
      └── Tap "Ask AI" → Chat page with context pre-loaded
```

### Flow C: Recognize (Camera Flow)
```
Bottom Nav → Camera Tab
  → Live camera preview (full-screen)
  → Capture button
  → Upload to POST /v1/media/upload
  → POST /v1/ai/recognize
  → Recognition result overlay (label + confidence + heritage card)
  → Tap card → Heritage Detail
  → XP awarded (+50 first-discovery) → badge animation
```

### Flow D: Social (Community)
```
Profile → View my visited map
  → Share "I visited Registan" → branded card → Instagram/Telegram
  → View friend's profile → follow
  → See friend in leaderboard → motivation
  → Write review on Heritage Detail → review composer sheet
      ├── Star rating + dimension sliders
      └── Attach photo → POST /v1/media/upload
```

### Flow E: Subscription (Paywall)
```
Trigger: user opens AR or unlimited audio (premium feature)
  → Soft paywall modal → "See Plans"
  → Plans page (animated tier comparison)
  → Checkout (Stripe card or Payme/Click for UZS)
  → Confirmation → unlock premium instantly
  → Manage Subscription page for cancellation/upgrade
```

---

## 7. Backend Capabilities (API for UI Features)

### Authentication & Identity
- `POST /v1/auth/register` — email + password + display name
- `POST /v1/auth/login` — returns JWT + refresh token (family rotation)
- `POST /v1/auth/refresh` — silent re-auth
- `POST /v1/auth/logout`
- `GET /v1/auth/me` — current user profile
- `POST /v1/auth/google` — OAuth (501 stub → FAZA 6)
- MFA: TOTP, WebAuthn FIDO2, backup codes

### Heritage Content
- `GET /v1/heritage` — paginated list with filters (kind, country, search, status)
- `GET /v1/heritage/:pubId` — full detail with multilingual name/summary/description
- `POST/PATCH/DELETE /v1/heritage` — admin CRUD with RBAC
- `GET /v1/heritage/:pubId/revisions` — bi-temporal version history

### AI Services
- `POST /v1/ai/recognize` — image → label + confidence + candidates (rate: 10/min)
- `POST /v1/ai/chat` — LLM conversation with system prompt (rate: 30/min)
- `POST /v1/ai/translate` — NLLB-200 / DeepL cascade (rate: 60/min)
- `POST /v1/ai/tts` — generates audio, stores to MinIO, returns signed URL (rate: 10/min)
- `POST /v1/ai/search` — pgvector HNSW semantic search

### Social
- `POST /v1/social/follow/:pubId`, `DELETE /v1/social/follow/:pubId`
- `GET /v1/social/feed` — whale-aware fanout
- `POST /v1/reviews` — rating + dimensions (architecture/preservation/accessibility/storytelling) + photos
- `POST /v1/reviews/:id/reactions`

### Gamification
- `GET /v1/gamification/xp` — XP summary + level + streak
- `GET /v1/gamification/badges` — earned + locked badges
- `GET /v1/gamification/leaderboard?scope=weekly|monthly|friends`
- Atomic XP ledger — idempotent award events

### Billing
- `GET /v1/billing/plans` — dynamic plans from DB (region-aware pricing)
- `POST /v1/billing/subscribe`
- `GET /v1/billing/invoices`
- `POST /v1/billing/webhooks/stripe` — Stripe-Signature verified
- Multi-currency: Stripe (USD), Payme (UZS), Click (UZS), PayPal

### Media
- `POST /v1/media/upload` — MIME magic-byte validated; stores to MinIO
- `GET /v1/media/:id/signed-url` — time-limited CDN URL
- TTS audio stored alongside user photos in same pipeline

### Notifications
- Templates + push (FCM) + email + SMS
- User preference management
- Streak loss warnings 24h before expiry

---

## 8. Design Constraints

### Technical Constraints
- **Flutter Material Design 3** — use M3 components and theming tokens
- **Minimum tap target**: 48×48dp (accessibility requirement)
- **Portrait orientation** primary; landscape optional for camera/map
- **RTL ready**: Arabic support planned in FAZA 4; all layouts must respect `Directionality`
- **Dynamic theming**: all colors come from admin panel at runtime — no hardcoded hex in production widgets (use `ThemeData` tokens)
- **Font loading**: Inter via Google Fonts (bundled in FAZA 2+); design must specify fallback system font behavior
- **Image loading**: shimmer skeleton required while images load; WebP format; 3 sizes (thumb/medium/full)
- **Offline state**: `OfflineBanner` widget wraps all screens; offline state must be visually communicated without breaking layout

### Accessibility
- Contrast ratio WCAG AA minimum (4.5:1 for text)
- All interactive elements labeled for screen readers
- Audio descriptions for recognition results

### Must-Haves
- Camera viewfinder must be full-bleed (no margins) with floating controls
- Map must show heritage pins with cluster support
- Heritage detail must support markdown rendering (flutter_markdown)
- Auth screens must show biometric button when device supports it
- Every screen must have an empty state design (no data, error state)
- Loading skeleton for every list/grid (ShimmerBox pattern already built)

### Performance Budget
- Cold start: <3 seconds to interactive
- API response display: <500ms perceived (shimmer fills the wait)
- Image progressive loading with blurhash placeholder
- Recognition result: <2 seconds end-to-end

---

## 9. Inspiration Apps

| App | What to Learn |
|---|---|
| **Duolingo** | Gamification UI — streak flame, XP bars, badge unlock animations, leaderboard rivalry. Warm, friendly, celebrates progress. |
| **Google Arts & Culture** | Heritage card layout — full-bleed photography, curator-quality typography, "explore nearby" map integration. Clean white variant reference. |
| **Atlas Obscura** | Content depth + discovery tone — "hidden wonders" framing, editorial headlines, adventurous photography style. |
| **iNaturalist** | Camera-to-identification flow — real-time overlay, confidence meter, community validation. UX pattern for recognition result screen. |
| **Shazam** | Core camera UX metaphor — single large action button, instant result reveal, minimal chrome around the viewfinder. |
| **Visited (World map app)** | Profile screen visited-countries heatmap — satisfying data visualization for travel history. |
| **Spotify Wrapped** | Annual stats share card concept — apply to "Your 2026 Heritage Journey" social share card. |
| **Mapbox Showcase apps** | Map styling reference — dark terrain tile style with glowing heritage pin markers. |
