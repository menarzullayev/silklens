# SilkLens API Endpoints Reference

Generated from: `/home/nsn/Workspace/silklens/services/api/src/api/routers/`
Base prefix for all versioned routes: `/v1`

---

## Meta / Health

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | None | Liveness probe — returns service name, env, version |
| GET | `/ready` | None | Readiness probe — checks DB connectivity |
| GET | `/version` | None | Returns current service version string |

**`GET /health` Response:**
```json
{ "status": "ok", "service": "silklens-api", "env": "production", "version": "1.0.0" }
```

---

## Public — Branding & Vocabularies

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/v1/branding` | None | Resolve tenant branding (logo, colors, theme) by host header or `?tenant=slug` |
| GET | `/v1/vocab/{vocab_slug}` | None | Fetch controlled vocabulary terms (hierarchical or flat) |

**`GET /v1/branding` Query Params:** `?tenant=<slug>` (optional; falls back to host header, then platform default)

**`GET /v1/branding` Response:**
```json
{
  "tenant_slug": "silklens",
  "app_name": {"en": "SilkLens"},
  "logo_url": "https://...",
  "logo_dark_url": "https://...",
  "primary_color": "#FF6B35",
  "accent_color": "#004E89",
  "splash_url": "https://...",
  "font_family": "Noto Sans",
  "theme_mode_default": "system",
  "extra": {}
}
```

**`GET /v1/vocab/{vocab_slug}` Response:**
```json
{
  "vocabulary_slug": "heritage_kinds",
  "is_hierarchical": true,
  "items": [
    { "slug": "mosque", "display_name": {"en": "Mosque"}, "parent_slug": null, "sort_order": 1 }
  ]
}
```

---

## Authentication

| Method | Path | Auth | Rate Limit | Description |
|--------|------|------|-----------|-------------|
| POST | `/v1/auth/register` | None | 3/min/IP | Register new user; returns JWT pair + user info |
| POST | `/v1/auth/login` | None | 5/min/IP | Password login; returns JWT pair (MFA challenge if enrolled) |
| POST | `/v1/auth/refresh` | None | 20/min/IP | Exchange refresh token for new JWT pair |
| GET | `/v1/auth/me` | Bearer | — | Return current user + session info |
| POST | `/v1/auth/google` | None | 10/min/IP | Google ID token sign-in (stub, returns 501 until configured) |
| POST | `/v1/auth/logout` | Bearer | — | Revoke current session and refresh-token family |

**`POST /v1/auth/register` Request:**
```json
{
  "email": "user@example.com",
  "password": "min12chars",
  "display_name": "Ali Karimov",
  "preferred_locale": "uz",
  "preferred_timezone": "Asia/Tashkent",
  "tenant_id": null,
  "residency_region": "global"
}
```

**`POST /v1/auth/login` Response (no MFA):**
```json
{
  "user": { "id": "...", "pub_id": "usr_...", "trust_tier": "standard", "is_verified": false },
  "tokens": { "access_token": "eyJ...", "refresh_token": "...", "token_type": "Bearer", "expires_in": 900 }
}
```

**`POST /v1/auth/login` Response (MFA enrolled — HTTP 403):**
```json
{
  "code": "identity.mfa_required",
  "challenge_id": "uuid",
  "available_methods": ["totp"]
}
```

---

## MFA (Multi-Factor Authentication)

| Method | Path | Auth | Rate Limit | Description |
|--------|------|------|-----------|-------------|
| GET | `/v1/me/mfa` | Bearer | — | List enrolled MFA methods |
| POST | `/v1/me/mfa/totp/enroll` | Bearer | — | Begin TOTP enrollment; returns provisioning URI |
| POST | `/v1/me/mfa/totp/verify-enrollment` | Bearer | — | Confirm TOTP with first code to activate |
| POST | `/v1/me/mfa/webauthn/begin-registration` | Bearer | — | Begin WebAuthn registration; returns challenge options |
| POST | `/v1/me/mfa/webauthn/finish-registration` | Bearer | — | Complete WebAuthn registration with attestation |
| POST | `/v1/me/mfa/backup-codes/generate` | Bearer + recent MFA | — | Regenerate backup codes (replaces previous set) |
| DELETE | `/v1/me/mfa/{mfa_id}` | Bearer + recent MFA | — | Disable an MFA method |
| POST | `/v1/auth/mfa/challenge` | None | 5/min/IP | Initiate MFA challenge post-password (step-up) |
| POST | `/v1/auth/mfa/verify` | None | 5/min/IP | Verify challenge code; returns elevated access token |

**`POST /v1/me/mfa/totp/enroll` Request:** `{ "label": "My Authenticator" }`

**`POST /v1/me/mfa/totp/enroll` Response:**
```json
{
  "mfa_id": "uuid",
  "secret_base32": "JBSWY3DPEHPK3PXP",
  "provisioning_uri": "otpauth://totp/...",
  "digits": 6,
  "period": 30,
  "algorithm": "sha1"
}
```

**`POST /v1/auth/mfa/verify` Request:**
```json
{ "challenge_id": "uuid", "method": "totp", "code": "123456" }
```

**`POST /v1/auth/mfa/verify` Response:**
```json
{ "access_token": "eyJ...", "token_type": "Bearer", "mfa": true }
```

---

## Heritage Objects

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/v1/heritage` | None | List + filter + paginate heritage objects (public) |
| GET | `/v1/heritage/{pub_id}` | None | Fetch single heritage object (public); increments view counter |
| POST | `/v1/heritage` | `heritage:create` | Create new heritage object |
| PATCH | `/v1/heritage/{pub_id}` | `heritage:update` | Partial update (status field requires `heritage:moderate`) |
| DELETE | `/v1/heritage/{pub_id}` | `heritage:delete` | Soft delete |
| POST | `/v1/heritage/{pub_id}/aliases` | `heritage:update` | Add multilingual alias |
| GET | `/v1/heritage/{pub_id}/revisions` | `heritage:read` | Paginated revision history |
| POST | `/v1/heritage/{pub_id}/transitions` | dynamic | Moderation state machine (submit/approve/reject/archive) |

