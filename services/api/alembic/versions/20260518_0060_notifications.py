"""notifications, templates, preferences, push, email/SMS, webhooks

Per Agent 7 §2.2–§2.5 this migration lands the entire multi-channel
notification stack plus push/email/SMS outbound and partner webhook
delivery. Highlights:

  - `notification_categories` / `templates` / `template_versions` /
    `template_variants` form the admin-managed messaging catalog. Critical
    categories (account_security, billing, system_alerts) cannot be opted
    out of — enforced at the API layer, see comment on preferences.
  - User-facing tables (`notification_preferences`, `notification_quiet_hours`,
    `notifications`, `notification_delivery_log`, `notification_bounces`,
    `push_devices`, `push_campaign_targets`, `email_messages`,
    `sms_messages`) carry residency_region and partition by LIST.
  - Append-only telemetry tables (`notification_delivery_log`,
    `email_messages`, `sms_messages`, `webhook_deliveries`) RANGE-partition
    on their event timestamp. Partition keys are folded into the PK per
    Postgres rules (lesson from migration 0005).
  - `webhooks_outbound`/`webhook_deliveries` are the partner-integration
    side of the same event bus (Agent 7 §2.5).

Forward references kept as nullable uuid columns without FK constraints:
  - `webhooks_outbound.tenant_id` already exists (tenants ship in 0002).
  - `notifications.related_object_id` is polymorphic — kept as plain uuid.

Revision ID: 0060_notifications
Revises: 0054_rls_tenancy
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta

from alembic import op

revision: str = "0060_notifications"
down_revision: str | Sequence[str] | None = "0054_rls_tenancy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


RESIDENCY_PARTITIONS = ("uz", "eu", "us", "global")


def _month_bounds(year: int, month: int) -> tuple[str, str]:
    start = date(year, month, 1)
    end = date(year + (month // 12), (month % 12) + 1, 1)
    return start.isoformat(), end.isoformat()


def _week_bounds(anchor: date) -> tuple[str, str]:
    # Anchor weeks to ISO Monday so partition boundaries are deterministic.
    start = anchor - timedelta(days=anchor.weekday())
    end = start + timedelta(days=7)
    return start.isoformat(), end.isoformat()


def upgrade() -> None:
    # --- notification_categories (admin vocabulary) -----------------------
    # `is_critical=true` means the category is transactional/legal and the
    # API MUST refuse to disable it for a user. The DB does not enforce this
    # because admins may need to override during incidents.
    op.execute(
        """
        CREATE TABLE notification_categories (
            slug                text PRIMARY KEY,
            name                jsonb NOT NULL DEFAULT '{}'::jsonb,
            description         jsonb NOT NULL DEFAULT '{}'::jsonb,
            default_enabled     boolean NOT NULL DEFAULT true,
            is_critical         boolean NOT NULL DEFAULT false,
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now(),
            CHECK (slug ~ '^[a-z][a-z0-9_]*$')
        );

        CREATE TRIGGER tg_notification_categories_updated_at
            BEFORE UPDATE ON notification_categories
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON COLUMN notification_categories.is_critical IS
            'When true the category is transactional/legal (security, billing, '
            'system alerts); preferences API must refuse to opt out.';
        """
    )

    op.execute(
        """
        INSERT INTO notification_categories (slug, name, description, default_enabled, is_critical) VALUES
            ('account_security',
                '{"en":"Account security"}'::jsonb,
                '{"en":"Login alerts, password changes, MFA events."}'::jsonb,
                true, true),
            ('social_activity',
                '{"en":"Social activity"}'::jsonb,
                '{"en":"Likes, comments, follows, mentions."}'::jsonb,
                true, false),
            ('gamification',
                '{"en":"Gamification"}'::jsonb,
                '{"en":"Badges earned, leaderboard movement, level-ups."}'::jsonb,
                true, false),
            ('content_updates',
                '{"en":"Content updates"}'::jsonb,
                '{"en":"New heritage entries, edits to followed entries."}'::jsonb,
                true, false),
            ('marketing',
                '{"en":"Marketing"}'::jsonb,
                '{"en":"Newsletters, product announcements, campaigns."}'::jsonb,
                false, false),
            ('billing',
                '{"en":"Billing"}'::jsonb,
                '{"en":"Invoices, payment results, subscription changes."}'::jsonb,
                true, true),
            ('system_alerts',
                '{"en":"System alerts"}'::jsonb,
                '{"en":"Service incidents, planned maintenance, breaking changes."}'::jsonb,
                true, true),
            ('recommendations',
                '{"en":"Recommendations"}'::jsonb,
                '{"en":"Personalised heritage suggestions and nearby places."}'::jsonb,
                true, false);
        """
    )

    # --- notification_templates (admin catalog, channel set CHECK'd) ------
    op.execute(
        """
        CREATE TABLE notification_templates (
            id                  uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            slug                text NOT NULL UNIQUE,
            category_slug       text NOT NULL REFERENCES notification_categories(slug) ON DELETE RESTRICT,
            name                jsonb NOT NULL DEFAULT '{}'::jsonb,
            channels            text[] NOT NULL DEFAULT ARRAY['in_app']::text[],
            default_priority    smallint NOT NULL DEFAULT 5
                CHECK (default_priority BETWEEN 1 AND 10),
            is_active           boolean NOT NULL DEFAULT true,
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now(),
            CHECK (slug ~ '^[a-z][a-z0-9_]*$'),
            CHECK (channels <@ ARRAY['in_app','email','sms','push']::text[]),
            CHECK (cardinality(channels) > 0)
        );

        CREATE INDEX idx_notification_templates_category
            ON notification_templates(category_slug) WHERE is_active;

        CREATE TRIGGER tg_notification_templates_updated_at
            BEFORE UPDATE ON notification_templates
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON COLUMN notification_templates.channels IS
            'Subset of (in_app,email,sms,push). Defaults to in_app. CHECK enforces subset.';
        """
    )

    # --- notification_template_versions -----------------------------------
    # Composite PK (template_id, version, language_tag). Auto-generated id
    # is added for cheap variant referencing in template_variants.
    op.execute(
        """
        CREATE TABLE notification_template_versions (
            id                      uuid NOT NULL DEFAULT gen_uuid_v7() UNIQUE,
            template_id             uuid NOT NULL REFERENCES notification_templates(id) ON DELETE CASCADE,
            version                 int  NOT NULL CHECK (version > 0),
            language_tag            text NOT NULL,
            subject                 text,
            body_md                 text NOT NULL,
            push_title              text,
            push_body               text,
            action_url_template     text,
            created_at              timestamptz NOT NULL DEFAULT now(),
            updated_at              timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (template_id, version, language_tag),
            CHECK (length(language_tag) BETWEEN 2 AND 32)
        );

        CREATE INDEX idx_notification_template_versions_lang
            ON notification_template_versions (language_tag, template_id);

        CREATE TRIGGER tg_notification_template_versions_updated_at
            BEFORE UPDATE ON notification_template_versions
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- notification_template_variants (A/B traffic split) ----------------
    op.execute(
        """
        CREATE TABLE notification_template_variants (
            template_id             uuid NOT NULL REFERENCES notification_templates(id) ON DELETE CASCADE,
            variant_slug            text NOT NULL,
            version_id              uuid NOT NULL REFERENCES notification_template_versions(id) ON DELETE RESTRICT,
            traffic_weight          smallint NOT NULL DEFAULT 50
                CHECK (traffic_weight BETWEEN 0 AND 100),
            is_active               boolean NOT NULL DEFAULT true,
            created_at              timestamptz NOT NULL DEFAULT now(),
            updated_at              timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (template_id, variant_slug),
            CHECK (variant_slug ~ '^[a-z][a-z0-9_]*$')
        );

        CREATE TRIGGER tg_notification_template_variants_updated_at
            BEFORE UPDATE ON notification_template_variants
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- notification_preferences (residency-partitioned) -----------------
    # PK includes partition key. The composite (user_id, residency_region,
    # category_slug, channel) is unique per Postgres-partitioning rules.
    op.execute(
        """
        CREATE TABLE notification_preferences (
            user_id             uuid NOT NULL,
            residency_region    text NOT NULL,
            category_slug       text NOT NULL REFERENCES notification_categories(slug) ON DELETE CASCADE,
            channel             text NOT NULL
                CHECK (channel IN ('in_app','email','sms','push')),
            enabled             boolean NOT NULL DEFAULT true,
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (user_id, residency_region, category_slug, channel),
            FOREIGN KEY (user_id, residency_region)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (residency_region IN ('uz','eu','us','global'))
        ) PARTITION BY LIST (residency_region);

        COMMENT ON TABLE notification_preferences IS
            'Per-user × per-category × per-channel opt-in/out. is_critical=true '
            'categories cannot be disabled at the API layer (DB permits for admin override).';
        """
    )
    for region in RESIDENCY_PARTITIONS:
        op.execute(
            f"""
            CREATE TABLE notification_preferences_{region}
                PARTITION OF notification_preferences
                FOR VALUES IN ('{region}');
            """
        )
    op.execute(
        """
        CREATE TRIGGER tg_notification_preferences_updated_at
            BEFORE UPDATE ON notification_preferences
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- notification_quiet_hours (residency-partitioned) -----------------
    op.execute(
        """
        CREATE TABLE notification_quiet_hours (
            user_id             uuid NOT NULL,
            residency_region    text NOT NULL,
            timezone            text NOT NULL DEFAULT 'UTC',
            start_time          time NOT NULL DEFAULT '22:00',
            end_time            time NOT NULL DEFAULT '08:00',
            weekdays            smallint[] NOT NULL DEFAULT ARRAY[0,1,2,3,4,5,6]::smallint[],
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (user_id, residency_region),
            FOREIGN KEY (user_id, residency_region)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (residency_region IN ('uz','eu','us','global')),
            CHECK (length(timezone) BETWEEN 1 AND 64)
        ) PARTITION BY LIST (residency_region);

        COMMENT ON TABLE notification_quiet_hours IS
            'NULL row (absence of a row for the user) means notifications are always-on. '
            'weekdays uses 0=Mon … 6=Sun.';
        """
    )
    for region in RESIDENCY_PARTITIONS:
        op.execute(
            f"""
            CREATE TABLE notification_quiet_hours_{region}
                PARTITION OF notification_quiet_hours
                FOR VALUES IN ('{region}');
            """
        )
    op.execute(
        """
        CREATE TRIGGER tg_notification_quiet_hours_updated_at
            BEFORE UPDATE ON notification_quiet_hours
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- notifications (residency-partitioned in-app inbox) ---------------
    op.execute(
        """
        CREATE TABLE notifications (
            id                      uuid NOT NULL DEFAULT gen_uuid_v7(),
            recipient_user_id       uuid NOT NULL,
            residency_region        text NOT NULL,
            template_id             uuid REFERENCES notification_templates(id) ON DELETE SET NULL,
            category_slug           text NOT NULL REFERENCES notification_categories(slug) ON DELETE RESTRICT,
            title                   text NOT NULL,
            body_md                 text NOT NULL,
            action_url              text,
            related_object_kind     text,
            related_object_id       uuid,
            is_read                 boolean NOT NULL DEFAULT false,
            read_at                 timestamptz,
            created_at              timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (id, residency_region),
            FOREIGN KEY (recipient_user_id, residency_region)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (residency_region IN ('uz','eu','us','global')),
            CHECK (length(title) BETWEEN 1 AND 256),
            CHECK ((is_read = false AND read_at IS NULL) OR (is_read = true AND read_at IS NOT NULL))
        ) PARTITION BY LIST (residency_region);

        CREATE INDEX idx_notifications_recipient_unread
            ON notifications (recipient_user_id, residency_region, is_read, created_at DESC);
        CREATE INDEX idx_notifications_related_object
            ON notifications (related_object_kind, related_object_id)
            WHERE related_object_id IS NOT NULL;

        COMMENT ON TABLE notifications IS
            'Logical in-app/persistent notification. One row per user-facing message. '
            'Delivery attempts per channel live in notification_delivery_log.';
        """
    )
    for region in RESIDENCY_PARTITIONS:
        op.execute(
            f"""
            CREATE TABLE notifications_{region}
                PARTITION OF notifications
                FOR VALUES IN ('{region}');
            """
        )

    # --- notification_delivery_log (RANGE-partitioned WEEKLY, append-only)
    # PK includes partition key (sent_at). Indexes inherited by children.
    op.execute(
        """
        CREATE TABLE notification_delivery_log (
            id                      uuid NOT NULL DEFAULT gen_uuid_v7(),
            notification_id         uuid,
            recipient_user_id       uuid NOT NULL,
            residency_region        text NOT NULL,
            channel                 text NOT NULL
                CHECK (channel IN ('in_app','email','sms','push')),
            provider                text,
            provider_message_id     text,
            status                  text NOT NULL
                CHECK (status IN ('queued','sent','delivered','bounced','failed','clicked')),
            error                   text,
            sent_at                 timestamptz NOT NULL DEFAULT now(),
            delivered_at            timestamptz,
            opened_at               timestamptz,
            PRIMARY KEY (id, sent_at),
            CHECK (residency_region IN ('uz','eu','us','global'))
        ) PARTITION BY RANGE (sent_at);

        CREATE INDEX idx_notification_delivery_log_recipient
            ON notification_delivery_log (recipient_user_id, residency_region, sent_at DESC);
        CREATE INDEX idx_notification_delivery_log_notification
            ON notification_delivery_log (notification_id, sent_at DESC)
            WHERE notification_id IS NOT NULL;
        CREATE INDEX idx_notification_delivery_log_status
            ON notification_delivery_log (status, sent_at DESC);
        CREATE INDEX idx_notification_delivery_log_provider_msg
            ON notification_delivery_log (provider, provider_message_id)
            WHERE provider_message_id IS NOT NULL;

        COMMENT ON TABLE notification_delivery_log IS
            'Append-only per-attempt delivery telemetry per Agent 7 §3.7. '
            'Range-partitioned by week. notification_id nullable for direct/ad-hoc sends.';
        """
    )
    today = date.today()
    for offset in range(-2, 3):
        anchor = today + timedelta(days=7 * offset)
        start, end = _week_bounds(anchor)
        suffix = start.replace("-", "")
        op.execute(
            f"""
            CREATE TABLE notification_delivery_log_w{suffix}
                PARTITION OF notification_delivery_log
                FOR VALUES FROM ('{start}') TO ('{end}');
            """
        )

    # --- notification_bounces (email/sms hard bounce registry) ------------
    op.execute(
        """
        CREATE TABLE notification_bounces (
            id                  uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            recipient_user_id   uuid,
            residency_region    text,
            channel             text NOT NULL
                CHECK (channel IN ('email','sms','push')),
            address             text NOT NULL,
            bounce_type         text NOT NULL
                CHECK (bounce_type IN ('hard','soft','spam_complaint')),
            provider            text,
            error               text,
            bounce_at           timestamptz NOT NULL DEFAULT now(),
            CHECK (residency_region IS NULL OR residency_region IN ('uz','eu','us','global')),
            CHECK (length(address) BETWEEN 1 AND 512)
        );

        CREATE INDEX idx_notification_bounces_address
            ON notification_bounces (address, bounce_at DESC);
        CREATE INDEX idx_notification_bounces_recipient
            ON notification_bounces (recipient_user_id, residency_region, bounce_at DESC)
            WHERE recipient_user_id IS NOT NULL;

        COMMENT ON TABLE notification_bounces IS
            'Permanent bounce register. Workers consult this before sending and '
            'auto-disable the channel for the address.';
        """
    )

    # --- push_devices (residency-partitioned) -----------------------------
    op.execute(
        """
        CREATE TABLE push_devices (
            id                  uuid NOT NULL DEFAULT gen_uuid_v7(),
            user_id             uuid NOT NULL,
            residency_region    text NOT NULL,
            platform            text NOT NULL
                CHECK (platform IN ('ios','android','web')),
            fcm_token           text,
            apns_token          text,
            installation_id     text NOT NULL,
            last_seen_at        timestamptz NOT NULL DEFAULT now(),
            is_active           boolean NOT NULL DEFAULT true,
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (id, residency_region),
            UNIQUE (user_id, residency_region, installation_id),
            FOREIGN KEY (user_id, residency_region)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (residency_region IN ('uz','eu','us','global')),
            CHECK (fcm_token IS NOT NULL OR apns_token IS NOT NULL OR platform = 'web')
        ) PARTITION BY LIST (residency_region);

        CREATE INDEX idx_push_devices_user
            ON push_devices (user_id, residency_region) WHERE is_active;
        CREATE INDEX idx_push_devices_last_seen
            ON push_devices (last_seen_at) WHERE is_active;
        """
    )
    for region in RESIDENCY_PARTITIONS:
        op.execute(
            f"""
            CREATE TABLE push_devices_{region}
                PARTITION OF push_devices
                FOR VALUES IN ('{region}');
            """
        )
    op.execute(
        """
        CREATE TRIGGER tg_push_devices_updated_at
            BEFORE UPDATE ON push_devices
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- push_segments (admin cohorts) ------------------------------------
    op.execute(
        """
        CREATE TABLE push_segments (
            id                  uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            slug                text NOT NULL UNIQUE,
            name                jsonb NOT NULL DEFAULT '{}'::jsonb,
            definition_jsonb    jsonb NOT NULL DEFAULT '{}'::jsonb,
            member_count        int NOT NULL DEFAULT 0 CHECK (member_count >= 0),
            refreshed_at        timestamptz,
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now(),
            CHECK (slug ~ '^[a-z][a-z0-9_]*$')
        );

        CREATE TRIGGER tg_push_segments_updated_at
            BEFORE UPDATE ON push_segments
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- push_campaigns ---------------------------------------------------
    op.execute(
        """
        CREATE TABLE push_campaigns (
            id                  uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            slug                text NOT NULL UNIQUE,
            name                jsonb NOT NULL DEFAULT '{}'::jsonb,
            template_id         uuid NOT NULL REFERENCES notification_templates(id) ON DELETE RESTRICT,
            segment_id          uuid NOT NULL REFERENCES push_segments(id) ON DELETE RESTRICT,
            scheduled_at        timestamptz,
            sent_at             timestamptz,
            total_targets       int NOT NULL DEFAULT 0 CHECK (total_targets >= 0),
            total_delivered     int NOT NULL DEFAULT 0 CHECK (total_delivered >= 0),
            total_clicked       int NOT NULL DEFAULT 0 CHECK (total_clicked >= 0),
            status              text NOT NULL DEFAULT 'draft'
                CHECK (status IN ('draft','scheduled','sending','done','canceled')),
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now(),
            CHECK (slug ~ '^[a-z][a-z0-9_-]*$'),
            CHECK (total_delivered <= total_targets),
            CHECK (total_clicked   <= total_delivered)
        );

        CREATE INDEX idx_push_campaigns_status
            ON push_campaigns(status, scheduled_at) WHERE status IN ('scheduled','sending');

        CREATE TRIGGER tg_push_campaigns_updated_at
            BEFORE UPDATE ON push_campaigns
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- push_campaign_targets (residency-partitioned) --------------------
    op.execute(
        """
        CREATE TABLE push_campaign_targets (
            campaign_id         uuid NOT NULL REFERENCES push_campaigns(id) ON DELETE CASCADE,
            user_id             uuid NOT NULL,
            residency_region    text NOT NULL,
            status              text NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending','sent','delivered','failed','clicked')),
            delivered_at        timestamptz,
            clicked_at          timestamptz,
            error               text,
            created_at          timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (campaign_id, user_id, residency_region),
            FOREIGN KEY (user_id, residency_region)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (residency_region IN ('uz','eu','us','global'))
        ) PARTITION BY LIST (residency_region);

        CREATE INDEX idx_push_campaign_targets_status
            ON push_campaign_targets (campaign_id, status);
        """
    )
    for region in RESIDENCY_PARTITIONS:
        op.execute(
            f"""
            CREATE TABLE push_campaign_targets_{region}
                PARTITION OF push_campaign_targets
                FOR VALUES IN ('{region}');
            """
        )

    # --- email_messages (RANGE-partitioned MONTHLY) -----------------------
    # recipient_user_id nullable for system emails (e.g. password reset
    # delivered before account confirmation). residency_region also nullable
    # for system emails — CHECK enforces both are set together when present.
    op.execute(
        """
        CREATE TABLE email_messages (
            id                  uuid NOT NULL DEFAULT gen_uuid_v7(),
            recipient_user_id   uuid,
            residency_region    text,
            to_address          text NOT NULL,
            from_address        text NOT NULL,
            subject             text NOT NULL,
            body_html           text,
            body_text           text,
            provider            text,
            provider_message_id text,
            status              text NOT NULL DEFAULT 'queued'
                CHECK (status IN ('queued','sent','delivered','bounced','failed','complained')),
            error               text,
            sent_at             timestamptz NOT NULL DEFAULT now(),
            delivered_at        timestamptz,
            PRIMARY KEY (id, sent_at),
            CHECK ((recipient_user_id IS NULL AND residency_region IS NULL)
                OR (recipient_user_id IS NOT NULL AND residency_region IN ('uz','eu','us','global'))),
            CHECK (length(to_address) BETWEEN 3 AND 512),
            CHECK (length(subject) BETWEEN 1 AND 998),
            CHECK (body_html IS NOT NULL OR body_text IS NOT NULL)
        ) PARTITION BY RANGE (sent_at);

        CREATE INDEX idx_email_messages_recipient
            ON email_messages (recipient_user_id, sent_at DESC)
            WHERE recipient_user_id IS NOT NULL;
        CREATE INDEX idx_email_messages_status
            ON email_messages (status, sent_at DESC);
        CREATE INDEX idx_email_messages_provider_msg
            ON email_messages (provider, provider_message_id)
            WHERE provider_message_id IS NOT NULL;
        """
    )
    today = date.today()
    for offset in range(-1, 4):
        target = today.replace(day=1)
        year = target.year + ((target.month - 1 + offset) // 12)
        month = ((target.month - 1 + offset) % 12) + 1
        start, end = _month_bounds(year, month)
        op.execute(
            f"""
            CREATE TABLE email_messages_y{year}m{month:02d}
                PARTITION OF email_messages
                FOR VALUES FROM ('{start}') TO ('{end}');
            """
        )

    # --- sms_messages (RANGE-partitioned MONTHLY) -------------------------
    op.execute(
        """
        CREATE TABLE sms_messages (
            id                  uuid NOT NULL DEFAULT gen_uuid_v7(),
            recipient_user_id   uuid,
            residency_region    text,
            to_phone            text NOT NULL,
            body                text NOT NULL,
            provider            text,
            provider_message_id text,
            status              text NOT NULL DEFAULT 'queued'
                CHECK (status IN ('queued','sent','delivered','failed','undelivered')),
            error               text,
            segments            int NOT NULL DEFAULT 1 CHECK (segments > 0),
            cost_estimate       numeric(8,4),
            sent_at             timestamptz NOT NULL DEFAULT now(),
            delivered_at        timestamptz,
            PRIMARY KEY (id, sent_at),
            CHECK ((recipient_user_id IS NULL AND residency_region IS NULL)
                OR (recipient_user_id IS NOT NULL AND residency_region IN ('uz','eu','us','global'))),
            CHECK (to_phone ~ '^\\+?[0-9]{6,20}$'),
            CHECK (length(body) BETWEEN 1 AND 1600)
        ) PARTITION BY RANGE (sent_at);

        CREATE INDEX idx_sms_messages_recipient
            ON sms_messages (recipient_user_id, sent_at DESC)
            WHERE recipient_user_id IS NOT NULL;
        CREATE INDEX idx_sms_messages_status
            ON sms_messages (status, sent_at DESC);
        CREATE INDEX idx_sms_messages_provider_msg
            ON sms_messages (provider, provider_message_id)
            WHERE provider_message_id IS NOT NULL;
        """
    )
    for offset in range(-1, 4):
        target = today.replace(day=1)
        year = target.year + ((target.month - 1 + offset) // 12)
        month = ((target.month - 1 + offset) % 12) + 1
        start, end = _month_bounds(year, month)
        op.execute(
            f"""
            CREATE TABLE sms_messages_y{year}m{month:02d}
                PARTITION OF sms_messages
                FOR VALUES FROM ('{start}') TO ('{end}');
            """
        )

    # --- sms_providers (admin registry) -----------------------------------
    op.execute(
        """
        CREATE TABLE sms_providers (
            slug                text PRIMARY KEY,
            name                text NOT NULL,
            api_endpoint        text NOT NULL,
            kind                text NOT NULL
                CHECK (kind IN ('twilio','eskiz_uz','playmobile_uz','custom')),
            is_active           boolean NOT NULL DEFAULT true,
            config              jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now(),
            CHECK (slug ~ '^[a-z][a-z0-9_]*$')
        );

        CREATE TRIGGER tg_sms_providers_updated_at
            BEFORE UPDATE ON sms_providers
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- webhooks_outbound (partner subscriptions) ------------------------
    op.execute(
        """
        CREATE TABLE webhooks_outbound (
            id                  uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            tenant_id           uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            partner_name        text NOT NULL,
            url                 text NOT NULL,
            secret              bytea NOT NULL,
            events              text[] NOT NULL DEFAULT ARRAY[]::text[],
            is_active           boolean NOT NULL DEFAULT true,
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now(),
            CHECK (length(partner_name) BETWEEN 1 AND 128),
            CHECK (url ~ '^https?://'),
            CHECK (cardinality(events) > 0)
        );

        CREATE INDEX idx_webhooks_outbound_tenant
            ON webhooks_outbound(tenant_id) WHERE is_active;
        CREATE INDEX idx_webhooks_outbound_events
            ON webhooks_outbound USING GIN (events) WHERE is_active;

        CREATE TRIGGER tg_webhooks_outbound_updated_at
            BEFORE UPDATE ON webhooks_outbound
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON COLUMN webhooks_outbound.events IS
            'Subscribed event_types.event_name strings. Wildcards (e.g. heritage.*) '
            'are resolved app-side at delivery time.';
        """
    )

    # --- webhook_deliveries (RANGE-partitioned WEEKLY, append-only) -------
    op.execute(
        """
        CREATE TABLE webhook_deliveries (
            id                  uuid NOT NULL DEFAULT gen_uuid_v7(),
            webhook_id          uuid NOT NULL REFERENCES webhooks_outbound(id) ON DELETE CASCADE,
            event_id            uuid NOT NULL,
            payload             jsonb NOT NULL,
            status              text NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending','sent','delivered','failed','retrying')),
            attempts            int NOT NULL DEFAULT 0 CHECK (attempts >= 0),
            last_attempt_at     timestamptz,
            response_status     smallint,
            response_body       text,
            created_at          timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (id, created_at),
            CHECK (response_status IS NULL OR response_status BETWEEN 100 AND 599)
        ) PARTITION BY RANGE (created_at);

        CREATE INDEX idx_webhook_deliveries_webhook
            ON webhook_deliveries (webhook_id, created_at DESC);
        CREATE INDEX idx_webhook_deliveries_pending
            ON webhook_deliveries (last_attempt_at)
            WHERE status IN ('pending','retrying');
        CREATE INDEX idx_webhook_deliveries_event
            ON webhook_deliveries (event_id);

        COMMENT ON TABLE webhook_deliveries IS
            'Append-only delivery attempts per Agent 7 §2.5. Partitioned weekly. '
            'Pending/retrying rows are scanned by the dispatcher.';
        """
    )
    for offset in range(-2, 3):
        anchor = today + timedelta(days=7 * offset)
        start, end = _week_bounds(anchor)
        suffix = start.replace("-", "")
        op.execute(
            f"""
            CREATE TABLE webhook_deliveries_w{suffix}
                PARTITION OF webhook_deliveries
                FOR VALUES FROM ('{start}') TO ('{end}');
            """
        )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS webhook_deliveries CASCADE;")
    op.execute("DROP TABLE IF EXISTS webhooks_outbound CASCADE;")
    op.execute("DROP TABLE IF EXISTS sms_providers CASCADE;")
    op.execute("DROP TABLE IF EXISTS sms_messages CASCADE;")
    op.execute("DROP TABLE IF EXISTS email_messages CASCADE;")
    op.execute("DROP TABLE IF EXISTS push_campaign_targets CASCADE;")
    op.execute("DROP TABLE IF EXISTS push_campaigns CASCADE;")
    op.execute("DROP TABLE IF EXISTS push_segments CASCADE;")
    op.execute("DROP TABLE IF EXISTS push_devices CASCADE;")
    op.execute("DROP TABLE IF EXISTS notification_bounces CASCADE;")
    op.execute("DROP TABLE IF EXISTS notification_delivery_log CASCADE;")
    op.execute("DROP TABLE IF EXISTS notifications CASCADE;")
    op.execute("DROP TABLE IF EXISTS notification_quiet_hours CASCADE;")
    op.execute("DROP TABLE IF EXISTS notification_preferences CASCADE;")
    op.execute("DROP TABLE IF EXISTS notification_template_variants CASCADE;")
    op.execute("DROP TABLE IF EXISTS notification_template_versions CASCADE;")
    op.execute("DROP TABLE IF EXISTS notification_templates CASCADE;")
    op.execute("DROP TABLE IF EXISTS notification_categories CASCADE;")
