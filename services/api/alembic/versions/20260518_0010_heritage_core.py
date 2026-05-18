"""heritage_objects (root polymorphic) + aliases + revisions (bi-temporal)

Per Agent 1 core-domain architecture §3:
- ``heritage_objects`` is the polymorphic root with hot denormalized columns
  (name, summary, hero coordinates). Hierarchical sub-tables (``heritage_movable_ext``,
  ``heritage_intangible_ext``) land in a follow-up migration once we need them.
- ``heritage_aliases`` carries multilingual historical names + transliterations.
- ``heritage_revisions`` is the bi-temporal audit log keyed on ``(heritage_id,
  valid_from)``. Every UPDATE on heritage_objects writes a row here.

UUIDv7 PKs · jsonb for i18n columns · GIN indexes on tags & names · soft delete
via deleted_at · provenance + confidence go onto ``heritage_facts`` in 0011.

Revision ID: 0010_heritage_core
Revises: 0009_sessions
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0010_heritage_core"
down_revision: str | Sequence[str] | None = "0009_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- heritage_objects --------------------------------------------------
    # tenant_id propagated for future B2B / white-label tenancy. residency_region
    # tracks the CONTENT origin, not user PII — UNESCO sites in Uzbekistan use
    # residency 'uz' regardless of who edits them.
    op.execute(
        """
        CREATE TABLE heritage_objects (
            id                  uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            tenant_id           uuid NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            pub_id              text NOT NULL UNIQUE,

            -- polymorphic discriminator → controlled_vocabularies.heritage_kinds
            kind_slug           text NOT NULL,

            -- denormalized i18n header fields (winning values; full provenance in 0011)
            name                jsonb NOT NULL DEFAULT '{}'::jsonb,
            summary_md          jsonb NOT NULL DEFAULT '{}'::jsonb,
            description_md      jsonb NOT NULL DEFAULT '{}'::jsonb,
            tags                text[] NOT NULL DEFAULT ARRAY[]::text[],

            -- geographic hot path (heritage may be intangible → nullable)
            country_code        char(2),
            admin_path          ltree,
            latitude            numeric(9, 6),
            longitude           numeric(9, 6),
            elevation_m         numeric(6, 1),

            -- temporal scope (year of foundation through abandonment; null = unknown)
            period_start_year   smallint,
            period_end_year     smallint,
            unesco_inscription_year smallint,

            -- editorial state
            status              text NOT NULL DEFAULT 'draft'
                CHECK (status IN ('draft','review','published','archived')),
            hero_media_id       uuid,
            confidence_score    smallint NOT NULL DEFAULT 0
                CHECK (confidence_score BETWEEN 0 AND 100),

            -- audit + soft-delete
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now(),
            deleted_at          timestamptz,
            created_by          uuid,
            updated_by          uuid,
            revision            int NOT NULL DEFAULT 1,

            CHECK (pub_id ~ '^[a-zA-Z0-9_-]{6,32}$'),
            CHECK (kind_slug ~ '^[a-z][a-z0-9_]*$'),
            CHECK (latitude IS NULL  OR latitude  BETWEEN -90  AND 90),
            CHECK (longitude IS NULL OR longitude BETWEEN -180 AND 180),
            CHECK (period_end_year IS NULL OR period_start_year IS NULL
                   OR period_end_year >= period_start_year)
        );

        COMMENT ON TABLE heritage_objects IS
            'Polymorphic root for every kind of cultural heritage. '
            'Discriminator is kind_slug (FK to controlled_vocabularies/heritage_kinds).';
        COMMENT ON COLUMN heritage_objects.confidence_score IS
            'Aggregate of fact confidences from heritage_facts (computed by a job, '
            'denormalized here for cheap reads).';

        CREATE INDEX idx_heritage_objects_status
            ON heritage_objects(status) WHERE deleted_at IS NULL;
        CREATE INDEX idx_heritage_objects_kind
            ON heritage_objects(kind_slug) WHERE deleted_at IS NULL;
        CREATE INDEX idx_heritage_objects_country
            ON heritage_objects(country_code) WHERE deleted_at IS NULL AND country_code IS NOT NULL;
        CREATE INDEX idx_heritage_objects_admin_path
            ON heritage_objects USING GIST (admin_path);
        CREATE INDEX idx_heritage_objects_tags
            ON heritage_objects USING GIN (tags);
        CREATE INDEX idx_heritage_objects_name_jsonb
            ON heritage_objects USING GIN (name jsonb_path_ops);
        CREATE INDEX idx_heritage_objects_geo
            ON heritage_objects (latitude, longitude)
            WHERE deleted_at IS NULL AND latitude IS NOT NULL;
        CREATE INDEX idx_heritage_objects_period
            ON heritage_objects (period_start_year, period_end_year)
            WHERE deleted_at IS NULL AND period_start_year IS NOT NULL;

        CREATE TRIGGER tg_heritage_objects_updated_at
            BEFORE UPDATE ON heritage_objects
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- heritage_aliases (multi-lingual historical / transliterated names) ---
    op.execute(
        """
        CREATE TABLE heritage_aliases (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            heritage_id     uuid NOT NULL REFERENCES heritage_objects(id) ON DELETE CASCADE,
            alias           text NOT NULL,
            language_tag    text NOT NULL,
            script          text,
            kind            text NOT NULL DEFAULT 'historical'
                CHECK (kind IN ('historical','transliteration','colloquial','official','misspelling')),
            source          text,
            confidence      smallint NOT NULL DEFAULT 80
                CHECK (confidence BETWEEN 0 AND 100),
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            UNIQUE (heritage_id, alias, language_tag),
            CHECK (length(alias) BETWEEN 1 AND 512),
            CHECK (length(language_tag) BETWEEN 2 AND 32)
        );

        CREATE INDEX idx_heritage_aliases_heritage
            ON heritage_aliases(heritage_id);
        CREATE INDEX idx_heritage_aliases_lang
            ON heritage_aliases(language_tag);
        CREATE INDEX idx_heritage_aliases_trgm
            ON heritage_aliases USING GIN (alias gin_trgm_ops);

        CREATE TRIGGER tg_heritage_aliases_updated_at
            BEFORE UPDATE ON heritage_aliases
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- heritage_revisions (bi-temporal audit) ---------------------------
    # Append-only. Each UPDATE on heritage_objects also writes a revision row
    # via the trigger below. The before-image is captured in 'before'.
    op.execute(
        """
        CREATE TABLE heritage_revisions (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            heritage_id     uuid NOT NULL REFERENCES heritage_objects(id) ON DELETE CASCADE,
            revision        int NOT NULL,
            action          text NOT NULL CHECK (action IN ('insert','update','soft_delete','restore')),
            actor_user_id   uuid,
            before          jsonb,
            after           jsonb NOT NULL,
            diff            jsonb,
            comment         text,
            valid_from      timestamptz NOT NULL DEFAULT now(),
            UNIQUE (heritage_id, revision)
        );

        CREATE INDEX idx_heritage_revisions_heritage
            ON heritage_revisions(heritage_id, valid_from DESC);
        CREATE INDEX idx_heritage_revisions_actor
            ON heritage_revisions(actor_user_id, valid_from DESC)
            WHERE actor_user_id IS NOT NULL;

        COMMENT ON TABLE heritage_revisions IS
            'Append-only revision log per Agent 1 §6. Forms the bi-temporal '
            'audit history; integrates with audit.audit_log via trace_id.';
        """
    )

    # --- Trigger functions: BEFORE bumps revision counter; AFTER writes log --
    # Split because heritage_revisions.heritage_id FK references heritage_objects:
    # BEFORE INSERT would write a child row before the parent exists.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app.tg_heritage_bump_revision() RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'UPDATE' AND to_jsonb(OLD) IS DISTINCT FROM to_jsonb(NEW) THEN
                NEW.revision := COALESCE(OLD.revision, 0) + 1;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE OR REPLACE FUNCTION app.tg_heritage_revision() RETURNS trigger AS $$
        DECLARE
            v_before jsonb;
            v_after  jsonb;
            v_action text;
        BEGIN
            IF TG_OP = 'INSERT' THEN
                v_before := NULL;
                v_after  := to_jsonb(NEW);
                v_action := 'insert';
            ELSIF TG_OP = 'UPDATE' THEN
                v_before := to_jsonb(OLD);
                v_after  := to_jsonb(NEW);
                IF v_before = v_after THEN
                    RETURN NULL;  -- no-op update, skip revision row
                END IF;
                IF OLD.deleted_at IS NULL AND NEW.deleted_at IS NOT NULL THEN
                    v_action := 'soft_delete';
                ELSIF OLD.deleted_at IS NOT NULL AND NEW.deleted_at IS NULL THEN
                    v_action := 'restore';
                ELSE
                    v_action := 'update';
                END IF;
            ELSE
                RETURN NULL;
            END IF;

            INSERT INTO heritage_revisions (
                heritage_id, revision, action, actor_user_id, before, after
            )
            VALUES (
                NEW.id,
                COALESCE(NEW.revision, 1),
                v_action,
                NEW.updated_by,
                v_before,
                v_after
            );
            RETURN NULL;  -- AFTER trigger return value is ignored
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER tg_heritage_objects_bump_revision
            BEFORE UPDATE ON heritage_objects
            FOR EACH ROW EXECUTE FUNCTION app.tg_heritage_bump_revision();

        CREATE TRIGGER tg_heritage_objects_revision
            AFTER INSERT OR UPDATE ON heritage_objects
            FOR EACH ROW EXECUTE FUNCTION app.tg_heritage_revision();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS tg_heritage_objects_revision ON heritage_objects;")
    op.execute("DROP TRIGGER IF EXISTS tg_heritage_objects_bump_revision ON heritage_objects;")
    op.execute("DROP FUNCTION IF EXISTS app.tg_heritage_revision();")
    op.execute("DROP FUNCTION IF EXISTS app.tg_heritage_bump_revision();")
    op.execute("DROP TABLE IF EXISTS heritage_revisions CASCADE;")
    op.execute("DROP TABLE IF EXISTS heritage_aliases CASCADE;")
    op.execute("DROP TABLE IF EXISTS heritage_objects CASCADE;")
