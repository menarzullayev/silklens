"""heritage_facts (atomic claims) + heritage_provenance (sources)

Per Agent 1 core-domain architecture §2-§3, this is the *invented* atomic
provenance system:

  heritage_facts        — quintuples (entity, predicate, value, confidence, source)
  heritage_provenance   — sources (URL, citation, contributor)
  fact_provenance       — many-to-many linkage

Denormalized winners go to heritage_objects (name, summary, dates, coordinates).
A background job (FAZA 2+) recomputes heritage_objects.confidence_score and
'winning' values from this table. The schema supports both fully and is the
schema-level answer to the "politically disputed heritage" risk from Agent 1's
Risks section.

Revision ID: 0011_heritage_facts
Revises: 0010_heritage_core
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0011_heritage_facts"
down_revision: str | Sequence[str] | None = "0010_heritage_core"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- heritage_provenance (sources catalog) ----------------------------
    op.execute(
        """
        CREATE TABLE heritage_provenance (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            slug            text NOT NULL UNIQUE,
            kind            text NOT NULL CHECK (kind IN (
                'wikipedia','wikidata','wikimedia_commons','unesco','openstreetmap',
                'scholarly_article','book','government','museum','expert','user_upload',
                'ai_generated','manual_entry','partner_api','field_observation'
            )),
            citation        jsonb NOT NULL DEFAULT '{}'::jsonb,
            url             text,
            language_tag    text,
            license         text,
            trust_score     smallint NOT NULL DEFAULT 50
                CHECK (trust_score BETWEEN 0 AND 100),
            retrieved_at    timestamptz,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            CHECK (slug ~ '^[a-z0-9][a-z0-9_-]*$')
        );

        CREATE INDEX idx_heritage_provenance_kind ON heritage_provenance(kind);
        CREATE TRIGGER tg_heritage_provenance_updated_at
            BEFORE UPDATE ON heritage_provenance
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE heritage_provenance IS
            'Source catalog. Every heritage_fact must cite at least one row here.';
        """
    )

    # --- heritage_facts (atomic claims) -----------------------------------
    op.execute(
        """
        CREATE TABLE heritage_facts (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            heritage_id     uuid NOT NULL REFERENCES heritage_objects(id) ON DELETE CASCADE,
            predicate       text NOT NULL,
            object_value    jsonb NOT NULL,
            object_text     text,
            language_tag    text,
            confidence      smallint NOT NULL DEFAULT 50
                CHECK (confidence BETWEEN 0 AND 100),
            is_winning      boolean NOT NULL DEFAULT false,
            is_disputed     boolean NOT NULL DEFAULT false,
            asserted_by     uuid,
            asserted_at     timestamptz NOT NULL DEFAULT now(),
            superseded_at   timestamptz,
            metadata        jsonb NOT NULL DEFAULT '{}'::jsonb,
            CHECK (predicate ~ '^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*)*$'),
            CHECK (superseded_at IS NULL OR superseded_at > asserted_at)
        );

        -- At most one winning fact per (heritage, predicate, language) at a time.
        CREATE UNIQUE INDEX uq_heritage_facts_winner
            ON heritage_facts (heritage_id, predicate, COALESCE(language_tag, ''))
            WHERE is_winning AND superseded_at IS NULL;

        CREATE INDEX idx_heritage_facts_heritage
            ON heritage_facts(heritage_id, predicate);
        CREATE INDEX idx_heritage_facts_disputed
            ON heritage_facts(heritage_id)
            WHERE is_disputed AND superseded_at IS NULL;
        CREATE INDEX idx_heritage_facts_predicate
            ON heritage_facts(predicate)
            WHERE superseded_at IS NULL;

        COMMENT ON TABLE heritage_facts IS
            'Atomic provenance-tagged claims. predicate uses dot.notation '
            '(e.g. ''founded_year'', ''name.uz'', ''architect''). '
            'is_winning is computed by the fact-resolver job from confidence + source trust.';
        COMMENT ON COLUMN heritage_facts.is_disputed IS
            'true → multiple high-confidence conflicting facts. Presentation '
            'layer chooses what to show per Agent 1 §10 risk #2.';
        """
    )

    # --- fact_provenance (M:N linkage with per-link confidence) -----------
    op.execute(
        """
        CREATE TABLE fact_provenance (
            fact_id         uuid NOT NULL REFERENCES heritage_facts(id) ON DELETE CASCADE,
            provenance_id   uuid NOT NULL REFERENCES heritage_provenance(id) ON DELETE RESTRICT,
            citation_detail text,
            page_or_locator text,
            confidence      smallint NOT NULL DEFAULT 80
                CHECK (confidence BETWEEN 0 AND 100),
            created_at      timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (fact_id, provenance_id)
        );

        CREATE INDEX idx_fact_provenance_provenance
            ON fact_provenance(provenance_id);

        COMMENT ON TABLE fact_provenance IS
            'M:N — one fact can be cited by multiple sources; one source can cite many facts.';
        """
    )

    # --- Seed common provenance sources ----------------------------------
    op.execute(
        """
        INSERT INTO heritage_provenance (slug, kind, citation, url, trust_score) VALUES
            ('wikipedia',         'wikipedia',         '{"name":"Wikipedia"}'::jsonb,
             'https://en.wikipedia.org', 60),
            ('wikidata',          'wikidata',          '{"name":"Wikidata"}'::jsonb,
             'https://www.wikidata.org', 75),
            ('wikimedia_commons', 'wikimedia_commons', '{"name":"Wikimedia Commons"}'::jsonb,
             'https://commons.wikimedia.org', 70),
            ('unesco_whc',        'unesco',
             '{"name":"UNESCO World Heritage Centre"}'::jsonb,
             'https://whc.unesco.org', 95),
            ('openstreetmap',     'openstreetmap',     '{"name":"OpenStreetMap"}'::jsonb,
             'https://www.openstreetmap.org', 70),
            ('claude_ai',         'ai_generated',
             '{"name":"Claude (Anthropic)"}'::jsonb, NULL, 40),
            ('manual_admin',      'manual_entry',
             '{"name":"Manual admin entry"}'::jsonb, NULL, 85);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS fact_provenance CASCADE;")
    op.execute("DROP TABLE IF EXISTS heritage_facts CASCADE;")
    op.execute("DROP TABLE IF EXISTS heritage_provenance CASCADE;")
