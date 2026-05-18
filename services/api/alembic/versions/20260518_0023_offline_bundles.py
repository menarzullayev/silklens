"""offline_bundles + versions + contents + downloads + signatures (Ed25519)

Per Agent 4 §8 and Master §8 (offline-first), this migration lands the bundle-
distribution schema that lets tourists in Khiva/Marv/Kunya-Urgench operate
fully offline.

  offline_bundles            — bundle definition (region + language set).
  offline_bundle_versions    — immutable semver-tagged snapshot. current_version_id
                               is forward-referenced from offline_bundles.
  offline_bundle_contents    — many-to-many (bundle_version × asset/variant).
                               tier 1 = metadata-only, 2 = full media, 3 = streamed.
  offline_bundle_downloads   — per-device install record, partitioned MONTHLY.
  offline_bundle_signatures  — Ed25519 manifest signatures. Only defence against
                               rooted-device bundle substitution (Agent 4 §8.5).

Forward references resolved:
  offline_bundles.current_version_id → offline_bundle_versions.id (declared here
    as nullable uuid; FK attached at end of upgrade once versions table exists).

Cross-domain forward references:
  offline_bundles.region_id → geographic_admin_levels(id) — Agent A migration 0012.
    Kept as nullable uuid with no FK; attached in a later cross-cutting migration.

Revision ID: 0023_offline_bundles
Revises: 0022_media_licensing
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from alembic import op

revision: str = "0023_offline_bundles"
down_revision: str | Sequence[str] | None = "0022_media_licensing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _month_bounds(year: int, month: int) -> tuple[str, str]:
    start = date(year, month, 1)
    end = date(year + (month // 12), (month % 12) + 1, 1)
    return start.isoformat(), end.isoformat()


def upgrade() -> None:
    # --- offline_bundles (bundle definition) ------------------------------
    # region_id is a forward reference to geographic_admin_levels which lands
    # in Agent A's 0012 (or a later cross-cutting migration). We keep it as
    # a nullable uuid without FK — null = "global" bundle (base app pack).
    op.execute(
        """
        CREATE TABLE offline_bundles (
            id                  uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            slug                text NOT NULL UNIQUE,
            name                jsonb NOT NULL DEFAULT '{}'::jsonb,
            bundle_kind         text NOT NULL DEFAULT 'region'
                CHECK (bundle_kind IN
                    ('country','region','city','heritage_site','curated_tour',
                     'language_pack','base_app')),
            region_id           uuid,  -- forward FK → geographic_admin_levels (Agent A)
            language_set        text[] NOT NULL DEFAULT ARRAY[]::text[],
            current_version_id  uuid,  -- forward FK within this migration; attached below
            is_active           boolean NOT NULL DEFAULT true,
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now(),
            CHECK (slug ~ '^[a-z0-9][a-z0-9._-]*$')
        );

        CREATE INDEX idx_offline_bundles_kind
            ON offline_bundles(bundle_kind) WHERE is_active;
        CREATE INDEX idx_offline_bundles_region
            ON offline_bundles(region_id) WHERE region_id IS NOT NULL;

        CREATE TRIGGER tg_offline_bundles_updated_at
            BEFORE UPDATE ON offline_bundles
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE offline_bundles IS
            'Bundle definition (Agent 4 §8). region_id is a forward reference to '
            'geographic_admin_levels (Agent 1/A). NULL region means "global" base pack.';
        """
    )

    # --- offline_bundle_versions (immutable semver snapshot) --------------
    op.execute(
        """
        CREATE TABLE offline_bundle_versions (
            id                      uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            bundle_id               uuid NOT NULL REFERENCES offline_bundles(id) ON DELETE CASCADE,
            version                 int NOT NULL CHECK (version > 0),
            semver                  text,
            byte_size               bigint NOT NULL CHECK (byte_size >= 0),
            asset_count             int NOT NULL DEFAULT 0 CHECK (asset_count >= 0),
            manifest_url            text NOT NULL,
            manifest_sha256         bytea NOT NULL,
            signature_ed25519       bytea,
            signing_key_id          text,
            delta_against_version_id uuid REFERENCES offline_bundle_versions(id) ON DELETE SET NULL,
            published_at            timestamptz,
            deprecated_at           timestamptz,
            created_at              timestamptz NOT NULL DEFAULT now(),
            updated_at              timestamptz NOT NULL DEFAULT now(),
            UNIQUE (bundle_id, version),
            CHECK (octet_length(manifest_sha256) = 32),
            CHECK (signature_ed25519 IS NULL OR octet_length(signature_ed25519) = 64),
            CHECK (deprecated_at IS NULL OR published_at IS NULL OR deprecated_at >= published_at)
        );

        CREATE INDEX idx_bundle_versions_bundle
            ON offline_bundle_versions(bundle_id, version DESC);
        CREATE INDEX idx_bundle_versions_published
            ON offline_bundle_versions(bundle_id, published_at DESC)
            WHERE published_at IS NOT NULL AND deprecated_at IS NULL;

        CREATE TRIGGER tg_bundle_versions_updated_at
            BEFORE UPDATE ON offline_bundle_versions
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE offline_bundle_versions IS
            'Immutable semver-tagged snapshot per Agent 4 §8.1. manifest_url points '
            'at the JSON manifest in silklens-offline-bundles. signature_ed25519 is '
            '64 bytes per RFC 8032.';
        """
    )

    # Attach the forward FK from offline_bundles.current_version_id.
    # Nullable + ON DELETE SET NULL: if the current version is retired without
    # a replacement, the bundle keeps existing but has no live version.
    op.execute(
        """
        ALTER TABLE offline_bundles
            ADD CONSTRAINT fk_offline_bundles_current_version
            FOREIGN KEY (current_version_id)
            REFERENCES offline_bundle_versions (id)
            ON DELETE SET NULL
            DEFERRABLE INITIALLY DEFERRED;
        """
    )

    # --- offline_bundle_contents (M:N) ------------------------------------
    # tier semantics:
    #   1 = L1 metadata only (asset row in Isar, no media bytes)
    #   2 = L2 full media (variant bytes packed into the ZIP)
    #   3 = L3 streamed (referenced but fetched on-demand)
    # Composite identity is (bundle_version_id, asset_id, variant_id) — but
    # variant_id is nullable (tier-1 metadata-only inclusions reference the
    # asset, no specific rendition). PostgreSQL forbids COALESCE in PK, so
    # we synthesise an id and enforce identity through a partial UNIQUE
    # index pair covering the null and non-null cases.
    op.execute(
        """
        CREATE TABLE offline_bundle_contents (
            id                  uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            bundle_version_id   uuid NOT NULL REFERENCES offline_bundle_versions(id) ON DELETE CASCADE,
            asset_id            uuid NOT NULL REFERENCES media_assets(id) ON DELETE RESTRICT,
            variant_id          uuid REFERENCES media_variants(id) ON DELETE RESTRICT,
            tier                smallint NOT NULL CHECK (tier BETWEEN 1 AND 3),
            byte_size           bigint NOT NULL DEFAULT 0 CHECK (byte_size >= 0),
            inclusion_reason    text,
            is_required         boolean NOT NULL DEFAULT true,
            created_at          timestamptz NOT NULL DEFAULT now()
        );

        -- Identity invariant: at most one row per (version, asset, variant) tuple.
        CREATE UNIQUE INDEX uq_bundle_contents_with_variant
            ON offline_bundle_contents (bundle_version_id, asset_id, variant_id)
            WHERE variant_id IS NOT NULL;
        CREATE UNIQUE INDEX uq_bundle_contents_no_variant
            ON offline_bundle_contents (bundle_version_id, asset_id)
            WHERE variant_id IS NULL;

        CREATE INDEX idx_bundle_contents_asset
            ON offline_bundle_contents(asset_id);
        CREATE INDEX idx_bundle_contents_variant
            ON offline_bundle_contents(variant_id) WHERE variant_id IS NOT NULL;
        CREATE INDEX idx_bundle_contents_tier
            ON offline_bundle_contents(bundle_version_id, tier);

        COMMENT ON TABLE offline_bundle_contents IS
            'Many-to-many: bundle version x (asset, variant). tier 1=L1 metadata, '
            '2=L2 full media, 3=L3 streamed (Agent 4 §8 + Master §8). '
            'Composite identity is (bundle_version_id, asset_id, variant_id) enforced '
            'via partial unique indexes because PostgreSQL forbids COALESCE in PRIMARY KEY.';
        """
    )

    # --- offline_bundle_downloads (partitioned MONTHLY) -------------------
    # PRIMARY KEY must include downloaded_at (partition key) per PG rules.
    op.execute(
        """
        CREATE TABLE offline_bundle_downloads (
            id                      uuid NOT NULL DEFAULT gen_uuid_v7(),
            bundle_version_id       uuid NOT NULL REFERENCES offline_bundle_versions(id) ON DELETE CASCADE,
            device_fingerprint_id   uuid REFERENCES device_fingerprints(id) ON DELETE SET NULL,
            user_id                 uuid,
            downloaded_at           timestamptz NOT NULL DEFAULT now(),
            completed_at            timestamptz,
            byte_count              bigint NOT NULL DEFAULT 0 CHECK (byte_count >= 0),
            completion_status       text NOT NULL DEFAULT 'started'
                CHECK (completion_status IN ('started','completed','failed','aborted')),
            client_ip               inet,
            PRIMARY KEY (id, downloaded_at),
            CHECK (completed_at IS NULL OR completed_at >= downloaded_at)
        ) PARTITION BY RANGE (downloaded_at);

        CREATE INDEX idx_bundle_downloads_version
            ON offline_bundle_downloads (bundle_version_id, downloaded_at DESC);
        CREATE INDEX idx_bundle_downloads_device
            ON offline_bundle_downloads (device_fingerprint_id, downloaded_at DESC)
            WHERE device_fingerprint_id IS NOT NULL;
        CREATE INDEX idx_bundle_downloads_user
            ON offline_bundle_downloads (user_id, downloaded_at DESC)
            WHERE user_id IS NOT NULL;

        COMMENT ON TABLE offline_bundle_downloads IS
            'Per-device install record (Agent 4 §8.3). Partitioned monthly. '
            'Used to push update notifications + B2B partner install counts.';
        """
    )

    # Provision ±3 months of monthly partitions.
    today = date.today()
    for offset in range(-3, 4):
        target = today.replace(day=1)
        year = target.year + ((target.month - 1 + offset) // 12)
        month = ((target.month - 1 + offset) % 12) + 1
        start, end = _month_bounds(year, month)
        op.execute(
            f"""
            CREATE TABLE offline_bundle_downloads_y{year}m{month:02d}
                PARTITION OF offline_bundle_downloads
                FOR VALUES FROM ('{start}') TO ('{end}');
            """
        )

    # --- offline_bundle_signatures (Ed25519) ------------------------------
    # PK is bundle_version_id — one canonical signature per version. Key
    # rotation is handled by re-signing into a new bundle version row.
    op.execute(
        """
        CREATE TABLE offline_bundle_signatures (
            bundle_version_id       uuid PRIMARY KEY REFERENCES offline_bundle_versions(id) ON DELETE CASCADE,
            public_key_pem          text NOT NULL,
            signature_algorithm     text NOT NULL DEFAULT 'ed25519'
                CHECK (signature_algorithm = 'ed25519'),
            signed_payload_hash     bytea NOT NULL,
            signature               bytea NOT NULL,
            signing_key_id          text NOT NULL,
            signed_at               timestamptz NOT NULL DEFAULT now(),
            CHECK (octet_length(signed_payload_hash) = 32),
            CHECK (octet_length(signature) = 64)
        );

        CREATE INDEX idx_bundle_signatures_key
            ON offline_bundle_signatures(signing_key_id);

        COMMENT ON TABLE offline_bundle_signatures IS
            'Ed25519 manifest signatures per Agent 4 §8.5. Only defence against '
            'rooted-device bundle substitution. Flutter app verifies the signature '
            'before activating any downloaded bundle.';
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS offline_bundle_signatures CASCADE;")
    op.execute("DROP TABLE IF EXISTS offline_bundle_downloads CASCADE;")
    op.execute("DROP TABLE IF EXISTS offline_bundle_contents CASCADE;")
    op.execute(
        "ALTER TABLE offline_bundles "
        "DROP CONSTRAINT IF EXISTS fk_offline_bundles_current_version;"
    )
    op.execute("DROP TABLE IF EXISTS offline_bundle_versions CASCADE;")
    op.execute("DROP TABLE IF EXISTS offline_bundles CASCADE;")
