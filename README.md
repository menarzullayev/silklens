# SilkLens

> AI-powered global cultural-heritage platform. Built around a Flutter mobile client, FastAPI backend, PostgreSQL + pgvector, and an on-prem GPU AI stack.

**Status:** FAZA 1 — Hafta 1 (foundation in progress)

**Vision and roadmap:** [`Roadmap.md`](Roadmap.md)
**Design philosophy and decisions:** [`Project-Decisions.md`](Project-Decisions.md)
**Database & domain architecture (~328 tables across 8 designs):** [`docs/architecture/`](docs/architecture/)

---

## Quick start (developer)

```bash
# 1. Boot the local dev stack
make dev

# 2. Install the API service into a venv
make api-install

# 3. Apply migrations (none yet at FAZA 1 Hafta 1; will land mid-week)
make api-migrate

# 4. Run the API
make api-run

# 5. Verify
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

## Repository layout

```
silklens/
├── apps/
│   ├── mobile/              # Flutter — iOS + Android (FAZA 1 Hafta 2)
│   └── admin/               # Next.js admin panel (FAZA 1 Hafta 2)
├── services/
│   └── api/                 # FastAPI backend
│       ├── alembic/         # Migrations
│       ├── src/
│       │   ├── api/         # HTTP routers
│       │   ├── core/        # Settings, DB, logging
│       │   ├── domain/      # Bounded contexts (heritage, identity, …)
│       │   ├── infrastructure/
│       │   └── middleware/
│       └── tests/
├── infra/
│   └── docker/              # docker-compose, init.sql
├── packages/
│   └── shared/              # Cross-service shared types / contracts
├── scripts/
│   └── …                    # One-off scripts (seed data, migrations helpers)
└── docs/
    ├── adr/                 # Architecture Decision Records
    ├── architecture/        # 8-domain database design (see master synthesis)
    ├── Roadmap.md
    └── Project-Decisions.md
```

## Tech stack

| Layer | Choice | Notes |
|---|---|---|
| Mobile | Flutter (Dart) | iOS + Android single codebase · Clean Architecture · Riverpod · Go Router · Isar (offline) |
| Backend | FastAPI 0.115+ on Python 3.12 | Async first · Pydantic v2 · SQLAlchemy 2.0 async |
| Admin | Next.js 14 · shadcn/ui · TypeScript | React Server Components |
| RDBMS | PostgreSQL 16 + pgvector | RLS for multi-tenant · partitioning per Agent 8 |
| Cache | Redis 7 | Sessions · leaderboards · AI cache |
| Storage | MinIO (S3-compatible) | Media · offline bundles (Ed25519-signed) |
| Search | Elasticsearch 8 | Tiered analyzers for 200 languages |
| Bus | Redpanda (Kafka API) | Outbox-driven event publishing |
| Workers | Celery + Redis broker | AI inference · ingestion · notifications |
| AI | LLaVA / InternVL · Kokoro / Piper TTS · NLLB-200 · Claude / GPT-4 | Local first, cloud fallback per admin config |

## Development workflow

- **Branching:** GitFlow (`main` ← `develop` ← `feature/*`); see Project-Decisions §37
- **Commit messages:** Conventional Commits
- **PRs:** at least one review (AI or human) + green CI
- **Migrations:** generated revisions are reviewed by hand before merge; SilkLens uses DB features (RLS, partitions, GIN/HNSW indexes) that Alembic autogenerate cannot infer

```bash
make help                  # See every available target
make api-lint              # ruff
make api-mypy              # mypy strict
make api-test              # pytest
make api-test-cov          # with coverage
```

## Architecture documents

Read in this order:

1. [`Project-Decisions.md`](Project-Decisions.md) — Why every choice was made (50+ Q&A)
2. [`Roadmap.md`](Roadmap.md) — What ships when (12 phases)
3. [`docs/architecture/00-MASTER-ARCHITECTURE.md`](docs/architecture/00-MASTER-ARCHITECTURE.md) — Schema + 20-section integrated design
4. The eight per-domain designs `01-` through `08-` for details

## License

Source-available during development. Production licence to be set before FAZA 1 launch.