**`GET /v1/heritage` Query Params:**
- `kind=mosque`, `country=UZ`, `status=published`, `search=Samarkand`
- `limit` (1–100, default 20), `offset` (default 0)

**`POST /v1/heritage` Request:**
```json
{
  "kind_slug": "mosque",
  "name": {"en": "Bibi-Khanym Mosque", "uz": "Bibi-Xonim masjidi"},
  "summary_md": {"en": "14th century Timurid mosque..."},
  "tags": ["timurid", "silk-road", "unesco"],
  "country_code": "UZ",
  "latitude": 39.6557,
  "longitude": 66.9758,
  "period_start_year": 1399,
  "period_end_year": 1404,
  "unesco_inscription_year": 2001
}
```

**`POST /v1/heritage/{pub_id}/transitions` Request:**
```json
{ "action": "submit_for_review", "comment": "Ready for moderation" }
```
Actions: `submit_for_review`, `approve`, `reject`, `archive`, `restore`

---

## AI

| Method | Path | Auth | Rate Limit | Description |
|--------|------|------|-----------|-------------|
| POST | `/v1/ai/recognize` | Bearer | 10/min/user | Vision recognition on a media asset |
| POST | `/v1/ai/chat` | Bearer | 30/min/user | LLM chat with optional system prompt |
| POST | `/v1/ai/translate` | Optional | 60/min/user | Text translation with TM cache |
| POST | `/v1/ai/tts` | Bearer | 10/min/user | Text-to-speech; persists audio to media_assets |
| POST | `/v1/ai/search` | Optional | — | pgvector semantic search (public) |
| GET | `/v1/ai/models` | `ai:configure` | — | List AI model registry |
| GET | `/v1/ai/fallback-chains` | `ai:configure` | — | List fallback chains + steps |
| PATCH | `/v1/ai/models/{slug}` | `ai:configure` | — | Toggle model enabled / update sort order |

