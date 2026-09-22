# SilkLens — Project Overview

## What is SilkLens?

SilkLens is an AI-powered global cultural heritage discovery platform built to let anyone — from a local tourist to an international researcher — explore, recognize, and engage with cultural monuments and heritage sites anywhere in the world. The platform combines on-device AI vision recognition (point your camera at a monument and get instant rich context), multilingual audio guides, social features, gamification, and a full offline mode. Starting from Uzbekistan's UNESCO-listed Silk Road sites and expanding across Central Asia and eventually to 100,000+ heritage objects worldwide, SilkLens is designed to be the definitive digital layer over humanity's built cultural heritage.

---

## Target Users

- **Cultural heritage enthusiasts** — people passionate about history, archaeology, and world monuments
- **Tourists (local and international)** — travelers seeking contextual, multilingual information about sites they visit
- **Researchers and academics** — professionals who need structured heritage data, provenance records, and scholarly references
- **Government and tourism agencies** — B2G white-label partners who embed SilkLens capabilities in their own apps

---

## Platform

| Layer | Technology |
|---|---|
| Mobile app | Flutter (Dart) — single codebase for iOS + Android |
| Architecture | Clean Architecture + Riverpod state management + Go Router navigation |
| Offline | Isar local database with Ed25519-signed offline bundles |
| AR | ARCore (Android) + ARKit (iOS) — scaffolded, pending real device testing |
| Admin panel | Next.js 14 + shadcn/ui + TypeScript (React Server Components) |

---

## Current FAZA Status

> As of 2026-05-18 — tag `v0.3.0-beta`

| FAZA | Name | Status |
|---|---|---|
| FAZA 1 — Launch | Foundation, auth, heritage CRUD, frontends, CI | ✅ COMPLETE |
| FAZA 2 — Boost | AI endpoints (MockProvider), media pipeline, offline cache, Elasticsearch | ✅ ~85% COMPLETE |
| FAZA 3 — Spark | AI Chat (Anthropic SDK), full gamification, social graph, billing | ✅ ~70% COMPLETE |
| FAZA 4 — NOVA | Rate limiting, observability, GDPR/UZ PD-law, real Stripe, Anthropic SDK | ✅ COMPLETE |
| FAZA 5 — TURBO | Central Asia 95 heritage entries, multi-currency payments, MFA, white-label | ✅ COMPLETE |
| FAZA 6 — VELOCITY | Silk Road expansion (CN/IR/TR/IN, 1200+ monuments), UNESCO partnership | Upcoming |
| FAZA 7 — QUANTUM | Europe + global (IT/GR/EG/MA/JP), 50K+ monuments, fine-tuning | Upcoming |
| FAZA 8-12 — HORIZON→APEX | 100K+ monuments, VR/AR full, IPO/acquisition | Future |

**Key stats at current checkpoint:**
- 28 migration files (0001–0084), ~250+ DB tables, 81 RLS policies
- 100+ backend API endpoints, 275/275 tests green
- 24 Flutter screens wired, 8 admin pages wired
- ~200 heritage entries seeded (UZ 5 UNESCO + Central Asia 95)

---

## Design System

### Color Palette

| Role | Hex | Usage |
|---|---|---|
| Deep navy (darkest) | `#0D2337` | App background, primary surfaces |
| Dark navy | `#1A3A5C` | Cards, navigation bar |
| Medium navy | `#1E4976` | Elevated surfaces, accent areas |
| White | `#FFFFFF` | Primary text, icons |
| Accent gold | TBD (Silk Road motif) | CTAs, highlights, heritage badges |

### Typography Style

- **White text on dark navy backgrounds** throughout — high contrast for outdoor / field use
- Clean sans-serif hierarchy with bold headings and regular body weight
- Multilingual typography support: Latin (English/Uzbek), Cyrillic (Russian/Uzbek), CJK (Chinese), Arabic RTL — all handled via dynamic font loading

### Visual Language

- Silk Road wave motif in the compass-based app icon and splash screen
- Shimmer skeleton loading states for all content cards
- Native splash screen with compass logo at all pixel densities (adaptive icon)
- Smooth page transitions: fade, slideUp, slideRight, fadeScale — no jarring cuts

---

## Key Features

### Core Heritage Discovery
- AI vision recognition: point camera at any monument for instant identification
- Rich multilingual monument profiles (Uzbek, Russian, English, Chinese + dynamic expansion)
- Heritage timeline with bi-temporal revision history and provenance chains
- Offline mode: download complete monument bundles for field use without connectivity

### AI & Intelligence
- `POST /v1/ai/recognize` — vision recognition (LLaVA/InternVL local, Google Vision/GPT-4V fallback)
- `POST /v1/ai/tts` — audio guide generation (Kokoro/Piper TTS local, ElevenLabs/OpenAI fallback)
- `POST /v1/ai/chat` — AI heritage assistant (Anthropic Claude with prompt caching + streaming)
- NLLB-200 translation pipeline (200 languages, runs locally on GPU server)
- pgvector HNSW semantic search across heritage embeddings

### Social & Gamification
- Social graph: follow, friend, block, whale-aware feed fanout
- UGC: reviews, ratings, photo uploads, comments, reactions, moderation reports
- XP ledger + badge system + streaks + leaderboards (atomic idempotency, Redis-backed)
- Group travel schema (infrastructure ready)

### Monetization & Enterprise
- Freemium subscription plans with entitlement gating (admin-configured)
- Real Stripe integration (PaymentIntent + webhook verification)
- Multi-currency routing: Payme (UZS), Click (UZS), Stripe (USD), PayPal — per-currency provider rules
- Central Asia pricing zone ($1.99/mo, $19.99/yr) with KZT/TJS/TMT/KGS currencies
- White-label / reseller onboarding (B2G partnerships, revenue share, MOU templates)

### Auth & Security
- Argon2id password hashing + JWT HS256 with refresh token family rotation + replay defense
- MFA: TOTP (RFID authenticator apps), WebAuthn/FIDO2 passkeys, backup codes, step-up auth
- Row-Level Security (81 RLS policies) for full multi-tenant data isolation
- GDPR + Uzbekistan PD-law compliance: data export, right to erasure, anonymization
- Audit log with HMAC hash chain + Merkle root anchoring

### Admin & Operations
- Full admin panel (Next.js + shadcn/ui): tenants, branding, feature flags, AI model config
- Observability: Sentry, OpenTelemetry, 9 Prometheus metrics, 4 Grafana dashboards, 5 alert rules
- Rate limiting: slowapi + Redis (8 endpoints gated, 423 Locked response on breach)
- 5-language Elasticsearch search (tiered analyzers) + Wikidata SPARQL ingestion pipeline

---

## Backend Capabilities Summary

| Capability | Detail |
|---|---|
| API endpoints | 100+ across auth, heritage, media, social, gamification, billing, admin, compliance |
| Database | PostgreSQL 16 + pgvector; partitioned tables, HNSW indexes, RLS, HMAC audit chain |
| AI providers | Local-first (GPU server RTX 4090) with cloud fallback; provider switching via admin panel |
| Search | Elasticsearch 8 — 5 languages, vector hybrid search |
| Event bus | Redpanda (Kafka API) with transactional outbox pattern |
| Background workers | Celery + Redis for AI inference, ingestion, notifications |
| Storage | MinIO (S3-compatible) — media, signed offline bundles |
| Multi-tenancy | Full RLS isolation; white-label branding per tenant from admin panel |
| Test coverage | 275/275 pytest tests green; ruff lint clean; mypy strict |
