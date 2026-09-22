# SilkLens Database Schema Summary

Generated from 52 Alembic migration files.  
Source: `/home/nsn/Workspace/silklens/services/api/alembic/versions/`  
Date: 2026-05-18

---

## Architecture Notes

- All PKs use UUIDv7 (`gen_uuid_v7()`) for time-ordered B-tree locality.
- i18n text columns use `jsonb` with BCP-47 keys (`{"en":"…","uz":"…","ru":"…"}`).
- `users`, `user_profiles`, `sessions`, `refresh_tokens`, `user_roles`, `user_identities`, `user_emails`, `user_phones` are LIST-partitioned by `residency_region` (`uz/eu/us/global`) for data-residency compliance.
- High-volume event/log tables are RANGE-partitioned monthly or weekly.
- Two schemas: `public` (app data) and `audit` (append-only audit log).

---

## Identity & Auth

## users
**Purpose:** Root user table — every authenticated or guest account. Partitioned by residency_region for PII data-residency compliance (Uzbek PD-law).
**Key columns:** id (uuid), pub_id (text, URL-safe public handle), tenant_id, residency_region, password_hash, password_algorithm, status (active/suspended/pending_verification/banned/deleted), is_guest, email_verified_at, phone_verified_at, mfa_enabled, trust_score (0–100), trust_tier (new/regular/trusted/contributor/staff/admin), login_count, last_login_at, last_active_at, preferred_locale, preferred_timezone, created_at, updated_at, deleted_at, anonymized_at
**Relations:** belongs to tenants; has many user_profiles, user_identities, user_emails, user_phones, sessions, user_roles, reviews, badges, xp_events, follows, subscriptions

## user_profiles
**Purpose:** User-visible profile data — display name, avatar, bio, interests. Partitioned by residency_region.
**Key columns:** user_id, residency_region, tenant_id, display_name (citext), full_name, avatar_url, bio, country_code, city, interests (text[]), stats (jsonb), created_at, updated_at
**Relations:** belongs to users (composite FK user_id+residency_region)

## oauth_providers
**Purpose:** Admin-managed catalog of enabled auth providers (Google, Apple, Telegram, etc.). Toggling a provider is a DB row update, not a deploy.
**Key columns:** id, slug, display_name (jsonb), kind (oauth2/oidc/saml/telegram/custom), is_enabled, client_id, authorize_url, token_url, scopes (text[]), icon_url, sort_order
**Relations:** has many user_identities; has one oauth_provider_secrets

## user_identities
**Purpose:** Binding between a user and an OAuth/OIDC provider. Partitioned by residency_region.
**Key columns:** id, user_id, residency_region, tenant_id, provider_id, provider_subject, email_at_link, access_token, refresh_token, token_expires_at, linked_at, last_used_at
**Relations:** belongs to users, belongs to oauth_providers

## user_emails
**Purpose:** Multi-email support with primary-email flag, verification tracking, and Apple Hide-My-Email detection.
**Key columns:** id, user_id, residency_region, email (citext), is_primary, verified_at, bounce_count, is_forwarded
**Relations:** belongs to users

## user_phones
**Purpose:** Multi-phone support with verification and primary-phone flag.
**Key columns:** id, user_id, residency_region, phone_e164, country_code, is_primary, verified_at
**Relations:** belongs to users

## sessions
**Purpose:** Active login sessions tied to a device fingerprint. Revocable tokens.
**Key columns:** id, user_id, residency_region, tenant_id, device_fingerprint_id, ip_address, user_agent, issued_at, last_seen_at, expires_at, revoked_at
**Relations:** belongs to users, belongs to device_fingerprints; has many refresh_tokens

## refresh_tokens
**Purpose:** HMAC-stored opaque refresh tokens with family-based rotation to detect replay attacks.
**Key columns:** id, session_id, user_id, residency_region, token_hash (bytea), family_id, replaced_by_id, expires_at, used_at, revoked_at
**Relations:** belongs to sessions, belongs to users

## device_fingerprints
**Purpose:** Device-level fingerprint hash for sock-puppet detection and abuse signaling.
**Key columns:** id, fingerprint_hash, platform_hint (ios/android/web/desktop), first_seen_at, last_seen_at, seen_count, is_flagged, associated_user_count
**Relations:** referenced by sessions

---

## RBAC & Access Control

## permissions
**Purpose:** Atomic permission strings in format `<resource>:<action>` (e.g. `heritage:create`).
**Key columns:** id, slug, description, created_at
**Relations:** has many role_permissions

## roles
**Purpose:** Named bags of permissions. Can be platform-wide (tenant_id NULL) or tenant-scoped.
**Key columns:** id, slug, display_name (jsonb), description, is_system, tenant_id, created_at
**Relations:** has many role_permissions; has many user_roles

## role_permissions
**Purpose:** M:N join between roles and permissions.
**Key columns:** role_id, permission_id, created_at
**Relations:** belongs to roles, belongs to permissions

## user_roles
**Purpose:** Scoped role assignments per user. Supports expiry and revocation. Partitioned by residency_region.
**Key columns:** id, user_id, residency_region, role_id, scope_tenant_id, scope_region, granted_by, granted_at, expires_at, revoked_at
**Relations:** belongs to users, belongs to roles

---

## Admin Configuration

## tenants
**Purpose:** White-label tenant root. Default tenant (well-known UUID) serves single-tenant deployments automatically.
**Key columns:** id, slug, display_name (jsonb), status (active/suspended/archived), plan_tier, owner_user_id, parent_tenant_id, metadata (jsonb), created_at, updated_at, deleted_at
**Relations:** has one tenant_branding; has many tenant_domains, users, heritage_objects, products

