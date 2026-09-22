# SilkLens Flutter Data Models

> Generated: 2026-05-18
> Source: `apps/mobile/lib/domain/` (entities) and `apps/mobile/lib/data/api/dto/` (DTOs)
> Total entities: 19 | Total DTOs: 12 classes across 6 files

---

## Domain Entities

### Heritage

**File:** `domain/heritage/entities/heritage.dart`
**Fields:**
- `id`: String — internal UUID (partition-aware, never exposed to other users)
- `pubId`: String — public-facing UUIDv7 used in URLs and cross-service references
- `kindSlug`: String — heritage type slug (e.g. `monument`, `ritual`, `craft`)
- `name`: Map<String, String> — i18n display name keyed by BCP-47 locale code
- `summaryMd`: Map<String, String> — short markdown summary per locale
- `descriptionMd`: Map<String, String> — full markdown description per locale
- `tags`: List<String> — searchable flat tags
- `status`: String — lifecycle state (`draft`, `published`, `archived`)
- `countryCode`: String? — ISO 3166-1 alpha-2 country code
- `adminPath`: String? — administrative hierarchy path (e.g. `UZ/TAS/OLD_CITY`)
- `latitude`: double? — WGS-84 latitude for map pin
- `longitude`: double? — WGS-84 longitude for map pin
- `periodStartYear`: int? — historical period start (negative = BCE)
- `periodEndYear`: int? — historical period end
- `heroMediaId`: String? — foreign key to media_assets for primary image
- `confidenceScore`: int — AI recognition confidence 0–100 (default 0)
- `revision`: int — optimistic concurrency revision counter (default 1)
- `isSaved`: bool — client-side saved/bookmarked state (default false)

**Companion classes:** `HeritageFilters` (query parameters), `HeritagePage` (paginated list)
**Used in:** `presentation/pages/heritage/heritage_list_page.dart`, `presentation/widgets/heritage_card.dart`, `presentation/providers/heritage_list_provider.dart`, `presentation/providers/heritage_detail_provider.dart`, `presentation/providers/map_provider.dart`

---

### AuthUser

**File:** `domain/identity/entities/auth_user.dart`
**Fields:**
- `id`: String — internal partition-scoped user UUID (never exposed cross-user)
- `pubId`: String — public UUIDv7 used on profile pages and social graph
- `tenantId`: String — tenant the user belongs to (multi-tenancy support)
- `residencyRegion`: String — data-residency partition (`global`, `eu`, `cn`, …)
- `trustTier`: String — moderation trust level (`new`, `member`, `trusted`, `expert`)
- `preferredLocale`: String — BCP-47 locale for UI (default `en`)
- `isVerified`: bool — email/identity verified flag
- `displayName`: String? — user-chosen display name
- `avatarUrl`: String? — CDN URL of profile photo

**Used in:** `presentation/providers/auth_provider.dart`, `core/storage/secure_token_storage.dart`, wrapped by `AuthSession`

---

### AuthSession

**File:** `domain/identity/entities/auth_session.dart`
**Fields:**
- `accessToken`: String — JWT bearer token for API calls
- `refreshToken`: String — long-lived token for silent re-auth
- `user`: AuthUser — embedded authenticated user data
- `expiresIn`: int — token TTL in seconds (default 900 = 15 min)
- `tokenType`: String — always `Bearer`
- `expiresAt`: DateTime? — absolute expiry timestamp
- `email`: String? — authenticated email (convenience for display)

**Computed:** `isExpired` — true if current time is past `expiresAt`
**Used in:** `presentation/providers/auth_provider.dart`, `core/storage/secure_token_storage.dart`, login/register flows

---

### Review

**File:** `domain/social/entities/review.dart`
**Status:** Stub — factory pending codegen
**Notes:** User-generated heritage review. Architecture §8 specifies LWW + optimistic lock CRDT for the `text` field. Will include rating dimensions from `ReviewDimensions`.

---

### ReviewDimensions

