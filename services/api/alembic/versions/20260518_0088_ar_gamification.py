"""AR gamification v2 — challenges, sessions, overlays, spatial anchors

FAZA 3/6: AR o'yin — tarixiy topishmoqlar + AR overlay + multi-user AR.

Tables
------
- ar_challenges       — challenge catalog with GPS anchor, i18n, anti-cheat
- ar_challenge_completions — append-only, idempotent UNIQUE(challenge, user)
- ar_sessions         — solo/group AR sessions (6-char group code)
- ar_session_participants — composite PK, join/leave tracking
- ar_overlays         — admin-curated AR overlay definitions per heritage
- ar_spatial_anchors  — provider-native cloud anchor IDs + metadata

Seeds
-----
- 5 AR challenges for Uzbek UNESCO sites (Registon, Itchan Kala, Yasawi Mausoleum)
- ar_explorer badge_type (criterion: 5 ar_completions, 500 XP)
- ar.challenge.completed.v1 + ar.session.started.v1 events

Revision ID: 0088_ar_gamification
Revises: 0081_central_asia_currencies
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0088_ar_gamification"
# Merge all parallel branch heads from FAZA 5-7 waves so ``alembic upgrade
# head`` resolves to a single head again.
down_revision: tuple[str, ...] = (
    "0085_silk_road_seed",
    "0086_mediterranean_asia_seed",
    "0090_finetuning_dataset",
    "0091_enterprise_sla",
    "0092_investor_dataroom",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # ar_challenges — challenge catalog
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE ar_challenges (
            id                      uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            heritage_id             uuid NOT NULL
                REFERENCES heritage_objects(id) ON DELETE CASCADE,
            tenant_id               uuid NOT NULL
                REFERENCES tenants(id) ON DELETE CASCADE,
            slug                    text NOT NULL UNIQUE,
            title                   jsonb NOT NULL DEFAULT '{}'::jsonb,
            description_md          jsonb NOT NULL DEFAULT '{}'::jsonb,
            kind                    text NOT NULL
                CHECK (kind IN (
                    'historical_riddle','object_hunt',
                    'reconstruction_quiz','photo_spot','time_period_guess'
                )),
            difficulty              text NOT NULL
                CHECK (difficulty IN ('easy','medium','hard','expert')),
            reward_xp               integer NOT NULL DEFAULT 50
                CHECK (reward_xp >= 0),
            time_limit_seconds      integer
                CHECK (time_limit_seconds IS NULL OR time_limit_seconds > 0),
            ar_anchor_lat           numeric(9,6) NOT NULL,
            ar_anchor_lng           numeric(9,6) NOT NULL,
            ar_anchor_altitude_m    numeric(6,1),
            trigger_radius_m        numeric(6,1) NOT NULL DEFAULT 50,
            clue_text_md            jsonb NOT NULL DEFAULT '{}'::jsonb,
            correct_answer          jsonb NOT NULL DEFAULT '{}'::jsonb,
            hint_text_md            jsonb,
            is_active               boolean NOT NULL DEFAULT true,
            completion_count        integer NOT NULL DEFAULT 0
                CHECK (completion_count >= 0),
            created_at              timestamptz NOT NULL DEFAULT now(),
            updated_at              timestamptz NOT NULL DEFAULT now()
        );

        CREATE INDEX idx_ar_challenges_heritage
            ON ar_challenges (heritage_id)
            WHERE is_active;
        CREATE INDEX idx_ar_challenges_kind_difficulty
            ON ar_challenges (kind, difficulty)
            WHERE is_active;
        CREATE INDEX idx_ar_challenges_tenant
            ON ar_challenges (tenant_id, is_active);

        CREATE TRIGGER tg_ar_challenges_updated_at
            BEFORE UPDATE ON ar_challenges
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE ar_challenges IS
            'AR challenge catalog. correct_answer is jsonb so each kind can '
            'store its own answer schema (text, bounding-box, year-range, etc.). '
            'completion_count is a denormalised counter bumped by the completion '
            'trigger for leaderboard ordering without aggregation.';
        """
    )

    # ------------------------------------------------------------------
    # ar_challenge_completions — one row per (challenge, user)
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE ar_challenge_completions (
            id                  uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            challenge_id        uuid NOT NULL
                REFERENCES ar_challenges(id) ON DELETE CASCADE,
            user_id             uuid NOT NULL,
            residency_region    text NOT NULL
                CHECK (residency_region IN ('uz','eu','us','global')),
            completed_at        timestamptz NOT NULL DEFAULT now(),
            time_taken_seconds  integer NOT NULL
                CHECK (time_taken_seconds >= 0),
            score               smallint NOT NULL
                CHECK (score BETWEEN 0 AND 100),
            hint_used           boolean NOT NULL DEFAULT false,
            photo_media_id      uuid,
            xp_awarded          integer NOT NULL DEFAULT 0
                CHECK (xp_awarded >= 0),

            UNIQUE (challenge_id, user_id),
            FOREIGN KEY (user_id, residency_region)
                REFERENCES users(id, residency_region) ON DELETE CASCADE
        );

        CREATE INDEX idx_ar_completions_user
            ON ar_challenge_completions (user_id, completed_at DESC);
        CREATE INDEX idx_ar_completions_challenge
            ON ar_challenge_completions (challenge_id, completed_at DESC);

        COMMENT ON TABLE ar_challenge_completions IS
            'One row per (challenge, user). UNIQUE enforces at-most-one completion. '
            'The INSERT trigger bumps ar_challenges.completion_count and emits '
            'badge.unlocked.v1 when the ar_explorer threshold is crossed.';
        """
    )

    # Trigger: bump completion_count on parent challenge after each insert
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app.tg_ar_completion_post_insert()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            UPDATE ar_challenges
            SET    completion_count = completion_count + 1
            WHERE  id = NEW.challenge_id;
            RETURN NEW;
        END;
        $$;

        CREATE TRIGGER tg_ar_completion_count
            AFTER INSERT ON ar_challenge_completions
            FOR EACH ROW EXECUTE FUNCTION app.tg_ar_completion_post_insert();
        """
    )

    # ------------------------------------------------------------------
    # ar_sessions — solo / group AR sessions
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE ar_sessions (
            id                  uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            user_id             uuid NOT NULL,
            residency_region    text NOT NULL
                CHECK (residency_region IN ('uz','eu','us','global')),
            heritage_id         uuid
                REFERENCES heritage_objects(id) ON DELETE SET NULL,
            session_kind        text NOT NULL
                CHECK (session_kind IN ('solo','group')),
            started_at          timestamptz NOT NULL DEFAULT now(),
            ended_at            timestamptz,
            max_participants    smallint NOT NULL DEFAULT 1
                CHECK (max_participants BETWEEN 1 AND 20),
            session_code        text UNIQUE,
            created_at          timestamptz NOT NULL DEFAULT now(),

            FOREIGN KEY (user_id, residency_region)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (
                (session_kind = 'group' AND session_code IS NOT NULL AND max_participants > 1)
                OR (session_kind = 'solo' AND session_code IS NULL)
            )
        );

        CREATE INDEX idx_ar_sessions_user
            ON ar_sessions (user_id, started_at DESC);
        CREATE INDEX idx_ar_sessions_code
            ON ar_sessions (session_code)
            WHERE session_code IS NOT NULL;
        CREATE INDEX idx_ar_sessions_heritage
            ON ar_sessions (heritage_id, started_at DESC)
            WHERE heritage_id IS NOT NULL;

        COMMENT ON TABLE ar_sessions IS
            'Solo or group AR sessions. Group sessions carry a 6-char session_code '
            'that participants use to join. session_code UNIQUE is already partial '
            'but the full column UNIQUE covers all non-NULL codes globally.';
        """
    )

    # ------------------------------------------------------------------
    # ar_session_participants — who joined a group session
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE ar_session_participants (
            session_id          uuid NOT NULL
                REFERENCES ar_sessions(id) ON DELETE CASCADE,
            user_id             uuid NOT NULL,
            residency_region    text NOT NULL
                CHECK (residency_region IN ('uz','eu','us','global')),
            joined_at           timestamptz NOT NULL DEFAULT now(),
            left_at             timestamptz,

            PRIMARY KEY (session_id, user_id),
            FOREIGN KEY (user_id, residency_region)
                REFERENCES users(id, residency_region) ON DELETE CASCADE
        );

        CREATE INDEX idx_ar_session_participants_user
            ON ar_session_participants (user_id, joined_at DESC);

        COMMENT ON TABLE ar_session_participants IS
            'Composite PK (session, user). left_at NULL means still in session.';
        """
    )

    # ------------------------------------------------------------------
    # ar_overlays — admin-curated AR info overlays per heritage site
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE ar_overlays (
            id                  uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            heritage_id         uuid NOT NULL
                REFERENCES heritage_objects(id) ON DELETE CASCADE,
            tenant_id           uuid NOT NULL
                REFERENCES tenants(id) ON DELETE CASCADE,
            overlay_kind        text NOT NULL
                CHECK (overlay_kind IN (
                    'info_card','historical_photo','3d_model',
                    'audio_hotspot','measurement_guide'
                )),
            position_data       jsonb NOT NULL DEFAULT '{}'::jsonb,
            content_md          jsonb NOT NULL DEFAULT '{}'::jsonb,
            media_asset_id      uuid,
            is_active           boolean NOT NULL DEFAULT true,
            display_from_date   date,
            display_until_date  date,
            created_at          timestamptz NOT NULL DEFAULT now(),

            CHECK (
                display_from_date IS NULL
                OR display_until_date IS NULL
                OR display_from_date <= display_until_date
            )
        );

        CREATE INDEX idx_ar_overlays_heritage_active
            ON ar_overlays (heritage_id, overlay_kind)
            WHERE is_active;
        CREATE INDEX idx_ar_overlays_date_range
            ON ar_overlays (display_from_date, display_until_date)
            WHERE is_active;

        COMMENT ON TABLE ar_overlays IS
            'Admin-curated overlays positioned at lat/lng/alt/heading/pitch/roll '
            'stored in position_data JSONB. display_from/until allow seasonal '
            'or event-tied overlays (e.g. Nowruz festival highlights).';
        """
    )

    # ------------------------------------------------------------------
    # ar_spatial_anchors — cloud AR anchor IDs from external providers
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE ar_spatial_anchors (
            id                  uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            heritage_id         uuid NOT NULL
                REFERENCES heritage_objects(id) ON DELETE CASCADE,
            anchor_provider     text NOT NULL
                CHECK (anchor_provider IN (
                    'google_cloud_ar','apple_ar','arcore','marker_based'
                )),
            anchor_id           text NOT NULL,
            anchor_data         jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at          timestamptz NOT NULL DEFAULT now(),
            expires_at          timestamptz,

            UNIQUE (anchor_provider, anchor_id)
        );

        CREATE INDEX idx_ar_spatial_anchors_heritage
            ON ar_spatial_anchors (heritage_id, anchor_provider);
        CREATE INDEX idx_ar_spatial_anchors_expiry
            ON ar_spatial_anchors (expires_at)
            WHERE expires_at IS NOT NULL;

        COMMENT ON TABLE ar_spatial_anchors IS
            'Cloud AR anchor registrations. anchor_id is the provider-assigned '
            'identifier (Google: alphanumeric, Apple: UUID, ARCore: URL). '
            'anchor_data carries provider-specific metadata (pose, quality score, etc.).';
        """
    )

    # ------------------------------------------------------------------
    # Seed: AR explorer badge
    # ------------------------------------------------------------------
    op.execute(
        """
        INSERT INTO badge_types
            (slug, category, name, description, criterion_kind, criterion_params, rarity, xp_reward)
        VALUES (
            'ar_explorer',
            'exploration',
            '{"en":"AR Explorer","uz":"AR Kashfiyotchisi","ru":"AR Исследователь"}'::jsonb,
            '{"en":"Complete 5 AR challenges across heritage sites","uz":"5 ta AR topishmoqni yakunlang"}'::jsonb,
            'count_visited',
            '{"ar_completions": 5}'::jsonb,
            'rare',
            500
        )
        ON CONFLICT (slug) DO NOTHING;
        """
    )

    # ------------------------------------------------------------------
    # Seed: event types for AR domain
    # ------------------------------------------------------------------
    op.execute(
        """
        INSERT INTO event_types (event_name, display_name)
        VALUES
            ('ar.challenge.completed.v1', '{"en":"AR challenge completed"}'::jsonb),
            ('ar.session.started.v1',     '{"en":"AR session started"}'::jsonb),
            ('ar.session.joined.v1',      '{"en":"AR session joined"}'::jsonb),
            ('badge.unlocked.v1',         '{"en":"Badge unlocked"}'::jsonb)
        ON CONFLICT (event_name) DO NOTHING;
        """
    )

    # ------------------------------------------------------------------
    # Seed: 5 AR challenges for Uzbek UNESCO heritage sites
    # We reference heritage_objects by pub_id (seeded in 0080).
    # Uses ON CONFLICT on slug so re-running upgrade is safe.
    # ------------------------------------------------------------------
    op.execute(
        """
        INSERT INTO ar_challenges (
            heritage_id, tenant_id, slug, title, description_md,
            kind, difficulty, reward_xp, time_limit_seconds,
            ar_anchor_lat, ar_anchor_lng, ar_anchor_altitude_m,
            trigger_radius_m, clue_text_md, correct_answer, hint_text_md
        )
        SELECT
            ho.id,
            (SELECT id FROM tenants ORDER BY created_at LIMIT 1),
            c.slug,
            c.title,
            c.description_md,
            c.kind,
            c.difficulty,
            c.reward_xp,
            c.time_limit_seconds,
            c.lat, c.lng, c.alt,
            c.radius,
            c.clue, c.answer, c.hint
        FROM (
            VALUES
                -- 1. Registon Square — historical riddle
                ('registon-riddle-inscriptions',
                 '{"en":"Registan: Whose Words?","uz":"Registon: Kimning so''zlari?","ru":"Регистан: Чьи слова?"}'::jsonb,
                 '{"en":"# Registan Inscription Riddle. Scan the central portal of the **Ulugh Beg Madrasa** and find the calligraphic inscription.","uz":"# Registon yozuv topishmoqi"}'::jsonb,
                 'historical_riddle', 'easy', 100, 300,
                 39.654588, 66.975661, 280.0, 60.0,
                 '{"en":"Look for the portal niche above the main iwan — the inscription names the patron ruler."}'::jsonb,
                 '{"text":"Ulugh Beg","accepted":["ulugh beg","ulugbek","Ulugbek"]}'::jsonb,
                 '{"en":"The ruler was a 15th-century astronomer and the grandson of Timur."}'::jsonb),

                -- 2. Registon — object hunt for the Sher-Dor portal
                ('registon-sherdor-hunt',
                 '{"en":"Registan: Find the Tiger Mosaic","uz":"Registon: Yo''lbars mozaikasini toping","ru":"Регистан: Найди тигриную мозаику"}'::jsonb,
                 '{"en":"# Sher-Dor Tiger Hunt. Use the AR overlay to locate the **Sher-Dor Madrasa** tile featuring a tiger chasing a deer."}'::jsonb,
                 'object_hunt', 'easy', 75, 180,
                 39.654750, 66.975900, 280.0, 50.0,
                 '{"en":"Look at the tympanum of the Sher-Dor Madrasa — the mosaic shows a predator and prey above a human face."}'::jsonb,
                 '{"object":"sher_dor_tympanum","keywords":["tiger","deer","sun face"]}'::jsonb,
                 '{"en":"''Sher-Dor'' literally means ''lion-bearing'' in Persian."}'::jsonb),

                -- 3. Itchan Kala — reconstruction quiz
                ('itchan-kala-minaret-reconstruction',
                 '{"en":"Itchan Kala: Reconstruct the Kalta Minor","uz":"Ichon Qal''a: Kalta Minor restavratsiyasi","ru":"Ичан-кала: Воссоздайте Кальта Минор"}'::jsonb,
                 '{"en":"# Kalta Minor Reconstruction Quiz. The **Kalta Minor** was never finished. Using the AR time-slider, select which architectural form the minaret would have had if completed."}'::jsonb,
                 'reconstruction_quiz', 'medium', 150, 240,
                 41.378330, 60.363330, 290.0, 75.0,
                 '{"en":"Compare the Kalta Minor base diameter (~14.2 m) with completed minarets of the same era and estimate the intended height."}'::jsonb,
                 jsonb_build_object('height_range_m',array[70,80]::int[],'accepted_min',60,'accepted_max',85),
                 '{"en":"The unfinished minaret was started under Muhammad Amin Khan in the 19th century — his death halted construction."}'::jsonb),

                -- 4. Mausoleum of Khoja Ahmed Yasawi — time period guess
                ('yasawi-mausoleum-era-guess',
                 '{"en":"Yasawi: When Was It Built?","uz":"Yasaviy maqbarasi: Qachon qurilgan?","ru":"Мавзолей Яссауи: Когда был построен?"}'::jsonb,
                 '{"en":"# Timur''s Commission. Stand before the **main portal** and examine the architectural style, tile patterns, and construction techniques visible in AR. Guess the construction century."}'::jsonb,
                 'time_period_guess', 'medium', 125, 200,
                 43.297222, 68.268889, 370.0, 80.0,
                 '{"en":"The mausoleum features Timurid muqarnas vaulting and was commissioned by the ruler who unified Central Asia from Samarkand."}'::jsonb,
                 jsonb_build_object('century',14,'accepted_range',array[1380,1405]::int[],'era','Timurid'),
                 '{"en":"Construction began in 1389 CE under Timur (Tamerlane), who wished to honour the 12th-century Sufi saint."}'::jsonb),

                -- 5. Itchan Kala — photo spot
                ('itchan-kala-djuma-photo-spot',
                 '{"en":"Itchan Kala: Frame the Friday Mosque","uz":"Ichon Qal''a: Jome'' masjidini suratga oling","ru":"Ичан-кала: Сфотографируй Джума-мечеть"}'::jsonb,
                 '{"en":"# Friday Mosque Photo Spot. The AR compass will guide you to the exact vantage point where the **Djuma Mosque** wooden columns align with the minaret. Capture the shot!"}'::jsonb,
                 'photo_spot', 'easy', 50, NULL,
                 41.378000, 60.362500, 290.0, 40.0,
                 '{"en":"Walk to the north colonnade of the Djuma Mosque courtyard — align the 213 carved columns with the leaning minaret in your camera frame."}'::jsonb,
                 jsonb_build_object('required_elements',array['columns','minaret'],'min_column_count',5),
                 '{"en":"The Djuma Mosque has 213 intricately carved wooden columns, some dating to the 10th century."}'::jsonb)
        ) AS c(slug, title, description_md, kind, difficulty, reward_xp, time_limit_seconds,
               lat, lng, alt, radius, clue, answer, hint)
        JOIN (
            VALUES
                ('registon-riddle-inscriptions', 'registon-square'),
                ('registon-sherdor-hunt',        'registon-square'),
                ('itchan-kala-minaret-reconstruction', 'itchan-kala'),
                ('yasawi-mausoleum-era-guess',    'yasawi-mausoleum'),
                ('itchan-kala-djuma-photo-spot',  'itchan-kala')
        ) AS slug_site(slug, site_slug) ON c.slug = slug_site.slug
        JOIN heritage_objects ho ON ho.pub_id = slug_site.site_slug
        ON CONFLICT (slug) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ar_spatial_anchors CASCADE;")
    op.execute("DROP TABLE IF EXISTS ar_overlays CASCADE;")
    op.execute("DROP TABLE IF EXISTS ar_session_participants CASCADE;")
    op.execute("DROP TABLE IF EXISTS ar_sessions CASCADE;")
    op.execute("DROP TABLE IF EXISTS ar_challenge_completions CASCADE;")
    op.execute("DROP TABLE IF EXISTS ar_challenges CASCADE;")
    op.execute(
        """
        DROP FUNCTION IF EXISTS app.tg_ar_completion_post_insert() CASCADE;
        """
    )
    op.execute(
        "DELETE FROM badge_types WHERE slug = 'ar_explorer';"
    )
    op.execute(
        """
        DELETE FROM event_types WHERE event_name IN (
            'ar.challenge.completed.v1',
            'ar.session.started.v1',
            'ar.session.joined.v1',
            'badge.unlocked.v1'
        );
        """
    )
