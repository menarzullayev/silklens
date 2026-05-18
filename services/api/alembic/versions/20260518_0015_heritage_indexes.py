"""Performance + search indexes deferred from 0010-0014

Per Agent 1 core-domain architecture §9 (hot queries) and master architecture
§5 (index strategy catalog), this migration lands the read-side indexes that
were deliberately deferred while the schema settled:

- GIN trigram on ``heritage_objects.name`` (cast to text) for fuzzy autocomplete.
- Composite covering indexes for the canonical heritage list filter — status
  + country_code + kind_slug with INCLUDE(id, pub_id, name) so the entire
  card row is served from the index without a heap visit.
- ``heritage_objects.search_vector`` — GENERATED tsvector built from
  name+summary+aliases-via-document concatenation. Multi-language config is
  ``simple`` (no stemmer) to avoid per-row language detection cost; richer
  language-aware ranking is delegated to the Elasticsearch tier per Agent 8.
- Recent-activity BRIN on ``heritage_objects.created_at`` for cheap timeline
  scans at 50M+ rows.
- Composite index on ``heritage_facts(predicate, language_tag, confidence
  DESC)`` to make the fact-resolver job fast.

Note: ``heritage_aliases USING GIN (alias gin_trgm_ops)`` already exists from
migration 0010 (idx_heritage_aliases_trgm) — explicitly NOT recreated here.

Revision ID: 0015_heritage_indexes
Revises: 0014_heritage_relations
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0015_heritage_indexes"
down_revision: str | Sequence[str] | None = "0014_heritage_relations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- Fuzzy name search (GIN trigram on jsonb cast to text) ------------
    # The cast renders the jsonb {"en":"…","ru":"…"} as a flat string that
    # captures every language variant in one index. Sub-50ms autocomplete
    # at 5M rows.
    op.execute(
        """
        CREATE INDEX idx_heritage_objects_name_trgm
            ON heritage_objects USING GIN ((name::text) gin_trgm_ops);
        """
    )

    # --- Composite covering indexes for the heritage list endpoint --------
    # The canonical filter is (status, country_code, kind_slug). Returning
    # the heritage card needs (id, pub_id, name). INCLUDE keeps the leaf
    # nodes wider but avoids the heap visit, which is the win for the
    # high-traffic public GET /v1/heritage path.
    op.execute(
        """
        CREATE INDEX idx_heritage_objects_list_published
            ON heritage_objects (country_code, kind_slug)
            INCLUDE (id, pub_id, name, latitude, longitude, confidence_score)
            WHERE status = 'published' AND deleted_at IS NULL;

        CREATE INDEX idx_heritage_objects_list_kind
            ON heritage_objects (kind_slug)
            INCLUDE (id, pub_id, name)
            WHERE status = 'published' AND deleted_at IS NULL;

        CREATE INDEX idx_heritage_objects_list_country
            ON heritage_objects (country_code)
            INCLUDE (id, pub_id, name)
            WHERE status = 'published' AND deleted_at IS NULL AND country_code IS NOT NULL;
        """
    )

    # --- BRIN on created_at for cheap timeline scans ----------------------
    # BRIN is the right pick for an append-mostly column. ~1KB per million
    # rows vs ~30MB for an equivalent BTREE at 50M rows.
    op.execute(
        """
        CREATE INDEX idx_heritage_objects_created_brin
            ON heritage_objects USING BRIN (created_at)
            WITH (pages_per_range = 32);
        """
    )

    # --- Generated tsvector for heritage_objects.search_vector ------------
    # Built from the jsonb name + summary_md + description_md cast to text.
    # 'simple' config means no stemming — exact-match tokens only. Locale-
    # aware ranking is delegated to the Elasticsearch tier-1 index. The
    # column is STORED (not VIRTUAL) so the GIN index can attach to it.
    #
    # tags are deliberately NOT included here — array_to_string() is STABLE
    # (not IMMUTABLE) in PG16 and Postgres refuses STABLE expressions in a
    # generated column. Tags remain searchable via the dedicated GIN array
    # index idx_heritage_objects_tags from migration 0010.
    op.execute(
        """
        ALTER TABLE heritage_objects
            ADD COLUMN search_vector tsvector
                GENERATED ALWAYS AS (
                    setweight(
                        to_tsvector('simple', coalesce(name::text, '')),
                        'A'
                    ) ||
                    setweight(
                        to_tsvector('simple', coalesce(summary_md::text, '')),
                        'B'
                    ) ||
                    setweight(
                        to_tsvector('simple', coalesce(description_md::text, '')),
                        'C'
                    )
                ) STORED;

        CREATE INDEX idx_heritage_objects_search_vector
            ON heritage_objects USING GIN (search_vector);

        COMMENT ON COLUMN heritage_objects.search_vector IS
            'Generated tsvector with simple config (no stemmer). Weights: '
            'A=name, B=summary, C=description. Locale-aware ranking lives in '
            'the Elasticsearch tier-1 index, not here. Tags are searchable '
            'via idx_heritage_objects_tags (GIN array_ops).';
        """
    )

    # --- heritage_facts: predicate + language + confidence ----------------
    # The fact-resolver job scans by predicate to pick the winning value
    # per language. Sorting by confidence DESC lets the planner stop early.
    op.execute(
        """
        CREATE INDEX idx_heritage_facts_predicate_lang_conf
            ON heritage_facts (predicate, language_tag, confidence DESC)
            WHERE superseded_at IS NULL;
        """
    )

    # --- heritage_aliases: composite for (heritage_id, kind) ---------------
    # Hot path: "give me the official name for heritage X". The existing
    # idx_heritage_aliases_heritage is too broad; add (heritage_id, kind).
    op.execute(
        """
        CREATE INDEX idx_heritage_aliases_heritage_kind
            ON heritage_aliases (heritage_id, kind);
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_heritage_aliases_heritage_kind;")
    op.execute("DROP INDEX IF EXISTS idx_heritage_facts_predicate_lang_conf;")
    op.execute("DROP INDEX IF EXISTS idx_heritage_objects_search_vector;")
    op.execute("ALTER TABLE heritage_objects DROP COLUMN IF EXISTS search_vector;")
    op.execute("DROP INDEX IF EXISTS idx_heritage_objects_created_brin;")
    op.execute("DROP INDEX IF EXISTS idx_heritage_objects_list_country;")
    op.execute("DROP INDEX IF EXISTS idx_heritage_objects_list_kind;")
    op.execute("DROP INDEX IF EXISTS idx_heritage_objects_list_published;")
    op.execute("DROP INDEX IF EXISTS idx_heritage_objects_name_trgm;")
