"""B2B listings + auctions + enterprise API + affiliate network

Per Agent 6 monetization architecture §3.10–§3.12:

  b2b_accounts                — KYC-verified business partners (hotels, tour ops…).
  b2b_listing_categories      — controlled vocab (hotel/restaurant/transport/…).
  b2b_listings                — actual listings, geocoded, may be heritage-scoped
                                or global. Status discriminates moderation lifecycle.
  b2b_auctions / b2b_bids     — sealed-bid auctions for featured slots per
                                heritage × period. Closed-form, settled offline.
  b2b_listing_clicks          — high-volume telemetry. RANGE-partitioned monthly.

  enterprise_accounts         — strategic B2B (banks, ministries, OTAs).
  api_keys                    — Enterprise API credentials. secret_hash only,
                                never the raw key (Agent 6 §3 risk #5 — leaked
                                keys must be unusable from a DB read).
  api_usage_records           — every billable API call. RANGE-partitioned daily.

  affiliate_partners          — Booking.com / GetYourGuide / Klook / Aviasales.
  affiliate_links             — tracked redirect URLs per partner × heritage.
  affiliate_clicks            — outbound clicks. RANGE-partitioned monthly.
  affiliate_conversions       — partner-reported conversions, lifecycle to paid.

Range-partitioned tables follow Agent 7's convention: the partition key is
part of the PK (Postgres requirement), partitions are pre-provisioned ±7 of
today, pg_partman extends in production.

Revision ID: 0053_b2b_enterprise
Revises: 0052_payments_invoicing
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta

from alembic import op

revision: str = "0053_b2b_enterprise"
down_revision: str | Sequence[str] | None = "0052_payments_invoicing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _month_first(d: date) -> date:
    return d.replace(day=1)


def _next_month_first(d: date) -> date:
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return date(d.year, d.month + 1, 1)


def upgrade() -> None:
    # --- b2b_accounts ----------------------------------------------------
    op.execute(
        """
        CREATE TABLE b2b_accounts (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            tenant_id       uuid NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            legal_name      text NOT NULL,
            contact_email   text NOT NULL,
            country_code    char(2),
            tax_id          text,
            kyc_status      text NOT NULL DEFAULT 'pending' CHECK (kyc_status IN (
                'pending','verified','rejected'
            )),
            payout_method   jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            CHECK (contact_email ~ '^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$'),
            CHECK (country_code IS NULL OR country_code ~ '^[A-Z]{2}$')
        );

        CREATE INDEX idx_b2b_accounts_tenant
            ON b2b_accounts (tenant_id);
        CREATE INDEX idx_b2b_accounts_kyc
            ON b2b_accounts (kyc_status);

        CREATE TRIGGER tg_b2b_accounts_updated_at
            BEFORE UPDATE ON b2b_accounts
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- b2b_listing_categories (vocab) ----------------------------------
    op.execute(
        """
        CREATE TABLE b2b_listing_categories (
            slug        text PRIMARY KEY,
            name        jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at  timestamptz NOT NULL DEFAULT now(),
            updated_at  timestamptz NOT NULL DEFAULT now(),
            CHECK (slug ~ '^[a-z][a-z0-9_]*$')
        );

        CREATE TRIGGER tg_b2b_listing_categories_updated_at
            BEFORE UPDATE ON b2b_listing_categories
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    op.execute(
        """
        INSERT INTO b2b_listing_categories (slug, name) VALUES
            ('hotel',          '{"en":"Hotel","ru":"Отель"}'::jsonb),
            ('restaurant',     '{"en":"Restaurant","ru":"Ресторан"}'::jsonb),
            ('transport',      '{"en":"Transport","ru":"Транспорт"}'::jsonb),
            ('tour_agency',    '{"en":"Tour Agency","ru":"Турагентство"}'::jsonb),
            ('souvenir',       '{"en":"Souvenir","ru":"Сувениры"}'::jsonb),
            ('museum_partner', '{"en":"Museum Partner","ru":"Музей-партнёр"}'::jsonb);
        """
    )

    # --- b2b_listings ----------------------------------------------------
    op.execute(
        """
        CREATE TABLE b2b_listings (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            tenant_id       uuid NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            b2b_account_id  uuid NOT NULL REFERENCES b2b_accounts(id) ON DELETE CASCADE,
            heritage_id     uuid REFERENCES heritage_objects(id) ON DELETE SET NULL,
            category_slug   text NOT NULL REFERENCES b2b_listing_categories(slug) ON DELETE RESTRICT,
            name            jsonb NOT NULL DEFAULT '{}'::jsonb,
            description     jsonb NOT NULL DEFAULT '{}'::jsonb,
            price_range     text,
            contact_phone   text,
            contact_email   text,
            lat             numeric(9, 6),
            lng             numeric(9, 6),
            website         text,
            status          text NOT NULL DEFAULT 'draft' CHECK (status IN (
                'draft','pending_review','active','paused','banned'
            )),
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            CHECK (lat IS NULL OR lat BETWEEN -90 AND 90),
            CHECK (lng IS NULL OR lng BETWEEN -180 AND 180)
        );

        CREATE INDEX idx_b2b_listings_account
            ON b2b_listings (b2b_account_id);
        CREATE INDEX idx_b2b_listings_heritage
            ON b2b_listings (heritage_id) WHERE heritage_id IS NOT NULL;
        CREATE INDEX idx_b2b_listings_active
            ON b2b_listings (category_slug, status) WHERE status = 'active';
        CREATE INDEX idx_b2b_listings_geo
            ON b2b_listings (lat, lng) WHERE lat IS NOT NULL AND status = 'active';

        CREATE TRIGGER tg_b2b_listings_updated_at
            BEFORE UPDATE ON b2b_listings
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- b2b_auctions ----------------------------------------------------
    # Featured-slot auctions per (heritage, category, period). winning_bid_id
    # FK is attached AFTER b2b_bids is created (circular dependency).
    op.execute(
        """
        CREATE TABLE b2b_auctions (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            tenant_id       uuid NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            heritage_id     uuid NOT NULL REFERENCES heritage_objects(id) ON DELETE CASCADE,
            slot_position   smallint NOT NULL CHECK (slot_position > 0),
            category_slug   text NOT NULL REFERENCES b2b_listing_categories(slug) ON DELETE RESTRICT,
            billing_period  text NOT NULL CHECK (billing_period IN ('daily','weekly','monthly')),
            period_start    date NOT NULL,
            period_end      date NOT NULL,
            status          text NOT NULL DEFAULT 'open' CHECK (status IN (
                'open','settled','canceled'
            )),
            settled_at      timestamptz,
            winning_bid_id  uuid,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            UNIQUE (heritage_id, category_slug, slot_position, period_start),
            CHECK (period_end > period_start)
        );

        CREATE INDEX idx_b2b_auctions_open
            ON b2b_auctions (period_end) WHERE status = 'open';

        CREATE TRIGGER tg_b2b_auctions_updated_at
            BEFORE UPDATE ON b2b_auctions
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- b2b_bids --------------------------------------------------------
    op.execute(
        """
        CREATE TABLE b2b_bids (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            auction_id      uuid NOT NULL REFERENCES b2b_auctions(id) ON DELETE CASCADE,
            b2b_account_id  uuid NOT NULL REFERENCES b2b_accounts(id) ON DELETE CASCADE,
            bid_amount      numeric(20, 4) NOT NULL CHECK (bid_amount >= 0),
            currency        char(3) NOT NULL REFERENCES currencies(code) ON DELETE RESTRICT,
            max_clicks      int CHECK (max_clicks IS NULL OR max_clicks > 0),
            submitted_at    timestamptz NOT NULL DEFAULT now(),
            status          text NOT NULL DEFAULT 'submitted' CHECK (status IN (
                'submitted','withdrawn','winning','losing','settled'
            )),
            UNIQUE (auction_id, b2b_account_id)
        );

        CREATE INDEX idx_b2b_bids_auction_amount
            ON b2b_bids (auction_id, bid_amount DESC);
        """
    )

    # Now attach winning_bid_id FK on b2b_auctions (circular ref resolved).
    op.execute(
        """
        ALTER TABLE b2b_auctions
            ADD CONSTRAINT fk_b2b_auctions_winning_bid
            FOREIGN KEY (winning_bid_id) REFERENCES b2b_bids(id) ON DELETE SET NULL;
        """
    )

    # --- b2b_listing_clicks (range-partitioned monthly) ------------------
    # High-volume click telemetry. The partition key (clicked_at) must be in
    # the PK. We synthesize a UUIDv7 click_id so duplicates can be detected.
    op.execute(
        """
        CREATE TABLE b2b_listing_clicks (
            id                  uuid NOT NULL DEFAULT gen_uuid_v7(),
            listing_id          uuid NOT NULL REFERENCES b2b_listings(id) ON DELETE CASCADE,
            clicked_at          timestamptz NOT NULL DEFAULT now(),
            user_id             uuid,
            residency_region    text,
            session_id          uuid,
            referrer            text,
            PRIMARY KEY (id, clicked_at),
            CHECK (residency_region IS NULL OR residency_region IN ('uz','eu','us','global'))
        ) PARTITION BY RANGE (clicked_at);

        CREATE INDEX idx_b2b_listing_clicks_listing
            ON b2b_listing_clicks (listing_id, clicked_at DESC);

        COMMENT ON TABLE b2b_listing_clicks IS
            'Click-through telemetry for B2B listings. Range-partitioned monthly. '
            'pg_partman extends partitions in production.';
        """
    )

    today = date.today()
    for offset in range(-1, 7):
        month_year = today.year
        month_num = today.month + offset
        while month_num <= 0:
            month_num += 12
            month_year -= 1
        while month_num > 12:
            month_num -= 12
            month_year += 1
        d = date(month_year, month_num, 1)
        d_next = _next_month_first(d)
        part_name = f"b2b_listing_clicks_{d.strftime('%Y%m')}"
        op.execute(
            f"""
            CREATE TABLE {part_name}
                PARTITION OF b2b_listing_clicks
                FOR VALUES FROM ('{d.isoformat()}') TO ('{d_next.isoformat()}');
            """
        )

    # --- enterprise_accounts --------------------------------------------
    op.execute(
        """
        CREATE TABLE enterprise_accounts (
            id                      uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            tenant_id               uuid NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            company_name            text NOT NULL,
            primary_contact_email   text NOT NULL,
            tier                    text NOT NULL DEFAULT 'standard' CHECK (tier IN (
                'standard','premium','strategic'
            )),
            mou_signed_at           timestamptz,
            mou_url                 text,
            created_at              timestamptz NOT NULL DEFAULT now(),
            updated_at              timestamptz NOT NULL DEFAULT now(),
            CHECK (primary_contact_email ~ '^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$')
        );

        CREATE INDEX idx_enterprise_accounts_tier
            ON enterprise_accounts (tier);

        CREATE TRIGGER tg_enterprise_accounts_updated_at
            BEFORE UPDATE ON enterprise_accounts
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- api_keys (Enterprise API credentials) --------------------------
    op.execute(
        """
        CREATE TABLE api_keys (
            id                      uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            tenant_id               uuid NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            enterprise_account_id   uuid REFERENCES enterprise_accounts(id) ON DELETE CASCADE,
            name                    text NOT NULL,
            prefix                  text NOT NULL UNIQUE,
            secret_hash             bytea NOT NULL,
            scopes                  text[] NOT NULL DEFAULT ARRAY[]::text[],
            rate_limit_per_minute   int NOT NULL DEFAULT 60 CHECK (rate_limit_per_minute > 0),
            ip_allowlist            inet[] NOT NULL DEFAULT ARRAY[]::inet[],
            expires_at              timestamptz,
            last_used_at            timestamptz,
            revoked_at              timestamptz,
            created_at              timestamptz NOT NULL DEFAULT now(),
            updated_at              timestamptz NOT NULL DEFAULT now(),
            CHECK (octet_length(secret_hash) = 32),  -- sha256
            CHECK (prefix ~ '^[A-Za-z0-9_-]{4,32}$')
        );

        CREATE INDEX idx_api_keys_tenant
            ON api_keys (tenant_id) WHERE revoked_at IS NULL;
        CREATE INDEX idx_api_keys_enterprise
            ON api_keys (enterprise_account_id)
            WHERE enterprise_account_id IS NOT NULL AND revoked_at IS NULL;

        CREATE TRIGGER tg_api_keys_updated_at
            BEFORE UPDATE ON api_keys
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON COLUMN api_keys.secret_hash IS
            'sha256 of the raw key. The raw key is shown ONCE at issuance and '
            'never stored — Agent 6 §3 risk #5 (leaked-key resilience).';
        """
    )

    # --- api_usage_records (range-partitioned daily) --------------------
    op.execute(
        """
        CREATE TABLE api_usage_records (
            id              uuid NOT NULL DEFAULT gen_uuid_v7(),
            api_key_id      uuid NOT NULL,  -- FK enforced on child reads via composite
            endpoint        text NOT NULL,
            status_code     smallint NOT NULL,
            latency_ms      int NOT NULL CHECK (latency_ms >= 0),
            byte_count      int NOT NULL DEFAULT 0 CHECK (byte_count >= 0),
            recorded_at     timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (id, recorded_at)
        ) PARTITION BY RANGE (recorded_at);

        CREATE INDEX idx_api_usage_records_key_time
            ON api_usage_records (api_key_id, recorded_at DESC);
        CREATE INDEX idx_api_usage_records_endpoint
            ON api_usage_records (endpoint, recorded_at DESC);

        COMMENT ON TABLE api_usage_records IS
            'Per-call telemetry; powers billing aggregation. Range-partitioned daily. '
            'api_key_id is NOT a hard FK because the parent api_keys row may be '
            'revoked while history must remain queryable.';
        """
    )

    for offset in range(-7, 8):
        d = today + timedelta(days=offset)
        d_next = d + timedelta(days=1)
        part_name = f"api_usage_records_{d.strftime('%Y%m%d')}"
        op.execute(
            f"""
            CREATE TABLE {part_name}
                PARTITION OF api_usage_records
                FOR VALUES FROM ('{d.isoformat()}') TO ('{d_next.isoformat()}');
            """
        )

    # --- affiliate_partners ---------------------------------------------
    op.execute(
        """
        CREATE TABLE affiliate_partners (
            id                          uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            slug                        text NOT NULL UNIQUE,
            name                        text NOT NULL,
            kind                        text NOT NULL CHECK (kind IN (
                'booking_com','getyourguide','klook','aviasales','custom'
            )),
            base_url                    text NOT NULL,
            attribution_window_days     int NOT NULL DEFAULT 30
                CHECK (attribution_window_days > 0),
            default_commission_pct      numeric(5, 2) NOT NULL DEFAULT 0
                CHECK (default_commission_pct BETWEEN 0 AND 100),
            is_active                   boolean NOT NULL DEFAULT true,
            created_at                  timestamptz NOT NULL DEFAULT now(),
            updated_at                  timestamptz NOT NULL DEFAULT now(),
            CHECK (slug ~ '^[a-z0-9][a-z0-9_-]*$')
        );

        CREATE TRIGGER tg_affiliate_partners_updated_at
            BEFORE UPDATE ON affiliate_partners
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();
        """
    )

    # --- affiliate_links ------------------------------------------------
    op.execute(
        """
        CREATE TABLE affiliate_links (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            partner_id      uuid NOT NULL REFERENCES affiliate_partners(id) ON DELETE CASCADE,
            heritage_id     uuid REFERENCES heritage_objects(id) ON DELETE SET NULL,
            generated_url   text NOT NULL,
            utm_params      jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at      timestamptz NOT NULL DEFAULT now()
        );

        CREATE INDEX idx_affiliate_links_partner
            ON affiliate_links (partner_id);
        CREATE INDEX idx_affiliate_links_heritage
            ON affiliate_links (heritage_id) WHERE heritage_id IS NOT NULL;
        """
    )

    # --- affiliate_clicks (range-partitioned monthly) -------------------
    op.execute(
        """
        CREATE TABLE affiliate_clicks (
            id                  uuid NOT NULL DEFAULT gen_uuid_v7(),
            link_id             uuid NOT NULL REFERENCES affiliate_links(id) ON DELETE CASCADE,
            user_id             uuid,
            residency_region    text,
            clicked_at          timestamptz NOT NULL DEFAULT now(),
            ip_address          inet,
            referrer            text,
            PRIMARY KEY (id, clicked_at),
            CHECK (residency_region IS NULL OR residency_region IN ('uz','eu','us','global'))
        ) PARTITION BY RANGE (clicked_at);

        CREATE INDEX idx_affiliate_clicks_link
            ON affiliate_clicks (link_id, clicked_at DESC);
        """
    )

    for offset in range(-1, 7):
        month_year = today.year
        month_num = today.month + offset
        while month_num <= 0:
            month_num += 12
            month_year -= 1
        while month_num > 12:
            month_num -= 12
            month_year += 1
        d = date(month_year, month_num, 1)
        d_next = _next_month_first(d)
        part_name = f"affiliate_clicks_{d.strftime('%Y%m')}"
        op.execute(
            f"""
            CREATE TABLE {part_name}
                PARTITION OF affiliate_clicks
                FOR VALUES FROM ('{d.isoformat()}') TO ('{d_next.isoformat()}');
            """
        )

    # --- affiliate_conversions ------------------------------------------
    op.execute(
        """
        CREATE TABLE affiliate_conversions (
            id                  uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            click_id            uuid NOT NULL,  -- composite ref; FK not enforced (partitioned parent)
            partner_id          uuid NOT NULL REFERENCES affiliate_partners(id) ON DELETE RESTRICT,
            conversion_amount   numeric(20, 4) NOT NULL CHECK (conversion_amount >= 0),
            commission_amount   numeric(20, 4) NOT NULL CHECK (commission_amount >= 0),
            currency            char(3) NOT NULL REFERENCES currencies(code) ON DELETE RESTRICT,
            status              text NOT NULL DEFAULT 'reported' CHECK (status IN (
                'reported','confirmed','voided','paid'
            )),
            reported_at         timestamptz NOT NULL DEFAULT now(),
            confirmed_at        timestamptz,
            paid_at             timestamptz
        );

        CREATE INDEX idx_affiliate_conversions_partner
            ON affiliate_conversions (partner_id, status, reported_at DESC);
        CREATE INDEX idx_affiliate_conversions_click
            ON affiliate_conversions (click_id);
        CREATE INDEX idx_affiliate_conversions_unpaid
            ON affiliate_conversions (reported_at DESC)
            WHERE status IN ('reported','confirmed');

        COMMENT ON TABLE affiliate_conversions IS
            'Partner-reported conversions. click_id references affiliate_clicks but '
            'no hard FK because the parent is range-partitioned (composite PK with '
            'clicked_at). Lifecycle: reported → confirmed → paid (or voided).';
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS affiliate_conversions CASCADE;")
    op.execute("DROP TABLE IF EXISTS affiliate_clicks CASCADE;")
    op.execute("DROP TABLE IF EXISTS affiliate_links CASCADE;")
    op.execute("DROP TABLE IF EXISTS affiliate_partners CASCADE;")
    op.execute("DROP TABLE IF EXISTS api_usage_records CASCADE;")
    op.execute("DROP TABLE IF EXISTS api_keys CASCADE;")
    op.execute("DROP TABLE IF EXISTS enterprise_accounts CASCADE;")
    op.execute("DROP TABLE IF EXISTS b2b_listing_clicks CASCADE;")
    op.execute("ALTER TABLE b2b_auctions DROP CONSTRAINT IF EXISTS fk_b2b_auctions_winning_bid;")
    op.execute("DROP TABLE IF EXISTS b2b_bids CASCADE;")
    op.execute("DROP TABLE IF EXISTS b2b_auctions CASCADE;")
    op.execute("DROP TABLE IF EXISTS b2b_listings CASCADE;")
    op.execute("DROP TABLE IF EXISTS b2b_listing_categories CASCADE;")
    op.execute("DROP TABLE IF EXISTS b2b_accounts CASCADE;")
