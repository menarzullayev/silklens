# SilkLens Feature Specifications — Backend-Derived User Flows

> Source: `services/api/tests/` — 34 test files, 32 feature-bearing modules
> Purpose: UI/UX design context — written from the user's perspective
> Date: 2026-05-18

---

## 1. Authentication & Account Security
*Source: test_auth.py, test_auth_middleware.py*

- User can register with email + password (password must be at least 12 characters and contain a digit)
- Registration immediately returns access + refresh tokens — user lands inside the app with no extra step
- User receives a Bearer access token and a longer-lived refresh token
- Login with correct credentials returns fresh tokens
- Login with wrong password or unknown email returns a clear error
- Access token expires; user can silently refresh it using the refresh token
- Refresh token is rotated on every use — the old token is immediately invalidated
- Replaying a consumed refresh token locks the entire token family (security protection against token theft)
- User can view their own profile (GET /me) while authenticated
- User can logout; after logout the refresh token is revoked
- Expired or malformed access tokens are clearly rejected
- Platform tracks which session created the authentication

---

## 2. Multi-Factor Authentication (MFA)
*Source: test_mfa.py*

- User can enroll a TOTP authenticator app (e.g. Google Authenticator) — receives a QR-code provisioning URI
- User verifies the TOTP enrollment by entering a live 6-digit code
- Once enrolled, every subsequent login requires the TOTP code before full access is granted
- Login with MFA active returns a challenge — user must verify the code on a second screen
- After successful MFA verification, a new elevated token is issued with `mfa=true` claim
- User can generate 10 one-time backup codes (12 characters each) as fallback
- Each backup code can only be used once; a second attempt is rejected
- User can list all their active MFA methods
- User can register a hardware security key (WebAuthn / passkey) for passwordless second factor
- Sensitive actions (delete account, disable MFA method) require a fresh MFA proof — if the proof is older than the window, the action is blocked with a step-up prompt
- Accounts without MFA can still self-delete without step-up
- TOTP secrets are encrypted at rest — plaintext never stored
- MFA challenges expire after a set window; expired challenges are rejected with a clear error code

---

## 3. Heritage Discovery & Browsing
*Source: test_heritage.py, test_heritage_writes.py*

- Anyone (no login required) can browse the heritage catalog
- Heritage list is paginated (default 20 per page)
- User can filter heritage by kind (mosque, madrasa, mausoleum, etc.) and country
- User can view full detail of any heritage object by its public ID
- Requesting a non-existent heritage object returns a clear "not found" error
- Heritage objects support multilingual names (uz / en / ru / zh / others)
- Each heritage object tracks: kind, country, GPS coordinates, construction period, status (draft/review/published)
- Content goes through a moderation workflow: draft → submit for review → approve → published
- Editors can update heritage objects — each edit creates a new revision (full audit trail)
- Editors can add historical aliases to a heritage object in any language (e.g. "Maracanda" in Ancient Greek)
- Admins can soft-delete a heritage object; deleted objects disappear from public listing but the record is preserved
- Users can view the complete revision history of a heritage object (who changed what and when)

---

## 4. Text Search
*Source: test_search.py*

- User can search heritage by keyword in their preferred language
- Search supports filtering by country and kind simultaneously
- Results are ranked by relevance
- Search covers multilingual content — Uzbek, English, Russian, Chinese, and other languages each indexed separately
- When a search returns zero results, the query is recorded (helps the team discover gaps in coverage)
- Admin can trigger a full search index rebuild (requires permission)

---

## 5. AI-Powered Features
*Source: test_ai_service.py*

### Image Recognition
- User can submit a photo; the system identifies which heritage site it shows
- Result includes a confidence score and candidate matches

### AI Chat (Heritage Guide)
- Authenticated user can ask questions about heritage in natural language
- Each user gets a daily free quota of chat requests; exceeding it shows a clear "quota reached" message
- Responses are attributed to the AI model used (e.g. Claude)

### Translation
- Any user (no login required) can translate text between supported languages
- Translation memory reuses previous translations — identical inputs are served instantly from cache
- Translating from a language to itself is rejected with a helpful error

