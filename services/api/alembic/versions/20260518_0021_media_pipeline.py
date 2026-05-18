"""media_transcoding_presets + jobs + lifecycle + signed_url_grants + cdn_invalidations + usage_log

Per Agent 4 §6 (transcoding) and §9 (CDN), this migration lands the operational
plumbing around media_assets:

  media_transcoding_presets  — admin-managed preset catalog (8 seeded).
  media_transcoding_jobs     — Celery job state machine (pending/processing/done/failed/cancelled).
  media_lifecycle_events     — append-only forensic timeline, partitioned by MONTH on created_at.
  signed_url_grants          — per-issue audit row for pre-signed URLs (B2B forensics + anti-hotlink).
  cdn_invalidations          — log of cache-purge requests (Cloudflare/Bunny/R2).
  media_usage_log            — origin-hit log for B2B billing, partitioned by WEEK on accessed_at.

Partitioned tables include the partition key in their PRIMARY KEY per
Postgres requirement (lesson from migration 0005).

Forward references: signed_url_grants.grantee_b2b_account_id is left as a
nullable uuid column with no FK — b2b_accounts ships from Agent 6 later.

Revision ID: 0021_media_pipeline
Revises: 0020_media_core
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta

from alembic import op

revision: str = "0021_media_pipeline"
down_revision: str | Sequence[str] | None = "0020_media_core"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _month_bounds(year: int, month: int) -> tuple[str, str]:
    start = date(year, month, 1)
    end = date(year + (month // 12), (month % 12) + 1, 1)
    return start.isoformat(), end.isoformat()


def _week_bounds(anchor: date) -> tuple[str, str]:
    # Weeks anchored to ISO Monday so partition boundaries are deterministic.
    start = anchor - timedelta(days=anchor.weekday())
    end = start + timedelta(days=7)
    return start.isoformat(), end.isoformat()


def upgrade() -> None:
    # --- media_transcoding_presets (admin catalog) ------------------------
    op.execute(
        """
        CREATE TABLE media_transcoding_presets (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            slug            text NOT NULL UNIQUE,
            name            jsonb NOT NULL DEFAULT '{}'::jsonb,
            target_kind     text NOT NULL CHECK (target_kind IN (
                'image','video','audio_tts','audio_human','video_hls',
                'ar_marker','ar_overlay','3d_model','document'
            )),
            ffmpeg_args     jsonb NOT NULL DEFAULT '{}'::jsonb,
            imgproxy_args   jsonb NOT NULL DEFAULT '{}'::jsonb,
            output_mime     text NOT NULL,
            max_dim         int,
            is_active       boolean NOT NULL DEFAULT true,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            CHECK (slug ~ '^[a-z0-9][a-z0-9_]*$'),
            CHECK (max_dim IS NULL OR max_dim > 0)
        );

        CREATE INDEX idx_media_presets_kind
            ON media_transcoding_presets(target_kind) WHERE is_active;

        CREATE TRIGGER tg_media_presets_updated_at
            BEFORE UPDATE ON media_transcoding_presets
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # Seed via jsonb_build_object to keep the SQL free of literal "value":NUMBER
    # JSON tokens that SQLAlchemy's text() parser would otherwise mistake for
    # bind parameters. Stylistic equivalent of the literal JSON we'd write by hand.
    op.execute(
        """
        INSERT INTO media_transcoding_presets
            (slug, name, target_kind, imgproxy_args, ffmpeg_args, output_mime, max_dim)
        VALUES
            ('thumb_256',
                jsonb_build_object('en','Thumbnail 256px WebP'),
                'image',
                jsonb_build_object('width',256,'quality',75,'format','webp'),
                '{}'::jsonb, 'image/webp', 256),
            ('medium_720',
                jsonb_build_object('en','Medium 720px WebP'),
                'image',
                jsonb_build_object('width',720,'quality',80,'format','webp'),
                '{}'::jsonb, 'image/webp', 720),
            ('avif_1080',
                jsonb_build_object('en','AVIF 1080px'),
                'image',
                jsonb_build_object('width',1080,'quality',60,'format','avif'),
                '{}'::jsonb, 'image/avif', 1080),
            ('poster_jpg',
                jsonb_build_object('en','JPEG poster (legacy fallback)'),
                'image',
                jsonb_build_object('width',1080,'quality',82,'format','jpg'),
                '{}'::jsonb, 'image/jpeg', 1080),
            ('hls_480',
                jsonb_build_object('en','HLS 480p H.264'),
                'video_hls',
                '{}'::jsonb,
                jsonb_build_object('vcodec','h264','vbitrate','800k','abitrate','96k'),
                'application/vnd.apple.mpegurl', 480),
            ('hls_720',
                jsonb_build_object('en','HLS 720p H.264'),
                'video_hls',
                '{}'::jsonb,
                jsonb_build_object('vcodec','h264','vbitrate','2000k','abitrate','128k'),
                'application/vnd.apple.mpegurl', 720),
            ('mp3_128k',
                jsonb_build_object('en','MP3 128kbps stereo'),
                'audio_tts',
                '{}'::jsonb,
                jsonb_build_object('acodec','libmp3lame','abitrate','128k','loudnorm','-16LUFS'),
                'audio/mpeg', NULL),
            ('opus_96k',
                jsonb_build_object('en','Opus 96kbps'),
                'audio_tts',
                '{}'::jsonb,
                jsonb_build_object('acodec','libopus','abitrate','96k','loudnorm','-16LUFS'),
                'audio/ogg', NULL);
        """
    )

    # --- media_transcoding_jobs (Celery FSM mirror) -----------------------
    # output_variant_id is a forward reference within the same migration —
    # nullable until the worker writes the result row.
    op.execute(
        """
        CREATE TABLE media_transcoding_jobs (
            id                  uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            asset_id            uuid NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
            preset_id           uuid NOT NULL REFERENCES media_transcoding_presets(id) ON DELETE RESTRICT,
            status              text NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending','processing','done','failed','cancelled')),
            attempts            int NOT NULL DEFAULT 0 CHECK (attempts >= 0),
            worker_id           text,
            error               text,
            started_at          timestamptz,
            finished_at         timestamptz,
            output_variant_id   uuid REFERENCES media_variants(id) ON DELETE SET NULL,
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now(),
            CHECK (finished_at IS NULL OR started_at IS NULL OR finished_at >= started_at)
        );

        CREATE INDEX idx_media_jobs_status
            ON media_transcoding_jobs(status, created_at) WHERE status IN ('pending','processing');
        CREATE INDEX idx_media_jobs_asset
            ON media_transcoding_jobs(asset_id);

        CREATE TRIGGER tg_media_jobs_updated_at
            BEFORE UPDATE ON media_transcoding_jobs
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE media_transcoding_jobs IS
            'Celery job mirror per Agent 4 §6.1 FSM: pending→processing→done|failed|cancelled. '
            'attempts >= 3 is policy-failed.';
        """
    )

    # --- media_lifecycle_events (append-only, partitioned by MONTH) -------
    # PRIMARY KEY must include the partition key (created_at) per PG rules.
    op.execute(
        """
        CREATE TABLE media_lifecycle_events (
            id              uuid NOT NULL DEFAULT gen_uuid_v7(),
            asset_id        uuid NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
            event_type      text NOT NULL CHECK (event_type IN (
                'uploaded','scan_passed','scan_failed','quarantined',
                'transcoded','published','cdn_invalidated','archived','deleted'
            )),
            actor_user_id   uuid,
            details         jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at      timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (id, created_at)
        ) PARTITION BY RANGE (created_at);

        CREATE INDEX idx_media_lifecycle_asset
            ON media_lifecycle_events (asset_id, created_at DESC);
        CREATE INDEX idx_media_lifecycle_event
            ON media_lifecycle_events (event_type, created_at DESC);

        COMMENT ON TABLE media_lifecycle_events IS
            'Append-only forensic timeline per Agent 4 §3.13. Partitioned monthly. '
            'No UPDATE/DELETE — enforced by app role grants in a later migration.';
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
            CREATE TABLE media_lifecycle_events_y{year}m{month:02d}
                PARTITION OF media_lifecycle_events
                FOR VALUES FROM ('{start}') TO ('{end}');
            """
        )

    # --- signed_url_grants (B2B forensics + anti-hotlink) -----------------
    # grantee_b2b_account_id is a forward reference: b2b_accounts ships in
    # Agent 6's migrations. We keep it as a nullable uuid column without an
    # FK constraint. A later migration will attach the FK.
    op.execute(
        """
        CREATE TABLE signed_url_grants (
            id                      uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            asset_id                uuid NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
            grantee_user_id         uuid,
            grantee_b2b_account_id  uuid,  -- forward FK → b2b_accounts (Agent 6)
            purpose                 text NOT NULL,
            expires_at              timestamptz NOT NULL,
            used_count              int NOT NULL DEFAULT 0 CHECK (used_count >= 0),
            max_uses                int CHECK (max_uses IS NULL OR max_uses > 0),
            client_ip               inet,
            user_agent_hash         bytea,
            created_at              timestamptz NOT NULL DEFAULT now(),
            revoked_at              timestamptz,
            CHECK (length(purpose) BETWEEN 1 AND 64),
            CHECK (max_uses IS NULL OR used_count <= max_uses)
        );

        CREATE INDEX idx_signed_url_expires
            ON signed_url_grants(expires_at) WHERE revoked_at IS NULL;
        CREATE INDEX idx_signed_url_user
            ON signed_url_grants(grantee_user_id) WHERE grantee_user_id IS NOT NULL;
        CREATE INDEX idx_signed_url_b2b
            ON signed_url_grants(grantee_b2b_account_id)
            WHERE grantee_b2b_account_id IS NOT NULL;
        CREATE INDEX idx_signed_url_asset
            ON signed_url_grants(asset_id, created_at DESC);

        COMMENT ON TABLE signed_url_grants IS
            'Per-issue audit row for every pre-signed URL handed out. Agent 4 §3.14: '
            'without this most teams have no B2B abuse forensics six months later.';
        COMMENT ON COLUMN signed_url_grants.grantee_b2b_account_id IS
            'Forward reference to b2b_accounts (Agent 6). No FK until that migration ships.';
        """
    )

    # --- cdn_invalidations (cache-purge log) ------------------------------
    op.execute(
        """
        CREATE TABLE cdn_invalidations (
            id                  uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            asset_id            uuid REFERENCES media_assets(id) ON DELETE SET NULL,
            cdn_provider        text NOT NULL CHECK (cdn_provider IN
                ('cloudflare','bunny','r2','fastly','minio')),
            key_pattern         text NOT NULL,
            status              text NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending','done','failed')),
            provider_request_id text,
            requested_at        timestamptz NOT NULL DEFAULT now(),
            completed_at        timestamptz,
            error               text,
            CHECK (length(key_pattern) BETWEEN 1 AND 1024),
            CHECK (completed_at IS NULL OR completed_at >= requested_at)
        );

        CREATE INDEX idx_cdn_invalidations_pending
            ON cdn_invalidations(requested_at) WHERE status = 'pending';
        CREATE INDEX idx_cdn_invalidations_asset
            ON cdn_invalidations(asset_id) WHERE asset_id IS NOT NULL;

        COMMENT ON TABLE cdn_invalidations IS
            'Cache-purge audit per Agent 4 §9.2. asset_id is nullable because some '
            'invalidations are bulk (tag-based or prefix-based across many assets).';
        """
    )

    # --- media_usage_log (partitioned by WEEK; B2B billing source) --------
    # PRIMARY KEY must include accessed_at (partition key) per PG rules.
    op.execute(
        """
        CREATE TABLE media_usage_log (
            id                  uuid NOT NULL DEFAULT gen_uuid_v7(),
            asset_id            uuid NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
            accessor_user_id    uuid,
            b2b_account_id      uuid,  -- forward FK → b2b_accounts (Agent 6)
            accessed_at         timestamptz NOT NULL DEFAULT now(),
            byte_count          bigint NOT NULL CHECK (byte_count >= 0),
            status_code         smallint NOT NULL,
            referrer            text,
            served_by           text CHECK (served_by IN ('cdn','origin')),
            client_country      char(2),
            PRIMARY KEY (id, accessed_at)
        ) PARTITION BY RANGE (accessed_at);

        CREATE INDEX idx_media_usage_asset
            ON media_usage_log (asset_id, accessed_at DESC);
        CREATE INDEX idx_media_usage_b2b
            ON media_usage_log (b2b_account_id, accessed_at DESC)
            WHERE b2b_account_id IS NOT NULL;
        CREATE INDEX idx_media_usage_user
            ON media_usage_log (accessor_user_id, accessed_at DESC)
            WHERE accessor_user_id IS NOT NULL;

        COMMENT ON TABLE media_usage_log IS
            'Origin-hit log per Agent 4 §3.14. Partitioned weekly because B2B billing '
            'aggregates roll up by week and old partitions can be archived to ClickHouse.';
        """
    )

    # Provision ±2 weeks of weekly partitions.
    today = date.today()
    for offset in range(-2, 3):
        anchor = today + timedelta(days=7 * offset)
        start, end = _week_bounds(anchor)
        # Build a stable partition suffix from the ISO week start.
        suffix = start.replace("-", "")
        op.execute(
            f"""
            CREATE TABLE media_usage_log_w{suffix}
                PARTITION OF media_usage_log
                FOR VALUES FROM ('{start}') TO ('{end}');
            """
        )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS media_usage_log CASCADE;")
    op.execute("DROP TABLE IF EXISTS cdn_invalidations CASCADE;")
    op.execute("DROP TABLE IF EXISTS signed_url_grants CASCADE;")
    op.execute("DROP TABLE IF EXISTS media_lifecycle_events CASCADE;")
    op.execute("DROP TABLE IF EXISTS media_transcoding_jobs CASCADE;")
    op.execute("DROP TABLE IF EXISTS media_transcoding_presets CASCADE;")
