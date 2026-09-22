# SilkLens Security Review — 2026-05-18

> **Reviewer:** security-reviewer agent
> **Scope:** Wave 1-2-3 deliverables (commits `3a0fc12`, `aa8f0fa`, `6c18b26`)
> **Status:** 4 Critical · 5 High · 6 Medium · 8 Low/Info · 7 Deferred
> **Verdict:** Cannot tag `v0.1.0-alpha` without fixing the 4 critical findings.

## TL;DR

The architecture is sound; the runtime is missing several load-bearing
plumbing pieces that make existing security designs (RLS, HMAC audit chain,
BOLA checks) non-functional in their current state.

**Must fix before any tag:**

1. **SEC-001** — `POST /v1/billing/webhooks/{provider}` accepts any payload with zero signature verification.
2. **SEC-002** — `app.audit()` falls back to `'dev-only-fallback'` HMAC key; the per-request middleware that should set the real key is not wired.
3. **SEC-003** — `GET /v1/media/{asset_id}` returns metadata to any authenticated user regardless of ownership.
4. **SEC-004** — Refresh tokens hashed with bare SHA-256 (claimed HMAC but code is just `hashlib.sha256`).

## Findings

### Critical (block ship)

| ID | Where | What | Fix |
|---|---|---|---|
| SEC-001 | `routers/billing.py:348-389` | Unauthenticated webhook; attacker-controlled `provider` + `provider_event_id` | Allow-list providers, verify Stripe-Signature, require shared secret pre-FAZA4 |
| SEC-002 | `alembic/.../0007_audit_log.py:162-168` + missing middleware | Hash chain HMAC'd with public string until middleware wires `SET LOCAL app.audit_hmac_key` | Add per-request middleware; remove fallback constant |
| SEC-003 | `routers/media.py:164-174` + `media/service.py:128-132` + `media/repository.py` | No tenant/owner filter on media GET | Add `AND tenant_id = :tenant` to repository |
| SEC-004 | `infrastructure/security.py:102-106` | `hashlib.sha256(plaintext).digest()` — comment lies about HMAC | Use `hmac.new(secret, plaintext, sha256).digest()` |

### High

| ID | Where | What | Fix |
|---|---|---|---|
| SEC-005 | All auth routes | No rate-limiting; Argon2 burns CPU per login | Add `slowapi` w/ Redis backend; 5/min login |
| SEC-006 | Migration `0054` + `get_session` | RLS enabled but `app.set_tenant_context()` never called → either all rows invisible or BYPASSRLS makes RLS decorative | Call `app.set_tenant_context(tenant_id)` in `get_session` after auth |
| SEC-007 | `api/app.py:64` | `openapi.json` always public | Gate `openapi_url` on `env != 'prod'` |
| SEC-008 | `0006_rbac.py:228-251` (`app.has_permission`) | No `users.deleted_at` filter — banned users keep permissions until JWT expires | Add `JOIN users ON …deleted_at IS NULL AND status='active'` |
| SEC-009 | `routers/ai.py:205-227` + `ai/service.py:555-573` | User-supplied `system` prompt passed verbatim to Anthropic — direct prompt injection | Remove field or gate behind `ai:invoke_unrestricted`; classify input, not output |

### Medium

| ID | Where | What |
|---|---|---|
| SEC-010 | `identity/service.py:100` | Account-enumeration via distinct 409 vs 422 errors on register |
| SEC-011 | `routers/media.py:147-148` | Client-supplied MIME type accepted without magic-byte validation |
| SEC-012 | `infrastructure/identity/repositories.py:483-591` | `rotate_refresh_token` non-atomic SELECT-then-UPDATE → race |
| SEC-013 | `core/settings.py:76` + admin/ai routers | Hardcoded default tenant UUID silently used in writes |
| SEC-014 | `ai/service.py:644-677` | `where` built by concat; `vec_literal` formatted into SQL; future regression risk |
| SEC-015 | `media/service.py:143-156` + `minio_client.py:76` | 1h fixed TTL on signed URLs, no `max_uses` enforced, `minio_secure=False` default |

### Low / Informational

- SEC-016 — `PATCH /v1/heritage/{pub_id}` accepts `status` from caller with `heritage:update` — bypasses moderation FSM
- SEC-017 — `api_host=0.0.0.0` binds on all interfaces (acceptable behind reverse proxy)
- SEC-018 — `database_echo` would log token hashes if set true
- SEC-019 — `minio_secure=False` default
- SEC-020 — `ai.py` `UPDATE ai_models SET … WHERE slug=` uses string concat (closed field set, documented)
- SEC-021 — `FriendInviteOut.token` exposed in response after first send
- SEC-022 — `preferred_timezone` not validated against IANA database
- SEC-023 — Audit `prev_hash` read without row lock; concurrent writes can fork the chain

### Deferred / acceptable for v0.1.0-alpha

- MFA / WebAuthn
- KMS-backed HMAC key (env var is alpha-acceptable IF SEC-002 fix lands)
- OAuth Google/Apple/Telegram backend integration
- Real Stripe/Payme/Click integration (Mock provider keeps payments boundary off real money)
- Merkle anchor background job
- PII data residency for AI calls (Anthropic API leaves UZ)
- True RLS enforcement (after SEC-006 fix, RLS becomes actually enforced)

## Pre-tag checklist

- [ ] SEC-001 webhook signature + provider allow-list
- [ ] SEC-002 audit HMAC key middleware + remove fallback constant
- [ ] SEC-003 media GET tenant filter
- [ ] SEC-004 refresh-token HMAC fix
- [ ] SEC-006 `app.set_tenant_context()` per request
- [ ] SEC-007 `openapi.json` env gate
- [ ] SEC-008 `app.has_permission` deleted_at filter
- [ ] SEC-009 chat `system` field gated or removed
- [ ] SEC-012 atomic refresh-token rotation
- [ ] SEC-016 `heritage:moderate` required for direct status writes
- [ ] Confirm DB role does NOT have `BYPASSRLS`
- [ ] `pip-audit` clean on production deps
