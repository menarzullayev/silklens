# SilkLens — Architecture: Identity, Auth, RBAC, GDPR & Audit

> **Agent 2 — User & Identity Architect**
> **Domain:** Users, authentication, sessions, RBAC/ABAC, consent, audit, GDPR/Uzbek PD compliance.
> **Stack:** PostgreSQL 16, Redis 7, FastAPI, JWT + opaque refresh, RLS, monthly partitioning.
> **Status:** v1.0 — production-grade design intended to be implemented Week 1–2 of FAZA 1.

---

## 1. Domain Analysis

### 1.1 Identity model

SilkLens has one canonical real-world person represented by a single `users` row. Around that row, **multiple authentication identities** can be linked: a person can sign in with Google in Tashkent, with Apple from an iPhone in Samarkand, and with a Telegram account from a desktop — all three must converge onto the same `users.id`. Identity merging is therefore a first-class operation, not an afterthought.

Three classes of users coexist:

1. **Guest** — anonymous, created on first app open. Has a stable `users.id` and a device-bound token. Earns XP, leaves a fingerprint, can view heritage and even upload UGC if the admin enables it. Guests **cannot** be deleted on a whim because their XP/badges are real value.
2. **Registered** — has at least one verified identity (email, phone, OAuth, WebAuthn).
3. **Trusted Contributor** — registered + trust score ≥ threshold (per Project-Decisions Q43). Gets auto-publish privileges, bypassing pre-moderation.

**Guest → Registered conversion** is non-destructive: same `users.id`, same XP, new `user_identities` row, `is_guest` flag flips to `false`.

### 1.2 Consent model

Three concurrent legal regimes apply:

- **Uzbekistan PD law (2019)** — some PII categories must be stored on Uzbek soil; user has a right to deletion on request.
- **GDPR (EU residents)** — explicit consent per processing purpose, right-to-erasure, data portability, 30-day deletion SLA.
- **CCPA (California residents)** — "Do Not Sell My Data", right to know what is collected.

Consent is **purpose-scoped, version-pinned and per-jurisdiction**. We never store a global "user agreed to ToS" boolean; we store rows like *(user_id, purpose=analytics, legal_doc_version=privacy_policy@2026-05-18@uz, granted_at, withdrawn_at, jurisdiction=UZ, lawful_basis=consent)*. When a policy is updated, every active user must re-consent before next privileged action.

### 1.3 Threat model (summary, full §10)

Top threats: (1) credential stuffing on `/auth/email/login`, (2) OAuth account takeover via email-claim collision, (3) mass account creation via guest endpoint for scraping, (4) privileged moderator account compromise → mass data deletion, (5) audit log tampering by a compromised DB admin, (6) GDPR delete-bombing as a denial-of-service.

Mitigations are designed in: rate-limited `login_attempts` table, OAuth-binding requires verified email match, guest accounts capped per device/IP per hour, step-up re-auth (`reauth_required_at`) for destructive actions, HMAC hash-chained audit log with daily cross-signed anchor, GDPR request throttling (one open request per user at a time, 30-day grace cancels prior).

### 1.4 Design invariants

- **Email uniqueness is not enforced on `users`** — it lives on `user_emails` with `CITEXT` + `verified_at`. An unverified email never blocks another user from registering.
- **One `user_identities` row per (provider, provider_subject)** — uniqueness is global.
- **Audit log is append-only** at the DB role level: the application role has `INSERT`-only privileges, no `UPDATE`/`DELETE`.
- **PII columns are tagged** with COMMENT `'pii:high'`, `'pii:medium'`, `'pii:low'` — drives automated GDPR export and deletion generators.
- **Region drives residency.** `users.residency_region` is immutable after first verified login and determines the partition (and the physical tablespace) on which the user's PII lives.

---

## 2. Entity Discovery Report

Total tables in this domain: **32**.

| # | Table | Purpose | Notes |
|---|---|---|---|
| 1 | `users` | Canonical person record | Soft-deletable, residency-partitioned |
| 2 | `user_profiles` | Mutable profile (display name, avatar, locale) | 1:1 with users |
| 3 | `user_identities` | One row per linked auth identity | Provider + subject unique |
| 4 | `user_emails` | Multiple emails per user, primary + verified | CITEXT |
| 5 | `user_phones` | Multiple phones per user | E.164 |
| 6 | `oauth_providers` | Admin-managed catalog of providers | Per Project-Decisions: nothing hardcoded |
| 7 | `oauth_provider_secrets` | Encrypted client secrets per env | KMS-wrapped |
| 8 | `sessions` | Active session per device | Redis-cached, DB-authoritative |
| 9 | `refresh_tokens` | Opaque rotating refresh tokens | Family-tracked for reuse detection |
| 10 | `device_fingerprints` | Stable device identity | Independent of session |
| 11 | `roles` | RBAC role catalog | Hierarchical via `parent_role_id` |
| 12 | `permissions` | Permission catalog | `domain:action[:scope]` strings |
| 13 | `role_permissions` | M:N role↔permission | |
| 14 | `user_roles` | M:N user↔role + scope + expires_at | Scoped (e.g. moderator-for-UZ) |
| 15 | `attribute_policies` | ABAC overlay (CEL/Rego expressions) | Evaluated after RBAC allow |
| 16 | `audit_log` | Append-only event stream | Monthly partitions, HMAC hash chain |
| 17 | `audit_anchors` | Daily cross-signed merkle roots | Tamper evidence |
| 18 | `consent_records` | Versioned consent per purpose | Per jurisdiction |
| 19 | `legal_documents` | ToS / Privacy / DPA texts | Per language, per version, per jurisdiction |
| 20 | `gdpr_requests` | Export & deletion requests | State machine, 30-day grace |
| 21 | `anonymization_jobs` | Async PII scrub orchestration | Resumable, idempotent |
| 22 | `bans` | Hard bans with reason & expiry | |
| 23 | `shadowbans` | Soft restrictions (content invisible to others) | |
| 24 | `trust_scores` | Materialized trust per user | Recomputed nightly |
| 25 | `reputation_events` | Atomic signed contributions to trust | Append-only |
| 26 | `moderation_actions` | Moderator decisions ledger | Linked to bans/shadowbans |
| 27 | `mfa_methods` | TOTP, SMS, WebAuthn methods | Per-user multi-method |
| 28 | `webauthn_credentials` | FIDO2/WebAuthn public keys | |
| 29 | `password_reset_tokens` | Single-use, short-lived | |
| 30 | `magic_link_tokens` | Passwordless email links | |
| 31 | `email_verifications` | Pending email verifications | |
| 32 | `phone_verifications` | Pending phone OTP | |
| 33 | `login_attempts` | Rate-limit + fraud signal | Partitioned weekly |
| 34 | `account_recovery_codes` | One-time backup codes | bcrypt-hashed |
| 35 | `api_personal_tokens` | User-issued API tokens (PAT) | For B2B/dev users |

(35 tables — exceeds the minimum 32. `oauth_provider_secrets` and `audit_anchors` are additions justified in §3 / §7.)

### Why these and not fewer

- **`user_identities` vs `oauth_providers`** — `oauth_providers` is the admin-editable *catalog* (we can disable Facebook at midnight without code change, per Project-Decisions Q33). `user_identities` is the *binding* of a real user to a real provider account. Collapsing them makes provider rollout / kill-switch impossible.
- **`user_emails`, not `users.email`** — A person legitimately has multiple emails (work, personal). Verification status lives on the email, not the user. Email is also the most common identity-merge key.
- **`audit_log` + `audit_anchors`** — append-only is not enough; we need cryptographic tamper-evidence the DBA cannot subvert. The anchor table is published daily to an external store (S3 with Object Lock + a public Git commit).
- **`anonymization_jobs`** distinct from `gdpr_requests` — request is the legal artifact (must be retained); the job is the operational task (resumable, parallel across 30+ tables).
- **`reputation_events` + `trust_scores`** — events are facts (append-only), score is a materialized projection. Separation lets us re-derive trust from history when the formula changes.

