"""security patches: has_permission soft-delete, audit fallback removal,
heritage.deleted.v1 event, RLS-aware bypass setting

Fixes from the Wave-4 security + code reviews:
- SEC-002 / CRIT-1 audit fallback constant: the `app.audit()` function now
  raises if the HMAC key isn't set (no silent fallback).
- SEC-008: `app.has_permission()` joins users with `deleted_at IS NULL AND
  status = 'active'`. Banned/soft-deleted users no longer pass permission
  checks during the JWT-validity window.
- Seeds `heritage.deleted.v1` and a handful of other missing event_types
  that the application emits at runtime.

Revision ID: 0062_security_patches
Revises: 0061_search_jobs
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0062_security_patches"
down_revision: str | Sequence[str] | None = "0061_search_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- app.has_permission(): require users.deleted_at IS NULL ---
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app.has_permission(
            p_user_id uuid,
            p_residency_region text,
            p_permission_slug text,
            p_tenant_id uuid DEFAULT NULL
        ) RETURNS boolean
        LANGUAGE sql STABLE PARALLEL SAFE AS $$
            SELECT EXISTS (
                SELECT 1
                FROM user_roles ur
                JOIN users u ON u.id = ur.user_id
                            AND u.residency_region = ur.residency_region
                JOIN role_permissions rp ON rp.role_id = ur.role_id
                JOIN permissions p       ON p.id = rp.permission_id
                WHERE ur.user_id = p_user_id
                  AND ur.residency_region = p_residency_region
                  AND p.slug = p_permission_slug
                  AND ur.revoked_at IS NULL
                  AND (ur.expires_at IS NULL OR ur.expires_at > now())
                  AND (
                    ur.scope_tenant_id IS NULL
                    OR p_tenant_id IS NULL
                    OR ur.scope_tenant_id = p_tenant_id
                  )
                  AND u.deleted_at IS NULL
                  AND u.status = 'active'
            );
        $$;
        """
    )

    # --- app.audit(): fail closed when HMAC key absent ---
    op.execute(
        r"""
        CREATE OR REPLACE FUNCTION app.audit(
            p_tenant_id       uuid,
            p_actor_user_id   uuid,
            p_actor_residency text,
            p_action          text,
            p_entity_type     text,
            p_entity_id       uuid,
            p_entity_pub_id   text,
            p_before          jsonb,
            p_after           jsonb,
            p_details         jsonb DEFAULT '{}'::jsonb,
            p_ip              inet  DEFAULT NULL,
            p_ua              text  DEFAULT NULL,
            p_request_id      text  DEFAULT NULL,
            p_trace_id        text  DEFAULT NULL
        ) RETURNS uuid
        LANGUAGE plpgsql AS $$
        DECLARE
            v_prev_hash bytea;
            v_payload   jsonb;
            v_secret    text;
            v_id        uuid;
            v_row_hash  bytea;
            v_now       timestamptz := now();
        BEGIN
            BEGIN
                v_secret := current_setting('app.audit_hmac_key', true);
            EXCEPTION WHEN OTHERS THEN
                v_secret := NULL;
            END;
            IF v_secret IS NULL OR v_secret = '' THEN
                RAISE EXCEPTION USING
                    MESSAGE = 'app.audit_hmac_key not set on session; refusing to write tamper-evident audit row',
                    ERRCODE = '28000';
            END IF;

            SELECT row_hash INTO v_prev_hash
            FROM audit.audit_log
            WHERE tenant_id = p_tenant_id
            ORDER BY created_at DESC
            LIMIT 1;

            v_payload := jsonb_build_object(
                'tenant_id',       p_tenant_id,
                'actor_user_id',   p_actor_user_id,
                'actor_residency', p_actor_residency,
                'action',          p_action,
                'entity_type',     p_entity_type,
                'entity_id',       p_entity_id,
                'entity_pub_id',   p_entity_pub_id,
                'before',          p_before,
                'after',           p_after,
                'details',         p_details,
                'ip',              p_ip::text,
                'ua',              p_ua,
                'request_id',      p_request_id,
                'trace_id',        p_trace_id,
                'created_at',      v_now
            );

            v_row_hash := hmac(
                coalesce(v_prev_hash, '\x'::bytea) || convert_to(v_payload::text, 'UTF8'),
                convert_to(v_secret, 'UTF8'),
                'sha256'
            );

            v_id := gen_uuid_v7();
            INSERT INTO audit.audit_log (
                id, tenant_id, actor_user_id, actor_residency,
                action, entity_type, entity_id, entity_pub_id,
                before, after, details,
                ip_address, user_agent, request_id, trace_id,
                prev_hash, row_hash, created_at
            )
            VALUES (
                v_id, p_tenant_id, p_actor_user_id, p_actor_residency,
                p_action, p_entity_type, p_entity_id, p_entity_pub_id,
                p_before, p_after, p_details,
                p_ip, p_ua, p_request_id, p_trace_id,
                v_prev_hash, v_row_hash, v_now
            );
            RETURN v_id;
        END;
        $$;
        """
    )

    # --- Seed missing event_types that the application emits ---
    op.execute(
        """
        INSERT INTO event_types (event_name, display_name, retention_days, kafka_topic) VALUES
            ('heritage.deleted.v1',     '{"en":"Heritage deleted"}',     365, 'silklens.heritage.events'),
            ('heritage.transitioned.v1','{"en":"Heritage status transitioned"}', 365, 'silklens.heritage.events'),
            ('friend.invited.v1',       '{"en":"Friend invited"}',        90, 'silklens.social.events'),
            ('friend.accepted.v1',      '{"en":"Friend accepted"}',       90, 'silklens.social.events'),
            ('xp.awarded.v1',           '{"en":"XP awarded"}',            90, 'silklens.gamification.events'),
            ('badge.unlocked.v1',       '{"en":"Badge unlocked"}',       365, 'silklens.gamification.events'),
            ('streak.tick.v1',          '{"en":"Streak tick"}',           60, 'silklens.gamification.events'),
            ('streak.broken.v1',        '{"en":"Streak broken"}',         60, 'silklens.gamification.events'),
            ('ai.recognition.failed.v1','{"en":"Vision recognition failed"}', 90, 'silklens.ai.events'),
            ('media.uploaded.v1',       '{"en":"Media uploaded"}',       180, 'silklens.media.events'),
            ('media.scan_failed.v1',    '{"en":"Media scan failed"}',    365, 'silklens.media.events'),
            ('notification.sent.v1',    '{"en":"Notification sent"}',     30, 'silklens.notifications.events'),
            ('webhook.received.v1',     '{"en":"Webhook received"}',     365, 'silklens.billing.events'),
            ('webhook.rejected.v1',     '{"en":"Webhook rejected"}',     730, 'silklens.security.events')
        ON CONFLICT (event_name) DO NOTHING;
        """
    )


