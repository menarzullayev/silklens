# SilkLens — Architecture Document 04
## Media, Files, CDN, AR/3D Assets and Offline Bundles

**Owning agent:** Agent 4 — Media & Storage Architect
**Status:** Draft v1.0
**Date:** 2026-05-18
**Scope:** PostgreSQL metadata layer + MinIO object store + Cloudflare CDN + Celery transcoding pipeline + offline-bundle distribution for the SilkLens cultural-heritage platform.

---

## 1. Domain Analysis

### 1.1 What "media" means in SilkLens

In a generic SaaS product, "media" often degenerates to a single `files` table with a CDN URL column. SilkLens cannot afford that simplification, for five reasons:

1. **Heterogeneity.** A heritage object (e.g. Registan) is described simultaneously by: (a) imported Wikimedia photos (CC-BY-SA), (b) drone-captured originals (proprietary), (c) AI-generated TTS audio in N languages, (d) human-narrated premium audio, (e) 30-second UGC videos, (f) photogrammetry GLB/USDZ models, (g) AR marker images, (h) historical sketches scanned from museum archives, (i) subtitle WebVTT, (j) bitrate-laddered HLS streams. Each subtype has its own pipeline, license, lifecycle and storage tier.

2. **Offline-first imperative.** Per Project-Decisions Q7 the product is designed for tourists with no roaming inside museums and in remote desert sites (Khiva, Marv, Kunya-Urgench). Offline is not a "nice to have"; it is structural. Therefore every media asset must answer at design time: "can this be packed into an offline bundle, at what size budget, and how does a device detect that its packed copy is stale?"

3. **Polymorphic ownership.** A single image can simultaneously belong to a heritage record, a user review, a B2B sponsored listing, an AR overlay, and a souvenir-marketplace product. A naive `owner_id` column collapses this. The domain demands explicit polymorphic linkage with referential discipline.

4. **Legal weight.** Wikimedia CC-BY-SA imposes attribution forever; UGC requires snapshotting the user's license terms at upload; B2B-exclusive material has watermarking and DRM clauses; museum donations have moral-rights clauses. A "license_id" column without an admin-managed vocabulary leaks legal risk into application code.

5. **Deduplication asymmetry.** Exact dedup via SHA-256 is trivial. Perceptual dedup — "this user just uploaded the same photo of Registan that 12,000 other users already uploaded, but cropped 4px and re-encoded by Instagram" — is the actual operational problem and it is not solvable with vanilla Postgres B-tree indexes.

### 1.2 Implication for schema design

These five forces push the schema toward an **asset / variant / lifecycle** triad:

- **`media_assets`** is the polymorphic, source-of-truth row. One per logical asset, immutable identity.
- **`media_variants`** are the derived encodings (thumb / medium / full / AVIF / WebP / HLS rendition / GLB-LOD-2 / USDZ). Many per asset, regeneratable.
- **`media_lifecycle_events`** is the append-only audit log: uploaded, scanned, transcoded, published, watermarked, takedown-pending, archived, purged.

The original blob lives in MinIO; metadata lives in Postgres because (a) we need ACID joins to heritage / user / review tables, (b) full-text search on captions/EXIF, (c) soft-delete with retention, (d) license joins, (e) bundle composition queries. MinIO is the truth for **bytes**; Postgres is the truth for **meaning**.

---

## 2. Entity Discovery Report

The following 30 tables emerged. Tables are grouped by lifecycle phase.

### 2.1 Core asset & variant
- `media_assets` — polymorphic root; one row per logical asset.
- `media_variants` — derived encodings (thumb/medium/full/avif/webp/hls/dash/lod).
- `media_storage_locations` — every physical placement of asset/variant bytes (MinIO bucket, CDN edge cache key, archive tier).
- `media_content_hashes` — sha256 of original byte stream; exact-match dedup.
- `media_perceptual_hashes` — pHash / dHash / aHash / wavelet hash; near-duplicate detection.
- `media_metadata_exif` — extracted EXIF/XMP/IPTC; pre-stripping snapshot.
- `media_lifecycle_events` — append-only state log.

### 2.2 Pipeline & jobs
- `media_transcoding_jobs` — Celery job rows; FSM state.
- `media_transcoding_presets` — admin-managed preset matrix (per device/CDN tier).
- `media_scan_results` — AV scan, NSFW scan, malware scan results.

### 2.3 Type-specific
- `media_audio_tracks` — TTS or human; bitrate; speaker voice; language.
- `media_video_streams` — bitrate ladder, HLS manifest pointer.
- `media_subtitles` — WebVTT / SRT, per language, per track.
- `media_3d_models` — GLB/GLTF/USDZ root.
- `media_3d_lods` — LOD level → variant linkage; triangle-count and texture-resolution metadata.
- `media_ar_anchors` — marker images, ARCloud anchor IDs, GPS-anchored anchors.
- `media_ar_overlays` — composite AR scenes (anchor + 3D + audio).

### 2.4 Legal & licensing
- `license_types` — admin vocabulary (CC0, CC-BY, CC-BY-SA, CC-BY-NC, PD, Proprietary, B2B-Exclusive, UGC-Default, Museum-Custom).
- `media_licenses` — per-asset license assignment + license URL + commercial-use flag.
- `media_attributions` — required attribution chain (Wikimedia author, museum name).
- `media_copyright_claims` — externally raised claims, DMCA channel.
- `media_takedown_requests` — workflow rows for DMCA / GDPR erasure.
- `media_watermark_profiles` — admin presets (text, opacity, font, position).

### 2.5 Polymorphic linkage
- `media_asset_links` — generic (asset_id, entity_type, entity_id, role) — see §4 for trade-off discussion.

### 2.6 Distribution
- `cdn_invalidations` — log of cache-purge requests by URL/tag/zone.
- `signed_url_grants` — per-grant audit of pre-signed URL issuance (URL hash + grantee + TTL + IP).
- `media_usage_log` — origin-hit log for B2B billing and hot-link detection.

### 2.7 Offline bundles
- `offline_bundles` — bundle definition (region/city/heritage-set/language).
- `offline_bundle_versions` — semver-tagged immutable snapshot of bundle contents.
- `offline_bundle_contents` — many-to-many between bundle-version and asset-variant.
- `offline_bundle_downloads` — per-device download record; current installed version.
- `offline_bundle_signatures` — Ed25519 signatures of bundle manifests.

### 2.8 Non-obvious discoveries
Three entities that an inexperienced designer would miss:

1. **`media_perceptual_hashes`** with a `bucket` column (the high-order bits of pHash) — without this column, "find similar" queries are O(N) over every hash; with it, you get O(N/2^k) by pre-bucketing for BK-tree-like behaviour in vanilla Postgres.
2. **`signed_url_grants`** — most teams do not log signed-URL issuance, which makes B2B abuse forensics impossible six months later.
3. **`offline_bundle_signatures`** — without app-side signature verification, an attacker can substitute a malicious bundle on a rooted device and inject prompts into the in-app AI chat.

