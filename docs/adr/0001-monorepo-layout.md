# ADR 0001 — Monorepo layout with bounded contexts as Python packages

- **Status:** Accepted
- **Date:** 2026-05-18
- **Deciders:** menarzullayev (with AI agent guidance)
- **Supersedes:** —

## Context

SilkLens will produce code in three top-level deliverables — a FastAPI backend, a Flutter mobile client, and a Next.js admin panel — plus shared types/packages and infrastructure (Docker, K8s in the future). Project-Decisions §51 mandates that AI agents do 99% of the implementation work, which makes navigability of the repo a load-bearing concern: every fresh agent context starts from scratch and must orient itself quickly.

We need a layout that:

1. Reflects the eight bounded contexts identified by the architecture round (heritage, identity, AI, media, social, billing, events, infra) without prematurely splitting them into microservices.
2. Lets each context grow independently while sharing build/test/lint configuration.
3. Survives the inevitable future split into microservices without renaming everything.
4. Is friendly to AI agents — a clearly named bounded-context folder reads better than a deeply nested package soup.
5. Keeps mobile and admin out of the Python service so build pipelines don't intersect needlessly.

## Decision

We adopt a **modular monorepo** with this top-level layout:

```
apps/        # User-facing applications (mobile, admin)
services/    # Long-running services (api today; ai, media tomorrow)
packages/    # Shared cross-language contracts and SDK packages
infra/       # Docker, k8s, monitoring configs
docs/        # ADRs + architecture + roadmap + decisions
scripts/     # One-off operational scripts
```

Inside `services/api`, the FastAPI service follows Clean Architecture:

```
services/api/src/
  api/              # HTTP layer (routers, request/response schemas)
  core/             # Settings, DB engine, logging, security primitives
  domain/<context>/ # Bounded contexts; one folder per Agent 1-7 domain
  infrastructure/   # External adapters (MinIO, Redis, Kafka, ES)
  middleware/       # FastAPI middlewares (auth, audit, tenancy, RLS context)
```

Each bounded context owns:

- `models.py` — ORM models registered on `Base.metadata`
- `repository.py` — Repository pattern interfaces + implementations
- `service.py` — Domain services (business logic)
- `schemas.py` — Pydantic request/response models
- `router.py` — FastAPI router (mounted by `api/app.py`)

This mirrors the eight architecture documents one-to-one and lets a single agent own a single context.

## Consequences

**Positive:**

- Each `domain/<context>` maps cleanly to a future microservice via §14 of the master architecture; the seam (event outbox + RPC interfaces) is identified upfront.
- AI agents see a consistent shape and can be briefed with "read `docs/architecture/0N-*.md`, edit only `services/api/src/domain/<context>/`".
- Mobile and admin clients don't accidentally couple to Python build state.

**Negative:**

- More directories to navigate than a flat layout.
- Shared cross-context utilities risk landing in `infrastructure/` and growing into a kitchen sink. Mitigation: ADR will be filed when a `packages/` extraction is needed.

**Neutral:**

- We are not yet splitting into microservices; the layout *allows* a split but doesn't force one until contention justifies it (master architecture §14).

## Alternatives considered

- **Single-package layout** (`src/` with subpackages by layer) — simpler, but mixes contexts in a way that hurts agent-onboarding velocity.
- **Per-context separate repos** (poly-repo) — premature; we have zero releases yet; cross-cutting changes (auth, audit) would be PR-storms.
- **Django-style `apps/<app>`** — Django conventions but we're on FastAPI; would invite confusion.