**`POST /v1/ai/recognize` Request:**
```json
{ "media_asset_id": "uuid", "language": "uz" }
```

**`POST /v1/ai/chat` Request:**
```json
{
  "prompt": "Tell me about the Silk Road",
  "system": "You are a cultural heritage expert.",
  "conversation_id": null,
  "language": "en"
}
```

**`POST /v1/ai/translate` Request:**
```json
{ "text": "Hello World", "source_lang": "en", "target_lang": "uz" }
```

**`POST /v1/ai/search` Request:**
```json
{
  "query": "ancient mosques of Samarkand",
  "language": "en",
  "kind": "heritage_text",
  "filters": { "kind_slug": "mosque", "country_code": "UZ" },
  "limit": 10
}
```

---

## Media

| Method | Path | Auth | Rate Limit | Description |
|--------|------|------|-----------|-------------|
| POST | `/v1/media/uploads` | Bearer | 20/min/user | Multipart upload; stored to MinIO |
| GET | `/v1/media/{asset_id}` | Bearer | — | Fetch asset metadata (tenant-scoped; moderators bypass) |
| GET | `/v1/media/{asset_id}/signed-url` | Bearer | — | Get presigned GET URL (owner or moderator) |
| DELETE | `/v1/media/{asset_id}` | Bearer | — | Soft delete (owner or moderator) |

**`POST /v1/media/uploads` Form Fields:**
- `file` (binary), `kind` (image/video/audio/document/model_3d, default: image), `license_type_slug` (default: cc_by_sa)

**`POST /v1/media/uploads` Response:**
```json
{
  "asset": {
    "id": "uuid", "kind": "image", "mime_type": "image/jpeg",
    "byte_size": 204800, "status": "active", "width": 1920, "height": 1080
  },
  "signed_get_url": "https://minio.../..."
}
```

---

## Search (Elasticsearch-backed)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/v1/search` | None | Full-text semantic search over heritage objects via Elasticsearch |

**`GET /v1/search` Query Params:**
- `q=Registan` (required, 1–256 chars)
- `lang=uz` (default: en)
- `country=UZ` (optional, 2-char ISO)
- `kind=mosque` (optional)
- `limit=20` (1–50)

**Response:**
```json
{
  "query": "Registan",
  "language_tag": "uz",
  "total": 3,
  "hits": [
    { "heritage_id": "uuid", "pub_id": "her_...", "name": "Registan Square", "score": 9.82, "kind_slug": "plaza", "country_code": "UZ" }
  ],
  "suggestions": []
}
```
Resilient: returns empty page if Elasticsearch is offline.

---

## Billing

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/v1/billing/plans` | None | List subscription plans + prices |
| POST | `/v1/billing/webhooks/{provider}` | None (sig verified) | Provider webhook ingress (stripe/payme/click/paypal/apple_iap/google_iap) |
| GET | `/v1/billing/me/subscription` | Bearer | Current subscription or null |
| POST | `/v1/billing/subscriptions` | Bearer | Start a subscription (requires `Idempotency-Key` header) |
| POST | `/v1/billing/subscriptions/cancel` | Bearer | Cancel subscription (default: at period end) |
| POST | `/v1/billing/subscriptions/resume` | Bearer | Undo cancel-at-period-end |
| GET | `/v1/billing/me/invoices` | Bearer | Paginated invoice list |
| GET | `/v1/billing/me/entitlements` | Bearer | Materialised feature entitlements |

**`GET /v1/billing/plans` Query Params:** `?pricing_zone=cis`

**`POST /v1/billing/subscriptions` Request:**
```json
{
  "plan_slug": "pro-monthly",
  "payment_method_token": "pm_...",
  "pricing_zone_slug": "cis"
}
```
Header: `Idempotency-Key: <unique-string>`

**`GET /v1/billing/me/entitlements` Response:**
```json
{
  "items": [
    { "feature_key": "ai.recognize.monthly_quota", "granted": true, "limit_value": 500, "source": "subscription" }
  ]
}
```

---

## Gamification

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/v1/me/xp` | Bearer | XP balance, level, progress to next level |
| GET | `/v1/me/badges` | Bearer | All earned badges with rarity + progress |
| GET | `/v1/me/streak` | Bearer | Daily streak info + freeze credits |
| POST | `/v1/me/streak/tick` | Bearer | Record daily activity to advance streak |
| GET | `/v1/leaderboards` | None | List all leaderboards (slug, period, metric) |
| GET | `/v1/leaderboards/{slug}` | None | Paginated leaderboard entries |