---

## 3. Full Table-by-Table Specification

> Conventions: `id` = `BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY`. `pub_id` = `UUID DEFAULT gen_random_uuid() UNIQUE NOT NULL` for external exposure (never expose internal `id`). All tables: `created_at`, `updated_at` (`TIMESTAMPTZ NOT NULL DEFAULT now()`); soft delete via `deleted_at TIMESTAMPTZ`. All FK use `ON DELETE RESTRICT` unless noted; cascades are explicit and rare.

### 3.1 `media_assets`

```sql
CREATE TABLE media_assets (
  id              BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  pub_id          UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  asset_kind      TEXT NOT NULL
                    CHECK (asset_kind IN
                      ('image','video','audio','model3d','ar_marker',
                       'ar_overlay_bundle','subtitle','document','archive')),
  mime_type       TEXT NOT NULL,
  origin          TEXT NOT NULL
                    CHECK (origin IN
                      ('wikimedia','ugc','field_trip','partner_api',
                       'ai_generated','b2b_upload','admin_upload',
                       'photogrammetry','sketchfab','open_heritage')),
  original_filename TEXT,
  byte_size       BIGINT NOT NULL CHECK (byte_size > 0),
  width_px        INTEGER,
  height_px       INTEGER,
  duration_ms     INTEGER,            -- audio/video
  framerate       NUMERIC(6,3),       -- video
  color_profile   TEXT,
  channels        SMALLINT,           -- audio
  sample_rate_hz  INTEGER,            -- audio
  primary_language CHAR(3),           -- ISO 639-3 for audio/subtitle
  capture_at      TIMESTAMPTZ,        -- from EXIF DateTimeOriginal
  capture_lat     DOUBLE PRECISION,   -- only if user/admin permits retention
  capture_lng     DOUBLE PRECISION,
  capture_geom    GEOGRAPHY(POINT,4326) GENERATED ALWAYS AS
                    (CASE WHEN capture_lat IS NOT NULL
                          THEN ST_SetSRID(ST_MakePoint(capture_lng,capture_lat),4326)::geography
                          ELSE NULL END) STORED,
  uploaded_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
  uploaded_via    TEXT NOT NULL CHECK (uploaded_via IN
                    ('mobile_app','admin_panel','bulk_import','api_partner','scraper','system')),
  state           TEXT NOT NULL DEFAULT 'pending'
                    CHECK (state IN
                      ('pending','scanning','quarantined','processing',
                       'ready','published','restricted','archived','purged')),
  is_public       BOOLEAN NOT NULL DEFAULT FALSE,
  is_premium      BOOLEAN NOT NULL DEFAULT FALSE,
  is_b2b_exclusive BOOLEAN NOT NULL DEFAULT FALSE,
  is_safe_for_work BOOLEAN NOT NULL DEFAULT TRUE,
  exif_stripped   BOOLEAN NOT NULL DEFAULT FALSE,
  watermark_profile_id BIGINT REFERENCES media_watermark_profiles(id),
  caption_jsonb   JSONB,              -- {iso639_3: text} short captions per language
  alt_text_jsonb  JSONB,              -- a11y per language
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at      TIMESTAMPTZ
);
CREATE INDEX media_assets_kind_state_idx ON media_assets (asset_kind, state) WHERE deleted_at IS NULL;
CREATE INDEX media_assets_uploader_idx   ON media_assets (uploaded_by_user_id) WHERE deleted_at IS NULL;
CREATE INDEX media_assets_capture_geom_idx ON media_assets USING GIST (capture_geom);
CREATE INDEX media_assets_origin_idx     ON media_assets (origin);
CREATE INDEX media_assets_caption_gin    ON media_assets USING GIN (caption_jsonb jsonb_path_ops);
```

Why no FK directly to `heritages`: see §4 (polymorphic linkage).

### 3.2 `media_variants`

```sql
CREATE TABLE media_variants (
  id              BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  asset_id        BIGINT NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
  variant_kind    TEXT NOT NULL
                    CHECK (variant_kind IN
                      ('thumb_64','thumb_256','medium_720','large_1440','full_original',
                       'webp_720','webp_1440','avif_720','avif_1440','jpegxl_1440',
                       'hls_240p','hls_480p','hls_720p','hls_1080p','hls_master',
                       'dash_audio_64k','dash_audio_128k','mp3_128','opus_96',
                       'glb_lod0','glb_lod1','glb_lod2','usdz','draco_glb',
                       'subtitle_vtt','poster_jpg','sprite_sheet')),
  preset_id       BIGINT REFERENCES media_transcoding_presets(id),
  mime_type       TEXT NOT NULL,
  byte_size       BIGINT NOT NULL,
  width_px        INTEGER,
  height_px       INTEGER,
  duration_ms     INTEGER,
  bitrate_kbps    INTEGER,
  triangles       BIGINT,             -- 3D only
  storage_location_id BIGINT NOT NULL REFERENCES media_storage_locations(id),
  cdn_url         TEXT,               -- denormalised; nullable when restricted
  generated_by_job_id BIGINT REFERENCES media_transcoding_jobs(id),
  state           TEXT NOT NULL DEFAULT 'pending'
                    CHECK (state IN ('pending','ready','failed','superseded')),
  superseded_by_id BIGINT REFERENCES media_variants(id),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (asset_id, variant_kind, preset_id) WHERE state = 'ready'
);
CREATE INDEX media_variants_asset_idx ON media_variants (asset_id);
CREATE INDEX media_variants_kind_state_idx ON media_variants (variant_kind, state);
```

### 3.3 `media_storage_locations`

```sql
CREATE TABLE media_storage_locations (
  id              BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  backend         TEXT NOT NULL CHECK (backend IN
                    ('minio_hot','minio_warm','minio_cold','s3_glacier',
                     'cloudflare_r2','bunny_storage','local_fs')),
  bucket          TEXT NOT NULL,
  object_key      TEXT NOT NULL,
  region          TEXT,
  etag            TEXT,
  storage_class   TEXT,               -- e.g. STANDARD, REDUCED, GLACIER
  is_encrypted    BOOLEAN NOT NULL DEFAULT TRUE,
  sse_key_id      TEXT,
  byte_size       BIGINT NOT NULL,
  checksum_sha256 TEXT NOT NULL,
  uploaded_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_verified_at TIMESTAMPTZ,
  state           TEXT NOT NULL DEFAULT 'live'
                    CHECK (state IN ('uploading','live','migrating','archived','deleted')),
  UNIQUE (backend, bucket, object_key)
);
CREATE INDEX storage_loc_checksum_idx ON media_storage_locations (checksum_sha256);
```

### 3.4 `media_content_hashes` — exact-dedup

```sql
CREATE TABLE media_content_hashes (
  asset_id        BIGINT PRIMARY KEY REFERENCES media_assets(id) ON DELETE CASCADE,
  sha256          BYTEA NOT NULL,
  blake3          BYTEA,
  byte_size       BIGINT NOT NULL,
  first_seen_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  duplicate_of_asset_id BIGINT REFERENCES media_assets(id)
);
CREATE UNIQUE INDEX media_content_sha256_idx ON media_content_hashes (sha256);
```