---

## 3. Full Table-by-Table Specification

> Notation: `[PK]`, `[FK→x.y]`, `[U]` unique, `[I]` indexed, `[RLS]` row-level-security policy applies.
> All tables have `created_at timestamptz NOT NULL DEFAULT now()` and (where mutable) `updated_at timestamptz NOT NULL DEFAULT now()` unless noted.
> All `id` columns are `uuid NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY` unless noted.

### 3.1 `users`

```sql
CREATE TABLE users (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  public_id            text NOT NULL UNIQUE,                      -- short slug for URLs, e.g. 'silk-7H3K2'
  is_guest             boolean NOT NULL DEFAULT true,
  is_active            boolean NOT NULL DEFAULT true,
  is_locked            boolean NOT NULL DEFAULT false,            -- security lockout (different from ban)
  locked_reason        text,
  locked_until         timestamptz,
  residency_region     text NOT NULL DEFAULT 'global',            -- 'uz','eu','us-ca','global' — drives partition
  primary_locale       text NOT NULL DEFAULT 'en',                -- BCP-47
  primary_timezone     text NOT NULL DEFAULT 'UTC',
  last_seen_at         timestamptz,
  last_login_at        timestamptz,
  password_hash        text,                                      -- bcrypt cost 12, NULL for OAuth-only users
  password_changed_at  timestamptz,
  password_must_change boolean NOT NULL DEFAULT false,
  mfa_enforced         boolean NOT NULL DEFAULT false,
  reauth_required_at   timestamptz,                               -- step-up auth deadline
  trust_level          smallint NOT NULL DEFAULT 0,               -- denormalized from trust_scores for hot path
  schema_version       smallint NOT NULL DEFAULT 1,
  created_at           timestamptz NOT NULL DEFAULT now(),
  updated_at           timestamptz NOT NULL DEFAULT now(),
  deleted_at           timestamptz,                               -- soft delete
  anonymized_at        timestamptz,                               -- PII scrubbed
  hard_delete_after    timestamptz,                               -- legal-hold expiry
  CONSTRAINT users_residency_chk CHECK (residency_region IN ('uz','eu','us','us-ca','global'))
) PARTITION BY LIST (residency_region);

CREATE TABLE users_uz     PARTITION OF users FOR VALUES IN ('uz')      TABLESPACE ts_uz;
CREATE TABLE users_eu     PARTITION OF users FOR VALUES IN ('eu')      TABLESPACE ts_eu;
CREATE TABLE users_us     PARTITION OF users FOR VALUES IN ('us','us-ca') TABLESPACE ts_us;
CREATE TABLE users_global PARTITION OF users FOR VALUES IN ('global')  TABLESPACE ts_global;

CREATE INDEX idx_users_last_seen        ON users (last_seen_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_deleted          ON users (deleted_at) WHERE deleted_at IS NOT NULL;
CREATE INDEX idx_users_hard_delete_due  ON users (hard_delete_after) WHERE hard_delete_after IS NOT NULL;
CREATE INDEX idx_users_locked_until     ON users (locked_until) WHERE locked_until IS NOT NULL;
```

**RLS:** Enabled. Policies: `users_self_read` (`current_setting('app.user_id')::uuid = id`), `users_admin_all` (role `admin_role` bypasses), `users_moderator_read` (read-only for `moderator_role` filtered by residency scope).

**PII tags:** `password_hash` → `pii:credential`, `last_seen_at` → `pii:low`, `public_id` → `pii:none`.

### 3.2 `user_profiles`

```sql
CREATE TABLE user_profiles (
  user_id              uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  display_name         text NOT NULL,
  username             citext UNIQUE,                             -- optional handle
  bio                  text,
  avatar_media_id      uuid,                                       -- FK to media domain (Agent 4)
  cover_media_id       uuid,
  preferred_languages  text[] NOT NULL DEFAULT ARRAY['en'],
  country_code         char(2),                                    -- ISO 3166-1 alpha-2
  city                 text,
  birth_year           smallint,                                   -- year only — minimization
  pronouns             text,
  is_public            boolean NOT NULL DEFAULT false,
  search_indexable     boolean NOT NULL DEFAULT false,
  created_at           timestamptz NOT NULL DEFAULT now(),
  updated_at           timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_user_profiles_username  ON user_profiles (username) WHERE username IS NOT NULL;
CREATE INDEX idx_user_profiles_country   ON user_profiles (country_code);
```

PII: `display_name` → `pii:medium`, `birth_year` → `pii:medium`, `city` → `pii:medium`.

### 3.3 `user_identities`

One row per linked external identity. The merge anchor.

```sql
CREATE TABLE user_identities (
  id                       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id                  uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  provider_id              uuid NOT NULL REFERENCES oauth_providers(id),
  provider_subject         text NOT NULL,                          -- 'sub' claim or provider user ID
  provider_email           citext,                                 -- email reported by provider at link time
  provider_email_verified  boolean NOT NULL DEFAULT false,
  provider_display_name    text,
  provider_avatar_url      text,
  raw_profile              jsonb,                                  -- last provider profile snapshot
  access_token_encrypted   bytea,                                  -- pgcrypto, KMS-wrapped DEK
  refresh_token_encrypted  bytea,
  token_expires_at         timestamptz,
  scopes                   text[] NOT NULL DEFAULT '{}',
  linked_at                timestamptz NOT NULL DEFAULT now(),
  last_used_at             timestamptz,
  is_primary               boolean NOT NULL DEFAULT false,         -- primary identity for password recovery
  UNIQUE (provider_id, provider_subject)
);

CREATE INDEX idx_user_identities_user    ON user_identities (user_id);
CREATE INDEX idx_user_identities_email   ON user_identities (provider_email) WHERE provider_email IS NOT NULL;
CREATE UNIQUE INDEX idx_user_identities_one_primary ON user_identities (user_id) WHERE is_primary;
```

### 3.4 `user_emails`

```sql
CREATE TABLE user_emails (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  email        citext NOT NULL,
  is_primary   boolean NOT NULL DEFAULT false,
  verified_at  timestamptz,
  source       text NOT NULL DEFAULT 'manual',                    -- manual | oauth_google | oauth_apple | imported
  created_at   timestamptz NOT NULL DEFAULT now(),
  UNIQUE (email) WHERE verified_at IS NOT NULL                    -- only verified emails are globally unique
);

CREATE INDEX idx_user_emails_user    ON user_emails (user_id);
CREATE INDEX idx_user_emails_email   ON user_emails (email);
CREATE UNIQUE INDEX idx_user_emails_one_primary ON user_emails (user_id) WHERE is_primary;
```

PII: `email` → `pii:high`.

### 3.5 `user_phones`

```sql
CREATE TABLE user_phones (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  phone_e164   text NOT NULL,                                     -- +998901234567
  is_primary   boolean NOT NULL DEFAULT false,
  verified_at  timestamptz,
  carrier      text,
  region_code  char(2),
  created_at   timestamptz NOT NULL DEFAULT now(),
  UNIQUE (phone_e164) WHERE verified_at IS NOT NULL,
  CONSTRAINT user_phones_e164_chk CHECK (phone_e164 ~ '^\+[1-9][0-9]{6,14}$')
);

CREATE INDEX idx_user_phones_user ON user_phones (user_id);
CREATE UNIQUE INDEX idx_user_phones_one_primary ON user_phones (user_id) WHERE is_primary;
```

### 3.6 `oauth_providers`