**File:** `domain/social/entities/review_dimensions.dart`
**Fields:**
- `history`: double — accuracy/depth of historical content rating (0–5)
- `photos`: double — quality of photos/media at site (0–5)
- `access`: double — physical accessibility rating (0–5)
- `value`: double — value-for-money / entry experience (0–5)
- `atmosphere`: double — ambience and atmosphere rating (0–5)
- `familyFriendly`: double — suitability for families (0–5)

**Computed:** `average` — arithmetic mean of all 6 dimensions
**Used in:** embedded in `Review` entity, rendered on heritage detail and profile pages

---

### UserProfile

**File:** `domain/social/entities/user_profile.dart`
**Fields:**
- `pubId`: String — public UUIDv7 (never the internal partition id)
- `displayName`: String? — user's chosen display name
- `avatarUrl`: String? — CDN URL of avatar image
- `bio`: String? — short bio text
- `countryCode`: String? — user's displayed country ISO code
- `followersCount`: int — cached follower count (default 0)
- `followingCount`: int — cached following count (default 0)
- `isFollowing`: bool — whether the current viewer follows this user

**Notes:** Lightweight public projection; internal `id` is never included.
**Used in:** `presentation/pages/profile/user_profile_page.dart`, social feed cards

---

### Badge

**File:** `domain/gamification/entities/badge.dart`
**Fields:**
- `slug`: String — unique stable identifier (e.g. `first_scan`, `heritage_50`)
- `name`: String — human-readable badge name
- `description`: String — what the user did to earn it
- `iconUrl`: String? — CDN URL for badge icon image
- `earnedAt`: DateTime? — when the badge was awarded (null = not yet earned)

**Computed:** `isEarned` — true if `earnedAt` is not null
**Used in:** `presentation/pages/gamification/badges_page.dart`, profile trophy shelf

---

### XpSummary

**File:** `domain/gamification/entities/xp_summary.dart`
**Fields:**
- `currentXp`: int — XP within the current level (resets at level-up)
- `lifetimeXp`: int — total accumulated XP across all levels
- `levelName`: String — display name of current level (e.g. `Explorer`, `Scholar`)
- `levelNumber`: int — numeric level index
- `xpToNextLevel`: int — XP threshold required to reach next level

**Computed:** `progressToNextLevel` — 0.0–1.0 fraction for progress bar
**Used in:** `presentation/pages/gamification/badges_page.dart`, profile header XP bar, leaderboard

---

### LeaderboardEntry

**File:** `domain/gamification/entities/leaderboard_entry.dart`
**Status:** Stub — factory pending codegen
**Companion enum:** `LeaderboardScope { weekly, monthly, allTime, friends }`
**Notes:** Backend returns rows ordered by `rank ASC`. Will include user pubId, display name, avatar, XP total, and rank.

---

### MediaCapture

**File:** `domain/media/entities/media_capture.dart`
**Status:** Stub — factory pending codegen
**Companion enum:** `MediaCaptureKind { photo, video }`
**Notes:** Represents media taken by the in-app camera but not yet uploaded. Ephemeral — lives in memory until uploaded or discarded.
**Used in:** camera/scan flow (routed via `app_routes.dart` and `app_router.dart`)

---

### MediaUpload

**File:** `domain/media/entities/media_upload.dart`
**Status:** Stub — factory pending codegen
**Notes:** Result of `POST /v1/media/uploads`. Server returns `media_asset_id` (passed to AI recognition) and a CDN URL for immediate preview rendering.

---

### RecognitionResult

**File:** `domain/media/entities/recognition_result.dart`
**Fields:**
- `candidates`: List<RecognitionCandidate> — ranked list of potential heritage matches
- `topLabel`: String — display label for the best match
- `confidence`: double — 0.0–1.0 confidence of top match

**Computed:** `hasMatch` — true if `confidence > 0.5`

**RecognitionCandidate fields:**
- `heritagePubId`: String — links to Heritage.pubId
- `confidence`: double — per-candidate confidence score
- `name`: String? — display name of matched heritage