## tenant_branding
**Purpose:** Per-tenant dynamic branding (logo, colors, fonts). Read on app startup via the public branding endpoint.
**Key columns:** tenant_id (PK), app_name (jsonb), logo_url, logo_dark_url, primary_color, accent_color, splash_url, font_family, theme_mode_default (light/dark/system/national/high_contrast), extra (jsonb)
**Relations:** belongs to tenants (1:1)

## tenant_domains
**Purpose:** Custom domain-to-tenant mapping verified via DNS TXT challenge.
**Key columns:** id, tenant_id, domain (citext), is_primary, verified_at
**Relations:** belongs to tenants

## system_settings
**Purpose:** Admin-driven typed key/value runtime configuration per tenant. Cached in Redis with event-driven invalidation.
**Key columns:** id, tenant_id, key, value (jsonb), value_type (string/int/float/bool/json/duration/color/url), scope (tenant/global/user_overrideable), description, is_secret, requires_role
**Relations:** belongs to tenants

## feature_flags
**Purpose:** Per-tenant feature flags with percentage/allowlist rollout strategies. NULL tenant_id = platform default.
**Key columns:** id, tenant_id, flag_key, enabled, rollout_kind (boolean/percentage/user_allowlist/user_denylist/jsonl_rules), rollout_value (jsonb), description, owner
**Relations:** belongs to tenants

## controlled_vocabularies
**Purpose:** Runtime-extensible enum replacement. Every place a Postgres ENUM would be used is a row here instead.
**Key columns:** id, slug, display_name (jsonb), description, is_extensible, is_hierarchical
**Relations:** has many vocabulary_terms

## vocabulary_terms
**Purpose:** Individual terms within a controlled vocabulary (e.g. heritage kinds: mosque, madrasa, mausoleum).
**Key columns:** id, vocabulary_id, slug, display_name (jsonb), description (jsonb), parent_id, sort_order, is_active
**Relations:** belongs to controlled_vocabularies; self-referential parent_id

---

## Heritage Domain

## heritage_objects
**Purpose:** Polymorphic root table for every cultural heritage site/object. The core content entity of SilkLens.
**Key columns:** id, pub_id (URL-safe slug), tenant_id, kind_slug (monument/mosque/madrasa/mausoleum/caravanserai/archaeological_site/museum/palace/intangible_practice), name (jsonb i18n), summary_md (jsonb), description_md (jsonb), tags (text[]), country_code, admin_path (ltree), latitude, longitude, elevation_m, period_start_year, period_end_year, unesco_inscription_year, status (draft/review/published/archived), hero_media_id, confidence_score (0–100), admin_level_id, revision, created_at, updated_at, deleted_at
**Relations:** belongs to tenants; has many heritage_aliases, heritage_revisions, heritage_facts, heritage_relations, media_assets (via hero_media_id), reviews, comments, events, unesco_inscriptions, embeddings

## heritage_aliases
**Purpose:** Multi-lingual historical names and transliterations for a heritage object.
**Key columns:** id, heritage_id, alias, language_tag, script, kind (historical/transliteration/colloquial/official/misspelling), source, confidence
**Relations:** belongs to heritage_objects

## heritage_revisions
**Purpose:** Append-only bi-temporal audit log of every change to a heritage object.
**Key columns:** id, heritage_id, revision (int), action (insert/update/soft_delete/restore), actor_user_id, before (jsonb), after (jsonb), diff (jsonb), comment, valid_from
**Relations:** belongs to heritage_objects

## heritage_facts
**Purpose:** Atomic provenance-tagged claims about a heritage object. Supports disputed facts and multiple sources.
**Key columns:** id, heritage_id, predicate (dot-notation e.g. `name.uz`, `founded_year`), object_value (jsonb), object_text, language_tag, confidence (0–100), is_winning, is_disputed, asserted_by, asserted_at, superseded_at
**Relations:** belongs to heritage_objects; has many fact_provenance

## heritage_provenance
**Purpose:** Source catalog for heritage facts (Wikipedia, UNESCO, expert, user_upload, AI, etc.).
**Key columns:** id, slug, kind (wikipedia/wikidata/wikimedia_commons/unesco/openstreetmap/scholarly_article/book/government/museum/expert/user_upload/ai_generated/manual_entry/partner_api/field_observation), citation (jsonb), url, license, trust_score (0–100), retrieved_at
**Relations:** referenced by fact_provenance

## fact_provenance
**Purpose:** M:N join between heritage facts and their provenance sources with per-link confidence.
**Key columns:** fact_id, provenance_id, citation_detail, page_or_locator, confidence
**Relations:** belongs to heritage_facts, belongs to heritage_provenance

## heritage_relations
**Purpose:** Typed graph edges between heritage objects forming the knowledge graph layer.
**Key columns:** id, from_heritage_id, to_heritage_id, relation_type (part_of/contains/near/restored_from/replaced/inspired_by/predecessor_of/successor_of/associated_with), confidence, distance_m, asserted_by
**Relations:** both ends belong to heritage_objects

## unesco_inscriptions
**Purpose:** UNESCO WHS / tentative / ICH official records with criteria, status, and area details.
**Key columns:** id, heritage_id, inscription_id (official UNESCO number), inscription_year, in_danger_since, criteria (text[]), category (cultural/natural/mixed), status (inscribed/tentative/delisted/in_danger), area_hectares, buffer_zone_hectares, is_transboundary, transboundary_countries, statement (jsonb), official_url
**Relations:** belongs to heritage_objects