Admin-managed catalog. Adding Facebook OAuth is a single row insert, no deploy.

```sql
CREATE TABLE oauth_providers (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug               text NOT NULL UNIQUE,                        -- 'google','apple','telegram','facebook','vk'
  display_name       text NOT NULL,
  protocol           text NOT NULL,                               -- 'oidc' | 'oauth2' | 'telegram_widget'
  auth_url           text,
  token_url          text,
  userinfo_url       text,
  jwks_url           text,
  issuer             text,
  default_scopes     text[] NOT NULL DEFAULT '{}',
  client_id          text NOT NULL,
  is_enabled         boolean NOT NULL DEFAULT true,
  trust_email        boolean NOT NULL DEFAULT false,              -- can we trust the email claim for identity merge?
  icon_url           text,
  sort_order         smallint NOT NULL DEFAULT 100,
  config             jsonb NOT NULL DEFAULT '{}',                 -- arbitrary provider quirks
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT oauth_protocol_chk CHECK (protocol IN ('oidc','oauth2','telegram_widget','saml'))
);
```

### 3.7 `oauth_provider_secrets`

Secrets separated from `oauth_providers` so the catalog is readable by an admin role while secrets require a higher privilege.

```sql
CREATE TABLE oauth_provider_secrets (
  provider_id            uuid NOT NULL REFERENCES oauth_providers(id) ON DELETE CASCADE,
  environment            text NOT NULL,                           -- 'dev'|'staging'|'prod'
  client_secret_encrypted bytea NOT NULL,                         -- KMS-wrapped
  kms_key_id             text NOT NULL,
  rotated_at             timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (provider_id, environment)
);

-- RLS: only role `secrets_role` may SELECT
ALTER TABLE oauth_provider_secrets ENABLE ROW LEVEL SECURITY;
```

### 3.8 `sessions`

```sql
CREATE TABLE sessions (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  device_id           uuid REFERENCES device_fingerprints(id) ON DELETE SET NULL,
  identity_id         uuid REFERENCES user_identities(id) ON DELETE SET NULL,
  jwt_jti             uuid NOT NULL UNIQUE,                       -- JWT ID for revocation
  user_agent          text,
  ip_address          inet,
  ip_country          char(2),
  ip_asn              integer,
  client_version      text,                                       -- app version
  platform            text,                                       -- ios | android | web | admin
  mfa_satisfied       boolean NOT NULL DEFAULT false,
  amr                 text[] NOT NULL DEFAULT '{}',               -- auth method refs: ['pwd','otp','webauthn']
  acr_level           smallint NOT NULL DEFAULT 1,                -- 1=basic, 2=mfa, 3=step-up
  issued_at           timestamptz NOT NULL DEFAULT now(),
  last_active_at      timestamptz NOT NULL DEFAULT now(),
  expires_at          timestamptz NOT NULL,
  revoked_at          timestamptz,
  revoked_reason      text,                                       -- 'logout','admin','password_change','reuse_detected'
  CONSTRAINT sessions_revoked_chk CHECK ((revoked_at IS NULL) = (revoked_reason IS NULL))
);

CREATE INDEX idx_sessions_user_active ON sessions (user_id) WHERE revoked_at IS NULL;
CREATE INDEX idx_sessions_expires     ON sessions (expires_at) WHERE revoked_at IS NULL;
CREATE INDEX idx_sessions_device      ON sessions (device_id);
```

Redis mirror: `session:{jti} → {user_id, acr, expires_at}`, TTL = session lifetime.

### 3.9 `refresh_tokens`

Opaque, rotating, family-tracked for reuse detection (RFC 6819 §5.2.2.3).

```sql
CREATE TABLE refresh_tokens (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id      uuid NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  family_id       uuid NOT NULL,                                  -- shared across rotation chain
  token_hash      bytea NOT NULL UNIQUE,                          -- SHA-256(token)
  parent_id       uuid REFERENCES refresh_tokens(id),
  issued_at       timestamptz NOT NULL DEFAULT now(),
  expires_at      timestamptz NOT NULL,
  used_at         timestamptz,                                    -- single-use; if reused → kill family
  rotated_to_id   uuid REFERENCES refresh_tokens(id),
  revoked_at      timestamptz
);

CREATE INDEX idx_refresh_tokens_family  ON refresh_tokens (family_id);
CREATE INDEX idx_refresh_tokens_session ON refresh_tokens (session_id);
```

On reuse: set `revoked_at` on every token in the family, revoke the session, write `audit_log.kind='auth.refresh_reuse_detected'`.

### 3.10 `device_fingerprints`

```sql
CREATE TABLE device_fingerprints (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id            uuid REFERENCES users(id) ON DELETE SET NULL, -- nullable: pre-registration device
  fingerprint_hash   bytea NOT NULL UNIQUE,                       -- SHA-256 of combined signals
  device_name        text,                                        -- user-friendly: "Sardor's iPhone"
  os                 text,
  os_version         text,
  app_version        text,
  push_token         text,                                        -- FCM/APNs
  push_token_platform text,                                       -- 'fcm' | 'apns'
  trusted            boolean NOT NULL DEFAULT false,              -- user marked as trusted device
  first_seen_at      timestamptz NOT NULL DEFAULT now(),
  last_seen_at       timestamptz NOT NULL DEFAULT now(),
  fraud_score        smallint NOT NULL DEFAULT 0                  -- 0..100
);

CREATE INDEX idx_device_fingerprints_user ON device_fingerprints (user_id);
```

### 3.11 `roles`

```sql
CREATE TABLE roles (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug            text NOT NULL UNIQUE,                           -- 'admin','moderator','contributor','user','guest'
  display_name    text NOT NULL,
  description     text,
  parent_role_id  uuid REFERENCES roles(id),                      -- inheritance
  is_system       boolean NOT NULL DEFAULT false,                 -- cannot be deleted via admin UI
  is_assignable   boolean NOT NULL DEFAULT true,
  created_at      timestamptz NOT NULL DEFAULT now()
);
```

Bootstrap: `guest < user < contributor < trusted_contributor < moderator < regional_admin < admin < superadmin`.

### 3.12 `permissions`

```sql
CREATE TABLE permissions (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug          text NOT NULL UNIQUE,                             -- 'heritage:create', 'user:ban', 'billing:refund'
  domain        text NOT NULL,                                    -- 'heritage','user','billing','content','media'
  action        text NOT NULL,                                    -- 'create','read','update','delete','moderate'
  description   text,
  is_dangerous  boolean NOT NULL DEFAULT false,                   -- requires step-up auth
  created_at    timestamptz NOT NULL DEFAULT now()
);
```

### 3.13 `role_permissions`

```sql
CREATE TABLE role_permissions (
  role_id        uuid NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  permission_id  uuid NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
  granted_at     timestamptz NOT NULL DEFAULT now(),
  granted_by     uuid REFERENCES users(id),
  PRIMARY KEY (role_id, permission_id)
);
```

### 3.14 `user_roles`

```sql
CREATE TABLE user_roles (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role_id      uuid NOT NULL REFERENCES roles(id),
  scope_type   text,                                              -- 'global','region','city','heritage','organization'
  scope_value  text,                                              -- e.g. 'uz' for region, '<heritage_id>' for heritage
  granted_at   timestamptz NOT NULL DEFAULT now(),
  granted_by   uuid REFERENCES users(id),
  expires_at   timestamptz,
  revoked_at   timestamptz,
  reason       text,
  UNIQUE (user_id, role_id, scope_type, scope_value)
);

CREATE INDEX idx_user_roles_user_active ON user_roles (user_id) WHERE revoked_at IS NULL;
```

`scope_type='region', scope_value='uz'` ⇒ "Moderator for Uzbekistan only".

