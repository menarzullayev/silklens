# SilkLens Documentation Index

Documentation lives in three layers — **strategy** (the why), **architecture** (the how), and **operations** (the day-to-day). Start with `CLAUDE.md` and `PROGRESS.md` at the repo root; everything else here is reference material.

---

## Strategy

| Doc | What it owns |
|---|---|
| [`/Roadmap.md`](../Roadmap.md) | 12-month phased plan (FAZA 1 → APEX). The product narrative. |
| [`/Project-Decisions.md`](../Project-Decisions.md) | Philosophical decisions: admin-driven, no MVP shortcuts, dynamic everything. The non-negotiable spirit. |
| [`/PROGRESS.md`](../PROGRESS.md) | Live status tracker. SILK-NNNN tickets, FAZA milestones, deferred items. **Update with every ship.** |
| [`/CLAUDE.md`](../CLAUDE.md) | Cold-start project context for any Claude session. Hot paths, gotchas, commands. |
| [`TRACKING_CONVENTION.md`](TRACKING_CONVENTION.md) | SILK-NNNN ticket format, commit message rules, status/priority enums. |

---

## Architecture

The 8-domain database design (~328 tables). Read the master synthesis first, then drill into the domain doc you're touching.

| Doc | Domains covered |
|---|---|
| [`architecture/00-MASTER-ARCHITECTURE.md`](architecture/00-MASTER-ARCHITECTURE.md) | Master synthesis — read first |
| [`architecture/01-core-domain.md`](architecture/01-core-domain.md) | tenants, branding, system_settings, feature_flags, vocabularies |
| [`architecture/02-identity-rbac-gdpr.md`](architecture/02-identity-rbac-gdpr.md) | users, sessions, OAuth, RBAC, audit chain, GDPR |
| [`architecture/03-ai-vector-infra.md`](architecture/03-ai-vector-infra.md) | pgvector, AI providers, prompts, tool calls, embeddings |
| [`architecture/04-media-storage.md`](architecture/04-media-storage.md) | MinIO, media pipeline, MIME validation, signed URLs |
| [`architecture/05-social-gamification-ugc.md`](architecture/05-social-gamification-ugc.md) | follows, feed, badges, XP, missions, leaderboards, UGC |
| [`architecture/06-monetization-enterprise.md`](architecture/06-monetization-enterprise.md) | subscriptions, payments, multi-currency, B2B, white-label |
| [`architecture/07-infra-analytics-events.md`](architecture/07-infra-analytics-events.md) | event_outbox, Redpanda, Elasticsearch, metrics |
| [`architecture/08-performance-reliability.md`](architecture/08-performance-reliability.md) | rate limits, lockout, observability, SLA, photogrammetry |

---

## Architecture Decision Records

Numbered ADRs codify the irreversible choices. Read before introducing a competing pattern.

| ADR | Decision |
|---|---|
| [`adr/0001-monorepo-layout.md`](adr/0001-monorepo-layout.md) | Monorepo with `apps/`, `services/`, `packages/` |
| [`adr/0002-postgres-as-system-of-record.md`](adr/0002-postgres-as-system-of-record.md) | Postgres is SoR; ES/Redis are caches |
| [`adr/0003-clean-architecture-layers.md`](adr/0003-clean-architecture-layers.md) | domain ← infrastructure / api → domain |
| [`adr/0004-uuidv7-primary-keys.md`](adr/0004-uuidv7-primary-keys.md) | UUIDv7 via `app.uuidv7()` for B-tree locality |
| [`adr/0005-provider-switching.md`](adr/0005-provider-switching.md) | Strategy pattern for AI / payment providers |
| [`adr/0006-multi-currency-routing.md`](adr/0006-multi-currency-routing.md) | Per-currency provider routing (UZS→payme, USD→stripe, …) |

---

## Operations

| Doc | Purpose |
|---|---|
| [`HANDOFF.md`](HANDOFF.md) | Frozen FAZA-1 foundation snapshot (historical reference) |
| [`code-review-2026-05-18.md`](code-review-2026-05-18.md) | Periodic full-repo review — 13 findings fixed |
| [`security-review-2026-05-18.md`](security-review-2026-05-18.md) | Pre-FAZA-5 security audit findings + remediations |
| [`security-review-wave5-6.md`](security-review-wave5-6.md) | FAZA 5-6 MFA + multi-currency security review |

---

## Reading order for a new contributor

1. `/README.md` — repo overview + quick start
2. `/CLAUDE.md` — project context (auto-loaded by Claude Code)
3. `/PROGRESS.md` — what's shipped vs open
4. `Roadmap.md` — where this is going
5. `architecture/00-MASTER-ARCHITECTURE.md` — how it's built
6. `TRACKING_CONVENTION.md` — how to ticket and commit
7. The specific `architecture/0X-*.md` doc for the domain you're touching
8. Relevant ADRs in `adr/` before proposing pattern changes

---

## Adding a new doc

Live docs go in `docs/`. Update this README when adding a new top-level doc so future readers can find it. Domain-specific notes go inside `architecture/`. Per-ship reviews (code/security/perf) go directly in `docs/` with the date in the filename: `<kind>-review-YYYY-MM-DD.md`.

**Do not** create ad-hoc top-level `*_TASKLIST.md` or `*_NOTES.md` files. Use `PROGRESS.md` + SILK tickets, or `docs/architecture/` for design notes.
