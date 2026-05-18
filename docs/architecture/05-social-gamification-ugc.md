# SilkLens — Architecture 05
## Social Graph, User-Generated Content, Gamification, Moderation, Journals & Group Travel

> **Agent:** 5 of 8 — Social, Gamification & UGC Architect
> **Authoritative sources:** `Roadmap.md` (Faza 3 "SPARK", Faza 6 "VELOCITY"), `Project-Decisions.md` §11 (UGC), §24 (Gamification), §30 (Social), §42 (i18n), §43 (Moderation), §34 (Storage), §36 (GDPR).
> **Cross-agent contracts:** Agent 1 (`heritage.id`, `heritage.region_id`, `cities`), Agent 2 (`users.id`, `user_trust_scores`, `device_fingerprints`), Agent 3 (`ai_moderation_jobs`, vision/NLP moderation pipeline, NLLB-200 translate), Agent 4 (`media.id`, EXIF, perceptual hash, NSFW score), Agent 7 (push/email/telegram notification bus), Agent 6 (admin policy registry / feature flags), Agent 8 (event bus, analytics warehouse).
> **Target scale:** 10M MAU, 100M UGC items, 1B `xp_events`, sub-second feed reads, sub-100ms leaderboard reads.

---

## 1. Domain Analysis

SilkLens is not a single-purpose vision app — Project-Decisions §2 explicitly rejects "one core function" framing. Sociality is a **first-class platform layer**: cultural heritage is intrinsically a social experience (people visit *together*, brag about *streaks*, argue about *which dynasty built the minaret*, share photos, plan multi-day Silk Road itineraries with friends). The social/gamification/UGC layer therefore must support five distinct interaction archetypes simultaneously, and every entity in this document is shaped by which archetype it primarily serves:

1. **Solo expression** — A user uploads a photo of Registan, writes a 200-word review in Uzbek with 4-axis ratings (history accuracy / photo quality / accessibility / value), earns +30 XP for the photo and +20 XP for the review. The photo enters Agent 4's media pipeline; the review enters our `reviews` table. Both feed `ugc_submissions` for unified moderation.
2. **Pairwise interaction** — Follow, friend-request, react, comment, helpful-vote, report. Asymmetric (follow, block) and symmetric (friendship) social graph edges; threaded comments on heritage AND on reviews AND on user-photos.
3. **Group coordination** — Real-time multi-user trips: a Tashkent family of 4 plans a 3-day Samarkand itinerary together, each member adding stops, the itinerary syncing live via WebSocket, with a CRDT-backed shared state and an in-trip chat. Per Roadmap Faza 3.
4. **Asynchronous identity** — Travel journals (long-form, multi-day, multi-place, multi-photo "chapters"), badges, level progression, leaderboards (weekly/monthly/all-time × global/friends/city). This is the Strava/Duolingo loop: durable identity that compels return visits.
5. **Trust & safety** — Reviews drive purchase decisions for premium subscriptions (§17) and B2B featured listings (§19), which means review quality is a **revenue-protecting concern**. Vote-brigading, sock-puppets, XP farming, and cultural-context misjudgments by foreign moderators are all real attacks against SilkLens's credibility.

The **gamification economy** is treated like a financial ledger: `xp_events` is an append-only journal, `xp_balances` is a materialized projection, and reconciliation runs nightly. This is because §24's mention of "premium 1 month free for 30-day streak" promotes XP from a vanity number to a redeemable claim — and any redeemable claim demands an auditable ledger.

The **UGC moderation pipeline** must support all three modes from §43 (pre-mod, post-mod, AI-gated) simultaneously and **per-content-type, per-user-trust-tier, per-region** — Uzbekistan may post-moderate; a newly-opened Saudi region may pre-moderate for cultural sensitivity. The pipeline is driven by `moderation_policies` rows that admin (Agent 6) can change at runtime, with no code redeploy.

