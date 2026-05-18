"""reviews, multi-dim ratings, comments (ltree), reactions, UGC submission queue

Per Agent 5 §3.1-§3.8 (reviews/ratings/comments/reactions) + §3.38
(ugc_submissions polymorphic supertable).

Reviews are one-per-(user,heritage) but evolve via revision; the heart of the
"trust & safety" loop because reviews drive premium-subscription conversion.
Ratings live in a separate ``review_ratings`` row-per-dimension table so admin
can add a new dimension without a schema change.

Comments use Postgres-native ``ltree`` for materialised tree paths and a GIST
index for subtree queries; the depth column is denormalised so depth caps
are CHECK-enforceable without recursive lookup.

Reactions are polymorphic (target_kind + target_id) and reference an
admin-extensible ``reaction_types`` catalog — Agent 5 §3.8 "introduce a new
emoji without code deploy".

ugc_submissions is the single polymorphic queue: every user-generated artefact
(review, photo, video, edit suggestion, alias, comment) lands here and Agent C's
AI pipeline + Agent 5's human moderation pipeline both consume it. The
follow-up migration 0043 attaches the moderation_queue/actions/policies onto
this table.

All user FKs use composite (id, residency_region) per migration 0009.

Revision ID: 0041_reviews_ugc
Revises: 0040_social_graph
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0041_reviews_ugc"
down_revision: str | Sequence[str] | None = "0040_social_graph"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- review_dimensions (admin catalog) -------------------------------
    op.execute(
        """
        CREATE TABLE review_dimensions (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            slug            text NOT NULL UNIQUE,
            name            jsonb NOT NULL DEFAULT '{}'::jsonb,
            description     jsonb NOT NULL DEFAULT '{}'::jsonb,
            scale_min       smallint NOT NULL DEFAULT 1,
            scale_max       smallint NOT NULL DEFAULT 5,
            sort_order      smallint NOT NULL DEFAULT 0,
            weight          numeric(4,3) NOT NULL DEFAULT 1.000,
            is_active       boolean NOT NULL DEFAULT true,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            CHECK (slug ~ '^[a-z][a-z0-9_]*$'),
            CHECK (scale_min < scale_max),
            CHECK (weight >= 0)
        );

        CREATE TRIGGER tg_review_dimensions_updated_at
            BEFORE UPDATE ON review_dimensions
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE review_dimensions IS
            'Admin catalog of rating axes (history_accuracy, photo_quality, ...). '
            'Adding a new dimension is a row insert.';
        """
    )

    # Seed the v1 dimension set per Agent 5 §3.3 + spec.
    op.execute(
        """
        INSERT INTO review_dimensions (slug, name, sort_order, weight) VALUES
            ('history_accuracy',
             '{"en":"Historical accuracy","uz":"Tarixiy aniqlik","ru":"Историческая точность"}'::jsonb,
             10, 1.500),
            ('photo_quality',
             '{"en":"Photo opportunities","uz":"Suratga olish imkoniyatlari","ru":"Возможности для фото"}'::jsonb,
             20, 1.000),
            ('access',
             '{"en":"Accessibility","uz":"Qulaylik","ru":"Доступность"}'::jsonb,
             30, 1.000),
            ('value_for_money',
             '{"en":"Value for money","uz":"Pulning qiymati","ru":"Соотношение цена/качество"}'::jsonb,
             40, 1.000),
            ('atmosphere',
             '{"en":"Atmosphere","uz":"Muhit","ru":"Атмосфера"}'::jsonb,
             50, 1.200),
            ('family_friendliness',
             '{"en":"Family friendliness","uz":"Oilaviy sayohat uchun mos","ru":"Подходит для семьи"}'::jsonb,
             60, 0.800);
        """
    )

    # --- reviews -------------------------------------------------------------
    # NOTE: language_tag tracks the language the review was written in. Cached
    # NLLB translations land in review_translations (next).
    op.execute(
        """
        CREATE TABLE reviews (
            id                          uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            tenant_id                   uuid NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            heritage_id                 uuid NOT NULL REFERENCES heritage_objects(id) ON DELETE CASCADE,
            user_id                     uuid NOT NULL,
            residency_region            text NOT NULL,
            language_tag                text NOT NULL,
            title                       text,
            body_md                     text NOT NULL,
            average_rating              numeric(3,2),
            visited_at                  date,
            is_published                boolean NOT NULL DEFAULT false,
            machine_translated_from     text,
            helpful_count               integer NOT NULL DEFAULT 0,
            unhelpful_count             integer NOT NULL DEFAULT 0,
            report_count                integer NOT NULL DEFAULT 0,
            edited_count                smallint NOT NULL DEFAULT 0,
            quality_score               numeric(5,4),
            created_at                  timestamptz NOT NULL DEFAULT now(),
            updated_at                  timestamptz NOT NULL DEFAULT now(),
            deleted_at                  timestamptz,

            FOREIGN KEY (user_id, residency_region)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (residency_region IN ('uz','eu','us','global')),
            CHECK (length(body_md) BETWEEN 10 AND 10000),
            CHECK (length(language_tag) BETWEEN 2 AND 32),
            CHECK (average_rating IS NULL OR average_rating BETWEEN 1 AND 5),
            UNIQUE (user_id, heritage_id)
        );

        CREATE INDEX idx_reviews_heritage_pub
            ON reviews (heritage_id, created_at DESC)
            WHERE is_published AND deleted_at IS NULL;
        CREATE INDEX idx_reviews_user
            ON reviews (user_id, created_at DESC)
            WHERE deleted_at IS NULL;
        CREATE INDEX idx_reviews_quality
            ON reviews (heritage_id, quality_score DESC NULLS LAST)
            WHERE is_published AND deleted_at IS NULL;
        CREATE INDEX idx_reviews_lang
            ON reviews (language_tag)
            WHERE is_published AND deleted_at IS NULL;

        CREATE TRIGGER tg_reviews_updated_at
            BEFORE UPDATE ON reviews
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE reviews IS
            'One review per (user, heritage). Soft-deleted by deleted_at. '
            'average_rating is computed from review_ratings (per Agent 5 §7.1).';
        """
    )

    # --- review_ratings (per-dimension scores) -------------------------------
    # Cannot enforce "value BETWEEN dimension.scale_min AND dimension.scale_max"
    # at the CHECK level because subqueries are not allowed; app layer enforces.
    op.execute(
        """
        CREATE TABLE review_ratings (
            review_id       uuid NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
            dimension_slug  text NOT NULL,
            value           smallint NOT NULL,
            PRIMARY KEY (review_id, dimension_slug),
            FOREIGN KEY (dimension_slug) REFERENCES review_dimensions(slug) ON DELETE RESTRICT,
            CHECK (value BETWEEN 0 AND 10)
        );

        CREATE INDEX idx_review_ratings_dimension
            ON review_ratings (dimension_slug);

        COMMENT ON TABLE review_ratings IS
            'One row per dimension per review. CHECK value BETWEEN '
            'scale_min..scale_max is enforced at the application layer because '
            'Postgres CHECK cannot subquery review_dimensions.';
        """
    )

    # --- review_translations (cached NLLB output) ----------------------------
    op.execute(
        """
        CREATE TABLE review_translations (
            review_id           uuid NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
            language_tag        text NOT NULL,
            body_md             text NOT NULL,
            machine_translated  boolean NOT NULL DEFAULT true,
            engine              text NOT NULL DEFAULT 'nllb-200',
            confidence          smallint,
            created_at          timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (review_id, language_tag),
            CHECK (length(language_tag) BETWEEN 2 AND 32),
            CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 100)
        );

        CREATE INDEX idx_review_translations_engine
            ON review_translations (engine, created_at DESC);

        COMMENT ON TABLE review_translations IS
            'Cached translations of reviews. LRU-evictable by created_at.';
        """
    )

    # --- review_helpful_votes (-1/+1 per user per review) --------------------
    op.execute(
        """
        CREATE TABLE review_helpful_votes (
            review_id           uuid NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
            voter_user_id       uuid NOT NULL,
            voter_residency     text NOT NULL,
            vote                smallint NOT NULL CHECK (vote IN (-1, 1)),
            voted_at            timestamptz NOT NULL DEFAULT now(),
            device_fingerprint_id uuid REFERENCES device_fingerprints(id) ON DELETE SET NULL,
            ip_inet             inet,

            PRIMARY KEY (review_id, voter_user_id),
            FOREIGN KEY (voter_user_id, voter_residency)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (voter_residency IN ('uz','eu','us','global'))
        );

        CREATE INDEX idx_review_helpful_voted_at
            ON review_helpful_votes (voted_at);
        CREATE INDEX idx_review_helpful_voter
            ON review_helpful_votes (voter_user_id);

        COMMENT ON TABLE review_helpful_votes IS
            'Helpful/unhelpful votes. device_fingerprint_id + ip_inet retained '
            'for vote-brigading analysis (Agent 5 §3.48).';
        """
    )

    # --- reaction_types (admin catalog) --------------------------------------
    op.execute(
        """
        CREATE TABLE reaction_types (
            slug            text PRIMARY KEY,
            emoji           text,
            name            jsonb NOT NULL DEFAULT '{}'::jsonb,
            sort_order      smallint NOT NULL DEFAULT 0,
            is_active       boolean NOT NULL DEFAULT true,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            CHECK (slug ~ '^[a-z][a-z0-9_]*$')
        );

        CREATE INDEX idx_reaction_types_active
            ON reaction_types (sort_order) WHERE is_active;

        CREATE TRIGGER tg_reaction_types_updated_at
            BEFORE UPDATE ON reaction_types
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE reaction_types IS
            'Admin-extensible reactions. Localized labels via name jsonb. '
            'New reaction = INSERT, not deploy (Agent 5 §3.8).';
        """
    )

    op.execute(
        """
        INSERT INTO reaction_types (slug, emoji, name, sort_order) VALUES
            ('like',         '👍', '{"en":"Like","uz":"Yoqdi","ru":"Нравится"}'::jsonb,        10),
            ('love',         '❤️', '{"en":"Love","uz":"Sevdim","ru":"Люблю"}'::jsonb,           20),
            ('wow',          '😮', '{"en":"Wow","uz":"Voy","ru":"Вау"}'::jsonb,                 30),
            ('sad',          '😢', '{"en":"Sad","uz":"G''amgin","ru":"Грустно"}'::jsonb,        40),
            ('angry',        '😠', '{"en":"Angry","uz":"G''azabli","ru":"Возмущён"}'::jsonb,    50),
            ('helpful',      '🤝', '{"en":"Helpful","uz":"Foydali","ru":"Полезно"}'::jsonb,    60),
            ('informative',  '💡', '{"en":"Informative","uz":"Ma''lumotli","ru":"Познавательно"}'::jsonb, 70),
            ('beautiful',    '🌸', '{"en":"Beautiful","uz":"Go''zal","ru":"Красиво"}'::jsonb,  80);
        """
    )

    # --- comments (ltree threaded) -------------------------------------------
    # Per Agent 5 §8: ltree wins over adjacency / materialized-path-TEXT /
    # nested-set / closure-table for SilkLens's read-heavy access pattern.
    op.execute(
        """
        CREATE TABLE comments (
            id                  uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            tenant_id           uuid NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            parent_kind         text NOT NULL
                CHECK (parent_kind IN ('heritage','review','photo','comment','trip','journal','journal_entry')),
            parent_id           uuid NOT NULL,
            author_user_id      uuid NOT NULL,
            author_residency    text NOT NULL,
            body_md             text NOT NULL,
            language_tag        text NOT NULL,
            depth               smallint NOT NULL DEFAULT 0,
            path                ltree NOT NULL,
            status              text NOT NULL DEFAULT 'published'
                CHECK (status IN ('pending_moderation','published','removed','shadow_banned')),
            is_pinned           boolean NOT NULL DEFAULT false,
            reply_count         integer NOT NULL DEFAULT 0,
            reaction_count      integer NOT NULL DEFAULT 0,
            edited_count        smallint NOT NULL DEFAULT 0,
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now(),
            deleted_at          timestamptz,

            FOREIGN KEY (author_user_id, author_residency)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (author_residency IN ('uz','eu','us','global')),
            CHECK (depth BETWEEN 0 AND 6),
            CHECK (length(body_md) BETWEEN 1 AND 5000),
            CHECK (length(language_tag) BETWEEN 2 AND 32)
        );

        CREATE INDEX idx_comments_target
            ON comments (parent_kind, parent_id, created_at DESC)
            WHERE status = 'published' AND deleted_at IS NULL;
        CREATE INDEX idx_comments_path_gist
            ON comments USING GIST (path);
        CREATE INDEX idx_comments_author
            ON comments (author_user_id, created_at DESC);
        CREATE INDEX idx_comments_pinned
            ON comments (parent_kind, parent_id)
            WHERE is_pinned AND deleted_at IS NULL;

        CREATE TRIGGER tg_comments_updated_at
            BEFORE UPDATE ON comments
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE comments IS
            'Threaded polymorphic comments. ltree path encodes ancestry; depth '
            'cap is 6 per Agent 5 §8.2 — beyond that the reply UX collapses '
            'into "reply to thread".';
        """
    )

    # --- reactions (polymorphic) ---------------------------------------------
    op.execute(
        """
        CREATE TABLE reactions (
            id                  uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            reactor_user_id     uuid NOT NULL,
            reactor_residency   text NOT NULL,
            target_kind         text NOT NULL
                CHECK (target_kind IN ('review','comment','photo','journal','journal_entry','heritage')),
            target_id           uuid NOT NULL,
            reaction_type_slug  text NOT NULL REFERENCES reaction_types(slug) ON DELETE RESTRICT,
            created_at          timestamptz NOT NULL DEFAULT now(),

            FOREIGN KEY (reactor_user_id, reactor_residency)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (reactor_residency IN ('uz','eu','us','global')),
            UNIQUE (reactor_user_id, target_kind, target_id, reaction_type_slug)
        );

        CREATE INDEX idx_reactions_target
            ON reactions (target_kind, target_id);
        CREATE INDEX idx_reactions_reactor
            ON reactions (reactor_user_id, created_at DESC);

        COMMENT ON TABLE reactions IS
            'Polymorphic reactions. A user can apply multiple reaction types '
            'to the same target (UNIQUE includes reaction_type_slug).';
        """
    )

    # --- ugc_submissions (polymorphic supertable) ----------------------------
    # The single queue every UGC artefact flows through. Agent C's AI pipeline
    # writes auto_moderation_score; Agent 5's human pipeline (migration 0043)
    # picks up the rows that exceed thresholds.
    op.execute(
        """
        CREATE TABLE ugc_submissions (
            id                          uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            tenant_id                   uuid NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            kind                        text NOT NULL
                CHECK (kind IN (
                    'review','photo','video','edit_suggestion','heritage_alias',
                    'comment','journal','journal_entry'
                )),
            target_id                   uuid NOT NULL,
            author_user_id              uuid NOT NULL,
            author_residency            text NOT NULL,
            payload                     jsonb NOT NULL DEFAULT '{}'::jsonb,
            status                      text NOT NULL DEFAULT 'pending'
                CHECK (status IN (
                    'pending','auto_approved','awaiting_human',
                    'approved','rejected','quarantined','shadow_banned'
                )),
            user_trust_tier_snapshot    text,
            auto_moderation_score       numeric(4,3),
            ai_decision                 text
                CHECK (ai_decision IS NULL OR ai_decision IN ('approve','reject','escalate')),
            submitted_at                timestamptz NOT NULL DEFAULT now(),
            decided_at                  timestamptz,
            decided_by                  uuid,
            sla_due_at                  timestamptz,

            FOREIGN KEY (author_user_id, author_residency)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (author_residency IN ('uz','eu','us','global')),
            CHECK (auto_moderation_score IS NULL
                   OR (auto_moderation_score >= 0 AND auto_moderation_score <= 1))
        );

        CREATE INDEX idx_ugc_status_submitted
            ON ugc_submissions (status, submitted_at);
        CREATE INDEX idx_ugc_author
            ON ugc_submissions (author_user_id, submitted_at DESC);
        CREATE INDEX idx_ugc_kind_status
            ON ugc_submissions (kind, status);
        CREATE INDEX idx_ugc_sla
            ON ugc_submissions (sla_due_at)
            WHERE status IN ('pending','awaiting_human') AND sla_due_at IS NOT NULL;
        CREATE INDEX idx_ugc_target
            ON ugc_submissions (kind, target_id);

        COMMENT ON TABLE ugc_submissions IS
            'Single polymorphic queue for every UGC artefact awaiting decision. '
            'AI pipeline (Agent 3) writes auto_moderation_score; human pipeline '
            '(migration 0043) attaches moderation_queue/actions/policies.';
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ugc_submissions CASCADE;")
    op.execute("DROP TABLE IF EXISTS reactions CASCADE;")
    op.execute("DROP TABLE IF EXISTS comments CASCADE;")
    op.execute("DROP TABLE IF EXISTS reaction_types CASCADE;")
    op.execute("DROP TABLE IF EXISTS review_helpful_votes CASCADE;")
    op.execute("DROP TABLE IF EXISTS review_translations CASCADE;")
    op.execute("DROP TABLE IF EXISTS review_ratings CASCADE;")
    op.execute("DROP TABLE IF EXISTS reviews CASCADE;")
    op.execute("DROP TABLE IF EXISTS review_dimensions CASCADE;")