## events
**Purpose:** Narrative lifecycle milestones for heritage sites (built, destroyed, renovated, discovered, etc.).
**Key columns:** id, heritage_id, name (jsonb), kind (built/destroyed/renovated/discovered/excavated/abandoned/rededicated/inscribed/restored), event_year, event_date, uncertainty_years, narrative_md (jsonb), actor_person, source_id, confidence
**Relations:** belongs to heritage_objects, references heritage_provenance

---

## Geography & Taxonomy

## geographic_admin_levels
**Purpose:** ltree-based geographic hierarchy: continent → country → region → city → district → site. Enables sub-tree queries.
**Key columns:** id, parent_id, level (0–5), admin_level_type (continent/country/region/city/district/site), code, name (jsonb), aliases (text[]), country_code, path (ltree), centroid_lat, centroid_lng, polygon (geography or text WKT), timezone, population, elevation_m, external_ids (jsonb)
**Relations:** self-referential parent_id; referenced by countries, cities, heritage_objects

## countries
**Purpose:** ISO 3166-1 country reference with Silk Road corridor flag and centroid coordinates.
**Key columns:** id, iso2, iso3, iso_numeric, name (jsonb), capital, region, subregion, lat, lng, area_km2, population, currency_code, languages (text[]), calling_code, flag_emoji, admin_level_id, is_unesco_party, is_silk_road
**Relations:** belongs to geographic_admin_levels; has many cities