**Used in:** recognition/scan result overlay (future AR screen)

---

### Branding

**File:** `domain/branding/entities/branding.dart`
**Fields:**
- `tenantSlug`: String — tenant identifier (e.g. `silklens`, `nuu-musey`)
- `appName`: Map<String, String> — localized app name per locale
- `logoUrl`: String? — CDN URL of light-mode logo
- `logoDarkUrl`: String? — CDN URL of dark-mode logo
- `primaryColor`: String — hex color string (default `#1A3A5C`)
- `accentColor`: String? — hex accent/CTA color
- `splashUrl`: String? — CDN URL of splash screen image
- `fontFamily`: String? — custom font family name (loaded at runtime)
- `themeModeDefault`: String — `system`, `light`, or `dark`
- `extra`: Map<String, dynamic> — open-ended tenant customization bag

**Helpers:** `localizedAppName(lang)`, `primaryColorHex`, `accentColorHex`
**Default:** `Branding.defaults` constant with SilkLens values
**Used in:** `presentation/providers/branding_provider.dart`, `presentation/theme/theme_provider.dart`, `presentation/widgets/silklens_logo.dart`, `presentation/widgets/branded_app_name.dart`

---

### ChatMessage

**File:** `domain/ai/entities/chat_message.dart`
**Fields:**
- `id`: String — message UUID
- `role`: String — `user` or `assistant`
- `content`: String — raw message text (markdown supported by UI)
- `createdAt`: DateTime — UTC timestamp

**Computed:** `isUser` — true if `role == 'user'`
**Used in:** AI chat feature (screens not yet implemented in FAZA 1); stored via `chat_repository_impl.dart`

---

### VocabTerm

**File:** `domain/vocab/entities/vocab_term.dart`
**Fields:**
- `slug`: String — stable machine-readable key (e.g. `monument`, `silk-road`)
- `displayName`: Map<String, String> — i18n label per locale
- `parentSlug`: String? — parent term slug for hierarchical taxonomy
- `sortOrder`: int — display ordering within parent (default 0)

**Helper:** `localizedName(languageCode)` — falls back en → first available
**Used in:** `presentation/providers/vocab_provider.dart`, heritage filter chips, search taxonomy

---

### Subscription

**File:** `domain/billing/entities/subscription.dart`
**Fields:**
- `id`: String — subscription record UUID
- `planId`: String — FK to subscription plan
- `planSlug`: String — human-readable plan identifier (e.g. `free`, `explorer-monthly`)
- `planName`: String — display name of the plan
- `status`: String — `active`, `trialing`, `past_due`, `canceled`, `expired`, `paused`
- `currentPeriodEnd`: DateTime — when the current billing cycle ends
- `trialEndsAt`: DateTime? — trial expiry (null if not on trial)
- `cancelAtPeriodEnd`: bool — subscription set to cancel but still active
- `canceledAt`: DateTime? — when cancellation was requested

**Companion enum:** `SubscriptionStatus { none, active, trialing, pastDue, canceled, expired, paused }`
**Computed:** `isActive` — true if status is `active` or `trial`
**Used in:** `presentation/pages/billing/manage_subscription_page.dart`

---

### SubscriptionPlan

**File:** `domain/billing/entities/subscription_plan.dart`
**Fields:**
- `id`: String — plan record UUID
- `slug`: String — stable plan slug (e.g. `explorer-monthly`, `scholar-annual`)
- `name`: String — display name
- `billingPeriod`: String — `monthly` or `annual`
- `trialDays`: int — free trial length in days (0 = no trial)
- `isDefault`: bool — shown as recommended in plan picker
- `price`: double? — amount in `currency` (null or 0 = free tier)
- `currency`: String — ISO 4217 code (default `USD`)
- `features`: List<String> — marketing bullet points
- `isHighlighted`: bool — show "popular" badge in plan picker UI

