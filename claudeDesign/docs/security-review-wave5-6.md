# SilkLens — Wave 5+6 Security + Code Review (FAZA 4 + FAZA 5)

> **Reviewers:** security-reviewer + code-reviewer agents
> **Scope:** commits `914cce0` → `deaf0ff`
> **Date:** 2026-05-18
> **Verdict:** BLOCK `v0.2.0-beta` tag — critical findings must land first.

## TL;DR

Both reviewers independently flagged the same critical surfaces. Combined:

| Severity | Count |
|---|---|
| CRITICAL | 4 unique |
| HIGH | 7 unique |
| MEDIUM | 11 unique |
| LOW/Info | 8 unique |

## Critical (must fix before v0.2.0-beta)

| ID | Where | What |
|---|---|---|
| C-1 / SEC-W5-001 | `paypal_provider.py:230-244` | When PayPal SDK absent + webhook_id set → `return True` accepts any payload as verified |
| C-2 / SEC-W5-007 | `compliance.py:385,471` | `require_recent_mfa(allow_first_setup=True)` on account-delete + admin GDPR-approve lets session-token theft trigger destructive actions |
| H-1 / SEC-W5-003 | `ratelimit.py:71-83` | `X-Forwarded-For` trusted without proxy CIDR allowlist → IP rate-limit and lockout bypassed |
| SEC-W5-002 | `mfa/totp.py:53-68` + `mfa/service.py:163-197` | TOTP codes can be replayed within the 30s window across separate `mfa_challenges` rows |

## High

| ID | Where | What |
|---|---|---|
| H-2 | `mfa.py:337-339` | `POST /auth/mfa/challenge` returns 404 for unknown user_id — enumeration oracle |
| H-3 | `mfa/service.py:160,290` | Bare `assert` stripped with -O |
| H-4 | `tests/test_notifications.py` | Fixture teardown race in `test_send_templated_creates_inbox_entry` |
| SEC-W5-004 | `click_provider.py:71-83,227-242` | Click MD5 sign-string field order doesn't match docstring of HMAC-SHA1 variant |
| SEC-W5-005 | `mfa.py:183-203` (enrollment routes) | TOTP / WebAuthn enrollment doesn't require step-up or password re-auth → session-token theft → persistent MFA enrollment |
| SEC-W5-006 | `compliance.py:473-491` | `admin_process_request` scopes by admin's own residency_region → cross-region GDPR requests silently 404 |
| SEC-W5-008 | `reseller/service.py:262-283` | Revenue-share SELECT+INSERT non-atomic → cross-row sum can exceed 100% |

## Medium

(See agent transcripts for full list — webhook header propagation to 3rd party, OTel sign_count, step-up token session_id=user_id, legal-doc cross-tenant publishing via tenant_id=NULL, cookie consent unbound to session, GDPR payload_url admin-supplied no-validation, SPARQL interpolation pattern hygiene, etc.)

## Low / Informational

(OTel trace headers propagated to Anthropic/Stripe/PayPal, Retry-After leak, backup-code non-atomic replace, anonymization misses payment tables, dashboard datasource UID hardcoded, etc.)

## Commendations

- Backup-code single-use enforced via SQL `AND used_at IS NULL` + `RETURNING id` (correct)
- TOTP at-rest encrypted via pgcrypto with key from settings on every call
- MFA challenge expiry + replay defence solid (`is_completed` + atomic update)
- Wikidata 1-req/sec lock honoured under concurrency
- Domain layer SQLAlchemy-free after AiRepository extraction
- Prometheus metrics bounded labels (no per-user cardinality)
- Sentry `send_default_pii=False` correct + traces_sample_rate=0.1

## Pre-tag checklist for v0.2.0-beta

Items in this session before tag:
- [ ] C-1 / SEC-W5-001: PayPal — raise `InvalidWebhookSignature("paypal_sdk_unavailable")` when SDK absent + webhook_id set
- [ ] C-2 / SEC-W5-007: `allow_first_setup=False` on account-delete + admin GDPR
- [ ] H-1 / SEC-W5-003: trusted_proxy_cidrs setting + check origin before honouring X-Forwarded-For
- [ ] SEC-W5-005: TOTP/WebAuthn enrollment require step-up or re-auth
- [ ] SEC-W5-002: TOTP code-reuse defence — `mfa_used_totp_slots` table

Deferred to v0.3.0 (tracked in HANDOFF):
- TOTP reuse table + SQL function (lighter version: track latest slot per user)
- Revenue-share serializable transaction (lower urgency without active resellers)
- WebAuthn sign_count > previous explicit check (lib usually handles)
- All MEDIUM findings
- All LOW findings