The **multi-language UGC challenge** (§42) is that reviews are stored in the language the user wrote, tagged with detected language, then translated on read via NLLB-200 with a translation-memory cache. Reactions are language-agnostic but their *labels* (admin-extensible per §24's "dinamik" philosophy) are localized via the standard i18n layer.

The **anti-cheat surface** is large: same heritage visit cannot grant XP twice in 24 hours; check-ins require GPS within geofence of `heritage.coordinates`; suspicious patterns (10 check-ins/hour, all from same device, all from same IP, all with the same EXIF camera signature) trip `gamification_anti_abuse_rules` and freeze XP pending review.

The **whale problem** in the social graph: a celebrity Uzbek travel influencer might amass 2M followers. Pure push-based fan-out is fatal (writing 2M `activity_fanout` rows per action). We use a **hybrid pull-push**: regular users (< 5000 followers) push; whales pull on read; the boundary is admin-configurable.

---

## 2. Entity Discovery Report

Total tables specified: **47**. Grouped:

### 2.1 Reviews & ratings (5)
- `reviews` — top-level review object, one per (user, heritage)
- `review_ratings` — one row per rating dimension (history/photo/access/value/...) for extensibility
- `review_dimensions` — admin-configurable catalog of dimensions per content type
- `review_helpful_votes` — up/down/funny/insightful with vote-type extensibility
- `review_translations` — cached NLLB-200 translations per (review_id, target_language)

### 2.2 Comments & reactions (4)
- `comments` — threaded via `ltree` path; polymorphic target (heritage | review | media | journal_entry | group_trip_item)
- `comment_edits` — history (immutable)
- `reactions` — polymorphic target; admin-extensible reaction types (`reaction_types`)
- `reaction_types` — admin catalog (heart, fire, mosque, history-buff, traveler, ...)

### 2.3 Social graph (6)
- `follows` — one-way directed edge
- `friendships` — symmetric (stored canonically: user_id_a < user_id_b)
- `friend_invitations` — pending invitations (incl. external invites by email/phone)
- `block_list` — user → user blocks (cascade-suppresses follows, comments, reactions)
- `mutes` — softer than block: suppresses activity without notifying
- `close_friends` — Instagram-style inner circle (drives "Close Friends only" journals)

### 2.4 Activity feed (4)
- `activity_events` — source of truth for every social-worthy action (append-only)
- `activity_fanout` — delivered feed items per (recipient_user_id, event_id), monthly-partitioned
- `feed_subscriptions` — explicit subscriptions (e.g., "city of Samarkand", "topic: AR reconstructions")
- `whale_users` — high-follower users excluded from push fan-out (read-time merged)

### 2.5 Gamification core (10)
- `badge_types` — admin catalog
- `badge_criteria` — rule-DSL JSON; evaluated by Celery worker on trigger events
- `user_badges` — earned badges
- `xp_events` — append-only ledger; every +XP and every -XP (revocation) row
- `xp_balances` — materialized current total per user (refreshed by trigger or compensating job)
- `levels` — admin-configurable thresholds & rewards
- `user_levels` — cached current level per user
- `streaks` — current_streak, longest_streak, last_streak_date, timezone_anchor
- `streak_events` — daily heartbeat (date_local, user_id) used for streak reconstruction
- `gamification_anti_abuse_rules` — admin DSL rules to freeze/refund XP

### 2.6 Leaderboards (3)
- `leaderboards` — definitions (scope, period, metric)
- `leaderboard_entries` — Redis-mirrored Postgres durable copy
- `leaderboard_snapshots` — frozen at period end (durable history for "Best of Week 23, 2026")

### 2.7 Travel journals (3)
- `travel_journals` — top-level journal (title, cover_media_id, visibility, date_range)
- `journal_entries` — one entry per day OR per place; rich content (markdown blocks)
- `journal_collaborators` — multi-author journals

### 2.8 Group travel (4)
- `group_trips` — top-level shared trip
- `group_trip_members` — members with roles (owner, editor, viewer)
- `group_trip_items` — shared itinerary item (place, time, notes); CRDT vector clock columns
- `group_trip_chat` — in-trip messages (text + media + system events)

### 2.9 Moderation (6)
- `ugc_submissions` — polymorphic super-table for any UGC awaiting moderation
- `moderation_queue` — work queue with priority lanes
- `moderation_actions` — audit log of every moderator action
- `moderation_policies` — admin-configurable per (content_type × region × user_trust_tier)
- `reports` — user-submitted flags
- `report_resolutions` — outcome of report (dismissed, removed, escalated)

### 2.10 Trust & abuse (5)
- `auto_moderation_results` — link to Agent 3's AI pipeline output
- `content_quality_scores` — per-UGC quality (recency-weighted helpful votes, etc.)
- `helpfulness_scores` — per-review aggregated helpful score
- `spam_signals` — accumulated signals per user (repetition, velocity, link-density)
- `vote_brigading_signals` — sudden coordinated vote bursts

### 2.11 Cross-agent linkage (2)
- `device_fingerprints_link` — sockpuppet-graph edges (read from Agent 2's `device_fingerprints` table; this table stores the *suspicion graph*)
- `notification_triggers_map` — declarative table consumed by Agent 7's notification dispatcher

---

## 3. Full Table-by-Table Specification

All tables use:
- `id` UUID v7 (time-ordered, see ADR `id-strategy`)
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()` with trigger
- `deleted_at TIMESTAMPTZ` for soft delete where applicable
- All `user_id` FKs → `users(id)` (Agent 2), `ON DELETE` policy noted below

### 3.1 `reviews`

```sql
CREATE TABLE reviews (
  id              UUID PRIMARY KEY DEFAULT uuidv7(),
  user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  heritage_id     UUID NOT NULL REFERENCES heritage(id) ON DELETE CASCADE,
  body            TEXT NOT NULL CHECK (length(body) BETWEEN 10 AND 10000),
  body_lang       TEXT NOT NULL,            -- ISO 639-1, detected by NLLB lang-id
  rating_overall  NUMERIC(3,2) NOT NULL CHECK (rating_overall BETWEEN 1 AND 5),
  visited_at      DATE,                     -- when the user claims to have visited
  device_fingerprint_id UUID REFERENCES device_fingerprints(id),
  ip_inet         INET,                     -- captured at submit; for vote-brigade analysis
  status          TEXT NOT NULL DEFAULT 'pending_moderation'
                  CHECK (status IN ('pending_moderation','published','rejected','removed','shadow_banned')),
  moderation_id   UUID REFERENCES ugc_submissions(id),
  helpful_count   INTEGER NOT NULL DEFAULT 0,    -- denormalized cache
  unhelpful_count INTEGER NOT NULL DEFAULT 0,
  quality_score   NUMERIC(5,4),                  -- nightly recompute
  edited_count    SMALLINT NOT NULL DEFAULT 0,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at      TIMESTAMPTZ,
  UNIQUE (user_id, heritage_id)
);
CREATE INDEX idx_reviews_heritage_pub ON reviews(heritage_id, created_at DESC) WHERE status='published';
CREATE INDEX idx_reviews_user ON reviews(user_id, created_at DESC) WHERE status='published';
CREATE INDEX idx_reviews_quality ON reviews(heritage_id, quality_score DESC) WHERE status='published';
CREATE INDEX idx_reviews_lang ON reviews(body_lang) WHERE status='published';
```

**Why `UNIQUE(user_id, heritage_id)`:** one review per heritage per user. Edits update; full rewrite via "delete and resubmit" so old review remains in audit.

**Why `device_fingerprint_id` + `ip_inet` denormalized:** anti-brigade analysis needs immutable submission context even if the user later deletes their account.

### 3.2 `review_ratings`

```sql
CREATE TABLE review_ratings (
  review_id     UUID NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
  dimension_id  UUID NOT NULL REFERENCES review_dimensions(id),
  rating        SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
  PRIMARY KEY (review_id, dimension_id)
);
```

**Why a separate table, not JSONB on `reviews`:** admin can introduce new dimensions ("crowd level", "Instagram-worthiness") without schema change; aggregation queries become trivial (`AVG(rating) GROUP BY dimension_id`); query planner uses indexes properly.

### 3.3 `review_dimensions` (admin catalog)

```sql
CREATE TABLE review_dimensions (
  id              UUID PRIMARY KEY DEFAULT uuidv7(),
  code            TEXT NOT NULL UNIQUE,        -- 'history_accuracy', 'photo_quality', ...
  display_order   SMALLINT NOT NULL,
  applies_to      TEXT NOT NULL,               -- 'heritage' for now; future: 'restaurant'
  is_active       BOOLEAN NOT NULL DEFAULT true,
  weight          NUMERIC(4,3) NOT NULL DEFAULT 1.0,  -- weighted aggregate
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Seed rows: `history_accuracy`, `photo_quality`, `accessibility`, `value_for_money`, `crowd_level`.

### 3.4 `review_helpful_votes`

```sql
CREATE TABLE review_helpful_votes (
  review_id     UUID NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
  user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  vote          SMALLINT NOT NULL CHECK (vote IN (-1, 1)),
  voted_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  device_fingerprint_id UUID REFERENCES device_fingerprints(id),
  ip_inet       INET,
  PRIMARY KEY (review_id, user_id)
);
CREATE INDEX idx_helpful_voted_at ON review_helpful_votes(voted_at);  -- brigade detection
```

### 3.5 `review_translations`

```sql
CREATE TABLE review_translations (
  review_id       UUID NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
  target_lang     TEXT NOT NULL,
  translated_body TEXT NOT NULL,
  engine          TEXT NOT NULL,               -- 'nllb-200' | 'deepl' | 'google' | 'human'
  confidence      NUMERIC(4,3),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (review_id, target_lang)
);
```

Cache-fill on demand; LRU eviction by `created_at` if storage pressure arises.

### 3.6 `comments`

```sql
CREATE TABLE comments (
  id            UUID PRIMARY KEY DEFAULT uuidv7(),
  user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  target_type   TEXT NOT NULL CHECK (target_type IN ('heritage','review','media','journal_entry','group_trip_item','comment')),
  target_id     UUID NOT NULL,
  parent_id     UUID REFERENCES comments(id) ON DELETE CASCADE,
  path          LTREE NOT NULL,              -- materialized tree path: root_id.child_id....
  depth         SMALLINT NOT NULL CHECK (depth BETWEEN 0 AND 6),
  body          TEXT NOT NULL CHECK (length(body) BETWEEN 1 AND 5000),
  body_lang     TEXT NOT NULL,
  status        TEXT NOT NULL DEFAULT 'published'
                CHECK (status IN ('pending_moderation','published','removed','shadow_banned')),
  reply_count   INTEGER NOT NULL DEFAULT 0,   -- denormalized
  reaction_count INTEGER NOT NULL DEFAULT 0,
  edited_count  SMALLINT NOT NULL DEFAULT 0,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at    TIMESTAMPTZ
);
CREATE INDEX idx_comments_target ON comments(target_type, target_id, created_at DESC) WHERE status='published';
CREATE INDEX idx_comments_path_gist ON comments USING GIST(path);
CREATE INDEX idx_comments_user ON comments(user_id, created_at DESC);
```

See §8 for rationale on `ltree` over adjacency-list and materialized-path-as-TEXT.

### 3.7 `reactions`

```sql
CREATE TABLE reactions (
  id            UUID PRIMARY KEY DEFAULT uuidv7(),
  user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  target_type   TEXT NOT NULL CHECK (target_type IN ('review','comment','media','journal_entry','heritage')),
  target_id     UUID NOT NULL,
  reaction_type_id UUID NOT NULL REFERENCES reaction_types(id),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, target_type, target_id, reaction_type_id)
);
CREATE INDEX idx_reactions_target ON reactions(target_type, target_id);
```

**Why one row per reaction type (not aggregated):** a user can react with both "heart" and "fire" on the same item; matches §24/§30's "maximal possibilities" philosophy.

### 3.8 `reaction_types`

```sql
CREATE TABLE reaction_types (
  id            UUID PRIMARY KEY DEFAULT uuidv7(),
  code          TEXT NOT NULL UNIQUE,         -- 'heart','fire','mosque','history_buff'
  emoji         TEXT,
  icon_asset_id UUID REFERENCES media(id),
  display_order SMALLINT NOT NULL,
  is_active     BOOLEAN NOT NULL DEFAULT true,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Admin (Agent 6) introduces new reactions without code change. Labels localized via i18n layer.

### 3.9 `follows`

```sql
CREATE TABLE follows (
  follower_id   UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  followee_id   UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (follower_id, followee_id),
  CHECK (follower_id <> followee_id)
);
CREATE INDEX idx_follows_followee ON follows(followee_id, created_at DESC);  -- "who follows me"
```

Counter caches (`users.follower_count`, `users.following_count`) maintained by trigger AND nightly reconciliation.

### 3.10 `friendships`

```sql
CREATE TABLE friendships (
  user_id_a     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  user_id_b     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id_a, user_id_b),
  CHECK (user_id_a < user_id_b)              -- canonical ordering
);
CREATE INDEX idx_friendships_b ON friendships(user_id_b);  -- two-sided lookup
```

`CHECK (user_id_a < user_id_b)`: stores each friendship exactly once, halves storage, eliminates "is X friends with Y" disambiguation.

### 3.11 `friend_invitations`

```sql
CREATE TABLE friend_invitations (
  id            UUID PRIMARY KEY DEFAULT uuidv7(),
  inviter_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  invitee_user_id UUID REFERENCES users(id) ON DELETE CASCADE,    -- nullable: external invite
  invitee_email TEXT,
  invitee_phone TEXT,
  status        TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending','accepted','declined','expired','revoked')),
  message       TEXT,
  expires_at    TIMESTAMPTZ NOT NULL DEFAULT now() + INTERVAL '30 days',
  responded_at  TIMESTAMPTZ,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (invitee_user_id IS NOT NULL OR invitee_email IS NOT NULL OR invitee_phone IS NOT NULL)
);
CREATE INDEX idx_finv_invitee ON friend_invitations(invitee_user_id) WHERE status='pending';
CREATE UNIQUE INDEX uniq_finv_pair ON friend_invitations(inviter_id, invitee_user_id)
  WHERE status='pending' AND invitee_user_id IS NOT NULL;
```

### 3.12 `block_list`

```sql
CREATE TABLE block_list (
  blocker_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  blocked_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  reason        TEXT,                        -- optional user-provided reason
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (blocker_id, blocked_id)
);
```

Block side-effects (deferred to async worker): auto-unfollow both directions, hide existing comments/reviews between the pair, hide from search.

### 3.13 `mutes`

```sql
CREATE TABLE mutes (
  muter_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  muted_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  expires_at    TIMESTAMPTZ,                 -- nullable = permanent
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (muter_id, muted_id)
);
```

### 3.14 `close_friends`

```sql
CREATE TABLE close_friends (
  user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  close_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, close_user_id),
  CHECK (user_id <> close_user_id)
);
```

Drives `visibility='close_friends'` for journals and reviews.

### 3.15 `activity_events`

```sql
CREATE TABLE activity_events (
  id            UUID PRIMARY KEY DEFAULT uuidv7(),
  actor_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  event_type    TEXT NOT NULL,               -- 'review_posted','photo_uploaded','badge_earned','heritage_visited','journal_published','followed','reacted'
  object_type   TEXT NOT NULL,               -- 'review','media','badge','heritage','journal',...
  object_id     UUID NOT NULL,
  context       JSONB,                       -- e.g. {heritage_id, city_id, ...} for ranking/filtering
  visibility    TEXT NOT NULL DEFAULT 'public'
                CHECK (visibility IN ('public','followers','friends','close_friends','private')),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
) PARTITION BY RANGE (created_at);
-- monthly partitions: activity_events_2026_05, activity_events_2026_06, ...
CREATE INDEX idx_ae_actor_time ON activity_events(actor_id, created_at DESC);
CREATE INDEX idx_ae_type ON activity_events(event_type, created_at DESC);
CREATE INDEX idx_ae_context_gin ON activity_events USING GIN(context jsonb_path_ops);
```

### 3.16 `activity_fanout`

```sql
CREATE TABLE activity_fanout (
  recipient_id  UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  event_id      UUID NOT NULL,               -- FK NOT enforced cross-partition; logical
  event_created_at TIMESTAMPTZ NOT NULL,     -- denormalized for ORDER BY without join
  actor_id      UUID NOT NULL,
  event_type    TEXT NOT NULL,
  seen_at       TIMESTAMPTZ,
  inserted_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (recipient_id, event_id)
) PARTITION BY RANGE (event_created_at);
CREATE INDEX idx_fanout_recipient_time ON activity_fanout(recipient_id, event_created_at DESC);
```

**Partition by `event_created_at` (month), NOT by `recipient_id` range.** Justification:

1. **Eviction is cheap:** dropping the 90-day-old partition truncates the feed retention window in O(1).
2. **Hot data locality:** users read the *recent* feed almost exclusively; this concentrates working set in the latest partition (hot in cache).
3. **`recipient_id` range partitioning would be wrong** because user-id is UUIDv7 (time-ordered) — old users would skew to first partitions; we'd have stale partitions getting all the writes for whales who joined early.
4. **Cross-partition queries are bounded:** "give me the last 50 feed items" hits at most 2 partitions (current + previous month) because retention is short.

Retention: 90 days for free users, 365 days for premium (per Agent 6 policy).

### 3.17 `feed_subscriptions`

```sql
CREATE TABLE feed_subscriptions (
  id            UUID PRIMARY KEY DEFAULT uuidv7(),
  user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  subject_type  TEXT NOT NULL CHECK (subject_type IN ('user','city','region','heritage','topic','badge_type')),
  subject_id    UUID NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, subject_type, subject_id)
);
CREATE INDEX idx_feedsub_subject ON feed_subscriptions(subject_type, subject_id);
```

A user can subscribe to "everything in Bukhara" or "every new AR reconstruction" — extends the feed beyond strict follow-graph.

### 3.18 `whale_users`

```sql
CREATE TABLE whale_users (
  user_id           UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  follower_count    INTEGER NOT NULL,
  classified_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  fanout_strategy   TEXT NOT NULL DEFAULT 'pull'
                    CHECK (fanout_strategy IN ('push','pull','hybrid'))
);
```

Refreshed by a nightly Celery job: users with `follower_count >= settings.WHALE_THRESHOLD` (default 5000, admin-configurable) are promoted.

### 3.19 `badge_types`

```sql
CREATE TABLE badge_types (
  id            UUID PRIMARY KEY DEFAULT uuidv7(),
  code          TEXT NOT NULL UNIQUE,
  category      TEXT NOT NULL,               -- 'exploration','social','content','streak','seasonal'
  icon_media_id UUID REFERENCES media(id),
  rarity        TEXT NOT NULL CHECK (rarity IN ('common','rare','epic','legendary')),
  xp_reward     INTEGER NOT NULL DEFAULT 0,
  is_active     BOOLEAN NOT NULL DEFAULT true,
  released_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  retired_at    TIMESTAMPTZ,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Labels (name, description) live in i18n translation tables keyed by `badge_types.id`.

### 3.20 `badge_criteria`

```sql
CREATE TABLE badge_criteria (
  badge_type_id UUID PRIMARY KEY REFERENCES badge_types(id) ON DELETE CASCADE,
  rule_dsl      JSONB NOT NULL,
  -- Example DSL:
  -- { "type":"count", "event":"heritage_visited",
  --   "filter":{"city_id":"<uuid-of-Samarkand>"}, "threshold":10 }
  -- { "type":"streak", "event":"daily_open", "threshold":7 }
  -- { "type":"composite", "all":[ {...}, {...} ] }
  evaluator_version SMALLINT NOT NULL DEFAULT 1
);
```

A `BadgeEvaluator` worker subscribes to `xp_events` and re-checks affected badges via the DSL. Versioning lets us evolve evaluators safely.

### 3.21 `user_badges`

```sql
CREATE TABLE user_badges (
  user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  badge_type_id UUID NOT NULL REFERENCES badge_types(id) ON DELETE CASCADE,
  earned_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  source_event_id UUID,                       -- the xp_event/activity_event that triggered
  revoked_at    TIMESTAMPTZ,
  revoke_reason TEXT,
  PRIMARY KEY (user_id, badge_type_id)
);
CREATE INDEX idx_userbadges_user_time ON user_badges(user_id, earned_at DESC) WHERE revoked_at IS NULL;
```

### 3.22 `xp_events` (append-only ledger)

```sql
CREATE TABLE xp_events (
  id            UUID PRIMARY KEY DEFAULT uuidv7(),
  user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  delta         INTEGER NOT NULL,              -- positive or negative (revocation/anti-cheat)
  reason_code   TEXT NOT NULL,                 -- 'visit_heritage','first_visit','review','photo','review_helpful_received','referral','anti_cheat_clawback'
  idempotency_key TEXT NOT NULL,               -- e.g. 'visit:USER:HERITAGE:2026-05-18'
  context       JSONB,                         -- {heritage_id, review_id, ...}
  awarded_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, idempotency_key)
) PARTITION BY RANGE (awarded_at);
CREATE INDEX idx_xp_user_time ON xp_events(user_id, awarded_at DESC);
```

**Append-only ledger pattern, not column on user:**
- Audit: every XP delta is reconstructible (who, why, when, what triggered it).
- Anti-cheat clawback: post-hoc detection of XP-farming inserts a *negative* delta row; the original positive row is never mutated.
- Reconciliation: `xp_balances` can be rebuilt from scratch by summing `xp_events`.
- Migrations of formulas are safe — the historical XP awards remain mathematically correct.
- `idempotency_key` makes the "same visit can't be counted twice/day" rule a DB-level guarantee (unique constraint), not application logic.

### 3.23 `xp_balances`

```sql
CREATE TABLE xp_balances (
  user_id       UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  total_xp      BIGINT NOT NULL DEFAULT 0,
  weekly_xp     INTEGER NOT NULL DEFAULT 0,
  monthly_xp    INTEGER NOT NULL DEFAULT 0,
  yearly_xp     INTEGER NOT NULL DEFAULT 0,
  last_event_id UUID,
  refreshed_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Updated by trigger on `xp_events INSERT`, period buckets reset by cron at period boundaries (and a reconciliation job sums from `xp_events` nightly to catch drift).

### 3.24 `levels`

```sql
CREATE TABLE levels (
  level_number  SMALLINT PRIMARY KEY,
  code          TEXT NOT NULL UNIQUE,        -- 'sayohatchi','kashfiyotchi',...
  min_xp        INTEGER NOT NULL,
  perks         JSONB,                       -- {audio_minutes_per_month: 50, ar_unlocked: true, ...}
  is_active     BOOLEAN NOT NULL DEFAULT true
);
```

Editable by admin per §24 philosophy.

### 3.25 `user_levels`

```sql
CREATE TABLE user_levels (
  user_id       UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  current_level SMALLINT NOT NULL DEFAULT 1 REFERENCES levels(level_number),
  achieved_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  previous_level SMALLINT
);
```

### 3.26 `streaks`

```sql
CREATE TABLE streaks (
  user_id          UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  current_length   INTEGER NOT NULL DEFAULT 0,
  longest_length   INTEGER NOT NULL DEFAULT 0,
  last_active_date DATE,                       -- in user's local timezone
  timezone_anchor  TEXT NOT NULL DEFAULT 'Asia/Tashkent',
  freeze_credits   SMALLINT NOT NULL DEFAULT 0,  -- Duolingo-style streak freezes
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Timezone handling:** `streak_events.event_date` is the user's local date at submission time; `timezone_anchor` is sticky (last-used) to prevent abuse like flying east to "skip a day". When user travels and timezone shifts >6h, we treat the *union* of yesterday-local-OLD and yesterday-local-NEW as valid for that one rollover day. Edge case ADR follows below in §13.

### 3.27 `streak_events`

```sql
CREATE TABLE streak_events (
  user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  event_date   DATE NOT NULL,                 -- local date in user's timezone_anchor
  source       TEXT NOT NULL CHECK (source IN ('open','visit','review','photo','manual_freeze')),
  source_event_id UUID,
  PRIMARY KEY (user_id, event_date)
);
```

Rebuilds `streaks.current_length` from contiguous `event_date` runs ending at today.

### 3.28 `leaderboards`

```sql
CREATE TABLE leaderboards (
  id            UUID PRIMARY KEY DEFAULT uuidv7(),
  code          TEXT NOT NULL UNIQUE,
  scope_type    TEXT NOT NULL CHECK (scope_type IN ('global','city','region','country','friends')),
  scope_id      UUID,                          -- city/region/country id; NULL for global/friends
  period        TEXT NOT NULL CHECK (period IN ('weekly','monthly','yearly','all_time')),
  metric        TEXT NOT NULL CHECK (metric IN ('xp','visits','reviews','helpful_received','badges')),
  is_active     BOOLEAN NOT NULL DEFAULT true,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 3.29 `leaderboard_entries`

```sql
CREATE TABLE leaderboard_entries (
  leaderboard_id UUID NOT NULL REFERENCES leaderboards(id) ON DELETE CASCADE,
  user_id        UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  score          BIGINT NOT NULL,
  rank_cached    INTEGER,
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (leaderboard_id, user_id)
);
CREATE INDEX idx_lbe_top ON leaderboard_entries(leaderboard_id, score DESC);
```

Postgres is the durable source of truth; Redis sorted set is the live cache. See §9.

### 3.30 `leaderboard_snapshots`

```sql
CREATE TABLE leaderboard_snapshots (
  id              UUID PRIMARY KEY DEFAULT uuidv7(),
  leaderboard_id  UUID NOT NULL REFERENCES leaderboards(id) ON DELETE CASCADE,
  period_start    TIMESTAMPTZ NOT NULL,
  period_end      TIMESTAMPTZ NOT NULL,
  top_n           JSONB NOT NULL,              -- [{user_id, score, rank, display_name_snapshot}]
  total_participants INTEGER NOT NULL,
  frozen_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_lbsnap_lb_time ON leaderboard_snapshots(leaderboard_id, period_end DESC);
```

Frozen at period rollover so "winner of Week 23, 2026" is permanent even if users delete accounts.

### 3.31 `travel_journals`

```sql
CREATE TABLE travel_journals (
  id            UUID PRIMARY KEY DEFAULT uuidv7(),
  owner_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title         TEXT NOT NULL,
  subtitle      TEXT,
  cover_media_id UUID REFERENCES media(id),
  body_lang     TEXT NOT NULL,
  date_start    DATE,
  date_end      DATE,
  visibility    TEXT NOT NULL DEFAULT 'public'
                CHECK (visibility IN ('public','followers','friends','close_friends','private','unlisted_link')),
  share_token   TEXT UNIQUE,                  -- for 'unlisted_link'
  status        TEXT NOT NULL DEFAULT 'draft'
                CHECK (status IN ('draft','published','archived','removed')),
  region_summary JSONB,                       -- {countries:[...], cities:[...], heritage_count:N}
  like_count    INTEGER NOT NULL DEFAULT 0,
  view_count    INTEGER NOT NULL DEFAULT 0,
  published_at  TIMESTAMPTZ,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at    TIMESTAMPTZ
);
CREATE INDEX idx_journals_owner_pub ON travel_journals(owner_id, published_at DESC) WHERE status='published';
CREATE INDEX idx_journals_public ON travel_journals(published_at DESC) WHERE status='published' AND visibility='public';
```

### 3.32 `journal_entries`

```sql
CREATE TABLE journal_entries (
  id            UUID PRIMARY KEY DEFAULT uuidv7(),
  journal_id    UUID NOT NULL REFERENCES travel_journals(id) ON DELETE CASCADE,
  author_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  entry_date    DATE,
  heritage_id   UUID REFERENCES heritage(id),    -- nullable; entry may not be tied to one site
  position      INTEGER NOT NULL,                -- ordering within journal
  blocks        JSONB NOT NULL,                  -- block-based content: [{type:'paragraph',text:'...'},{type:'media',media_id:...}]
  word_count    INTEGER NOT NULL DEFAULT 0,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_jentry_journal_pos ON journal_entries(journal_id, position);
```

Block-based content (Notion/Outline-style) over single-blob markdown so that AI can re-translate per block, references to media stay typed, and inline reactions per block are possible in v2.

### 3.33 `journal_collaborators`

```sql
CREATE TABLE journal_collaborators (
  journal_id    UUID NOT NULL REFERENCES travel_journals(id) ON DELETE CASCADE,
  user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role          TEXT NOT NULL CHECK (role IN ('owner','editor','contributor','viewer')),
  invited_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  accepted_at   TIMESTAMPTZ,
  PRIMARY KEY (journal_id, user_id)
);
```

### 3.34 `group_trips`

```sql
CREATE TABLE group_trips (
  id            UUID PRIMARY KEY DEFAULT uuidv7(),
  owner_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title         TEXT NOT NULL,
  description   TEXT,
  date_start    DATE,
  date_end      DATE,
  status        TEXT NOT NULL DEFAULT 'planning'
                CHECK (status IN ('planning','in_progress','completed','cancelled','archived')),
  invite_code   TEXT UNIQUE NOT NULL,           -- short code for joining
  max_members   SMALLINT NOT NULL DEFAULT 50,
  itinerary_version BIGINT NOT NULL DEFAULT 0,  -- monotonic; bumped on every itinerary edit
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 3.35 `group_trip_members`

```sql
CREATE TABLE group_trip_members (
  trip_id       UUID NOT NULL REFERENCES group_trips(id) ON DELETE CASCADE,
  user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role          TEXT NOT NULL CHECK (role IN ('owner','admin','editor','viewer')),
  joined_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_at  TIMESTAMPTZ,
  PRIMARY KEY (trip_id, user_id)
);
```

**Authority model for itinerary edits:** owner + admin can edit any item; editor can edit own items + propose; viewer is read-only. Anti-griefing: only owner can remove other members.

### 3.36 `group_trip_items`

```sql
CREATE TABLE group_trip_items (
  id              UUID PRIMARY KEY DEFAULT uuidv7(),
  trip_id         UUID NOT NULL REFERENCES group_trips(id) ON DELETE CASCADE,
  day_number      SMALLINT NOT NULL,            -- 1..N
  position        INTEGER NOT NULL,
  heritage_id     UUID REFERENCES heritage(id),
  custom_place_name TEXT,                       -- if not a known heritage
  custom_lat      DOUBLE PRECISION,
  custom_lng      DOUBLE PRECISION,
  scheduled_start TIMESTAMPTZ,
  scheduled_end   TIMESTAMPTZ,
  notes           TEXT,
  created_by      UUID NOT NULL REFERENCES users(id),
  updated_by      UUID NOT NULL REFERENCES users(id),
  -- CRDT fields for last-writer-wins per field:
  field_clocks    JSONB NOT NULL DEFAULT '{}'::jsonb,
  -- e.g. {"notes":{"actor":"...","ts":"..."}, "scheduled_start":{...}}
  version         BIGINT NOT NULL DEFAULT 1,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at      TIMESTAMPTZ
);
CREATE INDEX idx_gti_trip_day ON group_trip_items(trip_id, day_number, position);
```

See §10 for sync/CRDT details.

### 3.37 `group_trip_chat`

```sql
CREATE TABLE group_trip_chat (
  id            UUID PRIMARY KEY DEFAULT uuidv7(),
  trip_id       UUID NOT NULL REFERENCES group_trips(id) ON DELETE CASCADE,
  user_id       UUID REFERENCES users(id) ON DELETE SET NULL,  -- nullable for system messages
  message_type  TEXT NOT NULL CHECK (message_type IN ('text','media','system','itinerary_change')),
  body          TEXT,
  media_id      UUID REFERENCES media(id),
  context       JSONB,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at    TIMESTAMPTZ
);
CREATE INDEX idx_gtc_trip_time ON group_trip_chat(trip_id, created_at DESC) WHERE deleted_at IS NULL;
```

### 3.38 `ugc_submissions` (polymorphic supertable)

```sql
CREATE TABLE ugc_submissions (
  id              UUID PRIMARY KEY DEFAULT uuidv7(),
  user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  content_type    TEXT NOT NULL CHECK (content_type IN ('review','comment','photo','video','journal','journal_entry')),
  content_id      UUID NOT NULL,
  user_trust_tier TEXT NOT NULL,               -- snapshot of Agent 2's user_trust_scores tier at submit time
  region_id       UUID,                        -- where content is geo-attached (Agent 1)
  status          TEXT NOT NULL DEFAULT 'queued'
                  CHECK (status IN ('queued','auto_approved','awaiting_human','approved','rejected','removed','shadow_banned')),
  ai_score        NUMERIC(5,4),                -- from Agent 3
  ai_decision     TEXT,                        -- 'approve','reject','escalate'
  policy_id       UUID REFERENCES moderation_policies(id),
  submitted_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  resolved_at    TIMESTAMPTZ
);
CREATE INDEX idx_ugc_status_time ON ugc_submissions(status, submitted_at);
CREATE INDEX idx_ugc_user ON ugc_submissions(user_id, submitted_at DESC);
```

### 3.39 `moderation_queue`

```sql
CREATE TABLE moderation_queue (
  id              UUID PRIMARY KEY DEFAULT uuidv7(),
  submission_id   UUID NOT NULL UNIQUE REFERENCES ugc_submissions(id) ON DELETE CASCADE,
  priority        SMALLINT NOT NULL DEFAULT 5,  -- 1 (highest) .. 10
  lane            TEXT NOT NULL,                 -- 'ai_review','human_general','human_cultural','human_safety','appeal'
  assigned_to     UUID REFERENCES users(id),     -- moderator user id
  assigned_at     TIMESTAMPTZ,
  sla_due_at      TIMESTAMPTZ NOT NULL,
  enqueued_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_modq_lane_priority ON moderation_queue(lane, priority, sla_due_at)
  WHERE assigned_to IS NULL;
```

### 3.40 `moderation_actions`

```sql
CREATE TABLE moderation_actions (
  id              UUID PRIMARY KEY DEFAULT uuidv7(),
  submission_id   UUID NOT NULL REFERENCES ugc_submissions(id) ON DELETE CASCADE,
  actor_type      TEXT NOT NULL CHECK (actor_type IN ('system','ai','moderator','admin','user_self')),
  actor_id        UUID,                          -- nullable for system/ai
  action          TEXT NOT NULL,                 -- 'approve','reject','remove','shadow_ban','restore','escalate','unfreeze'
  reason_code     TEXT,
  notes           TEXT,
  policy_id       UUID REFERENCES moderation_policies(id),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_modact_submission ON moderation_actions(submission_id, created_at);
```

Append-only audit log.

### 3.41 `moderation_policies` (admin-configurable)

```sql
CREATE TABLE moderation_policies (
  id              UUID PRIMARY KEY DEFAULT uuidv7(),
  code            TEXT NOT NULL UNIQUE,
  content_type    TEXT NOT NULL,                 -- 'review','comment','photo','video','journal'
  region_id       UUID,                          -- nullable = global
  user_trust_tier TEXT,                          -- nullable = all tiers
  mode            TEXT NOT NULL CHECK (mode IN ('pre_mod','post_mod','ai_gated')),
  ai_approve_threshold NUMERIC(4,3) DEFAULT 0.90,
  ai_reject_threshold  NUMERIC(4,3) DEFAULT 0.20,
  human_lane      TEXT NOT NULL DEFAULT 'human_general',
  sla_minutes     INTEGER NOT NULL DEFAULT 240,
  is_active       BOOLEAN NOT NULL DEFAULT true,
  effective_from  TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_modpol_lookup ON moderation_policies(content_type, region_id, user_trust_tier, is_active);
```

Embodiment of §43: admin picks pre/post/AI-gated per content × region × tier.

### 3.42 `reports`

```sql
CREATE TABLE reports (
  id              UUID PRIMARY KEY DEFAULT uuidv7(),
  reporter_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  target_type     TEXT NOT NULL CHECK (target_type IN ('review','comment','media','journal','journal_entry','user','heritage_fact')),
  target_id       UUID NOT NULL,
  reason_code     TEXT NOT NULL,                 -- 'spam','nsfw','hate','misinfo','wrong_geotag','copyright','cultural_insensitive','impersonation','other'
  reason_text     TEXT,
  status          TEXT NOT NULL DEFAULT 'open'
                  CHECK (status IN ('open','under_review','resolved','dismissed')),
  submission_id   UUID REFERENCES ugc_submissions(id),  -- linked if creates new mod work
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (reporter_id, target_type, target_id, reason_code)  -- de-dupe spam reports
);
CREATE INDEX idx_reports_target ON reports(target_type, target_id, status);
```

Threshold-triggered: N distinct reports of same reason auto-escalates priority.

### 3.43 `report_resolutions`

```sql
CREATE TABLE report_resolutions (
  report_id       UUID PRIMARY KEY REFERENCES reports(id) ON DELETE CASCADE,
  resolver_id     UUID REFERENCES users(id),
  outcome         TEXT NOT NULL CHECK (outcome IN ('upheld','dismissed','removed','warning_issued','user_banned')),
  moderation_action_id UUID REFERENCES moderation_actions(id),
  notes           TEXT,
  resolved_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 3.44 `auto_moderation_results` (Agent 3 link)

```sql
CREATE TABLE auto_moderation_results (
  submission_id   UUID PRIMARY KEY REFERENCES ugc_submissions(id) ON DELETE CASCADE,
  ai_job_id       UUID NOT NULL,                 -- → Agent 3's ai_moderation_jobs.id
  nsfw_score      NUMERIC(4,3),
  violence_score  NUMERIC(4,3),
  hate_score      NUMERIC(4,3),
  spam_score      NUMERIC(4,3),
  geotag_valid    BOOLEAN,
  language_detected TEXT,
  duplicate_of    UUID,                          -- if perceptual-hash match found (Agent 4)
  cultural_flags  JSONB,                         -- {region:'sa', concern:'religious-image'}
  raw_payload     JSONB,
  scored_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 3.45 `content_quality_scores`

```sql
CREATE TABLE content_quality_scores (
  content_type    TEXT NOT NULL,
  content_id      UUID NOT NULL,
  quality_score   NUMERIC(5,4) NOT NULL,
  helpful_score   NUMERIC(5,4),
  recency_score   NUMERIC(5,4),
  authority_score NUMERIC(5,4),                  -- author trust contribution
  spam_score      NUMERIC(5,4),
  computed_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (content_type, content_id)
);
```

Recomputed nightly + on-event (new helpful vote, etc.).

### 3.46 `helpfulness_scores` (review-specific roll-up; denormalized from `review_helpful_votes`)

```sql
CREATE TABLE helpfulness_scores (
  review_id       UUID PRIMARY KEY REFERENCES reviews(id) ON DELETE CASCADE,
  helpful_count   INTEGER NOT NULL DEFAULT 0,
  unhelpful_count INTEGER NOT NULL DEFAULT 0,
  wilson_lower    NUMERIC(6,5),                  -- Wilson lower bound of helpful ratio
  brigade_flag    BOOLEAN NOT NULL DEFAULT false,
  computed_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Wilson score is the right ranking signal for "helpful ratio with low n" — beats raw average decisively.

### 3.47 `spam_signals`

```sql
CREATE TABLE spam_signals (
  id              UUID PRIMARY KEY DEFAULT uuidv7(),
  user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  signal_type     TEXT NOT NULL,                 -- 'velocity','repetition','link_density','reused_text','foreign_geo'
  weight          NUMERIC(4,3) NOT NULL,
  context         JSONB,
  observed_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_spam_user_time ON spam_signals(user_id, observed_at DESC);
```

Aggregated into a rolling user-level spam score that feeds Agent 2's `user_trust_scores`.

### 3.48 `vote_brigading_signals`

```sql
CREATE TABLE vote_brigading_signals (
  id              UUID PRIMARY KEY DEFAULT uuidv7(),
  target_type     TEXT NOT NULL,
  target_id       UUID NOT NULL,
  detected_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  window_seconds  INTEGER NOT NULL,
  vote_burst      INTEGER NOT NULL,
  unique_ips      INTEGER NOT NULL,
  unique_devices  INTEGER NOT NULL,
  graph_edges_shared INTEGER,                     -- voters share follow graph clusters
  recommendation  TEXT NOT NULL CHECK (recommendation IN ('ignore','dampen','revert','review'))
);
CREATE INDEX idx_brigade_target ON vote_brigading_signals(target_type, target_id);
```

### 3.49 `device_fingerprints_link` (sock-puppet suspicion graph)

```sql
CREATE TABLE device_fingerprints_link (
  user_id_a       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  user_id_b       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  device_fingerprint_id UUID NOT NULL,            -- → Agent 2
  confidence      NUMERIC(4,3) NOT NULL,
  first_seen      TIMESTAMPTZ NOT NULL,
  last_seen       TIMESTAMPTZ NOT NULL,
  PRIMARY KEY (user_id_a, user_id_b, device_fingerprint_id),
  CHECK (user_id_a < user_id_b)
);
CREATE INDEX idx_dfl_a ON device_fingerprints_link(user_id_a);
CREATE INDEX idx_dfl_b ON device_fingerprints_link(user_id_b);
```

Derived from Agent 2's raw fingerprint observations: pairs of users that have used the *same* fingerprint. Used to dampen mutual upvotes (you can't make your sock-puppet "helpful" you) and detect XP-farming rings.

### 3.50 `gamification_anti_abuse_rules`

```sql
CREATE TABLE gamification_anti_abuse_rules (
  id              UUID PRIMARY KEY DEFAULT uuidv7(),
  code            TEXT NOT NULL UNIQUE,
  rule_dsl        JSONB NOT NULL,
  -- Example DSL:
  -- { "type":"velocity", "event":"heritage_visited",
  --   "max_per_window": 8, "window_minutes": 60, "action":"freeze_xp" }
  -- { "type":"geofence_violation", "max_distance_meters":500, "action":"reject" }
  -- { "type":"sockpuppet_helpful_chain", "min_confidence":0.85, "action":"dampen_score" }
  is_active       BOOLEAN NOT NULL DEFAULT true,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 3.51 `notification_triggers_map` (Agent 7 contract)

```sql
CREATE TABLE notification_triggers_map (
  id              UUID PRIMARY KEY DEFAULT uuidv7(),
  event_type      TEXT NOT NULL,                 -- 'follow_received','review_replied','badge_earned',...
  channel         TEXT NOT NULL CHECK (channel IN ('push','email','telegram','in_app')),
  template_code   TEXT NOT NULL,
  default_enabled BOOLEAN NOT NULL DEFAULT true,
  user_pref_key   TEXT NOT NULL,
  rate_limit_per_user_per_day INTEGER NOT NULL DEFAULT 50,
  UNIQUE (event_type, channel)
);
```

Declarative table consumed by Agent 7's dispatcher; Social/Gamification layer simply emits semantic events and this table maps them to channels.

---

## 4. Activity Feed Architecture

**Decision: hybrid push-pull with whale opt-out from push.**

### 4.1 Write path (action happens)

1. User performs action → service inserts row into `activity_events`.
2. Outbox row enqueued for Celery `fanout_activity` worker.
3. Worker reads `activity_events` row, looks up actor:
   - If actor is in `whale_users` AND `fanout_strategy='pull'` → no fanout writes happen.
   - Else → SELECT all `follower_id` from `follows WHERE followee_id = actor` AND merge with `feed_subscriptions WHERE subject_type='user' AND subject_id = actor`.
   - Filter recipients by `block_list`, `mutes`, visibility rules.
   - Bulk INSERT into `activity_fanout` (chunks of 5000 with `ON CONFLICT DO NOTHING`).
4. Triggers Agent 7 notifications via the events bus only for **high-signal events** (badge earned for a friend, friend posted a journal, etc.) — not every reaction.

### 4.2 Read path (user opens feed)

```
GET /feed → 
  1. Pull last 50 push-delivered items from `activity_fanout` for recipient_id.
  2. SELECT whales the user follows.
  3. For each whale, pull last 5 events from `activity_events WHERE actor_id IN whales AND created_at > floor`.
  4. Merge + sort by created_at DESC.
  5. Apply final filters (re-check visibility, block_list).
  6. Return.
```

This bounds the read amplification: at most `N_whales_followed × 5` extra DB rows. Most users follow < 20 whales.

### 4.3 Why hybrid (whale problem)

A pure push model would mean a 2M-follower influencer's review triggers 2M `activity_fanout` INSERTs — a sustained write storm bringing down Postgres. Pure pull would mean every feed read fans out an `IN (followee_list)` query that times out for users following 5K+ accounts.

Hybrid balances: regular users (most actions, low follower counts) get instant push-delivered feeds; whales (rare in count, high amplification) are pulled on read.

The threshold (5000) is in `settings` table (Agent 6), tunable as the platform grows.

### 4.4 Visibility re-check at read time

The push-time visibility check is best-effort. Things change: a user is blocked *after* a fanout. Therefore the read path always re-applies block/mute/visibility — this is cheap because the lists are small and cached.

### 4.5 Ranking (v1: chronological; v2: score-ranked)

v1 returns strict reverse-chronological — matches user mental model and avoids ranking-induced "the algorithm is broken" complaints in early adoption. v2 adds optional ranked feed with `score = recency_decay × actor_affinity × event_type_weight × content_quality_score`.

---

## 5. Gamification Anti-Abuse

### 5.1 Idempotency at the ledger level

Every `xp_events.idempotency_key` follows the pattern:

| Reason | Key pattern | Effective window |
|---|---|---|
| `visit_heritage` | `visit:{user_id}:{heritage_id}:{date_local}` | Once per local day |
| `first_visit` | `first_visit:{user_id}:{heritage_id}` | Lifetime |
| `review` | `review:{review_id}` | Once per review |
| `review_helpful_received` | `helpful:{review_id}:{voter_user_id}` | Once per (review, voter) |
| `referral` | `referral:{inviter_id}:{invitee_id}` | Once |
| `streak_milestone` | `streak:{user_id}:{milestone}` | Once per milestone |

`UNIQUE(user_id, idempotency_key)` makes double-award literally impossible at the DB layer. The application never has to "remember if it already awarded".

### 5.2 Velocity limits

`gamification_anti_abuse_rules` row of type `velocity` is evaluated by a worker before any XP commits:

```
Rule: visit_heritage max 8 per 60-minute rolling window
→ COUNT xp_events WHERE user_id = X AND reason_code='visit_heritage' AND awarded_at > now() - 1h
→ if >= 8 → write spam_signal AND insert xp_event with delta=0 and reason='velocity_throttled'
```

Tunable thresholds avoid hardcoding (§17/§24 philosophy).

### 5.3 Geofence validation

`check_in` event requires:
1. GPS coordinate from device
2. Distance to `heritage.coordinates` < `gamification_anti_abuse_rules['geofence_default'].max_distance_meters` (default 500m)
3. GPS accuracy < 100m

Failure → reject XP, log `spam_signal{type:'foreign_geo'}`.

### 5.4 Multi-account / sock-puppet detection

Cross-agent link: Agent 2 owns `device_fingerprints`. We materialize `device_fingerprints_link` (§3.49) as a derived "users sharing a fingerprint" graph. When user A's review gets a helpful vote from user B and `(A,B) ∈ device_fingerprints_link` with confidence > 0.8, the vote is logged but does NOT increment `helpful_count`. The user sees their vote (so they don't realize they're caught), but it's silently dampened.

Same rule applies to XP-from-friend-actions (e.g. referral): suspected sock-puppet referrals award 0 XP and emit a spam signal.

### 5.5 XP clawback

When abuse is confirmed (admin or sufficient signal aggregation), a **negative** `xp_events` row is inserted with `reason_code='anti_cheat_clawback'` and `context.original_event_id`. `xp_balances` self-heals from the next refresh. No deletion ever happens to the audit trail.

### 5.6 Anti-cheat for streaks

- `streak_events.event_date` is the user's *local* date; computed from device timezone at submission. The server stores `timezone_anchor` per user. Changing timezone more than once per 24h freezes the streak (logged in `spam_signals`) until reviewed.
- A "skipped day due to legitimate travel" is forgivable: `freeze_credits` (Duolingo pattern) consumed automatically on missed day; admin can grant or sell.
- The DST/timezone-jump edge case: if previous `last_active_date` is "yesterday" in BOTH old and new timezones, the streak survives. If it's "yesterday" in only one, the streak survives with a 1-credit consumption.

---

## 6. Moderation Pipeline State Machine

### 6.1 States

```
[submitted] 
   ↓ (always)
[queued: ai_review]
   ↓ Agent 3 returns ai_score & decision
   ├─ score ≥ policy.ai_approve_threshold AND no cultural_flag → [auto_approved] → [approved]
   ├─ score ≤ policy.ai_reject_threshold → [rejected] (with appeal option)
   └─ otherwise → [awaiting_human] (queued in moderation_queue with lane)
                     ↓ moderator action
                     ├─ approve → [approved]
                     ├─ reject  → [rejected]
                     ├─ remove  → [removed]
                     ├─ shadow-ban → [shadow_banned]
                     └─ escalate → [awaiting_human] (different lane)
```

### 6.2 Mode resolution

For each submission, resolve effective `moderation_policy` by:
1. Match `content_type` + `region_id` + `user_trust_tier` (most specific).
2. Fall back to `content_type` + `region_id`.
3. Fall back to `content_type` global default.

Policy `mode` determines:
- **`pre_mod`**: content invisible until `status='approved'`.
- **`post_mod`**: content visible immediately at `status='queued'`; if rejected, moved to `[removed]`.
- **`ai_gated`**: content visible iff AI auto-approved; else hidden pending human.

### 6.3 Lane prioritization

`moderation_queue.priority`:

| Priority | Trigger |
|---|---|
| 1 (highest) | Confirmed CSAM/violence flag from Agent 3; legal-hold reports |
| 2 | Reports with ≥10 distinct reporters in 1 hour |
| 3 | High-trust user content needing only spot-check; suspected vote-brigade |
| 4 | New user first 5 submissions (gate-keeping) |
| 5 | Default |
| 7 | Appeals (slower lane) |
| 9 | Cultural-sensitivity review (regional moderators) |

Lanes (`human_safety`, `human_cultural`, `human_general`, `appeal`) route to staff with appropriate language/region expertise.

### 6.4 SLAs

| Content type | Lane | SLA |
|---|---|---|
| Photo/video (active visible) | human_safety | 15 min |
| Review | human_general | 4 h |
| Comment | human_general | 4 h |
| Journal entry | human_general | 24 h |
| Appeal | appeal | 48 h |
| Cultural-sensitivity | human_cultural | 24 h |

Configurable per `moderation_policies.sla_minutes`. Breach emits PagerDuty + admin alert.

### 6.5 Trust-gate

`user_trust_tier` (mirrored from Agent 2's `user_trust_scores`):
- `new` (< 7 days, < 5 contributions) → forced into stricter policies
- `regular` → default policies apply
- `trusted` (per §11 "Trusted Contributor") → post-moderation default; auto-approve threshold relaxed
- `expert` (e.g., academic partner) → very high auto-approve

---

## 7. Multi-Dimensional Ratings

### 7.1 Schema

`reviews.rating_overall` is the *computed* overall; the *truth* is in `review_ratings` (one row per dimension). Calculation:

```
rating_overall = SUM(rating * weight) / SUM(weight)
                 for each (review_id, dimension_id) ∈ review_ratings
```

Where `weight` comes from `review_dimensions.weight` (admin-tunable).

### 7.2 Aggregation across users (heritage-level)

For each heritage, the public-facing "ratings breakdown" is computed:

```sql
SELECT 
  rd.code,
  AVG(rr.rating) AS avg_rating,
  COUNT(*) AS n,
  -- Bayesian smoothing with global prior
  (SUM(rr.rating) + C * mu) / (COUNT(*) + C) AS bayes_rating
FROM review_ratings rr
JOIN reviews r ON r.id = rr.review_id
JOIN review_dimensions rd ON rd.id = rr.dimension_id
WHERE r.heritage_id = $1 AND r.status = 'published'
GROUP BY rd.code;
```

Bayesian smoothing (with C=10, mu=global mean per dimension) is crucial: a single 5-star rating on a new heritage must not show "5.0 stars". The smoothing makes the displayed rating converge to the global prior when `n` is small.

### 7.3 Materialized aggregates

`heritage_rating_aggregates` (owned by Agent 1; this layer just reads it via heritage service). Refresh policy: incremental on every review status change + nightly full recompute.

### 7.4 Display

Mobile UI renders 4 horizontal bars (one per dimension); overall rating is the prominent number. The Bayesian smoothing means new sites display a "?" or muted rating until n ≥ 5.

---

## 8. Threaded Comments

### 8.1 Choice: `ltree` (Postgres native)

Compared:

| Approach | Pro | Con |
|---|---|---|
| Adjacency list (`parent_id`) | Simple inserts | "Get subtree" is recursive CTE, slow |
| Materialized path (TEXT) | Single SELECT for subtree | No native ops, must parse |
| `ltree` (Postgres) | Native operators (`<@`, `~`), GIST index, in-DB subtree queries | Postgres-locked |
| Nested set | Fast reads | Catastrophic writes |
| Closure table | Flexible | Extra table; O(N) inserts |

**Chosen: `ltree` + denormalized `depth`.** Postgres lock-in is fine — §15 already commits to Postgres + pgvector as primary; portability concerns are mitigated by the repository pattern (`CommentRepository.get_subtree()` hides the implementation).

### 8.2 Depth limit

`CHECK (depth BETWEEN 0 AND 6)`. Six levels handles every realistic conversation (Reddit caps at deep but collapses; we cap hard at 6). Beyond depth 6, "reply" UX collapses to "reply to thread" (target the root).

### 8.3 Path generation

On insert:
```sql
INSERT INTO comments (id, parent_id, path, depth, ...)
VALUES (
  $new_id,
  $parent_id,
  COALESCE((SELECT path FROM comments WHERE id = $parent_id), '') || $new_id::text,
  COALESCE((SELECT depth FROM comments WHERE id = $parent_id) + 1, 0),
  ...
)
```

UUIDv7 string form is compatible with `ltree` labels after replacing `-` with `_`.

### 8.4 Subtree query

```sql
SELECT * FROM comments
WHERE path <@ $root_path
  AND status='published'
ORDER BY path;
```

GIST index on `path` makes this O(log n) at the index level. Pagination by `path` lexicographic order preserves tree ordering.

### 8.5 Pre-computed reply counts

`reply_count` is denormalized on the parent and maintained by trigger; avoids `COUNT(*) WHERE parent_id=...` on every comment render.

---

## 9. Leaderboards at Scale

### 9.1 Two-tier storage

- **Redis sorted set** (`ZADD lb:{leaderboard_id} score user_id`) is the *online* store. All reads (`ZREVRANGE`, `ZRANK`) hit Redis. Sub-millisecond.
- **Postgres `leaderboard_entries`** is the *durable* store. Reconstructible from `xp_events`; survives Redis flush.

### 9.2 Write path

On every `xp_events` insert affecting a metric:
1. Trigger inserts/updates `leaderboard_entries`.
2. Async worker emits Redis `ZADD` for each active leaderboard the user is in.
3. Rate-limited: bursts of XP coalesce to one Redis write per user per leaderboard per 5s.

### 9.3 Period rollover

A scheduled job at period boundary (e.g. Monday 00:00 UTC for weekly):
1. Lock leaderboard.
2. Read top-N from Redis.
3. Insert into `leaderboard_snapshots`.
4. Trigger Agent 7 notifications for top finishers (rewards, badges).
5. Reset metric for new period: rebuild from `xp_events` filtered to new window.

### 9.4 Friends-only leaderboard

Cannot precompute every user's friend-leaderboard. Instead, compute on read:

```sql
WITH friends AS (
  SELECT user_id_b AS friend_id FROM friendships WHERE user_id_a = $me
  UNION
  SELECT user_id_a AS friend_id FROM friendships WHERE user_id_b = $me
  UNION SELECT $me
)
SELECT user_id, weekly_xp
FROM xp_balances
WHERE user_id IN (SELECT friend_id FROM friends)
ORDER BY weekly_xp DESC
LIMIT 50;
```

This is a tens-of-rows query (most users have < 200 friends); fully indexed on `xp_balances(user_id)`; sub-10ms. No global sorted set needed.

### 9.5 City leaderboard

`leaderboards.scope_type='city'` row per city. Membership inferred from user's home city (Agent 2's `users.home_city_id`) OR per-city visit count (top-N visitors of the month for "Samarkand top explorers"). Redis key includes city: `lb:city:{city_id}:weekly`.

### 9.6 Anti-cheat at leaderboard level

Users flagged with `spam_signals` aggregate score > threshold are excluded from public leaderboards. They still see their own rank (shadow-leaderboard) — abusers don't realize.

---

## 10. Travel Journals + Group Travel

### 10.1 Travel journals (single-author or invited multi-author)

- Block-based content (Notion-style) enables rich mixed media without HTML sanitization headaches.
- Visibility levels (`public`, `followers`, `friends`, `close_friends`, `private`, `unlisted_link`) match Instagram/Strava norms.
- Multi-author via `journal_collaborators`; conflicts on `journal_entries` are rare (entries are typically distinct days), but field-level CRDT clocks (similar to `group_trip_items`) handle simultaneous edits.

### 10.2 Group trips — sync model

**Authority:**
- Owner: full control, can change membership.
- Admin: edit any item, no membership control.
- Editor: create items, edit own items, propose changes to others' items.
- Viewer: read-only.

**Sync mechanism:**
- Client edits a `group_trip_items` row → WebSocket message to backend.
- Backend applies CRDT field-level last-writer-wins:
  - Each field has a logical clock `{actor, lamport_ts}` in `field_clocks` JSONB.
  - Incoming edit accepted iff `lamport_ts` > current OR (`lamport_ts == current` AND `actor` lexicographically greater).
- Successful application → bump `group_trips.itinerary_version` (monotonic).
- Broadcast diff to all connected members via Redis pub/sub → WebSocket.

**Why field-level LWW (not full document CRDT):**
- 90% of edits are to different fields of different items — conflicts essentially never happen.
- Full CRDT libraries (Yjs/Automerge) are powerful but add client SDK weight and a learning curve unjustified at this granularity.
- LWW is debuggable, server-authoritative, and `field_clocks` provides full audit.

**Offline reconciliation:**
- Client buffers edits offline (Isar) with local Lamport stamps.
- On reconnect, sends batch with stamps.
- Server applies in stamp order; broadcasts merged state.
- Client reconciles against authoritative state.

**Hard constraints (not CRDT'd):**
- Day ordering must be valid (`day_number ≥ 1`).
- Per-day position uniqueness enforced at commit via re-sequencing (server re-numbers positions if collision detected; clients refresh).

### 10.3 Group trip chat

Plain WebSocket-fanout chat backed by `group_trip_chat`. Media messages reference Agent 4's `media.id` (must be moderation-cleared). System messages auto-emitted on itinerary changes ("Aziz added Registan to Day 2").

---

## 11. Notification Triggers (Agent 7 link)

Events that fire push (via `notification_triggers_map`):

| Event | Default channels | Rationale |
|---|---|---|
| `follow_received` | push, in_app | High-affinity |
| `friend_invitation_received` | push, in_app | Action-required |
| `friend_invitation_accepted` | push | Affinity loop |
| `review_replied` | push, in_app | Author affinity |
| `comment_replied` | push, in_app | Conversation continuity |
| `mention_in_comment` | push, in_app | Direct addressing |
| `reaction_received` | in_app only by default; batched daily push | Avoid notification spam |
| `badge_earned` | push, in_app | Reward dopamine |
| `level_up` | push, in_app | Reward dopamine |
| `streak_at_risk` (23h since last action) | push | Retention loop |
| `streak_broken` | push (gentle) | Re-engagement |
| `friend_passed_you_in_leaderboard` | push | Social competition |
| `group_trip_invitation` | push, in_app | Action-required |
| `group_trip_itinerary_changed` | in_app, batched push hourly | High-frequency, dampened |
| `group_trip_chat_mention` | push | Direct addressing |
| `journal_published_by_friend` | in_app, daily-digest email | Content discovery |
| `moderation_decision` (your content) | push, in_app | Transparency |

Per-user preferences override via `notification_triggers_map.user_pref_key`. Agent 7 enforces rate limits (`rate_limit_per_user_per_day`).

---

## 12. Reputation & Trust Loops (Agent 2 link)

### 12.1 Outputs we emit (consumed by Agent 2)

This layer continuously emits signals that update `users.user_trust_scores` (owned by Agent 2):

| Signal | Effect on trust score |
|---|---|
| Review approved by moderation | +small |
| Review received helpful votes (Wilson-bounded) | +medium |
| Badge earned (especially `rare`+) | +small |
| Streak ≥ 30 days | +medium |
| Report against user upheld | -large |
| `spam_signals` aggregate exceeds threshold | -large |
| Sock-puppet network confirmed | -critical (auto-ban candidate) |
| Vote-brigade ringleader detected | -critical |
| Account age + consistent quality | +slow accrual |

### 12.2 Inputs we consume

We read `user_trust_tier` from Agent 2 (cached, refreshed at submission time into `ugc_submissions.user_trust_tier`). This is the **snapshot at the time of submission**, not the current trust — preventing "earn trust → flood spam → trust drops but spam was post-moderated" attacks.

### 12.3 Trust-gated capabilities

| Tier | Capability |
|---|---|
| `new` | Pre-mod for all UGC; rate limit 5 reviews/day; cannot react to receive XP for 24h |
| `regular` | Post-mod for low-risk content; standard rates |
| `trusted` | Post-mod for almost everything; can apply for `expert` |
| `expert` | Same as `trusted` + admin-granted; can author `journals` with "expert" badge; reviews shown with prominence |

---

## 13. Risks & Open Questions

### 13.1 Active risks

1. **Whale fanout cascades.** Even with whale opt-out from push, a celebrity gaining 100K followers in a week stresses follow inserts and feed reads. Mitigation: shard `follows` by `followee_id`; cache follower-count and serve approximate counts.

2. **Vote-brigade detection false positives.** Legitimate viral content (e.g., a beautiful Registan photo featured on Instagram) looks like a brigade. Mitigation: distinguish *organic* (unique IPs, geographically distributed, no follow-graph clustering) from *brigade* (small set of devices, follow-clustered, time-clustered).

3. **Cultural-context moderation.** A photo of a mosque interior is fine in Uzbekistan, possibly sensitive in some other Muslim regions; depiction of historical Bukharan figures may be celebrated by some, contested by others. Mitigation: `moderation_policies` keyed on `region_id`; regional moderator pool (`human_cultural` lane); AI provides `cultural_flags` but never auto-rejects on cultural axis.

4. **Multi-language spam.** Spam detector trained on English misses Uzbek/Russian/Chinese spam. Mitigation: per-language NLP models in Agent 3; spam_signals re-tuned per language; heuristic signals (link density, repetition, velocity) are language-agnostic and serve as fallback.

5. **Timezone-jump streak abuse.** Already mitigated (§5.6), but adversarial users will try edge cases. Open: how to handle a user who legitimately travels across multiple zones in a week (Silk Road tour!). Possibly relax streak rules during detected travel.

6. **`xp_events` table growth.** At 10M MAU averaging 5 XP-earning actions/day = 50M rows/day = 18B rows/year. Mitigated by partitioning by `awarded_at` month + automated archival of >2-year-old partitions to cold storage; queries always include time bounds.

7. **CRDT edge cases in group trips.** Field-level LWW can produce surprising results (one user's edit "wins" silently). Mitigation: surface "last edited by X at T" in UI on every field; show toast notification when your concurrent edit was overwritten.

8. **Badge criteria DSL versioning.** When admin changes criteria for an existing badge, do already-earned badges get revoked? Decision: no — earned badges are immutable; new criteria apply only to future earnings. Bump `badge_types.released_at` to mark version boundaries.

9. **Sock-puppet pre-detection.** We detect sock-puppets reactively. A determined attacker with fresh devices/IPs evades. Mitigation: layered (Agent 2 device-fingerprinting, ML behavioral models in v2, KYC for high-stakes contributors).

10. **Leaderboard gaming via region selection.** A user could move to an inactive city to dominate its leaderboard. Mitigation: city assignment is sticky and requires real activity (visits) within that city's geofence to count toward city leaderboard.

### 13.2 Open questions for owner

- **Q1:** What's the **streak freeze economics**? Free? Sold for IAP? Earned by referral? — affects `freeze_credits` issuance policy.
- **Q2:** Should journals be **monetizable** (Substack-style paid journals)? — adds payment schema dependencies.
- **Q3:** **Group trip max size** — 50 is the schema default; is 200 needed for school trips / B2B tour groups?
- **Q4:** **Comment edit window** — unlimited, or 15 minutes (Twitter-style)? Currently unlimited with `edited_count` shown.
- **Q5:** **Delete vs anonymize** when a user invokes GDPR right-to-be-forgotten — their reviews stay (anonymized as "Former Member") or vanish entirely? §36 implies deletion; community would prefer anonymization. Need legal review.
- **Q6:** **Badge rarity inflation** — should admin auto-rebalance criteria when too many users earn a "legendary" badge? Suggest yes, with periodic audit.
- **Q7:** **Cross-account merging** — user signs in via Telegram then via Google, both produce accounts. Who owns reviews/XP/badges when merged? Suggest "absorb into older account; ledger keeps actor history".

---

*Architecture v1.0 | Agent 5 of 8 | 2026-05-18*