On upload the worker computes `sha256` and probes; if hit, the upload is short-circuited and a new asset row is created pointing to the existing storage location, but with its own license/owner/link rows.

### 3.5 `media_perceptual_hashes` — near-dedup

```sql
CREATE TABLE media_perceptual_hashes (
  id              BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  asset_id        BIGINT NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
  algorithm       TEXT NOT NULL CHECK (algorithm IN ('phash64','dhash64','ahash64','whash64','phash256')),
  hash_value      BIT(256) NOT NULL,  -- left-aligned; 64-bit algos pad
  bucket_16       BIT(16) GENERATED ALWAYS AS (SUBSTRING(hash_value FROM 1 FOR 16)) STORED,
  computed_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (asset_id, algorithm)
);
CREATE INDEX mph_bucket_idx ON media_perceptual_hashes (algorithm, bucket_16);
CREATE INDEX mph_asset_idx  ON media_perceptual_hashes (asset_id);
```

Postgres has no native BK-tree. We pick **two-stage retrieval**:
1. Bucket-prefix query on `bucket_16` finds candidates with low Hamming distance in the top 16 bits.
2. A Python-side Hamming filter (popcount of XOR) keeps only `distance <= 8`.

At ≤ 1M assets this works fine. Beyond ~10M assets we externalise to **Milvus** or **Qdrant** with binary vector indexes (see §14 risks).

### 3.6 `media_metadata_exif`

```sql
CREATE TABLE media_metadata_exif (
  asset_id        BIGINT PRIMARY KEY REFERENCES media_assets(id) ON DELETE CASCADE,
  raw_jsonb       JSONB NOT NULL,     -- full ExifTool dump
  camera_make     TEXT,
  camera_model    TEXT,
  lens_model      TEXT,
  focal_length_mm NUMERIC(6,2),
  aperture        NUMERIC(4,2),
  iso             INTEGER,
  shutter_speed   TEXT,
  gps_lat         DOUBLE PRECISION,
  gps_lng         DOUBLE PRECISION,
  gps_altitude_m  NUMERIC(8,2),
  capture_at      TIMESTAMPTZ,
  software        TEXT,
  orientation     SMALLINT,
  has_pii_geo     BOOLEAN GENERATED ALWAYS AS (gps_lat IS NOT NULL) STORED,
  stripped_at     TIMESTAMPTZ
);
CREATE INDEX exif_capture_at_idx ON media_metadata_exif (capture_at);
CREATE INDEX exif_pii_geo_idx    ON media_metadata_exif (has_pii_geo) WHERE has_pii_geo = TRUE;
```

The `raw_jsonb` is **always** preserved server-side regardless of public-strip policy — for archival/forensic value. The user-served variants in MinIO have EXIF physically stripped (see §10).

### 3.7 `license_types` (admin vocabulary)

```sql
CREATE TABLE license_types (
  id              BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  code            TEXT NOT NULL UNIQUE,  -- 'CC-BY-4.0', 'CC-BY-SA-4.0', 'CC0', 'PD-OLD', 'PROPRIETARY', 'B2B-EXCLUSIVE', 'UGC-DEFAULT', 'MUSEUM-CUSTOM'
  display_name    TEXT NOT NULL,
  url             TEXT,
  requires_attribution BOOLEAN NOT NULL,
  allows_commercial    BOOLEAN NOT NULL,
  allows_derivatives   BOOLEAN NOT NULL,
  share_alike     BOOLEAN NOT NULL,
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 3.8 `media_licenses`

```sql
CREATE TABLE media_licenses (
  asset_id        BIGINT PRIMARY KEY REFERENCES media_assets(id) ON DELETE CASCADE,
  license_type_id BIGINT NOT NULL REFERENCES license_types(id),
  custom_terms_url TEXT,
  declared_by_user_id BIGINT REFERENCES users(id),
  declared_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  snapshot_jsonb  JSONB NOT NULL,     -- frozen copy of UGC click-through terms version
  expires_at      TIMESTAMPTZ
);
```

For UGC, `snapshot_jsonb` captures the exact ToS version the user accepted when uploading; if we later change the ToS, the user's prior asset stays under its original terms.

### 3.9 `media_attributions`

```sql
CREATE TABLE media_attributions (
  id              BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  asset_id        BIGINT NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
  position        SMALLINT NOT NULL DEFAULT 0,
  attributed_name TEXT NOT NULL,
  attributed_url  TEXT,
  role            TEXT,               -- 'author','photographer','rights_holder','translator'
  source_platform TEXT,               -- 'wikimedia_commons', 'sketchfab', 'museum_xyz'
  source_url      TEXT,
  UNIQUE (asset_id, position)
);
```

### 3.10 `media_copyright_claims`, `media_takedown_requests`

```sql
CREATE TABLE media_copyright_claims (
  id              BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  asset_id        BIGINT NOT NULL REFERENCES media_assets(id),
  claimant_name   TEXT NOT NULL,
  claimant_email  TEXT NOT NULL,
  claim_basis     TEXT NOT NULL CHECK (claim_basis IN ('copyright','trademark','privacy','defamation','other')),
  claim_body      TEXT NOT NULL,
  evidence_urls   TEXT[],
  state           TEXT NOT NULL DEFAULT 'received'
                    CHECK (state IN ('received','under_review','accepted','rejected','withdrawn')),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  resolved_at     TIMESTAMPTZ,
  resolved_by_admin_id BIGINT REFERENCES users(id)
);