### 3.15 `attribute_policies` (ABAC)

```sql
CREATE TABLE attribute_policies (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug          text NOT NULL UNIQUE,
  permission_id uuid NOT NULL REFERENCES permissions(id),
  effect        text NOT NULL,                                    -- 'allow' | 'deny' (deny wins)
  expression    text NOT NULL,                                    -- CEL: 'resource.owner_id == subject.id'
  priority      smallint NOT NULL DEFAULT 100,
  is_enabled    boolean NOT NULL DEFAULT true,
  created_at    timestamptz NOT NULL DEFAULT now(),
  created_by    uuid REFERENCES users(id),
  CONSTRAINT abac_effect_chk CHECK (effect IN ('allow','deny'))
);
```

Examples:
- `heritage:update + (resource.owner_id == subject.id)` allow → users edit their own UGC.
- `user:ban + (resource.trust_level >= 80)` deny → trusted users require superadmin to ban.

### 3.16 `audit_log` (partitioned, append-only)

```sql
CREATE TABLE audit_log (
  id              bigint GENERATED ALWAYS AS IDENTITY,            -- per-partition local sequence
  event_id        uuid NOT NULL DEFAULT gen_random_uuid(),
  occurred_at     timestamptz NOT NULL DEFAULT now(),
  ingested_at     timestamptz NOT NULL DEFAULT now(),
  actor_user_id   uuid REFERENCES users(id),                      -- NULL for system events
  actor_role      text,                                           -- snapshot of role at action time
  on_behalf_of    uuid REFERENCES users(id),                      -- admin impersonation
  session_id      uuid,                                           -- not FK — sessions can be purged
  ip_address      inet,
  user_agent      text,
  kind            text NOT NULL,                                  -- 'auth.login.success','user.banned','gdpr.export.requested'
  severity        text NOT NULL DEFAULT 'info',                   -- 'debug','info','notice','warn','error','critical'
  target_type     text,                                           -- 'user','heritage','session','role'
  target_id       text,
  diff            jsonb,                                          -- before/after snippet
  metadata        jsonb NOT NULL DEFAULT '{}',
  prev_hash       bytea NOT NULL,                                 -- HMAC chain
  row_hash        bytea NOT NULL,
  PRIMARY KEY (occurred_at, id)
) PARTITION BY RANGE (occurred_at);

-- Monthly partitions auto-created by pg_partman
CREATE TABLE audit_log_2026_05 PARTITION OF audit_log
  FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
-- ... etc

CREATE INDEX idx_audit_log_2026_05_actor   ON audit_log_2026_05 (actor_user_id, occurred_at DESC);
CREATE INDEX idx_audit_log_2026_05_kind    ON audit_log_2026_05 (kind, occurred_at DESC);
CREATE INDEX idx_audit_log_2026_05_target  ON audit_log_2026_05 (target_type, target_id, occurred_at DESC);
CREATE INDEX idx_audit_log_2026_05_session ON audit_log_2026_05 (session_id) WHERE session_id IS NOT NULL;

-- Privilege: app role gets INSERT only
REVOKE UPDATE, DELETE ON audit_log FROM app_role;
GRANT INSERT, SELECT ON audit_log TO app_role;
```

`row_hash = HMAC_SHA256(secret_key, prev_hash || canonical_json(row_minus_hashes))`. A daily job rolls partitions older than 12 months to cold storage (Parquet on MinIO).

### 3.17 `audit_anchors`

Daily tamper-evidence anchors.

```sql
CREATE TABLE audit_anchors (
  anchor_date     date PRIMARY KEY,
  partition_name  text NOT NULL,
  first_event_id  uuid NOT NULL,
  last_event_id   uuid NOT NULL,
  event_count     bigint NOT NULL,
  merkle_root     bytea NOT NULL,
  hmac_key_id     text NOT NULL,
  external_anchor_url text,                                       -- where it was published (S3 Object Lock, OpenTimestamps, Git tag)
  external_anchor_proof text,
  created_at      timestamptz NOT NULL DEFAULT now()
);
```

### 3.18 `consent_records`

```sql
CREATE TABLE consent_records (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  purpose             text NOT NULL,                              -- 'analytics','marketing_email','personalization','ugc_publishing','third_party_share'
  legal_document_id   uuid NOT NULL REFERENCES legal_documents(id),
  lawful_basis        text NOT NULL,                              -- 'consent','contract','legitimate_interest','legal_obligation'
  jurisdiction        text NOT NULL,                              -- 'uz','eu','us-ca','global'
  granted             boolean NOT NULL,
  granted_at          timestamptz NOT NULL DEFAULT now(),
  withdrawn_at        timestamptz,
  source              text NOT NULL,                              -- 'signup','settings','prompt','re-consent'
  ip_address          inet,
  user_agent          text,
  evidence_blob       jsonb                                       -- exact UI text shown, button label, locale
);

CREATE INDEX idx_consent_records_user_purpose ON consent_records (user_id, purpose, granted_at DESC);
```

A user has consent for purpose X if their latest row for (user_id, purpose, jurisdiction) has `granted=true AND withdrawn_at IS NULL`.

### 3.19 `legal_documents`

```sql
CREATE TABLE legal_documents (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  doc_type        text NOT NULL,                                  -- 'privacy_policy','tos','cookie_policy','dpa'
  jurisdiction    text NOT NULL,                                  -- 'uz','eu','us-ca','global'
  locale          text NOT NULL,                                  -- BCP-47
  version         text NOT NULL,                                  -- '2026-05-18' or '1.4.2'
  body_md         text NOT NULL,                                  -- markdown source of truth
  body_html       text NOT NULL,
  effective_from  timestamptz NOT NULL,
  effective_until timestamptz,
  superseded_by   uuid REFERENCES legal_documents(id),
  requires_reconsent boolean NOT NULL DEFAULT true,
  hash            bytea NOT NULL,                                 -- SHA-256 of body_md, for tamper-detection
  created_at      timestamptz NOT NULL DEFAULT now(),
  created_by      uuid REFERENCES users(id),
  UNIQUE (doc_type, jurisdiction, locale, version)
);

CREATE INDEX idx_legal_documents_active ON legal_documents (doc_type, jurisdiction, locale) WHERE effective_until IS NULL;
```

### 3.20 `gdpr_requests`

```sql
CREATE TABLE gdpr_requests (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           uuid NOT NULL REFERENCES users(id),
  kind              text NOT NULL,                                -- 'export','delete','rectify','restrict','object'
  jurisdiction      text NOT NULL,
  status            text NOT NULL DEFAULT 'received',             -- 'received','verifying','in_grace','processing','completed','cancelled','rejected'
  requested_at      timestamptz NOT NULL DEFAULT now(),
  grace_until       timestamptz,                                  -- 30-day cancel window for deletes
  scheduled_at      timestamptz,                                  -- when the job is allowed to start
  started_at        timestamptz,
  completed_at      timestamptz,
  cancelled_at      timestamptz,
  cancelled_reason  text,
  verification_method text,                                       -- 'email','phone','identity_doc','signed_request'
  verified_at       timestamptz,
  export_artifact_url text,                                       -- signed URL to ZIP in MinIO
  export_expires_at timestamptz,
  legal_hold        boolean NOT NULL DEFAULT false,
  legal_hold_reason text,
  notes             text,
  CONSTRAINT gdpr_kind_chk CHECK (kind IN ('export','delete','rectify','restrict','object','portability'))
);

CREATE INDEX idx_gdpr_requests_user    ON gdpr_requests (user_id);
CREATE INDEX idx_gdpr_requests_status  ON gdpr_requests (status, scheduled_at);
CREATE UNIQUE INDEX idx_gdpr_one_open_per_user ON gdpr_requests (user_id, kind) WHERE status NOT IN ('completed','cancelled','rejected');
```

