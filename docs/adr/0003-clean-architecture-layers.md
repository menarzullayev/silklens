# ADR 0003 — Clean Architecture layering inside `services/api`

- **Status:** Accepted
- **Date:** 2026-05-18

## Context

Project-Decisions §13 says: "kelajakda boshqa frameworklarga o'tib ketishimiz mumkin" (we may switch frameworks in the future). For the mobile client this is solved by isolating UI from domain. For the backend the same principle applies in reverse: if we ever swap FastAPI for NestJS, Go/Fiber, or split a service into microservices, the domain code should survive untouched.

## Decision

Inside `services/api/src/` we enforce **four layers**, with the dependency rule that inner layers never import outer layers:

```
domain/<context>/        ← Pure Python; entities, value objects, repository interfaces, services
infrastructure/          ← Adapters that implement repository interfaces (Postgres, Redis, MinIO, …)
api/                     ← HTTP routers, request/response schemas (FastAPI is here, and only here)
core/                    ← Cross-cutting: settings, DB engine, logging, security primitives
```

**Allowed imports:**

- `domain` → nothing (pure standard library + Pydantic + SQLAlchemy ORM types only)
- `infrastructure` → `domain` + external SDKs
- `api` → `domain` + `infrastructure` (only at the composition root) + Pydantic
- `core` → standard library + Pydantic + structlog

**Disallowed (enforced via ruff config in follow-up):**

- `domain` importing from `api`, `infrastructure`, or external SDKs
- `infrastructure` importing from `api`
- ORM models leaking into HTTP response schemas (Pydantic schemas mediate)

The Repository pattern is the seam. A `HeritageService` depends on `HeritageRepository` (a Protocol), not on `PostgresHeritageRepository`. Tests substitute an in-memory fake. Future microservice splits substitute a gRPC client. The domain doesn't notice.

## Consequences

**Positive:**

- Refactoring blast radius is bounded to one layer.
- Unit tests don't need Postgres.
- Future framework swap is mechanical: rewrite `api/` only.
- AI agents writing in one layer don't accidentally couple to another.

**Negative:**

- More files for the same feature (entity, repo interface, repo impl, schema, service, router).
- Repository pattern can feel heavy for trivial CRUD. We accept this cost because Project-Decisions §1 demands professional-grade, not minimal viable.

## Alternatives considered

- **Active Record / Django-style** — fast for CRUD, painful at scale. Rejected.
- **Hexagonal Architecture** — equivalent to what we picked; just a different name. Adopted in spirit.
- **No formal layering** — works at FAZA 1 scale but bites at FAZA 5+. Rejected upfront.
