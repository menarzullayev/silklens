"""Embedding tables per (target, model_family, dimension) + RAG chunks + regen jobs

Per Agent 3 §5: vectors from different model families are non-interchangeable
(cosine distance between CLIP-768 and e5-1024 is meaningless), so we physically
separate embedding tables per ``(target_kind, model_family, dimension)``. This
also keeps each HNSW index small and cache-hot.

Tables (5):
    embeddings_heritage_text_e5_1024      heritage description / summary vectors
    embeddings_heritage_image_clip_768    heritage hero / curated image vectors
    embeddings_media_image_clip_768       user-uploaded image vectors
    embeddings_chunks_text_e5_1024        RAG chunks (heritage long-form / reviews / articles)
    embedding_regeneration_jobs           bookkeeping when a model version flips current

HNSW parameters (m=16, ef_construction=200) are the Agent 3 §4 baseline; the
recall/latency curve is measured by the FAZA 4 benchmark suite and overridden
per-table only when warranted.

Revision ID: 0031_embeddings
Revises: 0030_ai_registry
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0031_embeddings"
down_revision: str | Sequence[str] | None = "0030_ai_registry"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- embeddings_heritage_text_e5_1024 ---------------------------------
    op.execute(
        """
        CREATE TABLE embeddings_heritage_text_e5_1024 (
            id                  uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            heritage_id         uuid NOT NULL REFERENCES heritage_objects(id) ON DELETE CASCADE,
            model_version_id    uuid NOT NULL REFERENCES ai_model_versions(id) ON DELETE RESTRICT,
            language_tag        text NOT NULL,
            embedding           vector(1024) NOT NULL,
            source_text_hash    bytea NOT NULL,
            chunk_index         int NOT NULL DEFAULT 0,
            created_at          timestamptz NOT NULL DEFAULT now(),
            UNIQUE (heritage_id, model_version_id, language_tag, chunk_index),
            CHECK (octet_length(source_text_hash) = 32),
            CHECK (chunk_index >= 0),
            CHECK (length(language_tag) BETWEEN 2 AND 32)
        );

        CREATE INDEX idx_eh_text_e5_1024_hnsw
            ON embeddings_heritage_text_e5_1024
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 200);

        CREATE INDEX idx_eh_text_e5_1024_heritage
            ON embeddings_heritage_text_e5_1024(heritage_id);
        CREATE INDEX idx_eh_text_e5_1024_lang
            ON embeddings_heritage_text_e5_1024(language_tag);
        CREATE INDEX idx_eh_text_e5_1024_model
            ON embeddings_heritage_text_e5_1024(model_version_id);

        COMMENT ON TABLE embeddings_heritage_text_e5_1024 IS
            'Per-heritage, per-language text embeddings via multilingual-e5-large. '
            'Source is heritage_objects.summary_md / description_md / name (chunk_index 0 = full).';
        """
    )

    # --- embeddings_heritage_image_clip_768 -------------------------------
    # Hero image embedding for visually similar heritage. media_asset_id is
    # nullable (some heritage rows have no hero yet) and ON DELETE SET NULL
    # so deleting an asset doesn't lose the embedding history.
    op.execute(
        """
        CREATE TABLE embeddings_heritage_image_clip_768 (
            id                  uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            heritage_id         uuid NOT NULL REFERENCES heritage_objects(id) ON DELETE CASCADE,
            media_asset_id      uuid REFERENCES media_assets(id) ON DELETE SET NULL,
            model_version_id    uuid NOT NULL REFERENCES ai_model_versions(id) ON DELETE RESTRICT,
            embedding           vector(768) NOT NULL,
            created_at          timestamptz NOT NULL DEFAULT now(),
            UNIQUE (heritage_id, media_asset_id, model_version_id)
        );

        CREATE INDEX idx_eh_image_clip_768_hnsw
            ON embeddings_heritage_image_clip_768
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 200);

        CREATE INDEX idx_eh_image_clip_768_heritage
            ON embeddings_heritage_image_clip_768(heritage_id);
        CREATE INDEX idx_eh_image_clip_768_model
            ON embeddings_heritage_image_clip_768(model_version_id);
        """
    )

    # --- embeddings_media_image_clip_768 ----------------------------------
    op.execute(
        """
        CREATE TABLE embeddings_media_image_clip_768 (
            media_asset_id      uuid PRIMARY KEY REFERENCES media_assets(id) ON DELETE CASCADE,
            model_version_id    uuid NOT NULL REFERENCES ai_model_versions(id) ON DELETE RESTRICT,
            embedding           vector(768) NOT NULL,
            created_at          timestamptz NOT NULL DEFAULT now()
        );

        CREATE INDEX idx_em_image_clip_768_hnsw
            ON embeddings_media_image_clip_768
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 200);

        CREATE INDEX idx_em_image_clip_768_model
            ON embeddings_media_image_clip_768(model_version_id);

        COMMENT ON TABLE embeddings_media_image_clip_768 IS
            'Per-media-asset CLIP-768 image embeddings. Powers visual search '
            'and ''photos similar to this one'' (Agent 3 §6 hybrid retrieval).';
        """
    )

    # --- embeddings_chunks_text_e5_1024 (RAG corpus) -----------------------
    # heritage_id is nullable: this table can also store chunks of reviews,
    # articles, or external docs that aren't owned by a specific heritage row.
    op.execute(
        """
        CREATE TABLE embeddings_chunks_text_e5_1024 (
            id                  uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            heritage_id         uuid REFERENCES heritage_objects(id) ON DELETE CASCADE,
            source_kind         text NOT NULL
                CHECK (source_kind IN ('heritage_description','heritage_summary','review','article')),
            source_id           uuid NOT NULL,
            language_tag        text NOT NULL,
            chunk_text          text NOT NULL,
            chunk_index         int NOT NULL,
            model_version_id    uuid NOT NULL REFERENCES ai_model_versions(id) ON DELETE RESTRICT,
            embedding           vector(1024) NOT NULL,
            created_at          timestamptz NOT NULL DEFAULT now(),
            UNIQUE (source_kind, source_id, language_tag, chunk_index, model_version_id),
            CHECK (chunk_index >= 0),
            CHECK (length(language_tag) BETWEEN 2 AND 32),
            CHECK (length(chunk_text) > 0)
        );

        CREATE INDEX idx_ec_text_e5_1024_hnsw
            ON embeddings_chunks_text_e5_1024
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 200);

        CREATE INDEX idx_ec_text_e5_1024_source
            ON embeddings_chunks_text_e5_1024(source_kind, source_id);
        CREATE INDEX idx_ec_text_e5_1024_heritage
            ON embeddings_chunks_text_e5_1024(heritage_id)
            WHERE heritage_id IS NOT NULL;
        CREATE INDEX idx_ec_text_e5_1024_lang
            ON embeddings_chunks_text_e5_1024(language_tag);

        COMMENT ON TABLE embeddings_chunks_text_e5_1024 IS
            'RAG corpus chunks. heritage_id is nullable so the same table can also '
            'host review/article chunks. source_id+source_kind identifies the parent row.';
        """
    )

    # --- embedding_regeneration_jobs --------------------------------------
    op.execute(
        """
        CREATE TABLE embedding_regeneration_jobs (
            id                  uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            model_version_id    uuid NOT NULL REFERENCES ai_model_versions(id) ON DELETE CASCADE,
            target_table        text NOT NULL,
            status              text NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending','running','done','failed')),
            rows_total          bigint,
            rows_done           bigint NOT NULL DEFAULT 0,
            error               text,
            created_at          timestamptz NOT NULL DEFAULT now(),
            started_at          timestamptz,
            finished_at         timestamptz,
            CHECK (rows_total IS NULL OR rows_total >= 0),
            CHECK (rows_done >= 0),
            CHECK (rows_total IS NULL OR rows_done <= rows_total),
            CHECK (target_table ~ '^[a-z][a-z0-9_]*$')
        );

        CREATE INDEX idx_embedding_regen_active
            ON embedding_regeneration_jobs(status, created_at DESC)
            WHERE status IN ('pending','running');
        CREATE INDEX idx_embedding_regen_model
            ON embedding_regeneration_jobs(model_version_id, created_at DESC);

        COMMENT ON TABLE embedding_regeneration_jobs IS
            'Bookkeeping when ai_model_versions.is_current flips: a new job row '
            'is created per affected embedding table, and a background worker '
            'backfills rows_done until target_table converges to the new model.';
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS embedding_regeneration_jobs CASCADE;")
    op.execute("DROP TABLE IF EXISTS embeddings_chunks_text_e5_1024 CASCADE;")
    op.execute("DROP TABLE IF EXISTS embeddings_media_image_clip_768 CASCADE;")
    op.execute("DROP TABLE IF EXISTS embeddings_heritage_image_clip_768 CASCADE;")
    op.execute("DROP TABLE IF EXISTS embeddings_heritage_text_e5_1024 CASCADE;")