**`GET /v1/me/xp` Response:**
```json
{
  "current_xp": 4200,
  "lifetime_xp": 12300,
  "weekly_xp": 350,
  "monthly_xp": 1200,
  "level": { "number": 7, "slug": "explorer", "xp_required": 4000 },
  "next_level": { "number": 8, "slug": "curator", "xp_required": 5500 },
  "xp_to_next_level": 1300,
  "progress_pct": 13.33
}
```

**`GET /v1/leaderboards/{slug}` Query Params:** `?period=weekly&limit=20`

---

## Social

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/v1/social/follow/{pub_id}` | Bearer | Follow a user |
| DELETE | `/v1/social/follow/{pub_id}` | Bearer | Unfollow a user |
| GET | `/v1/social/followers/{pub_id}` | None | Paginated follower list |
| GET | `/v1/social/following/{pub_id}` | None | Paginated following list |
| POST | `/v1/social/friends/invite` | Bearer | Send friend invitation (returns raw token once) |
| POST | `/v1/social/friends/accept` | Bearer | Accept friend invitation by token |
| POST | `/v1/social/block/{pub_id}` | Bearer | Block a user |
| DELETE | `/v1/social/block/{pub_id}` | Bearer | Unblock a user |
| GET | `/v1/social/feed` | Bearer | Paginated activity feed (cursor-based, `?before=ISO8601`) |

**`POST /v1/social/friends/invite` Request:**
```json
{ "target_pub_id": "usr_abc123", "message": "Join me on SilkLens!" }
```
Note: token is returned only at creation time (masked `***` on subsequent reads per SEC-021).

---

## Notifications

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/v1/notifications` | Bearer | Inbox (cursor-based; `?unread_only=true&limit=20&before=...`) |
| POST | `/v1/notifications/{notification_id}/read` | Bearer | Mark single notification as read |
| POST | `/v1/notifications/mark-all-read` | Bearer | Mark all notifications as read |
| GET | `/v1/notifications/preferences` | Bearer | List channel preferences by category |
| PATCH | `/v1/notifications/preferences` | Bearer | Bulk update channel preferences |
| POST | `/v1/notifications/push-devices` | Bearer | Register push device (FCM/APNs token) |
| DELETE | `/v1/notifications/push-devices/{installation_id}` | Bearer | Unregister push device |
| PUT | `/v1/notifications/quiet-hours` | Bearer | Set quiet hours for push notifications |

**`PATCH /v1/notifications/preferences` Request:**
```json
[
  { "category_slug": "heritage_updates", "channel": "push", "enabled": true },
  { "category_slug": "social", "channel": "email", "enabled": false }
]
```

**`PUT /v1/notifications/quiet-hours` Request:**
```json
{ "timezone": "Asia/Tashkent", "start_time": "22:00", "end_time": "07:00", "weekdays": [0,1,2,3,4,5,6] }
```

---