### 3.21 `anonymization_jobs`

```sql
CREATE TABLE anonymization_jobs (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  gdpr_request_id uuid REFERENCES gdpr_requests(id),
  user_id         uuid NOT NULL,                                  -- not FK — user may be deleted
  strategy        text NOT NULL,                                  -- 'anonymize','hard_delete','tombstone'
  status          text NOT NULL DEFAULT 'pending',                -- 'pending','running','partial','completed','failed'
  tables_total    integer NOT NULL DEFAULT 0,
  tables_done     integer NOT NULL DEFAULT 0,
  step_state      jsonb NOT NULL DEFAULT '{}',                    -- per-table checkpoints
  started_at      timestamptz,
  completed_at    timestamptz,
  error           text,
  retry_count     smallint NOT NULL DEFAULT 0,
  next_attempt_at timestamptz
);

CREATE INDEX idx_anonymization_jobs_pending ON anonymization_jobs (status, next_attempt_at) WHERE status IN ('pending','partial','failed');
```

### 3.22 `bans`

```sql
CREATE TABLE bans (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  kind              text NOT NULL,                                -- 'permanent','temporary','content_only','login_only'
  reason            text NOT NULL,
  reason_category   text NOT NULL,                                -- 'spam','abuse','fraud','tos_violation','dmca','legal'
  evidence          jsonb,
  imposed_by        uuid REFERENCES users(id),
  imposed_at        timestamptz NOT NULL DEFAULT now(),
  expires_at        timestamptz,
  lifted_at         timestamptz,
  lifted_by         uuid REFERENCES users(id),
  appeal_state      text,                                         -- 'none','pending','denied','approved'
  CONSTRAINT bans_kind_chk CHECK (kind IN ('permanent','temporary','content_only','login_only'))
);

CREATE INDEX idx_bans_active ON bans (user_id) WHERE lifted_at IS NULL AND (expires_at IS NULL OR expires_at > now());
```

### 3.23 `shadowbans`

```sql
CREATE TABLE shadowbans (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  scope        text NOT NULL,                                     -- 'ugc','comments','reviews','all'
  reason       text NOT NULL,
  imposed_by   uuid REFERENCES users(id),
  imposed_at   timestamptz NOT NULL DEFAULT now(),
  lifted_at    timestamptz
);

CREATE INDEX idx_shadowbans_active ON shadowbans (user_id, scope) WHERE lifted_at IS NULL;
```

### 3.24 `trust_scores`

```sql
CREATE TABLE trust_scores (
  user_id         uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  score           integer NOT NULL DEFAULT 0,                     -- 0..1000
  level           smallint NOT NULL DEFAULT 0,                    -- 0=new, 1=verified, 2=contributor, 3=trusted, 4=expert
  components      jsonb NOT NULL DEFAULT '{}',                    -- {'tenure':50,'ugc_quality':120,...}
  auto_publish    boolean NOT NULL DEFAULT false,                 -- bypass pre-moderation
  computed_at     timestamptz NOT NULL DEFAULT now(),
  next_recompute_at timestamptz NOT NULL DEFAULT now() + interval '24 hours'
);
```

### 3.25 `reputation_events`

```sql
CREATE TABLE reputation_events (
  id            bigint GENERATED ALWAYS AS IDENTITY,
  user_id       uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  event_kind    text NOT NULL,                                    -- 'ugc.published','ugc.upvoted','ugc.flagged','translation.approved','ban','warning'
  delta         integer NOT NULL,                                 -- positive or negative
  reason        text,
  source_type   text,                                             -- 'system','user','moderator','ai'
  source_id     uuid,
  occurred_at   timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (occurred_at, id)
) PARTITION BY RANGE (occurred_at);

CREATE INDEX idx_reputation_events_user ON reputation_events (user_id, occurred_at DESC);
```

### 3.26 `moderation_actions`

```sql
CREATE TABLE moderation_actions (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  moderator_id    uuid NOT NULL REFERENCES users(id),
  target_type     text NOT NULL,                                  -- 'user','heritage','comment','media','review'
  target_id       text NOT NULL,
  action          text NOT NULL,                                  -- 'approve','reject','hide','restore','warn','ban','shadowban','escalate'
  reason          text,
  reason_category text,
  related_ban_id  uuid REFERENCES bans(id),
  related_shadowban_id uuid REFERENCES shadowbans(id),
  ai_assist_score real,                                           -- 0..1 if AI suggested the action
  taken_at        timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_moderation_actions_target ON moderation_actions (target_type, target_id, taken_at DESC);
CREATE INDEX idx_moderation_actions_mod    ON moderation_actions (moderator_id, taken_at DESC);
```

### 3.27 `mfa_methods`

```sql
CREATE TABLE mfa_methods (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  kind          text NOT NULL,                                    -- 'totp','sms','email_otp','webauthn','recovery'
  label         text,                                             -- 'Authy', 'iPhone 15'
  secret_encrypted bytea,                                         -- for TOTP — KMS-wrapped
  phone_id      uuid REFERENCES user_phones(id),
  email_id      uuid REFERENCES user_emails(id),
  is_primary    boolean NOT NULL DEFAULT false,
  verified_at   timestamptz,
  created_at    timestamptz NOT NULL DEFAULT now(),
  last_used_at  timestamptz,
  disabled_at   timestamptz,
  CONSTRAINT mfa_kind_chk CHECK (kind IN ('totp','sms','email_otp','webauthn','recovery'))
);

CREATE INDEX idx_mfa_methods_user ON mfa_methods (user_id) WHERE disabled_at IS NULL;
```

### 3.28 `webauthn_credentials`

```sql
CREATE TABLE webauthn_credentials (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  mfa_method_id     uuid REFERENCES mfa_methods(id) ON DELETE CASCADE,
  credential_id     bytea NOT NULL UNIQUE,                        -- raw credential ID from authenticator
  public_key_cose   bytea NOT NULL,                               -- COSE-encoded public key
  sign_count        bigint NOT NULL DEFAULT 0,
  aaguid            uuid,
  transports        text[],                                       -- 'usb','nfc','ble','internal','hybrid'
  attestation_format text,
  attestation_blob  bytea,
  backup_eligible   boolean NOT NULL DEFAULT false,
  backup_state      boolean NOT NULL DEFAULT false,
  device_label      text,
  created_at        timestamptz NOT NULL DEFAULT now(),
  last_used_at      timestamptz
);
```

### 3.29 `password_reset_tokens`

```sql
CREATE TABLE password_reset_tokens (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash    bytea NOT NULL UNIQUE,                            -- SHA-256
  email_id      uuid NOT NULL REFERENCES user_emails(id),
  issued_at     timestamptz NOT NULL DEFAULT now(),
  expires_at    timestamptz NOT NULL,
  used_at       timestamptz,
  ip_address    inet
);

CREATE INDEX idx_password_reset_tokens_user ON password_reset_tokens (user_id) WHERE used_at IS NULL;
```

### 3.30 `magic_link_tokens`

```sql
CREATE TABLE magic_link_tokens (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       uuid REFERENCES users(id) ON DELETE CASCADE,      -- may be NULL on first-time signup-by-magic-link
  email         citext NOT NULL,
  token_hash    bytea NOT NULL UNIQUE,
  intent        text NOT NULL,                                    -- 'login','signup','add_email'
  issued_at     timestamptz NOT NULL DEFAULT now(),
  expires_at    timestamptz NOT NULL,                             -- typically 15 min
  used_at       timestamptz,
  ip_address    inet,
  user_agent    text
);
```

### 3.31 `email_verifications`

