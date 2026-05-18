# SilkLens Code Review — 2026-05-18

> **Reviewer:** code-reviewer agent
> **Scope:** Wave 1-2-3 (commits 3a0fc12, aa8f0fa, 6c18b26)
> **Grade:** B+
> **Verdict:** Block tag — 3 Critical items must land first.

## Top 3 critical (matches security review):

1. **CRIT-1 / SEC-006** — RLS deployed but `app.set_tenant_context()` never called per request. All multi-tenant queries are cross-readable.
2. **CRIT-2 / SEC-012** — `rotate_refresh_token` does non-atomic SELECT-then-UPDATE → concurrent refresh race bypasses replay defence.
3. **CRIT-3 / SEC-001** — `POST /v1/billing/webhooks/{provider}` accepts any payload with zero signature verification.

## Highlights of what the agents got right
- ADR-0002 outbox pattern honored across heritage, social, billing, gamification with zero bypass
- Identity Argon2id + family rotation correct
- Heritage bi-temporal revision trigger split BEFORE/AFTER cleanly
- Gamification gaps-and-islands streak SQL is elegant
- Billing idempotency-key required + duplicate-detection works
- Migration 0054 enumerates RLS targets dynamically from `information_schema` (smart)

## High-priority (resolve in Wave 4):
- HIGH-1: `get_by_pub_id` / `get_by_id` missing `deleted_at IS NULL`
- HIGH-2: XP idempotency uses SELECT-then-INSERT, should be `INSERT ON CONFLICT DO NOTHING RETURNING`
- HIGH-3: Media upload no MIME magic-byte validation
- HIGH-4: `domain/ai/service.py` imports SQLAlchemy — ADR-0003 violation
- HIGH-5: bare `assert` statements in production code paths
- HIGH-6: N+1 query in `GET /v1/ai/fallback-chains`

## Medium / Low — see full report in agent output transcript.

## Recommended Wave 4 work (priority order)
1. Ship `TenantContextMiddleware` calling `app.set_tenant_context()` per authenticated request
2. Atomic refresh-token rotation via `UPDATE … WHERE used_at IS NULL RETURNING …`
3. Webhook shared-secret check (until FAZA 4 real Stripe signature)
4. `deleted_at IS NULL` on heritage get methods
5. MIME magic-byte validation on media upload
6. Extract `AiRepository` protocol to fix ADR-0003 violation
7. Replace bare `assert` with explicit raise
8. Fix `record_payment` event double-emit on duplicate
9. Generate `invoice.number` via trigger/sequence
10. Add `zod` schemas to admin forms missing them