**Computed:** `isFree`, `amountMajor` (formatted price string), `interval` (alias for billingPeriod)
**Used in:** `presentation/pages/billing/manage_subscription_page.dart`, plan selection screen

---

### Invoice

**File:** `domain/billing/entities/invoice.dart`
**Fields:**
- `id`: String — invoice UUID
- `number`: String — human-readable invoice number (e.g. `INV-2026-001`)
- `total`: double — amount in `currency`
- `currency`: String — ISO 4217 code (default `USD`)
- `status`: String — `open`, `paid`, `void`, `uncollectible`
- `issuedAt`: DateTime? — when the invoice was created
- `paidAt`: DateTime? — when payment was received

**Computed:** `amountMajor` — formatted string e.g. `"9.99 USD"`
**Used in:** `presentation/pages/billing/invoices_page.dart`

---

### FeedItem

**File:** `domain/social/entities/feed_item.dart`
**Status:** Stub — factory pending codegen
**Companion enum:** `FeedItemKind { review, checkIn, badgeUnlock, follow, comment }`
**Notes:** Heterogeneous social feed row wrapping an actor + action. Presentation layer renders different card widgets per `kind`.

---

## DTOs (data/api/dto/)

### auth_dto.dart

| Class | Purpose |
|---|---|
| `RegisterRequestDto` | Request body for `POST /v1/auth/register` |
| `LoginRequestDto` | Request body for `POST /v1/auth/login` |
| `RefreshRequestDto` | Request body for `POST /v1/auth/refresh` |
| `TokenBundleDto` | Server response with `access_token` + `refresh_token` |
| `UserDto` | User projection in auth responses (maps to `AuthUser`) |
| `LoginResponseDto` | Full login response wrapping `UserDto` + `TokenBundleDto` |
| `MeResponseDto` | Response from `GET /v1/auth/me` — user + session_id + trust_tier |
| `LogoutResponseDto` | Simple `{"status": "ok"}` ack from logout |

### heritage_dto.dart

| Class | Purpose |
|---|---|
| `HeritageDto` | Single heritage item from `GET /v1/heritage/{id}` (maps to `Heritage`) |
| `HeritagePageDto` | Paginated heritage list with items/total/limit/offset |

### branding_dto.dart

| Class | Purpose |
|---|---|
| `BrandingDto` | Slim branding config from `/v1/branding` — tenantSlug, appName, logoUrl, primaryColor, themeModeDefault |

### tenant_branding_dto.dart

| Class | Purpose |
|---|---|
| `TenantBrandingDto` | Minimal tenant config (appName string + primaryColor) — lighter than BrandingDto |

### vocab_dto.dart

| Class | Purpose |
|---|---|
| `VocabTermDto` | Single vocab term (slug + i18n displayName map) |
| `VocabDto` | Collection wrapper: `{ items: [VocabTermDto] }` |

### version_dto.dart

| Class | Purpose |
|---|---|
| `VersionDto` | Health-check response: `{ "version": "x.y.z" }` |

---

## Summary

| Category | Count |
|---|---|
| Domain entity classes (fully implemented) | 12 |
| Domain entity classes (stubs, codegen pending) | 4 (Review, LeaderboardEntry, MediaCapture, MediaUpload, FeedItem — 5 stubs) |
| DTO classes | 12 |
| Domain files total | 19 |
| DTO files total | 6 |

**Stub entities requiring implementation:** `Review`, `LeaderboardEntry`, `MediaCapture`, `MediaUpload`, `FeedItem`

**Multi-tenant pattern:** `Heritage.name`, `Branding.appName`, `VocabTerm.displayName`, and `Heritage.summaryMd`/`descriptionMd` are all `Map<String, String>` keyed by BCP-47 locale — enabling zero-cost i18n without schema changes.

**Data flow:** API response JSON → DTO (fromJson) → Repository impl maps to Domain Entity → Provider exposes to presentation layer. DTOs are never passed beyond the repository layer.
