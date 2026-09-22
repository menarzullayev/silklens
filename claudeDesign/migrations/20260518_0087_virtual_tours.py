"""Virtual tour infrastructure — tables, indexes, seed collections.

FAZA 6 — Wave-8 Agent-3.

Creates:
- virtual_tours          (tour catalogue, WebGL viewer URL, i18n title/desc)
- virtual_tour_scenes    (ordered scenes, GLB/GLTF model refs, hotspot JSON)
- virtual_tour_progress  (per-user progress, composite PK)
- virtual_tour_collections  (thematic playlists)
- virtual_tour_collection_items  (m2m join, ordered)

Seeds 3 starter collections: Ancient Wonders / Silk Road Journey / UNESCO Highlights.

Revision ID: 0087_virtual_tours
Revises: 0081_central_asia_currencies
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0087_virtual_tours"
down_revision: str | Sequence[str] | None = "0081_central_asia_currencies"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. virtual_tours
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE virtual_tours (
            id                  uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            heritage_id         uuid REFERENCES heritage_objects(id) ON DELETE SET NULL,
            tenant_id           uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            slug                text NOT NULL UNIQUE,
            title               jsonb NOT NULL DEFAULT '{}'::jsonb,
            description_md      jsonb NOT NULL DEFAULT '{}'::jsonb,
            kind                text NOT NULL CHECK (kind IN (
                                    'museum_walkthrough',
                                    'site_flythrough',
                                    'room_exploration',
                                    'timeline_3d'
                                )),
            status              text NOT NULL DEFAULT 'draft' CHECK (status IN (
                                    'draft','processing','published','archived'
                                )),
            thumbnail_media_id  uuid REFERENCES media_assets(id) ON DELETE SET NULL,
            tour_duration_seconds int,
            viewer_url          text,
            embed_code          text,
            view_count          bigint NOT NULL DEFAULT 0,
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now(),
            deleted_at          timestamptz
        );
        """
    )
    op.execute(
        """
        CREATE INDEX ix_virtual_tours_tenant ON virtual_tours(tenant_id);
        CREATE INDEX ix_virtual_tours_heritage ON virtual_tours(heritage_id)
            WHERE heritage_id IS NOT NULL;
        CREATE INDEX ix_virtual_tours_status ON virtual_tours(status)
            WHERE deleted_at IS NULL;
        CREATE INDEX ix_virtual_tours_kind ON virtual_tours(kind)
            WHERE deleted_at IS NULL;
        """
    )
    op.execute(
        """
        DROP TRIGGER IF EXISTS tg_virtual_tours_updated_at ON virtual_tours;
        CREATE TRIGGER tg_virtual_tours_updated_at
            BEFORE UPDATE ON virtual_tours
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # ------------------------------------------------------------------
    # 2. virtual_tour_scenes
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE virtual_tour_scenes (
            id                  uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            tour_id             uuid NOT NULL REFERENCES virtual_tours(id) ON DELETE CASCADE,
            scene_order         int NOT NULL,
            title               jsonb NOT NULL DEFAULT '{}'::jsonb,
            description_md      jsonb NOT NULL DEFAULT '{}'::jsonb,
            panorama_media_id   uuid REFERENCES media_assets(id) ON DELETE SET NULL,
            model_3d_asset_id   uuid REFERENCES media_assets(id) ON DELETE SET NULL,
            hotspot_data        jsonb NOT NULL DEFAULT '[]'::jsonb,
            audio_guide_media_id uuid REFERENCES media_assets(id) ON DELETE SET NULL,
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now(),
            UNIQUE (tour_id, scene_order)
        );
        """
    )
    op.execute(
        """
        CREATE INDEX ix_virtual_tour_scenes_tour ON virtual_tour_scenes(tour_id);
        """
    )
    op.execute(
        """
        DROP TRIGGER IF EXISTS tg_virtual_tour_scenes_updated_at ON virtual_tour_scenes;
        CREATE TRIGGER tg_virtual_tour_scenes_updated_at
            BEFORE UPDATE ON virtual_tour_scenes
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # ------------------------------------------------------------------
    # 3. virtual_tour_progress
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE virtual_tour_progress (
            user_id             uuid NOT NULL,
            residency_region    text NOT NULL,
            tour_id             uuid NOT NULL REFERENCES virtual_tours(id) ON DELETE CASCADE,
            last_scene_order    int NOT NULL DEFAULT 0,
            completed           bool NOT NULL DEFAULT false,
            started_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (user_id, residency_region, tour_id)
        );
        """
    )
    op.execute(
        """
        CREATE INDEX ix_virtual_tour_progress_tour ON virtual_tour_progress(tour_id);
        """
    )
    op.execute(
        """
        DROP TRIGGER IF EXISTS tg_virtual_tour_progress_updated_at ON virtual_tour_progress;
        CREATE TRIGGER tg_virtual_tour_progress_updated_at
            BEFORE UPDATE ON virtual_tour_progress
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # ------------------------------------------------------------------
    # 4. virtual_tour_collections
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE virtual_tour_collections (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            tenant_id       uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            slug            text NOT NULL,
            title           jsonb NOT NULL DEFAULT '{}'::jsonb,
            description_md  jsonb NOT NULL DEFAULT '{}'::jsonb,
            is_featured     bool NOT NULL DEFAULT false,
            sort_order      int NOT NULL DEFAULT 0,
            created_at      timestamptz NOT NULL DEFAULT now(),
            UNIQUE (tenant_id, slug)
        );
        """
    )
    op.execute(
        """
        CREATE INDEX ix_virtual_tour_collections_tenant ON virtual_tour_collections(tenant_id);
        CREATE INDEX ix_virtual_tour_collections_featured
            ON virtual_tour_collections(is_featured, sort_order)
            WHERE is_featured = true;
        """
    )

    # ------------------------------------------------------------------
    # 5. virtual_tour_collection_items
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE virtual_tour_collection_items (
            collection_id   uuid NOT NULL REFERENCES virtual_tour_collections(id) ON DELETE CASCADE,
            tour_id         uuid NOT NULL REFERENCES virtual_tours(id) ON DELETE CASCADE,
            item_order      int NOT NULL DEFAULT 0,
            PRIMARY KEY (collection_id, tour_id)
        );
        """
    )
    op.execute(
        """
        CREATE INDEX ix_vt_collection_items_tour ON virtual_tour_collection_items(tour_id);
        """
    )

    # ------------------------------------------------------------------
    # 6. Seed 3 starter collections (default tenant)
    # ------------------------------------------------------------------
    op.execute(
        """
        INSERT INTO virtual_tour_collections
            (tenant_id, slug, title, description_md, is_featured, sort_order)
        SELECT
            '00000000-0000-0000-0000-000000000001'::uuid,
            col.slug,
            col.title::jsonb,
            col.description::jsonb,
            true,
            col.sort_order
        FROM (VALUES
            (
                'ancient-wonders',
                '{"en":"Ancient Wonders","uz":"Qadimiy Mo''jizalar","ru":"Древние чудеса"}',
                '{"en":"Explore the world''s greatest ancient monuments in immersive 3D.","uz":"Dunyoning eng buyuk qadimiy yodgorliklarini 3D formatida o''rganing."}',
                10
            ),
            (
                'silk-road-journey',
                '{"en":"Silk Road Journey","uz":"Ipak Yo''li Sayohati","ru":"Путешествие по Шёлковому пути"}',
                '{"en":"Walk the ancient trade routes connecting East and West.","uz":"Sharq va G''arbni bog''lagan qadimiy savdo yo''llari bo''ylab yuring."}',
                20
            ),
            (
                'unesco-highlights',
                '{"en":"UNESCO Highlights","uz":"YUNESKO Durdonalari","ru":"Достопримечательности ЮНЕСКО"}',
                '{"en":"Curated tours of UNESCO World Heritage sites.","uz":"YuNESKO Butunjahon merosi ob''ektlarining tanlangan ekskursiyalari."}',
                30
            )
        ) AS col(slug, title, description, sort_order)
        ON CONFLICT (tenant_id, slug) DO NOTHING;
        """
    )

    # Register virtual_tour domain events
    op.execute(
        """
        INSERT INTO event_types (event_name, display_name) VALUES
            ('virtual_tour.created.v1',   '{"en":"Virtual tour created"}'::jsonb),
            ('virtual_tour.published.v1', '{"en":"Virtual tour published"}'::jsonb),
            ('virtual_tour.progress.v1',  '{"en":"User tour progress recorded"}'::jsonb)
        ON CONFLICT (event_name) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM event_types WHERE event_name LIKE 'virtual_tour.%';"
    )
    op.execute("DROP TABLE IF EXISTS virtual_tour_collection_items;")
    op.execute("DROP TABLE IF EXISTS virtual_tour_collections;")
    op.execute("DROP TABLE IF EXISTS virtual_tour_progress;")
    op.execute("DROP TABLE IF EXISTS virtual_tour_scenes;")
    op.execute("DROP TABLE IF EXISTS virtual_tours;")