### Text-to-Speech
- User can request audio narration of heritage descriptions
- Generated audio is stored and a time-limited download URL is returned
- Duration of the audio clip is returned so the UI can show a progress bar

### Vector / Semantic Search
- User can search by meaning rather than exact keywords
- Results are ranked by semantic similarity score

---

## 6. Augmented Reality (AR) Challenges
*Source: test_ar.py*

- User can browse a list of AR challenges tied to real heritage sites
- Each challenge shows its kind, difficulty level, and XP reward
- User can view full detail of a challenge by its slug
- User can request a hint for a challenge (authenticated)
- User completes a challenge by submitting an answer; a score and XP award are returned
- Correct answers earn XP; incorrect answers earn 0 XP but the user can still see they tried
- Each challenge can only be completed once per user — a second attempt is blocked with a friendly error
- XP earned from AR challenges immediately updates the user's balance
- User can start a solo AR session at a heritage site
- User can start a group AR session and receive a 6-character join code to share with friends
- Friends can join a group session using the code
- User can view available AR overlays (3D/information layers) for any heritage site

---

## 7. Virtual Tours
*Source: test_virtual_tours.py*

- Anyone can browse the catalog of published virtual tours
- Tours are organized into curated collections (e.g. "Ancient Wonders", "Silk Road Journey", "UNESCO Highlights")
- User can view full detail of any published tour by its slug
- Tour progress is tracked per user — the platform remembers which scene the user last reached
- User can mark a tour as completed
- Published tours can be embedded in external websites via an embed code
- Draft tours are hidden from the public listing (admins can still access them by slug)
- Tours go through a publish workflow: draft → published
- Only authorized users (editors/admins) can create or publish tours

---

## 8. Social Features
*Source: test_social.py*

- User can follow another user
- User can unfollow a user they already follow
- User cannot follow themselves
- Following the same user twice shows a clear conflict error
- User can view who follows them (followers list)
- User can view who they are following (following list)
- User sees a feed of activity from people they follow (e.g. "Alisher followed Fatima")
- Blocked users' activity is invisible in the feed
- User can block another user; blocking automatically removes both follow relationships
- User can send a friend invitation to another user; the recipient can accept it
- Friend invitation tokens are shown only at creation; subsequent reads show a masked value (security)

---

## 9. Reviews & Community Content
*Source: test_reviews.py*

- Authenticated user can write a review for any heritage site
- Reviews support multi-dimensional ratings (e.g. history accuracy, atmosphere) on a 1–5 scale
- Each user can only write one review per heritage site — a second attempt is rejected
- New-user reviews go through moderation before becoming publicly visible
- User can vote a review as helpful (thumbs up / down)
- User can react to a review with an emoji-style reaction (e.g. "love")
- User can comment on a review
- Comments are threaded — users can reply to comments
- User can report a review for spam, inappropriate content, etc.

---

## 10. Gamification & Progress
*Source: test_gamification.py*

- User earns XP (experience points) for actions: visiting heritage sites, completing AR challenges, etc.
- XP awards are idempotent — the same action cannot accidentally award XP twice
- User progresses through named levels based on total XP:
  - 0–499 XP: Beginner (yangi)
  - 500–1,999 XP: Explorer (kashfiyotchi)
  - 2,000+ XP: Heritage Guardian (meros qoriqchi)
  - (further levels exist)
- User can see their current XP, current level, next level name, and how much XP is needed to level up
- Daily login streak is tracked — visiting each consecutive day extends the streak
- Opening the app multiple times in one day does not artificially inflate the streak count
- User can view all leaderboards (global, regional, weekly, etc.)
- Global all-time XP leaderboard is always available
- User can view all badges they have unlocked

---

## 11. Notifications
*Source: test_notifications.py*

- User has an in-app notification inbox
- Notifications use templates with personalised variables (e.g. "Welcome, Alisher!")
- User can mark a notification as read
- User can manage notification preferences per category and channel (email, push, in-app)
- Security-critical notifications (e.g. account alerts) cannot be disabled
- Non-critical categories (e.g. marketing) can be turned off
- User can register a mobile device for push notifications (Android / iOS via FCM)
- User can remove a registered push device
- User can configure quiet hours — specify a timezone, start/end time, and which weekdays to silence notifications

---