def downgrade() -> None:
    # Restore the previous (vulnerable) shape of has_permission + audit if rolled back.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app.has_permission(
            p_user_id uuid,
            p_residency_region text,
            p_permission_slug text,
            p_tenant_id uuid DEFAULT NULL
        ) RETURNS boolean
        LANGUAGE sql STABLE PARALLEL SAFE AS $$
            SELECT EXISTS (
                SELECT 1
                FROM user_roles ur
                JOIN role_permissions rp ON rp.role_id = ur.role_id
                JOIN permissions p       ON p.id = rp.permission_id
                WHERE ur.user_id = p_user_id
                  AND ur.residency_region = p_residency_region
                  AND p.slug = p_permission_slug
                  AND ur.revoked_at IS NULL
                  AND (ur.expires_at IS NULL OR ur.expires_at > now())
                  AND (
                    ur.scope_tenant_id IS NULL
                    OR p_tenant_id IS NULL
                    OR ur.scope_tenant_id = p_tenant_id
                  )
            );
        $$;
        """
    )
    op.execute(
        "DELETE FROM event_types WHERE event_name IN ("
        "'heritage.deleted.v1','heritage.transitioned.v1',"
        "'friend.invited.v1','friend.accepted.v1',"
        "'xp.awarded.v1','badge.unlocked.v1','streak.tick.v1','streak.broken.v1',"
        "'ai.recognition.failed.v1','media.uploaded.v1','media.scan_failed.v1',"
        "'notification.sent.v1','webhook.received.v1','webhook.rejected.v1');"
    )