```sql
CREATE TABLE email_verifications (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email_id      uuid NOT NULL REFERENCES user_emails(id) ON DELETE CASCADE,
  token_hash    bytea NOT NULL UNIQUE,
  issued_at     timestamptz NOT NULL DEFAULT now(),
  expires_at    timestamptz NOT NULL,
  verified_at   timestamptz,
  attempt_count smallint NOT NULL DEFAULT 0
);
```

### 3.32 `phone_verifications`

```sql
CREATE TABLE phone_verifications (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  phone_id      uuid NOT NULL REFERENCES user_phones(id) ON DELETE CASCADE,
  otp_hash      bytea NOT NULL,                                   -- HMAC of 6-digit OTP
  issued_at     timestamptz NOT NULL DEFAULT now(),
  expires_at    timestamptz NOT NULL,                             -- 5 min
  verified_at   timestamptz,
  attempt_count smallint NOT NULL DEFAULT 0,
  channel       text NOT NULL DEFAULT 'sms'                       -- 'sms','call','whatsapp'
);

CREATE INDEX idx_phone_verifications_phone ON phone_verifications (phone_id) WHERE verified_at IS NULL;
```

### 3.33 `login_attempts` (partitioned)

```sql
CREATE TABLE login_attempts (
  id              bigint GENERATED ALWAYS AS IDENTITY,
  occurred_at     timestamptz NOT NULL DEFAULT now(),
  email           citext,                                         -- attempted email (may not exist)
  user_id         uuid,                                           -- resolved if email matched a user
  identity_id     uuid,
  ip_address      inet NOT NULL,
  ip_country      char(2),
  ip_asn          integer,
  user_agent      text,
  device_id       uuid,
  outcome         text NOT NULL,                                  -- 'success','wrong_password','no_user','locked','mfa_required','mfa_failed','blocked'
  failure_reason  text,
  fraud_score     smallint,
  PRIMARY KEY (occurred_at, id)
) PARTITION BY RANGE (occurred_at);

CREATE INDEX idx_login_attempts_email_recent ON login_attempts (email, occurred_at DESC);
CREATE INDEX idx_login_attempts_ip_recent    ON login_attempts (ip_address, occurred_at DESC);
```

Weekly partitions. 90-day retention.

### 3.34 `account_recovery_codes`

```sql
CREATE TABLE account_recovery_codes (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  code_hash     bytea NOT NULL UNIQUE,                            -- bcrypt
  issued_at     timestamptz NOT NULL DEFAULT now(),
  used_at       timestamptz,
  batch_id      uuid NOT NULL                                     -- 10 codes issued together
);

CREATE INDEX idx_account_recovery_codes_user ON account_recovery_codes (user_id) WHERE used_at IS NULL;
```

### 3.35 `api_personal_tokens`

```sql
CREATE TABLE api_personal_tokens (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name            text NOT NULL,
  token_prefix    text NOT NULL,                                  -- first 8 chars, displayable
  token_hash      bytea NOT NULL UNIQUE,
  scopes          text[] NOT NULL DEFAULT '{}',                   -- subset of permission slugs
  issued_at       timestamptz NOT NULL DEFAULT now(),
  expires_at      timestamptz,
  last_used_at    timestamptz,
  last_used_ip    inet,
  revoked_at      timestamptz,
  revoked_reason  text
);

CREATE INDEX idx_api_personal_tokens_user ON api_personal_tokens (user_id) WHERE revoked_at IS NULL;
```

---

## 4. RBAC / ABAC Model

### 4.1 Roles (system-seeded, hierarchical)

```
guest
 └── user
      └── contributor
           └── trusted_contributor
                └── moderator
                     ├── regional_admin    (scoped: region=X)
                     └── content_admin
                          └── admin
                               └── superadmin
```

Inheritance is materialized at evaluation time, not stored. A user's effective permissions = union of permissions of all assigned roles + all ancestor roles.

### 4.2 Permission catalog (seeded examples)

| Slug | Description | Dangerous |
|---|---|---|
| `heritage:read` | View heritage data | no |
| `heritage:create` | Create heritage record | no |
| `heritage:update` | Edit heritage record | no |
| `heritage:delete` | Soft-delete heritage | yes |
| `heritage:moderate` | Approve/reject UGC heritage | no |
| `heritage:publish` | Bypass moderation queue | no |
| `media:upload` | Upload media | no |
| `media:moderate` | Moderate media | no |
| `comment:create` | Post comments | no |
| `comment:moderate` | Hide/restore comments | no |
| `user:read` | Read user profile (admin) | no |
| `user:ban` | Ban user | yes |
| `user:impersonate` | Login as another user | yes |
| `user:role_assign` | Assign roles | yes |
| `billing:read` | Read billing data | no |
| `billing:refund` | Issue refund | yes |
| `billing:configure` | Change prices/plans | yes |
| `admin:settings` | Modify system settings | yes |
| `admin:legal_publish` | Publish new ToS/Privacy version | yes |
| `audit:read` | Read audit log | no |
| `gdpr:approve` | Approve GDPR requests | yes |
| `ai:configure` | Change AI model selection | yes |

### 4.3 Scoped permissions

A `user_roles` row of `(user_id=U, role_id=moderator, scope_type=region, scope_value=uz)` grants moderator powers **only** when the target resource has `country_code='UZ'`. The evaluator combines:

1. Subject: `user.id`, `user.roles` (with scopes), `user.trust_level`, `user.residency_region`.
2. Resource: `resource.owner_id`, `resource.country_code`, `resource.published_at`, `resource.is_premium`.
3. Environment: `now()`, `request.ip_country`, `session.acr_level`.

### 4.4 Evaluation order

```
1. Hard deny (active ban?)                    → DENY
2. Step-up required & ACR < required?         → CHALLENGE
3. Collect effective permissions (RBAC)       → set P
4. Required permission ∈ P?                   → continue, else DENY
5. Evaluate attribute_policies in priority    → deny wins, allow continues
6. Final ALLOW
```

### 4.5 Dynamic role assignment

Two assignment paths:

- **Manual**: admin UI → `user_roles` insert → audit log row.
- **Automatic** (trust-driven): when a user's `trust_scores.level` crosses a threshold, a trigger inserts the corresponding role with `granted_by=NULL, reason='auto:trust_level_3'`. Reversible.

### 4.6 Caching

Effective permissions per user are cached in Redis: `perms:{user_id}:{session_id}` with TTL = 5 minutes or invalidated on `user_roles` change via `pg_notify`. ABAC results are **not** cached — resource attributes change.

---

## 5. Consent & Legal Versioning

### 5.1 Document lifecycle

1. Legal team drafts `legal_documents` row, `effective_from` in future.
2. `admin:legal_publish` action publishes.
3. On publish: if `requires_reconsent=true`, every active user's `consent_records` for affected purposes are flagged stale (no row update — new state derived from `legal_documents.effective_from > consent_records.granted_at`).
4. On next login, app prompts re-consent. Until granted, user is in **restricted mode**: read-only, no UGC, no analytics events sent.

### 5.2 Per-jurisdiction bundles

A user lands in jurisdiction via residency. The "active legal bundle" for user U is:

```sql
SELECT * FROM legal_documents
WHERE jurisdiction = u.residency_region
  AND locale       = u.primary_locale
  AND effective_from <= now()
  AND (effective_until IS NULL OR effective_until > now());
```

Fallback chain: `(uz, uz)` → `(uz, en)` → `(global, en)`.

### 5.3 Purposes (seeded)

- `account` (contract basis, cannot be withdrawn while account exists)
- `analytics_essential` (legitimate interest)
- `analytics_optional`
- `marketing_email`
- `marketing_push`
- `personalization`
- `ugc_publishing`
- `third_party_share_booking`
- `third_party_share_payment`

### 5.4 Withdrawal cascade