## cities
**Purpose:** Major urban hubs cross-referenced to the geographic hierarchy. Seeded with Silk Road cities (Samarkand, Bukhara, Khiva, Xi'an, Istanbul, Isfahan, etc.).
**Key columns:** id, admin_level_id, country_code, slug, name (jsonb), lat, lng, population, is_capital, is_silk_road, timezone, external_ids (jsonb)
**Relations:** belongs to geographic_admin_levels, belongs to countries

## historical_periods
**Purpose:** Named cultural epochs with year ranges and regional scope (e.g. Timurid, Samanid, Soviet).
**Key columns:** id, slug, name (jsonb), description (jsonb), start_year, end_year, region_scope, parent_period_id, sort_order, color_hex
**Relations:** self-referential parent_period_id; has many architectural_styles, dynasties, heritage_period_assoc

## architectural_styles
**Purpose:** Hierarchical architectural style catalog (e.g. Islamic → Timurid Architecture).
**Key columns:** id, slug, name (jsonb), description (jsonb), period_id, parent_style_id, region_scope
**Relations:** belongs to historical_periods; self-referential parent_style_id; has many heritage_style_assoc

## dynasties
**Purpose:** Ruling dynasties linked to historical periods with succession chain.
**Key columns:** id, slug, name (jsonb), description (jsonb), start_year, end_year, period_id, region_scope, capital_city_slug, successor_id
**Relations:** belongs to historical_periods; self-referential successor_id; has many heritage_dynasty_assoc

## heritage_period_assoc
**Purpose:** M:N link between heritage objects and historical periods with role context (built/used/abandoned/restored/destroyed).
**Key columns:** id, heritage_id, period_id, role, confidence, note (jsonb), created_by
**Relations:** belongs to heritage_objects, belongs to historical_periods

## heritage_style_assoc
**Purpose:** M:N link between heritage objects and architectural styles.
**Key columns:** id, heritage_id, style_id, is_primary, confidence, note (jsonb)
**Relations:** belongs to heritage_objects, belongs to architectural_styles

## heritage_dynasty_assoc
**Purpose:** M:N link between heritage objects and dynasties with role context.
**Key columns:** id, heritage_id, dynasty_id, role (built_under/flourished_under/destroyed_under/restored_under/patronized_by/associated_with), confidence, note (jsonb)
**Relations:** belongs to heritage_objects, belongs to dynasties

---

## Media

## media_assets
**Purpose:** Polymorphic source-of-truth row for every uploaded file. MinIO stores bytes; this table stores meaning.
**Key columns:** id, tenant_id, owner_user_id, kind (image/video/audio_tts/audio_human/video_hls/ar_marker/ar_overlay/3d_model/document), mime_type, byte_size, content_hash (sha256 bytea), perceptual_hash, perceptual_hash_bucket (top-16-bits for near-dedup), storage_bucket, storage_key, status (pending/scanning/processing/ready/quarantined/deleted), license_id, original_filename, exif (jsonb), width, height, duration_ms, language_tag
**Relations:** belongs to tenants; belongs to users (owner); has many media_variants, media_transcoding_jobs, media_lifecycle_events, signed_url_grants, media_usage_log; has one media_licenses, media_perceptual_hashes

## media_variants
**Purpose:** Derived renditions of a media asset (thumb_256, medium_720, avif_1080, hls_720, mp3_128k, etc.). Regeneratable.
**Key columns:** id, asset_id, variant_name, mime_type, byte_size, width, height, duration_ms, storage_location_id, storage_key, generated_at
**Relations:** belongs to media_assets, belongs to media_storage_locations

## media_storage_locations
**Purpose:** Admin-managed catalog of object-store buckets (MinIO/S3/R2). Adding a new CDN is a row insert.
**Key columns:** id, slug, name (jsonb), kind (minio/s3/r2/local), endpoint, bucket_name, region, public_read, is_active
**Relations:** has many media_variants

## media_licenses
**Purpose:** Per-asset license assignment with frozen ToS snapshot at upload time (CC0/CC-BY/proprietary/UGC default, etc.).
**Key columns:** asset_id (PK), license_type_id, holder, source_url, attribution_required, granted_to_tenant_id, snapshot_terms (jsonb), declared_by_user_id, expires_at
**Relations:** belongs to media_assets (1:1), belongs to media_license_types

## media_license_types
**Purpose:** Admin vocabulary of media license types (cc0/cc_by/cc_by_sa/cc_by_nc/public_domain/proprietary/ugc_default/b2b_exclusive).
**Key columns:** id, slug, name (jsonb), url, requires_attribution, allows_commercial, share_alike, allows_derivatives, is_active
**Relations:** has many media_licenses

## media_attributions
**Purpose:** Attribution chain displayed as "Photo: A. Karimov / Wikimedia Commons / CC BY-SA 4.0". Required by CC-BY-SA.
**Key columns:** id, asset_id, line_order, line_text, source_url, language_tag, role
**Relations:** belongs to media_assets

## media_copyright_claims
**Purpose:** DMCA-style takedown workflow. Open claims block hard-delete of the asset.
**Key columns:** id, asset_id, claimant_name, claimant_email, complaint_text, evidence_urls (text[]), status (submitted/under_review/upheld/dismissed/withdrawn), submitted_at, resolved_at, resolved_by_user_id
**Relations:** belongs to media_assets (ON DELETE RESTRICT)

## media_transcoding_presets
**Purpose:** Admin catalog of transcoding presets (imgproxy/ffmpeg args). 8 presets seeded at deploy.
**Key columns:** id, slug, name (jsonb), target_kind, ffmpeg_args (jsonb), imgproxy_args (jsonb), output_mime, max_dim, is_active
**Relations:** has many media_transcoding_jobs

## media_transcoding_jobs
**Purpose:** Celery FSM mirror: pending → processing → done/failed/cancelled.
**Key columns:** id, asset_id, preset_id, status, attempts, worker_id, error, started_at, finished_at, output_variant_id
**Relations:** belongs to media_assets, belongs to media_transcoding_presets, output_variant_id references media_variants

## media_perceptual_hashes
**Purpose:** Near-duplicate detection via pHash with bucket-prefix strategy (O(N/2^16) candidate retrieval).
**Key columns:** asset_id (PK), bucket_16 (smallint), hash_8bytes (bytea), model (phash_64/dhash_64/ahash_64/whash_64), computed_at
**Relations:** belongs to media_assets (1:1)

---

## AI / ML Infrastructure

## ai_providers
**Purpose:** Admin catalog of AI providers (Anthropic, OpenAI, local GPU). Switching models requires no deploy.
**Key columns:** id, slug, name (jsonb), kind (local_gpu/cloud_api), base_url, supports_streaming, requires_credit_card, status (active/disabled/deprecated)
**Relations:** has many ai_models

## ai_models
**Purpose:** Capability-scoped model catalog (vision/text/tts/translation/embedding/asr/moderation).
**Key columns:** id, slug, provider_id, name (jsonb), task_type, modality (text[]), context_window, max_output_tokens, supports_tools, cost_per_1k_input_tokens, cost_per_1k_output_tokens, is_enabled, sort_order
**Relations:** belongs to ai_providers; has many ai_model_versions, ai_fallback_chain_steps

## ai_model_versions
**Purpose:** Concrete weight versions of a model. is_current flag determines which version is active. Embedding rows carry `dimensions`.
**Key columns:** id, model_id, version, dimensions, is_current, released_at, deprecated_at, artifact_uri, artifact_sha256
**Relations:** belongs to ai_models; referenced by embeddings, ai_generations, ai_cache

## ai_fallback_chains
**Purpose:** Ordered fallback chains per task type (vision: llava-34b → internvl → gpt-4o, etc.).
**Key columns:** id, slug, task_type, name (jsonb), is_active
**Relations:** has many ai_fallback_chain_steps

## ai_fallback_chain_steps
**Purpose:** Individual steps in a fallback chain with latency/cost constraints and skip conditions.
**Key columns:** id, chain_id, step_order, model_id, max_latency_ms, max_cost_per_call, conditions (jsonb)
**Relations:** belongs to ai_fallback_chains, belongs to ai_models

## prompt_templates
**Purpose:** Admin-managed prompt templates with system/user slots and output schema definition.
**Key columns:** id, slug, name (jsonb), system_prompt, user_template, output_schema (jsonb), task_type, is_active
**Relations:** has many prompt_template_versions

## ai_generations
**Purpose:** Immutable log of every AI call. Range-partitioned monthly. Source of truth for reproducibility.
**Key columns:** id, tenant_id, user_id, model_version_id, prompt_template_id, task_type, input_hash, input_summary, output_text, output_jsonb, input_tokens, output_tokens, latency_ms, cost_estimate, status (ok/error/timeout/safety_blocked), trace_id, created_at
**Relations:** referenced by ai_cost_ledger

## ai_token_usage
**Purpose:** Per (user, model, day) usage roll-up. Range-partitioned monthly. Feeds quota enforcement.
**Key columns:** user_id, model_id, day, input_tokens, output_tokens, cost, request_count
**Relations:** aggregates from ai_generations

## ai_cost_ledger
**Purpose:** Append-only billing source for Agent 6. Supports reseller markups via billable_to_tenant_id.
**Key columns:** id, tenant_id, user_id, model_id, kind, tokens_in, tokens_out, cost, billable_to_tenant_id, created_at
**Relations:** belongs to ai_models, belongs to tenants

## ai_cache
**Purpose:** Deterministic prompt deduplication. Redis mirrors hot keys; this table survives Redis flush.
**Key columns:** input_hash (bytea PK), model_version_id, output_jsonb, hit_count, last_hit_at, created_at, expires_at
**Relations:** belongs to ai_model_versions

## ai_moderation_results
**Purpose:** Per-artifact AI moderation verdict. Polymorphic via target_kind.
**Key columns:** id, target_kind (heritage_description/review/user_upload_image/user_upload_text/chat_input), target_id, model_version_id, classification (safe/nsfw/violence/spam/hate/self_harm/prompt_injection/multi), score, labels (jsonb), action_taken (allowed/queued_for_review/auto_rejected/quarantined)
**Relations:** belongs to ai_model_versions

## embedding tables (4 tables)
**Purpose:** Separated vector tables per (target, model_family, dimension) with HNSW indexes (m=16, ef_construction=200).
- `embeddings_heritage_text_e5_1024` — per-heritage, per-language text embeddings (multilingual-e5-large, 1024-dim)
- `embeddings_heritage_image_clip_768` — heritage hero image embeddings (CLIP ViT-L/14, 768-dim)
- `embeddings_media_image_clip_768` — per-asset CLIP image embeddings for visual search
- `embeddings_chunks_text_e5_1024` — RAG corpus chunks (heritage/review/article text)
**Relations:** belong to heritage_objects and/or media_assets; belong to ai_model_versions

---

## Social Graph

## follows
**Purpose:** Directed follow graph (follower → followee). Asymmetric.
**Key columns:** follower_user_id, follower_residency, followee_user_id, followee_residency, created_at
**Relations:** both sides belong to users

## friendships
**Purpose:** Symmetric friendship edges with canonical ordering (user_a_id < user_b_id) to eliminate duplicates.
**Key columns:** user_a_id, user_a_residency, user_b_id, user_b_residency, status (invited/accepted/blocked), invited_at, accepted_at
**Relations:** both sides belong to users

## friend_invitations
**Purpose:** Outbound friend invitations including external email targets (for users not yet on SilkLens).
**Key columns:** id, from_user_id, to_user_id, to_email (citext, nullable), token (unique), status (pending/accepted/declined/expired/revoked), expires_at
**Relations:** belongs to users (from); optionally belongs to users (to)

## block_list
**Purpose:** Hard suppression — hides content in both directions; triggers async unfollow.
**Key columns:** blocker_user_id, blocker_residency, blocked_user_id, blocked_residency, reason, created_at
**Relations:** both sides belong to users

## mutes
**Purpose:** Soft suppression — muter stops seeing muted user's content; muted user is unaware.
**Key columns:** muter_user_id, muted_user_id, reason, expires_at, created_at
**Relations:** both sides belong to users

## close_friends
**Purpose:** Instagram-style inner circle for restricted visibility on journals/posts.
**Key columns:** user_id, close_user_id, created_at
**Relations:** both sides belong to users

## whale_users
**Purpose:** High-follower users excluded from push fanout — their feed is pulled on read instead.
**Key columns:** user_id, residency_region, threshold_reached_at, follower_count_at_threshold, fanout_mode (pull/push/hybrid), last_recomputed_at
**Relations:** belongs to users

## activity_events
**Purpose:** Append-only social verb log (actor verb object [target]). Source of truth for the social feed. Range-partitioned monthly.
**Key columns:** id, actor_user_id, actor_residency, verb (created/reviewed/visited/liked/followed/earned_badge/joined_trip/commented/reacted/photographed/journal_published), object_kind, object_id, target_kind, target_id, visibility (public/followers/friends/close_friends/private), payload (jsonb), created_at
**Relations:** belongs to users (actor)

## activity_fanout
**Purpose:** Pre-delivered feed items per recipient. Range-partitioned monthly. No FK to activity_events (cross-partition FK forbidden).
**Key columns:** id, recipient_user_id, recipient_residency, event_id, event_created_at, actor_user_id, verb, delivered_at, read_at
**Relations:** belongs to users (recipient)

---

## Reviews & UGC

## reviews
**Purpose:** One review per (user, heritage). Contains markdown body, rating, helpfulness votes. Core engagement driver.
**Key columns:** id, tenant_id, heritage_id, user_id, residency_region, language_tag, title, body_md, average_rating (1–5, computed), visited_at, is_published, machine_translated_from, helpful_count, unhelpful_count, report_count, edited_count, quality_score, created_at, updated_at, deleted_at
**Relations:** belongs to heritage_objects, belongs to users; has many review_ratings, review_translations, review_helpful_votes

## review_ratings
**Purpose:** Per-dimension scores for a review (history_accuracy, photo_quality, access, value_for_money, atmosphere, family_friendliness).
**Key columns:** review_id, dimension_slug, value (smallint)
**Relations:** belongs to reviews, belongs to review_dimensions

## review_dimensions
**Purpose:** Admin catalog of rating dimensions. Adding a new dimension is a row insert.
**Key columns:** id, slug, name (jsonb), description (jsonb), scale_min, scale_max, sort_order, weight, is_active
**Relations:** has many review_ratings

## review_translations
**Purpose:** Cached NLLB translation output for reviews in other languages.
**Key columns:** review_id, language_tag, body_md, machine_translated, engine, confidence
**Relations:** belongs to reviews

## review_helpful_votes
**Purpose:** Helpful/unhelpful votes on reviews with device fingerprint for brigading detection.
**Key columns:** review_id, voter_user_id, voter_residency, vote (-1 or +1), voted_at, device_fingerprint_id, ip_inet
**Relations:** belongs to reviews, belongs to users

## comments
**Purpose:** Threaded polymorphic comments using ltree path for efficient subtree queries. Depth capped at 6.
**Key columns:** id, tenant_id, parent_kind (heritage/review/photo/comment/trip/journal/journal_entry), parent_id, author_user_id, author_residency, body_md, language_tag, depth (0–6), path (ltree), status (pending_moderation/published/removed/shadow_banned), is_pinned, reply_count, reaction_count, edited_count
**Relations:** belongs to users (author); polymorphic parent via parent_kind+parent_id

## reactions
**Purpose:** Polymorphic emoji reactions on any content type. A user can apply multiple reaction types to the same target.
**Key columns:** id, reactor_user_id, reactor_residency, target_kind (review/comment/photo/journal/journal_entry/heritage), target_id, reaction_type_slug
**Relations:** belongs to users, belongs to reaction_types

## reaction_types
**Purpose:** Admin-extensible emoji catalog (like/love/wow/sad/angry/helpful/informative/beautiful). Adding a new emoji is a row insert.
**Key columns:** slug (PK), emoji, name (jsonb), sort_order, is_active
**Relations:** has many reactions

## ugc_submissions
**Purpose:** Single polymorphic queue for every UGC artefact awaiting AI + human moderation decision.
**Key columns:** id, tenant_id, kind (review/photo/video/edit_suggestion/heritage_alias/comment/journal/journal_entry), target_id, author_user_id, author_residency, payload (jsonb), status (pending/auto_approved/awaiting_human/approved/rejected/quarantined/shadow_banned), user_trust_tier_snapshot, auto_moderation_score (0–1), ai_decision (approve/reject/escalate), submitted_at, decided_at, decided_by, sla_due_at
**Relations:** belongs to users (author)

---

## Gamification

## badge_types
**Purpose:** Admin catalog of badge definitions with criterion DSL interpreted by the BadgeEvaluator worker.
**Key columns:** id, slug, category (exploration/social/content/streak/seasonal/curator/expert), name (jsonb), description (jsonb), icon_url, criterion_kind (count_visited/count_reviewed/streak_days/country_count/category_completion/special_event/count_photos/count_helpful_received/count_followers), criterion_params (jsonb), rarity (common/rare/epic/legendary), xp_reward, is_active, released_at, retired_at
**Relations:** has many user_badges

## user_badges
**Purpose:** Earned badges per user with partial-completion progress state in JSONB.
**Key columns:** user_id, badge_type_id, awarded_at, source_event_id, progress (jsonb), revoked_at
**Relations:** belongs to users, belongs to badge_types

## xp_events
**Purpose:** Append-only XP ledger. Every +XP and –XP (clawback) is a row. Idempotency key prevents XP farming. Range-partitioned monthly.
**Key columns:** id, user_id, residency_region, source_kind (visit/review/photo/badge/streak/referral/correction/admin_grant/clawback/helpful_received/velocity_throttled), source_id, delta (int, can be negative), idempotency_key, context (jsonb), created_at
**Relations:** belongs to users

## xp_balances
**Purpose:** Materialised XP projection (current/lifetime/weekly/monthly/yearly). Maintained by trigger + nightly reconciliation.
**Key columns:** user_id (PK), residency_region, current_xp, lifetime_xp, weekly_xp, monthly_xp, yearly_xp, last_event_at, refreshed_at
**Relations:** belongs to users (1:1)

## levels
**Purpose:** Admin-defined level thresholds with XP requirements and unlocked perks.
**Key columns:** number (smallint PK), slug, name (jsonb), xp_required, perks (jsonb), is_active
**Relations:** referenced by users via xp_balances.current_xp

## streaks
**Purpose:** Materialised daily activity streak state per user.
**Key columns:** user_id (PK), residency_region, current_streak, longest_streak, last_active_date, timezone_anchor, freeze_credits, broken_at
**Relations:** belongs to users; has many streak_events

## streak_events
**Purpose:** One row per (user, local_date). Rebuilds streak from contiguous date runs ending at today.
**Key columns:** user_id, event_date (date PK component), residency_region, source (open/visit/review/photo/manual_freeze/referral), source_event_id, recorded_at
**Relations:** belongs to users

## leaderboards
**Purpose:** Admin-configured leaderboards by scope×period×metric.
**Key columns:** id, slug, name (jsonb), scope (global/country/city/friends/region), scope_ref, period (daily/weekly/monthly/yearly/alltime), metric (xp/visits/reviews/badges/helpful_received/photos), is_active
**Relations:** has many leaderboard_snapshots

## leaderboard_snapshots
**Purpose:** Frozen end-of-period rankings. display_name_snapshot preserves winner identity after account deletion.
**Key columns:** leaderboard_id, period_end (date), rank (int), user_id, residency_region, metric_value, display_name_snapshot, frozen_at
**Relations:** belongs to leaderboards, belongs to users

---

## Billing & Monetization

## currencies
**Purpose:** ISO 4217 catalog with decimal-places metadata for provider boundary conversion (Stripe=cents, Payme=tiyin).
**Key columns:** code (char(3) PK), name (jsonb), symbol, decimal_places, is_active
**Relations:** referenced by prices, payment_intents, payments, invoices

## products
**Purpose:** Top-level SKU entities (subscription/one_time/credits/marketplace_item) per tenant.
**Key columns:** id, tenant_id, slug, name (jsonb), description (jsonb), kind, is_active
**Relations:** belongs to tenants; has many product_plans

## product_plans
**Purpose:** Billing variants of a product (monthly/quarterly/yearly/lifetime/one_time).
**Key columns:** id, tenant_id, product_id, slug, name (jsonb), billing_period, trial_days, is_default, sort_order, is_active
**Relations:** belongs to products; has many plan_features, prices, subscriptions

## feature_keys
**Purpose:** Controlled vocabulary of entitlement primitives (boolean/quota/threshold kinds).
**Key columns:** slug (PK), name (jsonb), description (jsonb), kind (boolean/quota/threshold)
**Relations:** has many plan_features, entitlements

## plan_features
**Purpose:** Admin entitlement matrix: (plan × feature_key) → enabled + limit_value + soft_limit.
**Key columns:** plan_id, feature_key, enabled, limit_value (bigint), soft_limit (bigint)
**Relations:** belongs to product_plans, belongs to feature_keys

## pricing_zones
**Purpose:** Regional PPP groupings for price discrimination (cis/eu/na/sea/latam/mena/oceania).
**Key columns:** id, slug, name (jsonb), country_codes (char(2)[]), default_currency, purchasing_power_index
**Relations:** has many prices

## prices
**Purpose:** Time-windowed price points per (plan, zone, currency). Historical rows never deleted; new rows set effective_until.
**Key columns:** plan_id, pricing_zone_id, currency, effective_from (timestamptz PK component), amount (numeric 20,4), effective_until, is_active
**Relations:** belongs to product_plans, belongs to pricing_zones, belongs to currencies

## subscriptions
**Purpose:** Recurring entitlement contracts. State machine: trial/active/past_due/canceled/expired/paused.
**Key columns:** id, tenant_id, user_id, residency_region, plan_id, status, current_period_start, current_period_end, trial_ends_at, cancel_at_period_end, canceled_at, ended_at
**Relations:** belongs to users, belongs to product_plans; has many subscription_items, subscription_events, payment_intents, invoices

## subscription_events
**Purpose:** Append-only state-transition log for subscriptions. Source of truth for billing analytics.
**Key columns:** id, subscription_id, event (created/trial_started/activated/renewed/upgraded/downgraded/paused/resumed/canceled/refunded/expired), from_status, to_status, payload (jsonb), created_at
**Relations:** belongs to subscriptions

## entitlements
**Purpose:** Derived denormalized (user, feature_key) entitlement cache for <5ms p99 feature checks.
**Key columns:** user_id, residency_region, feature_key (PK composite), granted, limit_value, source (plan/manual_grant/promo/admin), source_id, effective_until
**Relations:** belongs to users, belongs to feature_keys

## payment_methods
**Purpose:** Tokenized payment instruments (NEVER raw PAN). provider_token is opaque vault pointer.
**Key columns:** id, user_id, residency_region, provider (stripe/payme/click/apple_iap/google_iap/paypal), provider_token, kind (card/wallet/bank_transfer/in_app), last4, brand, expires_at, is_default, deleted_at
**Relations:** belongs to users

## payment_intents
**Purpose:** Idempotent charge initiation record. Stores FX snapshot at charge time for accurate refunds.
**Key columns:** id, tenant_id, user_id, subscription_id, idempotency_key (UNIQUE), amount, currency, fx_from_currency, fx_to_currency, fx_captured_at, status (requires_payment/processing/succeeded/canceled/failed), failure_reason
**Relations:** belongs to tenants, belongs to users, belongs to subscriptions; has many payments

## payments
**Purpose:** Provider charge captures. UNIQUE(provider, charge_id) deduplicates webhook replays.
**Key columns:** id, intent_id, provider, provider_charge_id, captured_amount, currency, fee_amount, exchange_rate_at_capture, captured_at
**Relations:** belongs to payment_intents; has many refunds, chargebacks

## invoices
**Purpose:** Accounting records with auto-generated SLN-YYYY-NNNNNNN sequence numbers. Numbers never reused.
**Key columns:** id, tenant_id, user_id, subscription_id, number (UNIQUE, format SLN-YYYY-NNNNNNN), total, currency, status (draft/open/paid/uncollectible/void), period_start, period_end, issued_at, paid_at, pdf_url
**Relations:** belongs to tenants, belongs to users, belongs to subscriptions; has many invoice_lines

## refunds
**Purpose:** Full or partial refund captures linked to the original payment.
**Key columns:** id, payment_id, amount, currency, reason, provider_refund_id, status (pending/succeeded/failed), created_at, processed_at
**Relations:** belongs to payments

## chargebacks
**Purpose:** Disputed transaction tracking through inquiry → disputed → won/lost lifecycle.
**Key columns:** id, payment_id, amount, reason_code, status (inquiry/disputed/won/lost), opened_at, resolved_at
**Relations:** belongs to payments

## dunning_state
**Purpose:** Retry machine state for past_due subscriptions. Idempotent retries with exponential backoff.
**Key columns:** subscription_id (PK), attempts, next_retry_at, failure_reason, last_attempt_at
**Relations:** belongs to subscriptions (1:1)

## trials
**Purpose:** One-free-trial-per-(user, plan) enforcement to prevent trial-stacking abuse.
**Key columns:** id, user_id, residency_region, plan_id, started_at, ends_at, converted_at
**Relations:** belongs to users, belongs to product_plans

---

## Notifications

## notifications
**Purpose:** Logical in-app persistent notifications per user. Partitioned by residency_region.
**Key columns:** id, recipient_user_id, residency_region, template_id, category_slug, title, body_md, action_url, related_object_kind, related_object_id, is_read, read_at, created_at
**Relations:** belongs to users, belongs to notification_templates, belongs to notification_categories

## notification_categories
**Purpose:** Admin vocabulary of notification categories. is_critical=true categories cannot be opted out of.
**Key columns:** slug (PK), name (jsonb), description (jsonb), default_enabled, is_critical
**Relations:** has many notification_templates, notifications, notification_preferences

## notification_templates
**Purpose:** Admin-managed notification templates with A/B variant support and multi-channel delivery.
**Key columns:** id, slug, category_slug, name (jsonb), channels (text[], subset of in_app/email/sms/push), default_priority, is_active
**Relations:** belongs to notification_categories; has many notification_template_versions, notification_template_variants

## notification_preferences
**Purpose:** Per-user × per-category × per-channel opt-in/out. Partitioned by residency_region.
**Key columns:** user_id, residency_region, category_slug, channel (in_app/email/sms/push), enabled
**Relations:** belongs to users, belongs to notification_categories

## push_devices
**Purpose:** Per-device FCM/APNS token registry for push notification delivery. Partitioned by residency_region.
**Key columns:** id, user_id, residency_region, platform (ios/android/web), fcm_token, apns_token, installation_id, last_seen_at, is_active
**Relations:** belongs to users

## email_messages
**Purpose:** Sent email log with provider delivery status. Range-partitioned monthly.
**Key columns:** id, recipient_user_id, to_address, from_address, subject, body_html, body_text, provider, provider_message_id, status (queued/sent/delivered/bounced/failed/complained), sent_at, delivered_at
**Relations:** optionally belongs to users

## sms_messages
**Purpose:** Sent SMS log with cost tracking. Range-partitioned monthly.
**Key columns:** id, recipient_user_id, to_phone, body, provider, provider_message_id, status (queued/sent/delivered/failed/undelivered), segments, cost_estimate, sent_at
**Relations:** optionally belongs to users

## webhooks_outbound
**Purpose:** Partner webhook subscriptions with HMAC secret for signed delivery.
**Key columns:** id, tenant_id, partner_name, url, secret (bytea), events (text[]), is_active
**Relations:** belongs to tenants; has many webhook_deliveries

---

## Virtual Tours (Wave-8)

## virtual_tours
**Purpose:** 3D/WebGL virtual tour catalogue linked to heritage objects. Supports museum walkthroughs, site flythroughs, room explorations, timeline 3D.
**Key columns:** id, heritage_id, tenant_id, slug, title (jsonb), description_md (jsonb), kind (museum_walkthrough/site_flythrough/room_exploration/timeline_3d), status (draft/processing/published/archived), thumbnail_media_id, tour_duration_seconds, viewer_url, embed_code, view_count
**Relations:** belongs to heritage_objects, belongs to tenants; has many virtual_tour_scenes, virtual_tour_progress

## virtual_tour_scenes
**Purpose:** Ordered scenes within a virtual tour with 3D model refs, panorama media, hotspot data, and audio guide.
**Key columns:** id, tour_id, scene_order, title (jsonb), description_md (jsonb), panorama_media_id, model_3d_asset_id, hotspot_data (jsonb array), audio_guide_media_id
**Relations:** belongs to virtual_tours; references media_assets (panorama, model, audio)

## virtual_tour_progress
**Purpose:** Per-user progress tracking within a virtual tour (last scene viewed, completion status).
**Key columns:** user_id, residency_region, tour_id (composite PK), last_scene_order, completed, started_at
**Relations:** belongs to users, belongs to virtual_tours

## virtual_tour_collections
**Purpose:** Thematic playlists/collections of virtual tours (e.g. Ancient Wonders, Silk Road Journey, UNESCO Highlights).
**Key columns:** id, tenant_id, slug, title (jsonb), description_md (jsonb), is_featured, sort_order
**Relations:** belongs to tenants; has many virtual_tour_collection_items

## virtual_tour_collection_items
**Purpose:** M:N ordered join between collections and virtual tours.
**Key columns:** collection_id, tour_id (composite PK), item_order
**Relations:** belongs to virtual_tour_collections, belongs to virtual_tours

---

## Audit & Event Bus

## audit.audit_log
**Purpose:** Append-only tamper-evident audit log with HMAC hash chain and daily Merkle root anchoring. Range-partitioned monthly.
**Key columns:** id, tenant_id, actor_user_id, actor_residency, action, entity_type, entity_id, entity_pub_id, before (jsonb), after (jsonb), details (jsonb), ip_address, user_agent, request_id, trace_id, prev_hash (bytea), row_hash (bytea HMAC-SHA256), created_at
**Relations:** append-only; referenced by domain writes via `app.audit()` function

## audit.audit_anchors
**Purpose:** Daily Merkle roots over audit_log rows, signed by KMS and published to S3 Object Lock + git.
**Key columns:** anchor_date (date PK), tenant_id, row_count, first_row_id, last_row_id, merkle_root (bytea), signature (bytea), signed_by_kid, published_at, external_refs (jsonb)
**Relations:** derived from audit.audit_log

## event_types
**Purpose:** Admin catalog of versioned event names. Validated at emit time to catch typos.
**Key columns:** id, event_name (unique, format `domain.action.vN`), display_name (jsonb), schema_url, retention_days, kafka_topic, downstream_targets (jsonb), is_deprecated
**Relations:** validated against event_outbox via app.emit_event()

## event_outbox
**Purpose:** Transactional outbox — domain writes INSERT here in the same transaction. Celery reaper drains to Redpanda then DELETEs.
**Key columns:** id, tenant_id, event_name, aggregate_type, aggregate_id, payload (jsonb), headers (jsonb), trace_id, scheduled_for, attempts, last_error
**Relations:** references event_types.event_name

## event_log
**Purpose:** Immutable canonical event history. Append-only. Range-partitioned daily. Source of truth for event replay.
**Key columns:** id, tenant_id, event_name, aggregate_type, aggregate_id, payload (jsonb), headers (jsonb), trace_id, published_at
**Relations:** populated from event_outbox by Celery reaper

---

*Total migrations: 52. Tables documented: ~120 (logical) across both schemas.*