## Reviews, Comments & Reports

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/v1/heritage/{pub_id}/reviews` | Bearer | Create a review for a heritage object |
| GET | `/v1/heritage/{pub_id}/reviews` | None | Paginated reviews (sort: recent/helpful) |
| PATCH | `/v1/reviews/{review_id}/helpful` | Bearer | Vote helpful (+1) or unhelpful (-1) |
| POST | `/v1/reviews/{review_id}/reactions` | Bearer | Add emoji reaction to a review |
| DELETE | `/v1/reviews/{review_id}/reactions/{reaction_slug}` | Bearer | Remove reaction |
| POST | `/v1/comments` | Bearer | Add threaded comment on a review or heritage |
| POST | `/v1/reports` | Bearer | Report content (review/comment/heritage) |

**`POST /v1/heritage/{pub_id}/reviews` Request:**
```json
{
  "body_md": "An extraordinary example of Timurid architecture...",
  "language_tag": "en",
  "title": "A must-visit UNESCO site",
  "visited_at": "2024-09-15",
  "ratings": [
    { "dimension_slug": "authenticity", "value": 10 },
    { "dimension_slug": "preservation", "value": 8 }
  ]
}
```

**`POST /v1/comments` Request:**
```json
{ "parent_kind": "review", "parent_id": "uuid", "body_md": "Agreed!", "language_tag": "en" }
```

**`POST /v1/reports` Request:**
```json
{ "target_kind": "review", "target_id": "uuid", "reason_slug": "spam", "details": "..." }
```

---

## Compliance & GDPR

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/v1/legal/{kind}` | None | Get current policy document (privacy_policy/terms_of_service/cookie_policy) |
| GET | `/v1/legal/{kind}/history` | `tenant:manage` | Policy version history |
| POST | `/v1/legal/{kind}` | `tenant:manage` | Publish a new policy version |
| GET | `/v1/me/consents` | Bearer | List user's consent records |
| POST | `/v1/me/consents` | Bearer | Record consent for a policy version |
| DELETE | `/v1/me/consents/{doc_id}` | Bearer | Withdraw consent |
| POST | `/v1/me/data-export` | Bearer | Schedule GDPR data export (async, 202) |
| GET | `/v1/me/data-export/{request_id}` | Bearer | Check export status / get download URL |
| POST | `/v1/me/account/delete` | Bearer + recent MFA | Schedule account deletion (+30d grace period) |
| POST | `/v1/me/account/delete/cancel` | Bearer | Cancel pending deletion within grace window |
| POST | `/v1/public/cookie-consent` | None | Record anonymous cookie banner choice |
| POST | `/v1/admin/gdpr-requests/{id}/process` | `gdpr:approve` + recent MFA | Admin: process a GDPR request |

**`GET /v1/legal/{kind}` Header:** `Accept-Language: uz` (determines language of returned content)

**`POST /v1/public/cookie-consent` Request:**
```json
{
  "session_cookie_id": "anon_sess_abc",
  "strictly_necessary": true,
  "analytics": true,
  "marketing": false,
  "ad_targeting": false,
  "region": "EU"
}
```

---

## AR (Augmented Reality)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/v1/ar/challenges` | None | List active AR challenges (filter: heritage, kind) |
| GET | `/v1/ar/challenges/{slug}` | None | Get single AR challenge detail |
| POST | `/v1/ar/challenges/{slug}/complete` | Bearer | Submit challenge answer; returns score + XP |
| GET | `/v1/ar/challenges/{slug}/hint` | Bearer | Get hint text for a challenge |
| POST | `/v1/ar/sessions` | Bearer | Start solo or group AR session |
| POST | `/v1/ar/sessions/{code}/join` | Bearer | Join group AR session by 6-char code |
| GET | `/v1/ar/overlays` | None | List active AR overlays for a heritage site |

**`POST /v1/ar/challenges/{slug}/complete` Request:**
```json
{
  "answer": { "selected": "1404" },
  "time_taken_seconds": 45,
  "hint_used": false,
  "photo_media_id": null
}
```

**`GET /v1/ar/overlays` Query Params:** `?heritage_pub_id=her_abc&date=2024-09-15`

---