## 12. Billing & Subscriptions
*Source: test_billing.py*

- Anyone can browse available subscription plans filtered by pricing zone (e.g. CIS region)
- Plan listing shows pricing in local currency
- Authenticated user can subscribe to a plan using a payment method token
- Trial plans start immediately with no payment charge; status shown as "trial"
- Paid plans process payment immediately; status shown as "active"
- Failed payments (e.g. card declined) show a clear payment error — no subscription is created
- Subscription creation is idempotent — retrying with the same key never double-charges
- User can cancel their subscription at end of period (access continues until period ends)
- User can resume a cancelled subscription before the period ends
- User can view which features/entitlements their plan unlocks (e.g. unlimited AI chat, ad-free)
- New users with no subscription see null/empty subscription state
- Each subscription creates a numbered invoice (format: SLN-YYYY-NNNNNNN)
- Payment webhooks from providers (Stripe, etc.) are processed once — duplicate webhook events are safely ignored

---

## 13. Media Uploads
*Source: test_media.py*

- Authenticated user can upload images (PNG, JPEG, etc.)
- Upload specifies a license type (e.g. Creative Commons)
- Upload returns asset metadata and a time-limited download URL
- User can view metadata for their own uploaded assets
- User can generate a new signed download URL for their asset
- User can delete their own uploaded asset; deleted assets are no longer publicly accessible
- Users cannot access another user's private assets (403 forbidden)
- System validates file content using magic-byte detection — a PDF disguised as PNG is rejected
- Unsupported file types (e.g. HTML) are always rejected

---

## 14. Compliance & Privacy (GDPR / UZ Data Law)
*Source: test_compliance.py*

- User can read the current Privacy Policy and Terms of Service in their language
- If a document is not available in the user's language, English is shown as fallback
- User can consent to a legal document (e.g. Privacy Policy)
- User can view all their active consents
- User can withdraw a consent at any time
- User can request a full export of their personal data — the request is queued and the user is notified when ready
- User can view the status of a data export request
- User can request account deletion — deletion is scheduled 30 days in the future (grace period)
- During the grace period, user can cancel the deletion request
- After the grace period expires, cancellation is no longer possible
- After anonymization: email is replaced with a placeholder, display name becomes "__deleted__", account status is "deleted"
- Anonymous visitors can submit cookie consent preferences (analytics, marketing, ad targeting) with their region
- Strictly necessary cookies cannot be disabled

---

## 15. Rate Limiting & Security
*Source: test_ratelimit.py*

- Login attempts are rate-limited by IP address — after 5 attempts per minute, further attempts are blocked with a Retry-After header
- AI chat requests are rate-limited per user — after 30 requests per minute, the user is temporarily blocked
- Repeated failed login attempts on the same account trigger a 15-minute account lockout
- All rate limit responses include a Retry-After header so the UI can show a countdown

---

## 16. Reseller & White-Label (B2B)
*Source: test_reseller.py*

- A company can submit a reseller application to white-label SilkLens for their own brand
- Application specifies: company name, plan kind (tourism agency, museum, etc.), expected users, country, and contact info
- Duplicate applications (same email + company) are rejected
- Applicant can check the status of their application (limited public view — no internal admin notes shown)
- Admin can approve a reseller application — this automatically creates a sub-tenant, a revenue-share agreement, and a branding stub
- Revenue share is configured as a percentage; total across all parents cannot exceed 100%
- Admin can reject an application with a reason
- Admin can view full application details including contact email and internal notes
- User can view their own tenant context including which parent tenants they belong to (tenant chain)

---

## 17. Partnerships & Uptime SLA
*Source: test_partnerships.py*

- Public visitors can see the list of active partners (museums, universities, cultural institutions)
- Anyone can view the current platform uptime status and any open incidents
- Admin can create a partnership agreement (partner name, tier, contact, annual value)
- Admin can generate an SLA report for a partner showing measured uptime percentage
- Admin can issue a partnership badge (e.g. "academic", "heritage champion") to a partner
- Each badge type can only be issued once per agreement (duplicate badge returns a conflict error)

---

## 18. Enterprise SLA
*Source: test_enterprise_sla.py*

