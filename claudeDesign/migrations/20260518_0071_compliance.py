"""compliance: legal documents, consent, GDPR requests, anonymization jobs,
cookie consents + app.anonymize_user() function.

Implements Project-Decisions §36 (GDPR + Uzbek PD-law compliance) and Agent 2
§3.18-§3.21 / §6 (GDPR workflows). The split between gdpr_requests (legal
artifact) and anonymization_jobs (operational task) is intentional — the
request must be retained for audit even after the job has scrubbed the PII.

Revision ID: 0071_compliance
Revises: 0062_security_patches
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0071_compliance"
down_revision: str | Sequence[str] | None = ("0070_login_attempts", "0072_wikidata_link")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


RESIDENCY_PARTITIONS = ("uz", "eu", "us", "global")
LEGAL_KINDS = ("privacy_policy", "tos", "cookies")
SEED_LANGUAGES = ("en", "uz", "ru", "zh")


def upgrade() -> None:
    # --- legal_documents -----------------------------------------------------
    op.execute(
        """
        CREATE TABLE legal_documents (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            tenant_id       uuid REFERENCES tenants(id) ON DELETE CASCADE,
            kind            text NOT NULL
                CHECK (kind IN ('privacy_policy','tos','cookies','dpa','cookie_policy')),
            version         text NOT NULL,
            language_tag    text NOT NULL,
            content_md      text NOT NULL,
            sha256          text NOT NULL,
            effective_from  timestamptz NOT NULL DEFAULT now(),
            effective_until timestamptz,
            created_by      uuid,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            UNIQUE (kind, version, language_tag),
            CHECK (language_tag ~ '^[a-z]{2}(-[A-Za-z0-9]+)*$')
        );

        CREATE INDEX idx_legal_documents_active
            ON legal_documents (kind, language_tag, effective_from DESC)
            WHERE effective_until IS NULL;
        CREATE INDEX idx_legal_documents_tenant
            ON legal_documents (tenant_id, kind, language_tag)
            WHERE tenant_id IS NOT NULL;

        CREATE TRIGGER tg_legal_documents_updated_at
            BEFORE UPDATE ON legal_documents
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON TABLE legal_documents IS
            'Versioned legal text (privacy, ToS, cookies). tenant_id NULL means '
            'platform default; tenants may override by inserting their own row. '
            'sha256 of content_md is recorded so we can prove what a user '
            'agreed to without re-storing the full text per consent.';
        """
    )

    # --- consent_records (partitioned by residency_region) -------------------
    op.execute(
        """
        CREATE TABLE consent_records (
            id                 uuid NOT NULL DEFAULT gen_uuid_v7(),
            user_id            uuid NOT NULL,
            residency_region   text NOT NULL,
            tenant_id          uuid NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            legal_document_id  uuid NOT NULL REFERENCES legal_documents(id) ON DELETE RESTRICT,
            basis              text NOT NULL
                CHECK (basis IN ('consent','contract','legitimate_interest',
                                 'legal_obligation','vital','public_task')),
            purpose            text,
            granted_at         timestamptz NOT NULL DEFAULT now(),
            withdrawn_at       timestamptz,
            ip_address         inet,
            user_agent         text,
            source             text NOT NULL DEFAULT 'settings',
            created_at         timestamptz NOT NULL DEFAULT now(),

            PRIMARY KEY (id, residency_region),
            FOREIGN KEY (user_id, residency_region)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (residency_region IN ('uz','eu','us','global'))
        ) PARTITION BY LIST (residency_region);
        """
    )
    for region in RESIDENCY_PARTITIONS:
        op.execute(
            f"CREATE TABLE consent_records_{region} "
            f"PARTITION OF consent_records FOR VALUES IN ('{region}');"
        )

    op.execute(
        """
        CREATE INDEX idx_consent_records_user
            ON consent_records (user_id, legal_document_id, granted_at DESC);
        CREATE INDEX idx_consent_records_active
            ON consent_records (user_id, legal_document_id)
            WHERE withdrawn_at IS NULL;
        """
    )

    # --- gdpr_requests (partitioned by residency_region) --------------------
    op.execute(
        """
        CREATE TABLE gdpr_requests (
            id                       uuid NOT NULL DEFAULT gen_uuid_v7(),
            user_id                  uuid NOT NULL,
            residency_region         text NOT NULL,
            tenant_id                uuid NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            request_kind             text NOT NULL
                CHECK (request_kind IN ('export','delete','access','rectify',
                                        'restrict','object','portability')),
            status                   text NOT NULL DEFAULT 'submitted'
                CHECK (status IN ('submitted','processing','completed','rejected','cancelled')),
            payload_url              text,
            reason                   text,
            scheduled_for            timestamptz,
            requested_by_user_id     uuid,
            decided_by_admin_user_id uuid,
            decision_note            text,
            created_at               timestamptz NOT NULL DEFAULT now(),
            updated_at               timestamptz NOT NULL DEFAULT now(),
            completed_at             timestamptz,

            PRIMARY KEY (id, residency_region),
            FOREIGN KEY (user_id, residency_region)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (residency_region IN ('uz','eu','us','global'))
        ) PARTITION BY LIST (residency_region);
        """
    )
    for region in RESIDENCY_PARTITIONS:
        op.execute(
            f"CREATE TABLE gdpr_requests_{region} "
            f"PARTITION OF gdpr_requests FOR VALUES IN ('{region}');"
        )

    op.execute(
        """
        CREATE INDEX idx_gdpr_requests_user_kind
            ON gdpr_requests (user_id, request_kind, created_at DESC);
        CREATE INDEX idx_gdpr_requests_pending
            ON gdpr_requests (status, scheduled_for)
            WHERE status IN ('submitted','processing');
        -- At most one pending delete request per user.
        CREATE UNIQUE INDEX uq_gdpr_one_open_delete
            ON gdpr_requests (user_id, residency_region)
            WHERE request_kind = 'delete' AND status IN ('submitted','processing');

        CREATE TRIGGER tg_gdpr_requests_updated_at
            BEFORE UPDATE ON gdpr_requests
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- anonymization_jobs --------------------------------------------------
    op.execute(
        """
        CREATE TABLE anonymization_jobs (
            id                  uuid NOT NULL DEFAULT gen_uuid_v7(),
            user_id             uuid NOT NULL,
            residency_region    text NOT NULL,
            tenant_id           uuid NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            gdpr_request_id     uuid,
            status              text NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending','running','completed','failed','cancelled')),
            scheduled_for       timestamptz NOT NULL,
            started_at          timestamptz,
            finished_at         timestamptz,
            rows_anonymized     int NOT NULL DEFAULT 0,
            tables_touched      text[] NOT NULL DEFAULT ARRAY[]::text[],
            error_message       text,
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now(),

            PRIMARY KEY (id, residency_region),
            FOREIGN KEY (user_id, residency_region)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (residency_region IN ('uz','eu','us','global'))
        ) PARTITION BY LIST (residency_region);
        """
    )
    for region in RESIDENCY_PARTITIONS:
        op.execute(
            f"CREATE TABLE anonymization_jobs_{region} "
            f"PARTITION OF anonymization_jobs FOR VALUES IN ('{region}');"
        )

    op.execute(
        """
        CREATE INDEX idx_anonymization_jobs_due
            ON anonymization_jobs (status, scheduled_for)
            WHERE status IN ('pending','running');
        CREATE INDEX idx_anonymization_jobs_user
            ON anonymization_jobs (user_id);

        CREATE TRIGGER tg_anonymization_jobs_updated_at
            BEFORE UPDATE ON anonymization_jobs
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- cookie_consents (anonymous, public) --------------------------------
    op.execute(
        """
        CREATE TABLE cookie_consents (
            id                   uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            session_cookie_id    text NOT NULL,
            user_id              uuid,
            tenant_id            uuid REFERENCES tenants(id) ON DELETE CASCADE,
            ip_hash              text,
            user_agent           text,
            categories           jsonb NOT NULL DEFAULT jsonb_build_object('strictly_necessary', true),
            region               text,
            given_at             timestamptz NOT NULL DEFAULT now(),
            CHECK ((categories ? 'strictly_necessary'))
        );

        CREATE INDEX idx_cookie_consents_session
            ON cookie_consents (session_cookie_id, given_at DESC);
        CREATE INDEX idx_cookie_consents_user
            ON cookie_consents (user_id, given_at DESC)
            WHERE user_id IS NOT NULL;

        COMMENT ON TABLE cookie_consents IS
            'Per-visitor cookie banner choice. session_cookie_id is the value '
            'of the silklens-consent-sid cookie (opaque), ip_hash is sha256 of '
            'the visitor IP to avoid storing raw addresses for anonymous users.';
        """
    )

    # --- app.anonymize_user() ------------------------------------------------
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app.anonymize_user(
            p_user_id  uuid,
            p_residency text
        ) RETURNS jsonb
        LANGUAGE plpgsql AS $$
        DECLARE
            v_touched jsonb := '{}'::jsonb;
            v_n int;
            v_tables text[] := ARRAY[]::text[];
        BEGIN
            -- core users row
            UPDATE users
            SET status        = 'deleted',
                anonymized_at = now(),
                deleted_at    = COALESCE(deleted_at, now()),
                password_hash = NULL,
                last_login_at = NULL,
                last_active_at = NULL,
                preferred_locale = 'en',
                preferred_timezone = 'UTC'
            WHERE id = p_user_id AND residency_region = p_residency;
            GET DIAGNOSTICS v_n = ROW_COUNT;
            v_touched := v_touched || jsonb_build_object('users', v_n);
            IF v_n > 0 THEN v_tables := array_append(v_tables, 'users'); END IF;

            UPDATE user_profiles
            SET display_name = '__deleted__',
                full_name    = NULL,
                bio          = NULL,
                avatar_url   = NULL,
                country_code = NULL,
                city         = NULL,
                interests    = ARRAY[]::text[]
            WHERE user_id = p_user_id AND residency_region = p_residency;
            GET DIAGNOSTICS v_n = ROW_COUNT;
            v_touched := v_touched || jsonb_build_object('user_profiles', v_n);
            IF v_n > 0 THEN v_tables := array_append(v_tables, 'user_profiles'); END IF;

            UPDATE user_emails
            SET email = (encode(digest('deleted-' || id::text, 'sha256'), 'hex')
                         || '@deleted.silklens.invalid')::citext,
                is_primary = false,
                bounce_count = 0
            WHERE user_id = p_user_id AND residency_region = p_residency;
            GET DIAGNOSTICS v_n = ROW_COUNT;
            v_touched := v_touched || jsonb_build_object('user_emails', v_n);
            IF v_n > 0 THEN v_tables := array_append(v_tables, 'user_emails'); END IF;

            UPDATE user_phones
            SET phone_e164 = '+999' || lpad((abs(hashtext(id::text)) % 1000000000000)::text, 12, '0'),
                is_primary = false
            WHERE user_id = p_user_id AND residency_region = p_residency;
            GET DIAGNOSTICS v_n = ROW_COUNT;
            v_touched := v_touched || jsonb_build_object('user_phones', v_n);
            IF v_n > 0 THEN v_tables := array_append(v_tables, 'user_phones'); END IF;

            DELETE FROM user_identities
            WHERE user_id = p_user_id AND residency_region = p_residency;
            GET DIAGNOSTICS v_n = ROW_COUNT;
            v_touched := v_touched || jsonb_build_object('user_identities', v_n);
            IF v_n > 0 THEN v_tables := array_append(v_tables, 'user_identities'); END IF;

            -- best-effort kill of live sessions / refresh tokens (tables exist
            -- per migration 0009 but in test we only assert the function ran)
            BEGIN
                EXECUTE 'DELETE FROM sessions WHERE user_id = $1 AND residency_region = $2'
                    USING p_user_id, p_residency;
                GET DIAGNOSTICS v_n = ROW_COUNT;
                v_touched := v_touched || jsonb_build_object('sessions', v_n);
                IF v_n > 0 THEN v_tables := array_append(v_tables, 'sessions'); END IF;
            EXCEPTION WHEN undefined_table THEN
                NULL;
            END;

            BEGIN
                EXECUTE 'DELETE FROM refresh_tokens WHERE user_id = $1 AND residency_region = $2'
                    USING p_user_id, p_residency;
                GET DIAGNOSTICS v_n = ROW_COUNT;
                v_touched := v_touched || jsonb_build_object('refresh_tokens', v_n);
                IF v_n > 0 THEN v_tables := array_append(v_tables, 'refresh_tokens'); END IF;
            EXCEPTION WHEN undefined_table THEN
                NULL;
            END;

            RETURN jsonb_build_object(
                'rows', v_touched,
                'tables_touched', to_jsonb(v_tables)
            );
        END;
        $$;
        """
    )

    # --- seed initial legal docs v1 per kind+language ----------------------
    for kind in LEGAL_KINDS:
        for lang in SEED_LANGUAGES:
            body = (
                f"# SilkLens — {kind.replace('_', ' ').title()} (v1)\n\n"
                f"Language: {lang}\n\n"
                "This is the seeded placeholder for the launch policy. "
                "Replace via POST /v1/legal/{kind} before public release."
            )
            op.execute(
                """
                INSERT INTO legal_documents
                    (kind, version, language_tag, content_md, sha256, effective_from)
                VALUES
                    (:k, '1.0.0', :lang, :body,
                     encode(digest(:body, 'sha256'), 'hex'),
                     now())
                ON CONFLICT (kind, version, language_tag) DO NOTHING;
                """.replace(":k", f"'{kind}'")
                .replace(":lang", f"'{lang}'")
                .replace(":body", "'" + body.replace("'", "''") + "'")
            )

    # --- ensure event_types exist for the events we emit -------------------
    op.execute(
        """
        INSERT INTO event_types (event_name, display_name, retention_days, kafka_topic) VALUES
            ('consent.withdrawn.v1', '{"en":"Consent withdrawn"}', 730, 'silklens.consent.events'),
            ('gdpr.export_requested.v1', '{"en":"GDPR export requested"}', 730, 'silklens.consent.events'),
            ('gdpr.deletion_requested.v1', '{"en":"GDPR deletion requested"}', 730, 'silklens.consent.events'),
            ('gdpr.deletion_cancelled.v1', '{"en":"GDPR deletion cancelled"}', 730, 'silklens.consent.events'),
            ('legal_document.published.v1', '{"en":"Legal document published"}', 730, 'silklens.consent.events'),
            ('cookie_consent.given.v1', '{"en":"Cookie consent given"}', 365, 'silklens.consent.events')
        ON CONFLICT (event_name) DO NOTHING;
        """
    )

    # --- seed gdpr:approve permission used by admin processing endpoint ----
    op.execute(
        """
        INSERT INTO permissions (slug, description)
        VALUES ('gdpr:approve', 'Approve / process GDPR requests')
        ON CONFLICT (slug) DO NOTHING;

        -- grant to super_admin (and tenant_admin)
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r, permissions p
        WHERE r.slug IN ('super_admin','tenant_admin')
          AND p.slug = 'gdpr:approve'
        ON CONFLICT DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS app.anonymize_user(uuid, text);")
    op.execute("DROP TABLE IF EXISTS cookie_consents CASCADE;")
    op.execute("DROP TABLE IF EXISTS anonymization_jobs CASCADE;")
    op.execute("DROP TABLE IF EXISTS gdpr_requests CASCADE;")
    op.execute("DROP TABLE IF EXISTS consent_records CASCADE;")
    op.execute("DROP TABLE IF EXISTS legal_documents CASCADE;")
    op.execute(
        "DELETE FROM event_types WHERE event_name IN ("
        "'consent.withdrawn.v1','gdpr.export_requested.v1',"
        "'gdpr.deletion_requested.v1','gdpr.deletion_cancelled.v1',"
        "'legal_document.published.v1','cookie_consent.given.v1');"
    )
    op.execute(
        "DELETE FROM role_permissions WHERE permission_id IN "
        "(SELECT id FROM permissions WHERE slug = 'gdpr:approve');"
    )
    op.execute("DELETE FROM permissions WHERE slug = 'gdpr:approve';")