## Virtual Tours

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/v1/virtual-tours` | None | Paginated list (filter: heritage, collection, kind) |
| GET | `/v1/virtual-tours/{slug}` | None | Full tour detail with scenes |
| POST | `/v1/virtual-tours` | `heritage:create` | Create a virtual tour |
| PATCH | `/v1/virtual-tours/{slug}` | `heritage:update` | Update tour metadata |
| POST | `/v1/virtual-tours/{slug}/publish` | `heritage:moderate` | Publish (state machine: draft → published) |
| GET | `/v1/virtual-tours/{slug}/embed` | None | Get embed code (published tours only) |
| POST | `/v1/virtual-tours/{slug}/progress` | Bearer | Record viewer scene progress |
| GET | `/v1/virtual-tour-collections` | None | List all tour collections |

**`POST /v1/virtual-tours` Request:**
```json
{
  "slug": "registan-360",
  "title": {"en": "Registan Square 360° Tour"},
  "kind": "panorama_360",
  "description_md": {"en": "An immersive walk through..."},
  "heritage_id": "uuid",
  "tour_duration_seconds": 1200
}
```

---

## Reseller / White-Label

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/v1/reseller/applications` | None (3/min/IP) | Submit reseller application |
| GET | `/v1/reseller/applications/{id}` | Optional | Get application (admin sees full data, applicant sees redacted) |
| GET | `/v1/admin/reseller/applications` | `reseller:read` | Admin list of all applications |
| POST | `/v1/admin/reseller/applications/{id}/approve` | `reseller:approve` | Approve; creates child tenant + revenue share |
| POST | `/v1/admin/reseller/applications/{id}/reject` | `reseller:approve` | Reject with reason |
| GET | `/v1/admin/tenants/{slug}/revenue-share` | `reseller:configure_revenue_share` | List revenue share rows |
| PUT | `/v1/admin/tenants/{slug}/revenue-share` | `reseller:configure_revenue_share` | Upsert revenue share percentage |
| GET | `/v1/me/tenant` | Bearer | Caller's tenant + parent chain |

---

## Admin

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/v1/admin/tenants` | `tenant:read` | Paginated tenant list |
| POST | `/v1/admin/tenants` | `tenant:create` | Create a new tenant |
| PATCH | `/v1/admin/tenants/{slug}` | `tenant:manage` | Update tenant status/plan/display_name |
| GET | `/v1/admin/tenants/{slug}/branding` | `tenant:branding` | Get tenant branding config |
| PUT | `/v1/admin/tenants/{slug}/branding` | `tenant:branding` | Upsert tenant branding |
| GET | `/v1/admin/system-settings` | `system:settings` | List system settings (secrets redacted) |
| PUT | `/v1/admin/system-settings` | `system:settings` | Upsert a system setting |
| GET | `/v1/admin/feature-flags` | `system:feature_flags` | List feature flags |
| PUT | `/v1/admin/feature-flags/{key}` | `system:feature_flags` | Upsert feature flag (boolean/percentage/allowlist) |
| GET | `/v1/admin/search/status` | `system:settings` | Search index stats |
| POST | `/v1/admin/search/rebuild` | `system:settings` | Trigger bulk Elasticsearch reindex |
| POST | `/v1/admin/ingestion/wikidata` | `tenant:manage` | Ingest heritage objects from Wikidata by country |
| POST | `/v1/admin/ingestion/wikidata/qid` | `tenant:manage` | Ingest single Wikidata QID |
| GET | `/v1/admin/ingestion/jobs` | `tenant:manage` | List background ingestion jobs |

**`POST /v1/admin/ingestion/wikidata` Request:**
```json
{ "country_code": "UZ", "limit": 100 }
```

**`PUT /v1/admin/feature-flags/{key}` Request:**
```json
{
  "enabled": true,
  "rollout_kind": "percentage",
  "rollout_value": { "percentage": 10 },
  "description": "Gradual AR rollout"
}
```

---

## Fine-Tuning Admin

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/v1/admin/finetuning/datasets` | `ai:configure` | List fine-tuning datasets |
| GET | `/v1/admin/finetuning/datasets/{slug}` | `ai:configure` | Dataset detail + stats |
| GET | `/v1/admin/finetuning/datasets/{slug}/export` | `ai:configure` | Download dataset as JSONL |
| POST | `/v1/admin/finetuning/datasets/{slug}/examples` | `ai:configure` | Add manual training example |
| GET | `/v1/admin/finetuning/datasets/{slug}/examples/pending` | `ai:configure` | Pending example approval queue |
| POST | `/v1/admin/finetuning/examples/{id}/approve` | `ai:configure` | Approve a training example |
| POST | `/v1/admin/finetuning/jobs` | `ai:configure` | Scaffold a fine-tuning training job |
| GET | `/v1/admin/finetuning/jobs/{id}` | `ai:configure` | Training job status |