Withdrawing `analytics_optional` triggers: insert into `consent_records` (granted=false), purge Mixpanel/Firebase pipeline for user (downstream Agent 7 contract), invalidate Redis user-segments cache.

---

## 6. GDPR Workflows

### 6.1 Export

```
T+0    User submits export request → gdpr_requests row, status='received'
T+0    Verification email/SMS sent → status='verifying'
T+v    User clicks link → verified_at set → status='processing'
T+v..  Worker walks pii-tagged columns, produces ZIP:
       /profile.json
       /identities.json
       /sessions.json
       /consent.json
       /ugc/heritage_<id>.json
       /ugc/media/<files>
       /reputation/events.json
       /audit/your_actions.json
       /legal/documents_at_time_of_consent/*.html
T+v+24h Signed URL emailed, export_artifact_url set, export_expires_at = now()+7d
```

### 6.2 Deletion

```
T+0   Request received  → status='received'
T+v   Verified           → status='in_grace', grace_until = now()+30d
                          User can cancel from any device until grace_until
T+30d Job scheduled      → status='processing', anonymization_jobs row created
      Per-table plan executed:
        users                  → anonymize (keep id, zero PII, set anonymized_at)
        user_profiles          → hard_delete
        user_identities        → hard_delete
        user_emails            → hard_delete
        user_phones            → hard_delete
        sessions               → hard_delete
        refresh_tokens         → hard_delete (already cascaded)
        device_fingerprints    → user_id → NULL, fingerprint kept for fraud
        consent_records        → KEEP (legal evidence, anonymize ip)
        gdpr_requests          → KEEP (legal evidence)
        audit_log              → KEEP (anonymize actor_user_id to special tombstone uuid)
        reputation_events      → anonymize user_id
        trust_scores           → hard_delete
        bans                   → KEEP (legal/safety), anonymize PII fields
        moderation_actions     → KEEP
        UGC (heritage, comments, media — Agent 3/4 domain)
                               → per content policy: anonymize author_id or hard delete
        legal hold ?           → if true, postpone, notify user
T+30d+ Completion         → anonymized_at set, hard_delete_after = now()+90d
T+120d Hard delete users row → if no legal hold
```

### 6.3 Orchestration

`anonymization_jobs.step_state` looks like:

```json
{
  "tables": {
    "user_profiles": {"status":"done","at":"2026-06-19T10:01:00Z"},
    "user_emails":   {"status":"done","at":"2026-06-19T10:01:02Z"},
    "media":         {"status":"in_progress","cursor":"<uuid>","retries":0}
  }
}
```

A scheduled Celery worker resumes from cursor. Idempotent: every step is `UPDATE ... WHERE not_yet_done`.

### 6.4 Legal hold

If `gdpr_requests.legal_hold=true` (set by `admin:legal_hold_set`), deletion is paused indefinitely. Recorded reason mandatory. User is informed.

---

## 7. Audit Log Strategy

### 7.1 What gets logged

Every state-changing action. Sample taxonomy:

```
auth.*               login.success, login.failure, logout, mfa.challenge, mfa.success,
                     refresh.rotate, refresh.reuse_detected, password.change, oauth.link
user.*               create, update, delete, anonymize, ban, unban, role.assign, role.revoke
session.*            create, revoke, revoke_all
consent.*            granted, withdrawn, reconsent.required
gdpr.*               export.requested, export.completed, delete.requested, delete.grace_started,
                     delete.cancelled, delete.completed, legal_hold.set, legal_hold.cleared
heritage.*           create, update, publish, unpublish, moderate
admin.*              setting.change, ai_model.switch, legal_doc.publish, impersonate.start, impersonate.end
security.*           rate_limit.tripped, fraud.flagged, csrf.violation
```

### 7.2 Append-only enforcement

- Application connects with `app_role` having `INSERT, SELECT` only on audit tables.
- Migrations connect with `migrator_role` separately.
- Even superadmin role in admin panel cannot `UPDATE/DELETE` audit rows; revocation is column-level reinforced.
- Postgres `event_trigger` on `sql_drop` blocks dropping audit partitions older than retention without an `audit_archive_role`.

### 7.3 Tamper evidence

- Per-row: `row_hash = HMAC(secret, prev_hash || canonical(row))`.
- HMAC secret stored in HSM/KMS, rotated yearly; old secrets retained for verification.
- Daily anchor job: compute Merkle root of all events that day → `audit_anchors` row → publish to (a) S3 with Object Lock 7-year retention, (b) public Git repo via signed commit, (c) optionally OpenTimestamps.
- Verifier tool reconstructs the chain on demand.

### 7.4 Partitioning & retention

- Monthly partitions, auto-managed via `pg_partman`.
- Hot: last 3 months on SSD.
- Warm: months 4–12 on cheaper storage tier.
- Cold: > 12 months exported to Parquet on MinIO, partitions dropped from PG **after** anchor verification.
- Authentication/security events: 24 months hot+warm. Business events: 12 months.

### 7.5 Separation of duties

Three Postgres roles for audit:

- `app_role` — INSERT, SELECT.
- `audit_reader_role` — SELECT only (assigned to security analysts).
- `audit_archive_role` — DROP PARTITION (assigned to scheduled job service account).

---

## 8. Session Architecture

### 8.1 Tokens

- **Access JWT** — RS256-signed, 15-minute lifetime, payload: `{sub, jti, sid, acr, amr, roles_hash, perms_hash, residency, exp, iat}`. `roles_hash` and `perms_hash` let the gateway short-circuit on revocation cache.
- **Refresh token** — opaque, random 256-bit, hashed in DB, 30-day default lifetime, single-use rotating.
- **Step-up token** — short-lived elevated ACR JWT minted after re-auth for dangerous actions, 5-minute lifetime, never refreshable.

### 8.2 Revocation paths

1. **User-initiated logout** — revoke session + its refresh family.
2. **Logout all devices** — revoke all sessions for user.
3. **Password change** — revoke all sessions except current.
4. **Admin force-logout** — revoke selected session.
5. **Refresh-reuse detection** — revoke entire family + session + write critical audit.
6. **Account ban** — revoke all sessions immediately.
7. **Compromise broadcast** — `revocation_bitmap` in Redis keyed by JTI prefix, gateway checks per request.

### 8.3 Concurrent session limits

| Tier | Max sessions | Behavior on exceed |
|---|---|---|
| Free | 3 | Oldest revoked |
| Premium | 10 | Oldest revoked |
| Family | 25 | Oldest revoked |
| Admin | 5 | New session rejected (must explicitly revoke) |

Configurable via admin panel (`admin:settings`).

### 8.4 Device-based listing

`/me/sessions` returns enriched session list with `device_fingerprints` join, showing OS, last activity, current location (approx by IP), trust flag.

### 8.5 Step-up auth

A `permissions.is_dangerous=true` permission requires `session.acr_level ≥ 2`. If not, API returns `401 reauth_required` with `WWW-Authenticate: Step-up`. Client triggers MFA prompt, mints elevated session, retries.

---

## 9. Trust & Reputation

### 9.1 Trust components (admin-tunable weights)

```
trust_score = w1 * tenure_days_log
            + w2 * verified_identities_count
            + w3 * ugc_quality_score
            + w4 * positive_reputation_events
            - w5 * negative_reputation_events
            - w6 * recent_violations
            + w7 * peer_endorsements
            + w8 * b2b_partner_attestation
```

Stored in `trust_scores.components` as JSON for explainability.

### 9.2 Level thresholds (defaults, admin-overridable)

| Level | Score | Privileges |
|---|---|---|
| 0 New | 0–49 | Read + comment only, pre-moderation everything |
| 1 Verified | 50–199 | Submit UGC, pre-moderation |
| 2 Contributor | 200–499 | Submit UGC, post-moderation |
| 3 Trusted | 500–899 | Auto-publish, suggest edits |
| 4 Expert | 900+ | Auto-publish + flagging power |

