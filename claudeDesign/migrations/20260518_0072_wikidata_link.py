"""wikidata link columns on heritage_objects + ingestion event seeds

Wave-5 Agent E (search indexer + Wikidata ingestion) attaches two cheap
lookup-side columns to ``heritage_objects`` so the ingestion job can detect
"already imported" without scanning ``heritage_facts``:

  - ``wikidata_qid``  text UNIQUE       — canonical Q-id (e.g. Q200583)
  - ``wikipedia_url_by_lang`` jsonb     — {"en": "https://en.wikipedia.org/wiki/...",
                                          "uz": "https://uz.wikipedia.org/wiki/..."}

Both nullable so existing rows keep working. The unique constraint on QID is
what makes ``import_one`` idempotent.

Also seeds two ingestion events into ``event_types`` (so the importer can
emit without the registry rejecting unknown names per Agent 7 §3.5).

Revision ID: 0072_wikidata_link
Revises: 0062_security_patches
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0072_wikidata_link"
down_revision: str | Sequence[str] | None = "0062_security_patches"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE heritage_objects
            ADD COLUMN IF NOT EXISTS wikidata_qid text,
            ADD COLUMN IF NOT EXISTS wikipedia_url_by_lang jsonb
                NOT NULL DEFAULT '{}'::jsonb;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE schemaname = 'public'
                  AND indexname = 'uq_heritage_objects_wikidata_qid'
            ) THEN
                CREATE UNIQUE INDEX uq_heritage_objects_wikidata_qid
                    ON heritage_objects (wikidata_qid)
                    WHERE wikidata_qid IS NOT NULL;
            END IF;
        END$$;
        """
    )
    op.execute(
        """
        ALTER TABLE heritage_objects
            ADD CONSTRAINT chk_heritage_wikidata_qid
            CHECK (wikidata_qid IS NULL OR wikidata_qid ~ '^Q[1-9][0-9]*$');
        """
    )

    # Seed the ingestion + search-sync events so emitters never trip the
    # event_types registry hard-fail at runtime. The catalog schema (migration
    # 0008) only carries (event_name, display_name, retention_days,
    # kafka_topic, ...) — keep this insert aligned with that.
    op.execute(
        """
        INSERT INTO event_types (event_name, display_name, retention_days, kafka_topic)
        VALUES
            ('heritage.imported.v1',
             '{"en": "Heritage imported from external source"}'::jsonb,
             365, 'heritage.imported.v1'),
            ('search.indexed.v1',
             '{"en": "Heritage indexed into Elasticsearch"}'::jsonb,
             90, 'search.indexed.v1')
        ON CONFLICT (event_name) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM event_types
        WHERE event_name IN ('heritage.imported.v1', 'search.indexed.v1');
        """
    )
    op.execute("ALTER TABLE heritage_objects DROP CONSTRAINT IF EXISTS chk_heritage_wikidata_qid;")
    op.execute("DROP INDEX IF EXISTS uq_heritage_objects_wikidata_qid;")
    op.execute(
        """
        ALTER TABLE heritage_objects
            DROP COLUMN IF EXISTS wikipedia_url_by_lang,
            DROP COLUMN IF EXISTS wikidata_qid;
        """
    )