CREATE TABLE media_takedown_requests (
  id              BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  asset_id        BIGINT NOT NULL REFERENCES media_assets(id),
  origin          TEXT NOT NULL CHECK (origin IN ('dmca','gdpr_erasure','self_request','court_order','internal_policy')),
  related_claim_id BIGINT REFERENCES media_copyright_claims(id),
  state           TEXT NOT NULL DEFAULT 'pending'
                    CHECK (state IN ('pending','executed','reversed','expired')),
  executed_at     TIMESTAMPTZ,
  reversed_at     TIMESTAMPTZ,
  retention_until TIMESTAMPTZ,        -- audit retention even after asset purge
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 3.11 Type-specific tables

```sql
CREATE TABLE media_audio_tracks (
  asset_id        BIGINT PRIMARY KEY REFERENCES media_assets(id) ON DELETE CASCADE,
  track_role      TEXT NOT NULL CHECK (track_role IN ('tts_guide','human_narration','ambient','music','effect')),
  language        CHAR(3) NOT NULL,
  voice_id        TEXT,               -- TTS voice identifier (Kokoro/Piper/ElevenLabs)
  generator       TEXT,               -- 'kokoro','piper','elevenlabs','openai_tts','human'
  generator_params_jsonb JSONB,
  loudness_lufs   NUMERIC(5,2),
  is_premium      BOOLEAN NOT NULL DEFAULT FALSE,
  related_heritage_id BIGINT,         -- soft cross-ref via media_asset_links preferred
  transcript_jsonb JSONB              -- {language: full_text}
);

CREATE TABLE media_video_streams (
  asset_id        BIGINT PRIMARY KEY REFERENCES media_assets(id) ON DELETE CASCADE,
  hls_manifest_variant_id BIGINT REFERENCES media_variants(id),
  dash_manifest_variant_id BIGINT REFERENCES media_variants(id),
  poster_variant_id BIGINT REFERENCES media_variants(id),
  has_drm         BOOLEAN NOT NULL DEFAULT FALSE,
  drm_provider    TEXT,               -- 'widevine','fairplay','playready'
  max_duration_ms INTEGER NOT NULL,
  ugc_max_30s_enforced BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE media_subtitles (
  id              BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  asset_id        BIGINT NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
  language        CHAR(3) NOT NULL,
  format          TEXT NOT NULL CHECK (format IN ('vtt','srt','ttml')),
  variant_id      BIGINT NOT NULL REFERENCES media_variants(id),
  generated_by    TEXT CHECK (generated_by IN ('human','whisper','nllb_translation','admin_edit')),
  UNIQUE (asset_id, language, format)
);

CREATE TABLE media_3d_models (
  asset_id        BIGINT PRIMARY KEY REFERENCES media_assets(id) ON DELETE CASCADE,
  source          TEXT NOT NULL CHECK (source IN ('sketchfab','open_heritage','photogrammetry','manual_3d','admin_upload')),
  source_url      TEXT,
  triangle_count  BIGINT,
  texture_resolution_max INTEGER,
  pbr_workflow    TEXT,               -- 'metallic_roughness','specular_glossy'
  scale_meters    NUMERIC(10,4),
  upright_axis    CHAR(1) CHECK (upright_axis IN ('X','Y','Z')),
  is_draco_compressed BOOLEAN NOT NULL DEFAULT FALSE,
  is_usdz_available BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE media_3d_lods (
  id              BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  model_asset_id  BIGINT NOT NULL REFERENCES media_3d_models(asset_id) ON DELETE CASCADE,
  lod_level       SMALLINT NOT NULL,  -- 0 = highest detail
  variant_id      BIGINT NOT NULL REFERENCES media_variants(id),
  triangles       BIGINT NOT NULL,
  byte_size       BIGINT NOT NULL,
  target_device_tier TEXT CHECK (target_device_tier IN ('low','mid','high','desktop')),
  UNIQUE (model_asset_id, lod_level)
);

CREATE TABLE media_ar_anchors (
  id              BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  pub_id          UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  anchor_kind     TEXT NOT NULL CHECK (anchor_kind IN ('image_marker','plane','gps_geospatial','arcloud','manual')),
  marker_asset_id BIGINT REFERENCES media_assets(id),
  arcloud_anchor_id TEXT,
  gps_lat         DOUBLE PRECISION,
  gps_lng         DOUBLE PRECISION,
  gps_altitude_m  NUMERIC(8,2),
  gps_accuracy_m  NUMERIC(6,2),
  geom            GEOGRAPHY(POINT,4326),
  yaw_deg         NUMERIC(6,2),
  pitch_deg       NUMERIC(6,2),
  roll_deg        NUMERIC(6,2),
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ar_anchor_geom_idx ON media_ar_anchors USING GIST (geom);

CREATE TABLE media_ar_overlays (
  id              BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  anchor_id       BIGINT NOT NULL REFERENCES media_ar_anchors(id),
  model_asset_id  BIGINT REFERENCES media_assets(id),
  audio_asset_id  BIGINT REFERENCES media_assets(id),
  text_jsonb      JSONB,
  scene_jsonb     JSONB NOT NULL,     -- transform graph
  starts_at       TIMESTAMPTZ,
  ends_at         TIMESTAMPTZ,
  is_premium      BOOLEAN NOT NULL DEFAULT FALSE
);
```

### 3.12 Pipeline tables

```sql
CREATE TABLE media_transcoding_presets (
  id              BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  code            TEXT NOT NULL UNIQUE,  -- 'image.webp.720','video.hls.720p','audio.mp3.128'
  target_kind     TEXT NOT NULL,        -- one of media_variants.variant_kind
  pipeline        TEXT NOT NULL CHECK (pipeline IN ('imgproxy','ffmpeg','gltfpack','draco','rapidcompact','whisper','custom')),
  params_jsonb    JSONB NOT NULL,
  is_default      BOOLEAN NOT NULL DEFAULT FALSE,
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  created_by_admin_id BIGINT REFERENCES users(id)
);

CREATE TABLE media_transcoding_jobs (
  id              BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  pub_id          UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  asset_id        BIGINT NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
  preset_id       BIGINT NOT NULL REFERENCES media_transcoding_presets(id),
  celery_task_id  TEXT,
  worker_pool     TEXT,                 -- 'cpu','gpu','3d'
  priority        SMALLINT NOT NULL DEFAULT 5,
  state           TEXT NOT NULL DEFAULT 'queued'
                    CHECK (state IN ('queued','running','succeeded','failed','retrying','cancelled')),
  attempts        SMALLINT NOT NULL DEFAULT 0,
  last_error      TEXT,
  scheduled_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  started_at      TIMESTAMPTZ,
  finished_at     TIMESTAMPTZ,
  output_variant_id BIGINT REFERENCES media_variants(id),
  duration_ms     INTEGER,
  cost_credits    NUMERIC(10,4)
);
CREATE INDEX jobs_state_priority_idx ON media_transcoding_jobs (state, priority, scheduled_at);
CREATE INDEX jobs_asset_idx          ON media_transcoding_jobs (asset_id);

CREATE TABLE media_scan_results (
  id              BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  asset_id        BIGINT NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
  scanner         TEXT NOT NULL CHECK (scanner IN ('clamav','nsfw_resnet','virustotal','custom_rule')),
  verdict         TEXT NOT NULL CHECK (verdict IN ('clean','suspicious','malicious','nsfw','safe')),
  score           NUMERIC(5,4),
  raw_jsonb       JSONB,
  scanned_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX scan_asset_idx ON media_scan_results (asset_id);
```

### 3.13 `media_lifecycle_events`

```sql
CREATE TABLE media_lifecycle_events (
  id              BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  asset_id        BIGINT NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
  event_type      TEXT NOT NULL CHECK (event_type IN
                    ('uploaded','scanned','quarantined','transcode_started','transcode_finished',
                     'published','watermarked','exif_stripped','license_assigned',
                     'takedown_pending','takedown_executed','restored','archived',
                     'tier_demoted','tier_promoted','cdn_invalidated','purged','accessed')),
  payload_jsonb   JSONB,
  actor_user_id   BIGINT REFERENCES users(id),
  actor_system    TEXT,                 -- 'celery_worker','admin_panel','user_app','dmca_bot'
  occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX lifecycle_asset_time_idx ON media_lifecycle_events (asset_id, occurred_at DESC);
CREATE INDEX lifecycle_event_idx      ON media_lifecycle_events (event_type, occurred_at DESC);
```

Append-only; no UPDATE/DELETE allowed (enforced by trigger). This is our forensic timeline.

### 3.14 Distribution tables

```sql
CREATE TABLE cdn_invalidations (
  id              BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  cdn_provider    TEXT NOT NULL CHECK (cdn_provider IN ('cloudflare','bunny','r2','fastly')),
  invalidation_kind TEXT NOT NULL CHECK (invalidation_kind IN ('url','prefix','tag','zone')),
  target          TEXT NOT NULL,
  reason          TEXT NOT NULL,        -- 'asset_update','takedown','license_change','bundle_release'
  related_asset_id BIGINT REFERENCES media_assets(id),
  requested_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  acknowledged_at TIMESTAMPTZ,
  provider_request_id TEXT,
  state           TEXT NOT NULL DEFAULT 'requested'
                    CHECK (state IN ('requested','acknowledged','propagated','failed'))
);

CREATE TABLE signed_url_grants (
  id              BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  variant_id      BIGINT NOT NULL REFERENCES media_variants(id) ON DELETE CASCADE,
  url_hash        BYTEA NOT NULL,       -- sha256 of issued URL
  grantee_user_id BIGINT REFERENCES users(id),
  grantee_b2b_account_id BIGINT,        -- FK to b2b_accounts (Agent 6)
  client_ip       INET,
  user_agent_hash BYTEA,
  scope           TEXT NOT NULL CHECK (scope IN ('read','put','multipart','head')),
  issued_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at      TIMESTAMPTZ NOT NULL,
  consumed_count  INTEGER NOT NULL DEFAULT 0,
  max_consumes    INTEGER,
  revoked_at      TIMESTAMPTZ
);
CREATE INDEX signed_url_expiry_idx ON signed_url_grants (expires_at);
CREATE INDEX signed_url_grantee_idx ON signed_url_grants (grantee_user_id);

CREATE TABLE media_usage_log (
  id              BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  variant_id      BIGINT NOT NULL REFERENCES media_variants(id),
  served_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  bytes_served    BIGINT NOT NULL,
  served_by       TEXT NOT NULL CHECK (served_by IN ('cdn','origin')),
  client_country  CHAR(2),
  referrer_host   TEXT,
  user_id         BIGINT REFERENCES users(id),
  b2b_account_id  BIGINT,
  billable        BOOLEAN NOT NULL DEFAULT FALSE
) PARTITION BY RANGE (served_at);
```

Partition monthly; retain hot partition online, archive older to cold storage with `pg_dump --section=data`.

### 3.15 Offline bundle tables

```sql
CREATE TABLE offline_bundles (
  id              BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  pub_id          UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  bundle_kind     TEXT NOT NULL CHECK (bundle_kind IN
                    ('country','region','city','heritage_site','curated_tour','language_pack','base_app')),
  code            TEXT NOT NULL UNIQUE, -- 'UZ.SAMARKAND', 'UZ.ALL', 'CN.XIAN'
  display_name_jsonb JSONB NOT NULL,
  primary_geom    GEOGRAPHY(MULTIPOLYGON,4326),
  language_set    CHAR(3)[],
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX bundles_geom_idx ON offline_bundles USING GIST (primary_geom);

CREATE TABLE offline_bundle_versions (
  id              BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  bundle_id       BIGINT NOT NULL REFERENCES offline_bundles(id) ON DELETE CASCADE,
  semver          TEXT NOT NULL,        -- '2026.05.18+12'
  manifest_storage_location_id BIGINT NOT NULL REFERENCES media_storage_locations(id),
  zip_storage_location_id BIGINT REFERENCES media_storage_locations(id),  -- full pack
  delta_against_version_id BIGINT REFERENCES offline_bundle_versions(id),
  delta_storage_location_id BIGINT REFERENCES media_storage_locations(id),
  total_byte_size BIGINT NOT NULL,
  asset_count     INTEGER NOT NULL,
  manifest_sha256 BYTEA NOT NULL,
  signature_id    BIGINT REFERENCES offline_bundle_signatures(id),
  released_at     TIMESTAMPTZ,
  retired_at      TIMESTAMPTZ,
  UNIQUE (bundle_id, semver)
);

CREATE TABLE offline_bundle_contents (
  bundle_version_id BIGINT NOT NULL REFERENCES offline_bundle_versions(id) ON DELETE CASCADE,
  variant_id      BIGINT NOT NULL REFERENCES media_variants(id),
  inclusion_reason TEXT,               -- 'heritage_primary_image','tts_uzbek','map_tile'
  is_required     BOOLEAN NOT NULL DEFAULT TRUE,
  byte_size       BIGINT NOT NULL,
  PRIMARY KEY (bundle_version_id, variant_id)
);

CREATE TABLE offline_bundle_downloads (
  id              BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  device_id       TEXT NOT NULL,        -- Flutter install id
  user_id         BIGINT REFERENCES users(id),
  bundle_version_id BIGINT NOT NULL REFERENCES offline_bundle_versions(id),
  installed_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  byte_size       BIGINT NOT NULL,
  state           TEXT NOT NULL DEFAULT 'active'
                    CHECK (state IN ('downloading','active','stale','superseded','removed')),
  last_seen_at    TIMESTAMPTZ,
  UNIQUE (device_id, bundle_version_id)
);
CREATE INDEX bundle_dl_device_idx ON offline_bundle_downloads (device_id);

CREATE TABLE offline_bundle_signatures (
  id              BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  manifest_sha256 BYTEA NOT NULL,
  algorithm       TEXT NOT NULL CHECK (algorithm IN ('ed25519','rsa_pss_sha256')),
  signing_key_id  TEXT NOT NULL,
  signature       BYTEA NOT NULL,
  signed_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 3.16 `media_watermark_profiles`

```sql
CREATE TABLE media_watermark_profiles (
  id              BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  code            TEXT NOT NULL UNIQUE,
  display_name    TEXT NOT NULL,
  watermark_kind  TEXT NOT NULL CHECK (watermark_kind IN ('text','image','steganographic')),
  text_template   TEXT,
  image_asset_id  BIGINT REFERENCES media_assets(id),
  opacity         NUMERIC(3,2) DEFAULT 0.30,
  position        TEXT CHECK (position IN ('bl','br','tl','tr','center','tile')),
  is_active       BOOLEAN NOT NULL DEFAULT TRUE
);
```

---

## 4. Polymorphic Linkage

Media is owned/used by many entity types (heritage, user, review, b2b_listing, ar_overlay, marketplace_product, tour_route). Three options:

**Option A — Per-entity link tables**
`heritage_media (heritage_id, asset_id, role)`, `review_media (review_id, asset_id, role)`, etc.
Pros: strong FK integrity, fast joins, easy partial indexes.
Cons: N×M tables; new entity type = new table + migration; harder to write generic admin tools.

**Option B — Generic (entity_type, entity_id)**
Single `media_asset_links (asset_id, entity_type, entity_id, role)`.
Pros: one table; new entity type is just a new enum value.
Cons: no FK to entity_id (must be enforced by application or trigger); ambiguous joins.

**Option C — Hybrid (chosen)**
- A single `media_asset_links` table for **discovery, listing, admin tooling, search**.
- Plus thin "interest-bearing" link tables where extra columns or strict FK are required: `heritage_primary_media (heritage_id, asset_id, sort_order)`, `b2b_listing_featured_media (...)`, `ar_overlays.model_asset_id` (direct FK).

```sql
CREATE TABLE media_asset_links (
  id              BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  asset_id        BIGINT NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
  entity_type     TEXT NOT NULL CHECK (entity_type IN
                    ('heritage','heritage_section','user_profile','review','tour_route',
                     'b2b_listing','b2b_account','ar_overlay','marketplace_product',
                     'announcement','language_pack','admin_setting')),
  entity_id       BIGINT NOT NULL,
  role            TEXT NOT NULL,       -- 'hero','gallery','avatar','before_after','sponsor_logo'
  sort_order      INTEGER NOT NULL DEFAULT 0,
  visibility      TEXT NOT NULL DEFAULT 'public'
                    CHECK (visibility IN ('public','premium','b2b','admin','hidden')),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (asset_id, entity_type, entity_id, role)
);
CREATE INDEX mal_entity_idx ON media_asset_links (entity_type, entity_id);
CREATE INDEX mal_asset_idx  ON media_asset_links (asset_id);
```

A nightly verification job confirms `entity_id` resolves; orphans are flagged in `media_lifecycle_events`. This is the price of polymorphism — accepted because the alternative (one link table per entity type) inflates Alembic migration count and slows admin-panel development.

---

## 5. MinIO Bucket Strategy

### 5.1 Buckets

| Bucket                     | Purpose                                                     | Tier  | Versioning | Public |
|----------------------------|-------------------------------------------------------------|-------|------------|--------|
| `silklens-uploads-raw`     | Receiving area for fresh uploads pending scan               | hot   | yes        | no     |
| `silklens-quarantine`      | Suspicious/quarantined originals                            | warm  | yes        | no     |
| `silklens-originals-hot`   | Published originals frequently accessed                     | hot   | yes        | no     |
| `silklens-originals-warm`  | Originals not accessed in 30d                               | warm  | yes        | no     |
| `silklens-originals-cold`  | Archive (S3 Glacier mirror candidate)                       | cold  | yes        | no     |
| `silklens-variants-cdn`    | All public-readable derived variants (webp/avif/hls/glb)    | hot   | no         | yes    |
| `silklens-variants-premium`| Variants gated by premium/b2b/DRM                           | hot   | no         | no     |
| `silklens-bundles`         | Offline bundle ZIPs, deltas, manifests, signatures          | warm  | yes        | yes    |
| `silklens-ar-3d`           | GLB/USDZ/photogrammetry intermediates                       | warm  | yes        | mixed  |
| `silklens-thumbs`          | Tiny thumbs (≤64KB) — high read rate                        | hot   | no         | yes    |
| `silklens-internal`        | EXIF dumps, scanner logs, raw photogrammetry inputs         | cold  | yes        | no     |

### 5.2 Object key naming

```
<asset_pub_id_prefix2>/<asset_pub_id>/<variant_kind>/<preset_code>.<ext>
e.g. 7a/7a3c1e98-...-f1/webp_1440/image.webp.1440.webp
```

Rationale:
- Two-char prefix flattens the listing distribution (avoids hot prefixes).
- pub_id, not numeric id — never leak DB id to object store ACL boundary.
- variant kind in path means lifecycle rules can target by prefix.

### 5.3 Versioning & lifecycle rules

- Originals buckets: versioning ON; 30-day non-current version retention; transition non-current to cold after 30d.
- Variants are regeneratable — versioning OFF; lifecycle deletes 7 days after asset takedown.
- Bundles versioned; old versions kept 180 days for client back-fill.

### 5.4 Signed URLs

- Public variants: served via `silklens-variants-cdn` behind Cloudflare; **no signing** (cache-friendly).
- Premium/B2B variants: signed URL TTL 5 minutes; `signed_url_grants` row written; rate limited per user via Redis token bucket (1000 grants/hr/user default, admin-configurable).
- Bundle ZIP downloads: longer TTL (30 min); resumable via `Range` headers; per-device throttle 3 concurrent.

---

## 6. Transcoding Pipeline

### 6.1 FSM

`media_transcoding_jobs.state`:

```
queued ── pick ──► running ── ok ─► succeeded
                       │
                       └── err ─► retrying (max 3) ─► failed
                                                       │
                                                       └── admin retry ─► queued
```

### 6.2 Celery topology

- Broker: Redis (existing).
- Queues: `media_cpu`, `media_gpu`, `media_3d`, `media_priority`, `media_bulk`.
- Workers:
  - CPU workers run imgproxy/ffmpeg for image and audio.
  - GPU workers run Whisper (transcription), AVIF/JPEG-XL encoder, NLLB caption translation.
  - 3D workers run `gltfpack`, Draco compression, `usdz` conversion, RapidCompact-like LOD generation.
- Priority queue serves admin "republish now" and DMCA takedown re-rendering.

### 6.3 Failure recovery

- Job `attempts >= 3` → `failed`, surfaced in admin queue.
- Idempotency: each preset run writes to a temporary key, then renames. Crash-safe.
- Poison-pill detection: `last_error` clustering by hash; identical error 3× across different assets pages SRE.

### 6.4 Preset matrix (initial)

| Source kind | Preset                  | Output                                                |
|-------------|-------------------------|-------------------------------------------------------|
| image       | image.thumb.256.webp    | 256px WebP q75                                        |
| image       | image.medium.720.webp   | 720px WebP q80                                        |
| image       | image.large.1440.avif   | 1440px AVIF q60                                       |
| image       | image.large.1440.jpegxl | 1440px JPEG XL (progressive enhancement clients)      |
| image       | image.poster.1080.jpg   | JPEG fallback for legacy iOS < 14                     |
| video       | video.hls.{240,480,720,1080}p | H.264 + AAC, fMP4 segments                      |
| video       | video.poster.jpg        | thumbnail at 1.0s                                     |
| audio       | audio.mp3.128, audio.opus.96 | Stereo/mono normalised to -16 LUFS               |
| audio       | audio.hls.aac           | HLS audio stream for streaming TTS                    |
| 3d          | glb.lod{0,1,2}.draco    | Draco-compressed GLB at three triangle budgets        |
| 3d          | usdz                    | Apple Quick Look variant                              |

Client capability negotiation (Accept header + UA hints) selects WebP/AVIF/JPEG-XL/JPEG fallback chain. imgproxy handles negotiation at edge.

---

## 7. Deduplication Strategy

### 7.1 Exact dedup (sha256)

On upload (or import), worker computes sha256 streamingly. Lookup `media_content_hashes.sha256`. If hit:
- Create a new `media_assets` row (the link, license, EXIF metadata may differ).
- Insert `media_content_hashes` with `duplicate_of_asset_id` set.
- Skip new MinIO upload; reuse storage location via `media_storage_locations` shared row.
- Re-run license/attribution flow against the new uploader's terms.

### 7.2 Near dedup (perceptual hash)

Pipeline:
1. Compute `phash64`, `dhash64`, `whash64` (we keep all three — pHash is robust to JPEG re-encoding, dHash to small crops, wHash to brightness shifts).
2. Insert into `media_perceptual_hashes`.
3. For each algorithm, query candidates with same `bucket_16` (or 1-bit Hamming neighbours via 16 OR-clauses).
4. For each candidate, compute full Hamming distance in Python; if `< 8`, mark as near-duplicate via `media_lifecycle_events(event_type='near_duplicate_detected', payload={candidate_asset_id, distance})`.

"Find similar uploaded photos to this heritage's existing photos": resolve heritage → linked assets → their `phash64` set → expand to bucket-prefix neighbours → filter by Hamming.

At ≥ 10M assets this strategy degrades; route this query to external Milvus (binary vector index) — but keep `media_perceptual_hashes` as the system of record. See §14.

---

## 8. Offline Bundle Strategy

### 8.1 Bundle manifest schema (in MinIO, JSON)

```json
{
  "bundle_pub_id": "...",
  "bundle_code": "UZ.SAMARKAND",
  "semver": "2026.05.18+12",
  "released_at": "2026-05-18T09:00:00Z",
  "language_set": ["uzb","rus","eng","cmn"],
  "manifest_sha256": "...",
  "delta_against": "2026.05.10+09",
  "assets": [
    {
      "asset_pub_id": "...",
      "variants": [
        {"kind": "webp_720", "url": "cdn/.../webp_720", "sha256":"...", "size": 84320},
        {"kind": "mp3_128",  "url": "cdn/.../mp3_128",  "sha256":"...", "size": 521000}
      ],
      "entity_links": [{"entity_type":"heritage","entity_id":"...","role":"hero"}],
      "license": {"code":"CC-BY-SA-4.0","attribution":["A. Karimov"]}
    }
  ],
  "signature": {"alg":"ed25519","key_id":"silklens-bundle-2026-q2","sig":"base64..."}
}
```

### 8.2 Delta updates

- Each `offline_bundle_versions` row may carry a delta against another version.
- Client sends `If-Bundle-Version: 2026.05.10+09`; server responds with delta manifest + delta ZIP (only added/changed variants).
- Removed variants are listed under `removed_variant_pub_ids` so the client can purge from local Isar.

### 8.3 Per-device version tracking

`offline_bundle_downloads(device_id, bundle_version_id, state)` lets us answer:
- "Show users on UZ.SAMARKAND v12 → push update."
- "B2B partner X wants count of installed Khiva bundle copies."
- "Device Y reports corrupt manifest → flag and reissue."

### 8.4 Bundle bump trigger

When a heritage in `UZ.SAMARKAND` gets a new primary image (or a takedown), an event-bus message fires `bundle.invalidate(UZ.SAMARKAND)`. A scheduled compaction job batches invalidations and produces a new `offline_bundle_versions` row (semver auto-incremented). Generation pipeline:

1. Query: all `media_variants` where `media_asset_links.entity_id` ∈ (heritages in region) **and** `variant_kind ∈ (thumb_256, webp_720, mp3_128, glb_lod2)`.
2. Build manifest JSON, sort deterministically.
3. Compute manifest sha256; Ed25519-sign with `silklens-bundle-2026-q2` key.
4. Build ZIP and delta-ZIP via `zstd`-compressed tar.
5. Upload to `silklens-bundles`; insert rows.
6. Push notification to devices on prior version: "Samarqand paket yangilandi (24 MB)".

### 8.5 Signature verification (client side)

Flutter app ships with embedded Ed25519 public key (rotatable via signed config). On bundle install:
1. Verify manifest signature.
2. Walk asset list, verify each downloaded blob's sha256.
3. On mismatch → reject, log, fall back to prior version.

This is the only defence against rooted-device bundle substitution.

---

## 9. CDN Strategy

### 9.1 Edge cache (Cloudflare)

- `silklens-variants-cdn` and `silklens-thumbs` are S3-compatible origins; Cloudflare R2-style worker serves from MinIO via origin shield (single regional cache).
- TTL: thumbs 1 year (immutable, content-hashed URLs); other public variants 30 days.
- Cache key includes `Accept` header (WebP/AVIF negotiation) plus client device tier hint.

### 9.2 Invalidation

- Asset takedown / republish → `cdn_invalidations(invalidation_kind='url')` rows queued and pushed to Cloudflare API.
- Bulk events (license change for 1000 Wikimedia assets) → tag-based purge (`Cache-Tag: lic-cc-by-sa-4`).
- Bundle release → prefix purge for `silklens-bundles/<code>/`.

### 9.3 Multi-CDN failover

- Primary: Cloudflare. Secondary: Bunny.net (cheaper egress in Asia). Tertiary: direct MinIO+nginx.
- DNS-level steering (Cloudflare Load Balancer) selects per region/health.
- `media_usage_log.served_by` records origin vs CDN — anomalies (origin pull > 1% of total) page SRE.

---

## 10. EXIF Privacy

User uploads from mobile cameras carry GPS coordinates and device serials — a privacy and stalking risk.

Pipeline (mandatory for `origin='ugc'`, configurable for `origin='admin_upload'`):

1. On upload, ExifTool dumps full metadata into `media_metadata_exif.raw_jsonb` (server-side only).
2. Pipeline produces a stripped copy for every public variant (no EXIF, no XMP, no maker notes).
3. Original blob in `silklens-originals-hot` keeps EXIF only if admin policy `preserve_originals = true`.
4. Admin override per asset: "preserve EXIF for archival" (museum donations, scientific value).
5. `media_assets.exif_stripped = true` flips on success.

Coordinate retention default policy:
- UGC: GPS removed from public variant; original GPS retained in `raw_jsonb` for 90 days then nulled.
- Admin upload of heritage photos: GPS retained (it is heritage-relevant, not personal-relevant).

---

## 11. License & Attribution

### 11.1 Required-attribution propagation

When rendering an asset, the client (mobile or admin) queries `/media/{pub_id}` and gets:

```json
{
  "license": {"code":"CC-BY-SA-4.0","requires_attribution":true,"share_alike":true},
  "attribution": [
    {"name":"Aleksandr Karimov","url":"https://commons.wikimedia.org/...","role":"photographer"},
    {"name":"Wikimedia Commons","url":"https://...","role":"source_platform"}
  ]
}
```

Mobile UI guarantees: if `requires_attribution` is true, the image cannot render in any view that does not also display attribution. Enforced via a Flutter widget contract (`AttributedImage(asset)`).

### 11.2 Commercial vs non-commercial

`license_types.allows_commercial = false` blocks the asset from `media_asset_links.entity_type IN ('b2b_listing','marketplace_product','announcement')`. Enforced by DB trigger:

```sql
CREATE OR REPLACE FUNCTION enforce_license_commercial() RETURNS trigger AS $$
BEGIN
  IF NEW.entity_type IN ('b2b_listing','marketplace_product','announcement') THEN
    IF NOT EXISTS (
      SELECT 1 FROM media_licenses ml
      JOIN license_types lt ON lt.id = ml.license_type_id
      WHERE ml.asset_id = NEW.asset_id AND lt.allows_commercial = TRUE
    ) THEN
      RAISE EXCEPTION 'Asset % license forbids commercial use', NEW.asset_id;
    END IF;
  END IF;
  RETURN NEW;
END;$$ LANGUAGE plpgsql;
```

### 11.3 UGC snapshot

When a user uploads, the active UGC ToS version is frozen into `media_licenses.snapshot_jsonb`. A subsequent ToS revision does **not** apply retroactively; this is a legal cleanliness property.

### 11.4 Share-alike propagation

If a derivative is created (we crop a CC-BY-SA Wikimedia photo to make a hero image), the derivative inherits `share_alike=true`; admin UI warns when re-licensing is attempted.

---

## 12. AR/3D Specifics

### 12.1 Anchor types

- **Image marker**: a printable picture; small, easy, fragile to lighting. Used for indoor museum signage.
- **Plane / surface**: ARCore/ARKit detected; volatile across sessions. For ad-hoc UGC AR.
- **GPS-geospatial**: lat/lng + altitude + heading; works outdoor; accuracy ±5–15m without RTK.
- **ARCloud anchor**: cloud-anchored persistence (ARCore Geospatial API); most stable for outdoor Registan-scale.

We default outdoor heritage AR to **GPS-geospatial + visual ARCloud refinement** (hybrid). Marker mode is fallback indoor only.

### 12.2 Photogrammetry pipeline

Inputs: drone photos in `silklens-internal`. Worker pool runs (or queues to external service) RealityCapture / Meshroom / RapidCompact. Outputs become `media_3d_models` + LODs.

### 12.3 LOD strategy

| LOD | Triangles | Texture | Device tier        | Bundle inclusion |
|-----|-----------|---------|--------------------|------------------|
| 0   | full      | 8K      | desktop, high-end  | online only      |
| 1   | 100K      | 4K      | high-end mobile    | online only      |
| 2   | 25K       | 2K      | mid mobile         | premium bundle   |
| 3   | 5K        | 1K      | low mobile, AR     | free bundle      |

### 12.4 Bandwidth

Mobile clients fetch LOD by `target_device_tier` resolved from `device_capability` (Agent 8 territory). The selector logic lives server-side so we can re-tune without app updates.

---

## 13. Future Storage Tiers

```
Hot (MinIO SSD, 30d access)
   │  age > 30d, access < 1/month
   ▼
Warm (MinIO HDD, lifecycle-managed)
   │  age > 180d, access < 1/quarter
   ▼
Cold (S3-compatible Glacier, days-to-retrieve)
   │  age > 2y, legal retention only
   ▼
Archive (tape / Deep Archive)
```

Lifecycle automation:
- `media_storage_locations.last_verified_at` periodically updated by a verifier job.
- Demotion is by `media_lifecycle_events.event_type='accessed'` density. If < threshold for window N, schedule `tier_demoted`.
- Promotion: any access from hot path triggers async copy back to hot bucket; signed URL points to hot once copy completes.

Originals: never deleted, only demoted (legal retention for license/attribution chain).

---

## 14. Risks & Open Questions

1. **Perceptual-hash search beyond 10M assets**: Postgres bucket-prefix breaks down. Decision needed: deploy Milvus/Qdrant for binary-vector ANN, or accept slower queries at scale. Open.

2. **Photogrammetry compute is expensive**: a single 500-photo drone set takes 4–12 hours on the RTX 4090. If 50 sites/month, the GPU saturates and starves AI vision inference. Likely outcome: contract with a cloud RealityCapture provider for surge; cost is non-trivial. Open: budget.

3. **Offline bundle size at 50K heritage objects**: even at 200KB average per heritage variant set, country bundles cross 10 GB. Decisions needed: per-region splits, on-demand asset stream-in, drop premium audio from free tier bundle. Open.

4. **DRM on B2B exclusive video**: Widevine L1 requires platform certificates and Google Widevine agreement (paid, slow). Open whether B2B-exclusive video should ship at all in v1 or be deferred.

5. **EXIF GPS retention policy** under O'zbekiston data law vs GDPR conflict for EU tourists: 90-day default may be too long under GDPR data-minimisation. Legal review pending.

6. **Cloudflare cache + signed URLs interplay**: signing fragments cache. We will likely need Cloudflare Workers to do signature verification at edge while keeping origin URLs cacheable. Spike required.

7. **Wikimedia attribution drift**: upstream author names change (renames, account deletion). Our snapshot is immutable. Decide: re-fetch policy quarterly? Acceptable risk?

8. **3D model copyright on Sketchfab imports**: Sketchfab's Standard licence is more restrictive than CC. Per-asset license vetting required; cannot bulk-trust.

9. **AR cloud anchor vendor lock-in**: ARCore Geospatial is Google-only. Multi-vendor fallback (Niantic Lightship, Apple ARKit anchor) requires per-platform alternative anchor IDs — schema supports `anchor_kind` and `arcloud_anchor_id` is provider-agnostic by intent, but ops complexity is real.

10. **Bundle signing key rotation**: shipped public key in Flutter app must be rotatable. We have `signing_key_id` per signature, but the client-side key trust list needs a separate signed-config channel (Agent 8 sync architecture).

---

## Cross-Agent Dependencies

- **Agent 1 (heritage)**: `media_asset_links.entity_type='heritage'`; `heritage` must expose `id` and stable `pub_id`.
- **Agent 3 (AI/embeddings)**: visual embeddings are linked back via `media_assets.id`; the embedding service consumes `media_variants(variant_kind='medium_720')` URLs. Embeddings table lives in Agent 3's domain but FKs to `media_assets`.
- **Agent 5 (UGC/reviews)**: `media_asset_links.entity_type='review'`.
- **Agent 6 (B2B/monetisation)**: `media_asset_links.entity_type IN ('b2b_listing','b2b_account')`; `signed_url_grants.grantee_b2b_account_id`; `media_usage_log.b2b_account_id` for billing.
- **Agent 7 (auth/users)**: `media_assets.uploaded_by_user_id`, `signed_url_grants.grantee_user_id`.
- **Agent 8 (offline/sync)**: `offline_bundle_downloads`, `offline_bundle_versions`, `cdn_invalidations`, bundle signature trust list. Sync conflict signals when a device's local mutation references a now-purged asset.

---

*End of document 04-media-storage.md*
