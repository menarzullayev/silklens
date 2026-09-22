"""media_license_types (vocab) + media_licenses + attributions + copyright_claims

Per Agent 4 §11 the license layer matters because:
  - Wikimedia CC-BY-SA imposes attribution forever.
  - UGC requires snapshotting the user's ToS version at upload time.
  - B2B-exclusive material has watermarking/DRM clauses.
  - Museum donations carry moral-rights clauses.

Schema split:
  media_license_types       — admin vocabulary (cc0/cc_by/cc_by_sa/... + proprietary/ugc/b2b).
  media_licenses            — per-asset license assignment (asset_id PK, license_type_id FK).
  media_attributions        — required attribution chain (Wikimedia author → platform).
  media_copyright_claims    — DMCA-style takedown workflow.

Also attaches the forward FK from media_assets.license_id → media_licenses.asset_id
that was declared as a plain uuid in migration 0020.

Revision ID: 0022_media_licensing
Revises: 0021_media_pipeline
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0022_media_licensing"
down_revision: str | Sequence[str] | None = "0021_media_pipeline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- media_license_types (admin vocabulary) ---------------------------
    op.execute(
        """
        CREATE TABLE media_license_types (
            id                      uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            slug                    text NOT NULL UNIQUE,
            name                    jsonb NOT NULL DEFAULT '{}'::jsonb,
            url                     text,
            requires_attribution    boolean NOT NULL,
            allows_commercial       boolean NOT NULL,
            share_alike             boolean NOT NULL,
            allows_derivatives      boolean NOT NULL DEFAULT true,
            is_active               boolean NOT NULL DEFAULT true,
            created_at              timestamptz NOT NULL DEFAULT now(),
            updated_at              timestamptz NOT NULL DEFAULT now(),
            CHECK (slug ~ '^[a-z0-9][a-z0-9_]*$')
        );

        CREATE TRIGGER tg_media_license_types_updated_at
            BEFORE UPDATE ON media_license_types
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE media_license_types IS
            'License vocabulary per Agent 4 §3.7. Adding a new license is a row insert.';
        """
    )

    op.execute(
        """
        INSERT INTO media_license_types
            (slug, name, url, requires_attribution, allows_commercial, share_alike, allows_derivatives)
        VALUES
            ('cc0',
                '{"en":"CC0 Public Domain Dedication"}'::jsonb,
                'https://creativecommons.org/publicdomain/zero/1.0/',
                false, true, false, true),
            ('cc_by',
                '{"en":"CC BY 4.0"}'::jsonb,
                'https://creativecommons.org/licenses/by/4.0/',
                true, true, false, true),
            ('cc_by_sa',
                '{"en":"CC BY-SA 4.0"}'::jsonb,
                'https://creativecommons.org/licenses/by-sa/4.0/',
                true, true, true, true),
            ('cc_by_nc',
                '{"en":"CC BY-NC 4.0"}'::jsonb,
                'https://creativecommons.org/licenses/by-nc/4.0/',
                true, false, false, true),
            ('cc_by_nc_sa',
                '{"en":"CC BY-NC-SA 4.0"}'::jsonb,
                'https://creativecommons.org/licenses/by-nc-sa/4.0/',
                true, false, true, true),
            ('cc_by_nd',
                '{"en":"CC BY-ND 4.0"}'::jsonb,
                'https://creativecommons.org/licenses/by-nd/4.0/',
                true, true, false, false),
            ('public_domain',
                '{"en":"Public Domain (expired copyright)"}'::jsonb,
                NULL, false, true, false, true),
            ('proprietary',
                '{"en":"Proprietary — all rights reserved"}'::jsonb,
                NULL, true, false, false, false),
            ('ugc_default',
                '{"en":"SilkLens UGC default terms"}'::jsonb,
                NULL, true, false, false, true),
            ('b2b_exclusive',
                '{"en":"B2B exclusive licence"}'::jsonb,
                NULL, true, true, false, false);
        """
    )

    # --- media_licenses (per-asset assignment) ----------------------------
    # asset_id is the PK so each asset has exactly one current license.
    # snapshot_terms captures the active ToS version at the moment of upload
    # (Agent 4 §11.3) — ToS revisions don't apply retroactively.
    op.execute(
        """
        CREATE TABLE media_licenses (
            asset_id                uuid PRIMARY KEY REFERENCES media_assets(id) ON DELETE CASCADE,
            license_type_id         uuid NOT NULL REFERENCES media_license_types(id) ON DELETE RESTRICT,
            holder                  text,
            source_url              text,
            attribution_required    text,
            license_terms_url       text,
            granted_to_tenant_id    uuid REFERENCES tenants(id) ON DELETE SET NULL,
            snapshot_terms          jsonb NOT NULL DEFAULT '{}'::jsonb,
            declared_by_user_id     uuid,
            expires_at              timestamptz,
            created_at              timestamptz NOT NULL DEFAULT now(),
            updated_at              timestamptz NOT NULL DEFAULT now()
        );

        CREATE INDEX idx_media_licenses_type
            ON media_licenses(license_type_id);
        CREATE INDEX idx_media_licenses_tenant
            ON media_licenses(granted_to_tenant_id) WHERE granted_to_tenant_id IS NOT NULL;
        CREATE INDEX idx_media_licenses_expires
            ON media_licenses(expires_at) WHERE expires_at IS NOT NULL;

        CREATE TRIGGER tg_media_licenses_updated_at
            BEFORE UPDATE ON media_licenses
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE media_licenses IS
            'One license per asset (PK asset_id). snapshot_terms freezes the ToS '
            'version at upload time per Agent 4 §11.3 — retroactive changes forbidden.';
        """
    )

    # Now that media_licenses exists, attach the deferred FK from
    # media_assets.license_id → media_licenses.asset_id. We keep it
    # NULLABLE so an asset can be uploaded before its license row is
    # written (admin-curation flow), and ON DELETE SET NULL because a
    # license row can be replaced.
    op.execute(
        """
        ALTER TABLE media_assets
            ADD CONSTRAINT fk_media_assets_license
            FOREIGN KEY (license_id)
            REFERENCES media_licenses (asset_id)
            ON DELETE SET NULL
            DEFERRABLE INITIALLY DEFERRED;
        """
    )

    # --- media_attributions (multi-source attribution chains) -------------
    # line_order lets the UI render: "Photo: A. Karimov / Wikimedia Commons / CC BY-SA 4.0"
    op.execute(
        """
        CREATE TABLE media_attributions (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            asset_id        uuid NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
            line_order      int NOT NULL DEFAULT 0,
            line_text       text NOT NULL,
            source_url      text,
            language_tag    text,
            role            text,
            created_at      timestamptz NOT NULL DEFAULT now(),
            UNIQUE (asset_id, line_order),
            CHECK (length(line_text) BETWEEN 1 AND 1024)
        );

        CREATE INDEX idx_media_attributions_asset
            ON media_attributions(asset_id, line_order);

        COMMENT ON TABLE media_attributions IS
            'Attribution chain per Agent 4 §3.9. Rendered in order by line_order. '
            'Required by CC-BY-SA, CC-BY, museum donation contracts.';
        """
    )

    # --- media_copyright_claims (DMCA-style workflow) ---------------------
    op.execute(
        """
        CREATE TABLE media_copyright_claims (
            id                      uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            asset_id                uuid NOT NULL REFERENCES media_assets(id) ON DELETE RESTRICT,
            claimant_name           text NOT NULL,
            claimant_email          text NOT NULL,
            claimant_address        text,
            complaint_text          text NOT NULL,
            evidence_urls           text[] NOT NULL DEFAULT ARRAY[]::text[],
            status                  text NOT NULL DEFAULT 'submitted'
                CHECK (status IN ('submitted','under_review','upheld','dismissed','withdrawn')),
            submitted_at            timestamptz NOT NULL DEFAULT now(),
            resolved_at             timestamptz,
            resolved_by_user_id     uuid,
            resolution_notes        text,
            created_at              timestamptz NOT NULL DEFAULT now(),
            updated_at              timestamptz NOT NULL DEFAULT now(),
            CHECK (length(claimant_name) BETWEEN 1 AND 256),
            CHECK (length(claimant_email) BETWEEN 3 AND 256),
            CHECK (length(complaint_text) BETWEEN 1 AND 16384),
            CHECK (resolved_at IS NULL OR resolved_at >= submitted_at)
        );

        CREATE INDEX idx_copyright_claims_status
            ON media_copyright_claims(status, submitted_at DESC)
            WHERE status IN ('submitted','under_review');
        CREATE INDEX idx_copyright_claims_asset
            ON media_copyright_claims(asset_id, submitted_at DESC);

        CREATE TRIGGER tg_copyright_claims_updated_at
            BEFORE UPDATE ON media_copyright_claims
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE media_copyright_claims IS
            'DMCA-style takedown workflow per Agent 4 §3.10. ON DELETE RESTRICT on '
            'asset_id: open claims block hard-delete; admins must resolve or dismiss first.';
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS media_copyright_claims CASCADE;")
    op.execute("DROP TABLE IF EXISTS media_attributions CASCADE;")
    op.execute("ALTER TABLE media_assets DROP CONSTRAINT IF EXISTS fk_media_assets_license;")
    op.execute("DROP TABLE IF EXISTS media_licenses CASCADE;")
    op.execute("DROP TABLE IF EXISTS media_license_types CASCADE;")