### 9.3 Auto-publish integration

Heritage/Media moderation pipelines (Agent 3/4) check `trust_scores.auto_publish`. If true, content goes live immediately; AI moderation still runs asynchronously and may yank.

### 9.4 Recomputation

Nightly Celery job recomputes `trust_scores` from event stream; immediate recompute trigger on `reputation_events` with `|delta| ≥ 50`.

---

## 10. Threat Model

| Threat | Vector | Mitigation |
|---|---|---|
| Credential stuffing | Bot login with leaked password lists | Rate limit per email+IP+ASN via `login_attempts`; HIBP-style breached-password check on registration; mandatory captcha after N failures |
| Account takeover via OAuth email-claim collision | Attacker registers email at provider X then "links" to victim's account | Never trust unverified provider email for merge; require verified `user_emails` on both sides; explicit user confirmation on identity link |
| Mass guest creation for scraping | Endless `POST /auth/guest` | IP + device fingerprint rate limit; proof-of-work challenge after threshold; require fingerprint stability before content access |
| Privileged mod compromise → mass deletion | Stolen mod cookie | Step-up MFA on `is_dangerous` permissions; rate-limit destructive ops; audit anomaly detection (mod deleting 100 items/hour pages on-call) |
| Audit log tampering by DBA | Direct SQL `UPDATE audit_log` | DB role separation, daily anchored Merkle roots published externally, verifier alerts on mismatch |
| GDPR delete-bombing as DoS | User submits delete, cancels, resubmits to lock account | `idx_gdpr_one_open_per_user` unique partial; cancellation count limit; cooldown on re-request |
| Refresh token theft | XSS or device compromise | Family rotation reuse detection; httpOnly cookies on web; bound to device fingerprint hash for mobile |
| Telegram-widget spoofing | Forged HMAC | Verify `hash` per Telegram spec using bot token; only-recent timestamps; rate-limit per `tg_user_id` |
| Phone number recycling | Old number reassigned to new person | Re-verification on suspicious geo change; SMS pumping detection via carrier+ASN; flag and require email verification on next login |
| MFA bypass via recovery codes | Phishing → use all codes | Account-recovery-code use triggers email alert + step-up; codes invalidated when MFA changes |
| Mass scraping via personal API tokens | Token leak | Per-token rate limits stored in token row; auto-revoke on anomaly; prefix-only display, full token shown once |

---

## 11. Cross-jurisdictional Data Residency

### 11.1 Mechanism

`users.residency_region` is set at first verified login (from country of verified phone, billing address, or explicit selection) and **immutable** thereafter without a manual support-mediated migration (which itself produces audit + GDPR-style export-then-import flow).

Partitioning on `users` (LIST by residency) extends to all PII-heavy child tables that we want to physically separate, achieved by **same-key partitioning**:

- `user_profiles`, `user_identities`, `user_emails`, `user_phones`, `consent_records`, `sessions`, `device_fingerprints` each carry a denormalized `residency_region` column (kept in sync by trigger) and are LIST-partitioned identically.
- Each residency partition lives in its own **tablespace** mapped to physically isolated disks: `ts_uz` → Uzbekistan-hosted disks; `ts_eu` → Frankfurt region; `ts_us` → US-East; `ts_global` → primary cluster.

### 11.2 Replication policy

- `ts_uz` replicates **only** to Uzbek standby nodes.
- `ts_eu` replicates only within EU.
- Backups encrypted with region-specific KMS keys.
- Cross-region read joins go through an aggregation layer that materializes redacted views, never raw PII.

### 11.3 Access policy

RLS policy on every PII-bearing table:

```sql
CREATE POLICY pii_residency_isolation ON user_emails
  FOR ALL TO app_role
  USING (
    residency_region = current_setting('app.connection_residency', true)
    OR current_setting('app.cross_region_allowed', true) = 'true'
  );
```

The connection's `app.connection_residency` is set by the connection pooler based on which physical PG instance the pool is bound to.

### 11.4 Migration on residency change

1. User requests change → admin ticket.
2. Verification (proof of new residency).
3. Export bundle from old region → encrypted transfer → import into new region partition.
4. Old rows hard-deleted post-verification.
5. Audit row in both regions.

---

## 12. Risks & Open Questions

1. **HMAC-key custody for audit log.** Whoever holds the HMAC secret can forge history. Mitigated by external anchors, but we need a procedural answer for key rotation that does not break verification of old chains. *Open: HSM vendor choice, or use Cloud KMS with envelope encryption.*

2. **Uzbekistan PD law specifics.** The 2019 law evolves; some interpretations require PII *processing* (not just storage) to occur on Uzbek soil. If true, AI inference on user-derived data must run on the UZ GPU server, which conflicts with global model routing decisions. *Open: legal opinion required before launch.*

3. **Telegram identity quality.** Telegram OAuth widget does not provide a verified email. Users who only use Telegram have no recovery channel except phone. *Open: enforce a recovery email/phone after first Telegram login, or accept lockout risk?*

4. **Cross-region UGC ownership.** If a UZ-resident user uploads UGC about an EU heritage site, where does the UGC live? Currently planned: content in `ts_global`, author link in user's residency. Joins span regions. *Open: validate this is acceptable to UZ PD law for "data about Uzbek citizens".*

5. **Guest-account abuse vs. Project-Decisions §11 (max UGC openness).** The product wants maximum UGC freedom, but guests are the obvious vector for spam. We propose guests have read + view-only UGC privileges, with UGC creation requiring a verified identity. *Open: confirm with product owner.*

6. **Identity merge UX risk.** If we merge two users (e.g. user accidentally registers twice — once with Google, once with email), losing audit history on the dropped `users.id` is unacceptable. *Open: design `users.merged_into` redirect column and a `user_merges` audit table; or refuse merge and force one account to be deleted.*

7. **Apple "Hide My Email" private relay.** Apple issues per-app relay emails that change if the user revokes. We must treat the Apple `sub` (not email) as the merge key, but then we lose the human-readable contact. *Open: encourage adding a non-relay email post-signup; document UX flow.*

8. **GDPR export bundle size for power users.** A trusted contributor with 10k UGC items + media may produce multi-GB exports. *Open: streaming ZIP generation, chunked downloads, S3 multipart.*

---

## Cross-agent Contracts

This domain exposes the following stable contracts to the other 7 agents:

- **Every other domain's tables MUST include** `created_by uuid REFERENCES users(id)` and (where applicable) `updated_by uuid REFERENCES users(id)`. Soft-deletable tables MUST include `deleted_by uuid REFERENCES users(id)`. Cascade rule: `ON DELETE SET NULL` (we never want a user delete to nuke business data — the GDPR job decides per-table policy).

- **Audit log insertion** is via a single SQL function `app.audit(kind text, target_type text, target_id text, diff jsonb, metadata jsonb)` callable by `app_role`. All agents MUST log through this function so the HMAC chain is maintained.

- **Permission checks** are exposed via `app.has_permission(user_id uuid, perm_slug text, resource jsonb)` SQL function and `/internal/authz/check` HTTP endpoint. All other services MUST authorize through one of these; no service may implement its own RBAC.

- **Residency setting** for connections is `app.connection_residency`. Agent 7 (Infra) MUST configure connection poolers to set this per pool.

- **User events** published to Redis stream `events:identity` with kinds: `user.created`, `user.merged`, `user.banned`, `user.anonymized`, `user.role_changed`, `consent.changed`. Other agents subscribe.

---

*Document version: 1.0 — 2026-05-18 — Agent 2 (User & Identity Architect)*