---

## Fundraising

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/v1/fundraising/campaigns` | None | List active fundraising campaigns |
| GET | `/v1/fundraising/campaigns/{slug}` | None | Campaign detail + progress |
| POST | `/v1/fundraising/campaigns` | `fundraising:manage` | Create campaign |
| PATCH | `/v1/fundraising/campaigns/{slug}` | `fundraising:manage` | Update campaign |
| POST | `/v1/fundraising/campaigns/{slug}/donate` | Bearer | Make a donation |
| GET | `/v1/fundraising/campaigns/{slug}/donors` | None | Public donor leaderboard |
| GET | `/v1/me/donations` | Bearer | My donation history |

---

## Partnerships

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/v1/partnerships/programs` | None | List partnership programs |
| POST | `/v1/partnerships/applications` | None | Submit partnership application |
| GET | `/v1/partnerships/applications/{id}` | Bearer | Track application status |
| GET | `/v1/admin/partnerships/applications` | `partnership:manage` | Admin view all applications |
| POST | `/v1/admin/partnerships/applications/{id}/approve` | `partnership:manage` | Approve application |
| POST | `/v1/admin/partnerships/applications/{id}/reject` | `partnership:manage` | Reject application |

---

## Enterprise SLA

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/v1/admin/enterprise/sla-tiers` | `enterprise:manage` | List SLA tier definitions |
| GET | `/v1/me/enterprise/sla` | Bearer | Current tenant SLA status + uptime metrics |
| POST | `/v1/admin/enterprise/sla-incidents` | `enterprise:manage` | Log SLA incident |
| GET | `/v1/admin/enterprise/sla-incidents` | `enterprise:manage` | List SLA incidents |

---

## AI Models Admin

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/v1/ai/models` | `ai:configure` | List all AI models (slug, provider, task_type, enabled) |
| GET | `/v1/ai/fallback-chains` | `ai:configure` | List fallback chains with ordered steps (single JOIN query) |
| PATCH | `/v1/ai/models/{slug}` | `ai:configure` | Toggle is_enabled or update sort_order |

---

## Summary

| Category | Router File | Endpoint Count |
|----------|------------|---------------|
| Meta/Health | health.py + public_meta.py | 5 |
| Auth | auth.py | 6 |
| MFA | mfa.py | 9 |
| Heritage | heritage.py | 8 |
| AI | ai.py | 8 |
| Media | media.py | 4 |
| Search | search.py | 1 |
| Billing | billing.py | 8 |
| Gamification | gamification.py | 6 |
| Social | social.py | 9 |
| Notifications | notifications.py | 8 |
| Reviews/Comments/Reports | reviews.py | 7 |
| Compliance/GDPR | compliance.py | 12 |
| AR | ar.py | 7 |
| Virtual Tours | virtual_tours.py | 8 |
| Reseller | reseller.py | 8 |
| Admin | admin.py | 13 |
| Fine-Tuning | finetuning.py | 8 |
| Fundraising | fundraising.py | 7 |
| Partnerships | partnerships.py | 6 |
| Enterprise SLA | enterprise_sla.py | 4 |
| **TOTAL** | **21 router files** | **~152 endpoints** |

---

*All authenticated endpoints require `Authorization: Bearer <access_token>` header.*
*Permission codes (e.g., `heritage:create`) are checked via `app.has_permission()` PostgreSQL function.*
