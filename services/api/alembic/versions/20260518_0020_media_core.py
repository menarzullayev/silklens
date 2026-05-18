"""media_assets (polymorphic root) + variants + storage_locations + perceptual hashes

Per Agent 4 §1-§3, media is modeled as an asset/variant/lifecycle triad:

  media_assets              — polymorphic source-of-truth row. Immutable identity.
  media_variants            — derived renditions (thumb_256, medium_720, avif_1080, hls, glb...).
  media_storage_locations   — admin-managed catalog of buckets (MinIO/S3/Cloudflare).
  media_perceptual_hashes   — separate table for pHash near-dedup. Carries a
                              ``bucket_16`` smallint (top 16 bits of pHash) so
                              candidate retrieval is O(N/2^16) in vanilla Postgres
                              before a Python-side Hamming filter — Agent 4 §3
                              bucket-prefix trick.

UUIDv7 PKs · jsonb for EXIF · sha256 content_hash UNIQUE for exact dedup ·
soft delete via deleted_at · MinIO is truth for bytes, Postgres for meaning.

Revision ID: 0020_media_core
Revises: 0015_heritage_indexes
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0020_media_core"
down_revision: str | Sequence[str] | None = "0015_heritage_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- media_storage_locations (admin catalog) --------------------------
    # Created first so media_assets/variants can reference it as an admin
    # vocabulary. The "kind" column distinguishes self-hosted MinIO from
    # cloud providers; "public_read" controls whether signed URLs are needed.
    op.execute(
        """
        CREATE TABLE media_storage_locations (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            slug            text NOT NULL UNIQUE,
            name            jsonb NOT NULL DEFAULT '{}'::jsonb,
            kind            text NOT NULL CHECK (kind IN ('minio','s3','r2','local')),
            endpoint        text,
            bucket_name     text NOT NULL,
            region          text,
            public_read     boolean NOT NULL DEFAULT false,
            is_active       boolean NOT NULL DEFAULT true,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            CHECK (slug ~ '^[a-z0-9][a-z0-9_-]*$')
        );

        CREATE INDEX idx_media_storage_locations_kind
            ON media_storage_locations(kind) WHERE is_active;

        CREATE TRIGGER tg_media_storage_locations_updated_at
            BEFORE UPDATE ON media_storage_locations
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE media_storage_locations IS
            'Admin-managed catalog of object-store buckets. Agent 4 §5 bucket strategy. '
            'Adding a new CDN provider is a row insert, not a deploy.';
        """
    )

    # Seed the three buckets we ship with: primary uploads, offline-bundle
    # bucket, and a placeholder Cloudflare CDN row for production.
    op.execute(
        """
        INSERT INTO media_storage_locations
            (slug, name, kind, endpoint, bucket_name, region, public_read)
        VALUES
            ('minio_primary',
                '{"en":"MinIO primary media bucket"}'::jsonb,
                'minio', 'http://minio:9000', 'silklens-media', 'us-east-1', false),
            ('minio_offline',
                '{"en":"MinIO offline-bundle bucket"}'::jsonb,
                'minio', 'http://minio:9000', 'silklens-offline-bundles', 'us-east-1', true),
            ('cdn_cloudflare',
                '{"en":"Cloudflare R2 (production placeholder)"}'::jsonb,
                'r2', NULL, 'silklens-cdn', 'auto', true);
        """
    )

    # --- media_assets (polymorphic root) ----------------------------------
    # license_id is a forward reference to media_licenses (created in 0022).
    # We declare it as a plain uuid column here and attach the FK in 0022.
    op.execute(
        """
        CREATE TABLE media_assets (
            id                      uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            tenant_id               uuid NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            owner_user_id           uuid,
            kind                    text NOT NULL CHECK (kind IN (
                'image','video','audio_tts','audio_human','video_hls',
                'ar_marker','ar_overlay','3d_model','document'
            )),
            mime_type               text NOT NULL,
            byte_size               bigint NOT NULL CHECK (byte_size > 0),
            content_hash            bytea NOT NULL,
            perceptual_hash         bytea,
            perceptual_hash_bucket  smallint,
            storage_bucket          text NOT NULL,
            storage_key             text NOT NULL,
            storage_etag            text,
            status                  text NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending','scanning','processing','ready','quarantined','deleted')),
            license_id              uuid,  -- forward FK → media_licenses (0022)
            original_filename       text,
            exif                    jsonb NOT NULL DEFAULT '{}'::jsonb,
            width                   int,
            height                  int,
            duration_ms             int,
            language_tag            text,
            created_at              timestamptz NOT NULL DEFAULT now(),
            updated_at              timestamptz NOT NULL DEFAULT now(),
            deleted_at              timestamptz,
            CHECK (length(mime_type) BETWEEN 3 AND 128),
            CHECK (octet_length(content_hash) = 32),  -- sha256 = 32 bytes
            CHECK (perceptual_hash IS NULL OR octet_length(perceptual_hash) = 8)
        );

        -- Exact-match dedup: content_hash is sha256 of the original byte stream.
        CREATE UNIQUE INDEX uq_media_assets_content_hash
            ON media_assets (content_hash) WHERE deleted_at IS NULL;

        -- pHash bucket-prefix index. Partial — only live assets are searchable.
        CREATE INDEX idx_media_assets_phash_bucket
            ON media_assets (perceptual_hash_bucket)
            WHERE deleted_at IS NULL AND perceptual_hash_bucket IS NOT NULL;

        CREATE INDEX idx_media_assets_kind_status
            ON media_assets (kind, status) WHERE deleted_at IS NULL;

        CREATE INDEX idx_media_assets_owner
            ON media_assets (owner_user_id)
            WHERE owner_user_id IS NOT NULL AND deleted_at IS NULL;

        CREATE INDEX idx_media_assets_tenant
            ON media_assets (tenant_id, created_at DESC) WHERE deleted_at IS NULL;

        CREATE TRIGGER tg_media_assets_updated_at
            BEFORE UPDATE ON media_assets
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE media_assets IS
            'Polymorphic source-of-truth row per Agent 4 §1.2 asset/variant/lifecycle triad. '
            'MinIO is the truth for bytes, this table is the truth for meaning.';
        COMMENT ON COLUMN media_assets.perceptual_hash_bucket IS
            'Top 16 bits of perceptual_hash; partial index enables sub-O(N) near-dedup search.';
        COMMENT ON COLUMN media_assets.license_id IS
            'Forward FK to media_licenses, attached in migration 0022.';
        """
    )

    # --- media_variants (derived renditions) ------------------------------
    # One asset → many variants. Variants are regeneratable; UNIQUE(asset_id,
    # variant_name) so the same preset can't be queued twice. variant_name
    # encodes target (thumb_256, avif_1080, hls_720, mp3_128k...).
    op.execute(
        """
        CREATE TABLE media_variants (
            id                      uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            asset_id                uuid NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
            variant_name            text NOT NULL,
            mime_type               text NOT NULL,
            byte_size               bigint NOT NULL CHECK (byte_size > 0),
            width                   int,
            height                  int,
            duration_ms             int,
            storage_location_id     uuid NOT NULL REFERENCES media_storage_locations(id) ON DELETE RESTRICT,
            storage_key             text NOT NULL,
            generated_at            timestamptz NOT NULL DEFAULT now(),
            created_at              timestamptz NOT NULL DEFAULT now(),
            updated_at              timestamptz NOT NULL DEFAULT now(),
            UNIQUE (asset_id, variant_name),
            CHECK (variant_name ~ '^[a-z0-9][a-z0-9_-]*$')
        );

        CREATE INDEX idx_media_variants_asset
            ON media_variants(asset_id);
        CREATE INDEX idx_media_variants_name
            ON media_variants(variant_name);

        CREATE TRIGGER tg_media_variants_updated_at
            BEFORE UPDATE ON media_variants
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE media_variants IS
            'Derived renditions: thumb_256, medium_720, avif_1080, hls_720, mp3_128k, '
            'glb_lod2, usdz. Regeneratable — variant rows can be deleted and re-emitted '
            'by the transcoding pipeline (Agent 4 §6).';
        """
    )

    # --- media_perceptual_hashes (separate, index-friendly) ---------------
    # Per Agent 4 §3 we keep this OUT of media_assets so pHash search workloads
    # don't compete with the row's other index pressure. bucket_16 carries the
    # top 16 bits of the hash and is the primary candidate-fetch axis.
    op.execute(
        """
        CREATE TABLE media_perceptual_hashes (
            asset_id        uuid PRIMARY KEY REFERENCES media_assets(id) ON DELETE CASCADE,
            bucket_16       smallint NOT NULL,
            hash_8bytes     bytea NOT NULL,
            model           text NOT NULL DEFAULT 'phash_64'
                CHECK (model IN ('phash_64','dhash_64','ahash_64','whash_64')),
            computed_at     timestamptz NOT NULL DEFAULT now(),
            CHECK (octet_length(hash_8bytes) = 8)
        );

        CREATE INDEX idx_media_phashes_bucket
            ON media_perceptual_hashes USING BTREE (bucket_16);
        CREATE INDEX idx_media_phashes_model
            ON media_perceptual_hashes(model);

        COMMENT ON TABLE media_perceptual_hashes IS
            'Near-duplicate detection. Agent 4 §3: bucket_16 (top 16 bits) enables '
            'two-stage retrieval — bucket-prefix query in Postgres then Python-side '
            'Hamming distance filter. Sufficient at <10M assets; route to Milvus beyond.';
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS media_perceptual_hashes CASCADE;")
    op.execute("DROP TABLE IF EXISTS media_variants CASCADE;")
    op.execute("DROP TABLE IF EXISTS media_assets CASCADE;")
    op.execute("DROP TABLE IF EXISTS media_storage_locations CASCADE;")