- Public visitors can browse enterprise tier options:
  - **Starter** ($499/month, 99.0% uptime SLA, 1,000 API calls/min)
  - **Professional** ($999/month, 99.5% uptime SLA, custom domain support)
  - **Enterprise** (custom, 99.9% uptime SLA, white-label included, unlimited seats)
  - **Strategic** (custom pricing, 1-hour support response, dedicated Customer Success Manager)
- Anyone can view the real-time platform status (uptime %, SLA met, open incidents)
- Public incident list only shows incidents marked as visible to the public
- Enterprise admins can view usage snapshots for their account (API calls, latency, active seats) per month
- SLA compliance reports show measured uptime and whether SLA obligations are met
- Admins can create incident reports and mark them as resolved with root cause documentation

---

## 19. AI Model Administration
*Source: test_ai_service.py*

- Super admins can list all registered AI models in the platform registry
- Super admins can enable or disable individual AI models
- Super admins can view and manage AI fallback chains (which model to use when the primary fails)
- System pre-configures fallback chains for: vision, TTS, translation, and chat

---

## 20. Admin Panel
*Source: test_admin.py*

- Super admin can list all tenants on the platform
- Super admin can update the branding of any tenant (app name, primary color)
- Super admin can read and write system settings (key-value configuration)
- Super admin can toggle feature flags for gradual rollouts
- Public API returns the current branding for the default tenant (used by the app at startup)
- Public API returns the list of supported languages

---

## 21. Fine-Tuning Dataset Management (Admin)
*Source: test_finetuning.py*

- Admin can list all AI fine-tuning datasets
- Admin can view details of a specific dataset (purpose, target model kind, status)
- Admin can add manual training examples (question/answer pairs, labeled by language)
- Admin can review the list of pending (unreviewed) examples
- Admin can approve an example; approved examples are exported to the training pipeline
- Dataset can be exported in JSONL format with messages/user/assistant schema
- Admin can create a fine-tuning job specifying the provider (OpenAI, Anthropic), base model, and hyperparameters
- Admin can check the status of a running fine-tuning job

---

## Summary

| # | Feature Area | Test File | User-Visible Flows |
|---|---|---|---|
| 1 | Authentication | test_auth.py, test_auth_middleware.py | Register, login, refresh, logout |
| 2 | Multi-Factor Auth | test_mfa.py | TOTP, backup codes, WebAuthn, step-up |
| 3 | Heritage Discovery | test_heritage.py, test_heritage_writes.py | Browse, filter, edit, moderate, revisions |
| 4 | Text Search | test_search.py | Full-text, multilingual, filters |
| 5 | AI Features | test_ai_service.py | Recognition, chat, translation, TTS, vector search |
| 6 | AR Challenges | test_ar.py | Challenges, solo/group sessions, overlays, XP |
| 7 | Virtual Tours | test_virtual_tours.py | Browse, progress, embed, collections |
| 8 | Social | test_social.py | Follow, feed, block, friend invitations |
| 9 | Reviews | test_reviews.py | Write, vote, react, comment, report |
| 10 | Gamification | test_gamification.py | XP, levels, streaks, leaderboards, badges |
| 11 | Notifications | test_notifications.py | Inbox, preferences, push devices, quiet hours |
| 12 | Billing | test_billing.py | Plans, subscribe, cancel, entitlements, invoices |
| 13 | Media | test_media.py | Upload, signed URLs, delete, MIME validation |
| 14 | Compliance / GDPR | test_compliance.py | Legal docs, consent, data export, account deletion |
| 15 | Rate Limiting | test_ratelimit.py | IP rate limits, user quotas, account lockout |
| 16 | Reseller / White-label | test_reseller.py | Applications, approve, reject, revenue share |
| 17 | Partnerships | test_partnerships.py | Partner list, SLA reports, badges |
| 18 | Enterprise SLA | test_enterprise_sla.py | Tiers, status, incidents, usage reports |
| 19 | AI Model Admin | test_ai_service.py | Model registry, enable/disable, fallback chains |
| 20 | Admin Panel | test_admin.py | Tenants, branding, settings, feature flags |
| 21 | Fine-Tuning | test_finetuning.py | Datasets, examples, export, training jobs |

**Total: 21 distinct feature areas, ~180+ individual user flows**
