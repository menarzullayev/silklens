# 06 — Monetization, Payments, Enterprise & White-Label Architecture

> Agent 6 / 8 — Monetization & Enterprise Architect
> Scope: subscriptions, payments, dynamic pricing, B2B listings, enterprise API, white-label tenants, revenue analytics, double-entry accounting, tax compliance.
> Tech baseline: PostgreSQL 16 + pgcrypto + Row-Level Security, NUMERIC(20,4) money, Redis 7 entitlement cache, Stripe primary, idempotent webhook processing, Celery for dunning/payouts.

---

## 1. Domain Analysis

SilkLens monetization is **not a single billing system**. It is six adjacent financial subsystems that must coexist in one ledger:

1. **B2C consumer subscriptions** — Premium tier sold through Stripe (global card), Payme/Click (Uzbekistan), Apple IAP, Google Play Billing. Prices are **PPP-tiered per region** and **seasonally adjusted** (May–Sep tourist season standard; off-season −50%); see Q18. The app must never hardcode a price — every charge resolves through a `(plan_id, pricing_zone_id, currency, effective_at)` lookup.
2. **B2B marketplace** — hotels, restaurants, transport providers buy *featured slots adjacent to a heritage object (obida)*. Listings are sold by **first-price sealed-bid auction per billing period per `(heritage_id, slot_position)`**, plus CPC overage. See Q19.
3. **Enterprise / API resellers** — turizm agentliklari consume SilkLens via API keys with scopes, IP allowlists and per-key quotas; some resell SilkLens under their own brand (white-label).
4. **White-label tenants** (Q50) — Visit Tashkent, Samarkand Guide, Aga Khan, regional ministries each operate the *same* platform under a distinct brand. **Every monetary, behavioural and content row is `tenant_id`-scoped** with PostgreSQL Row-Level Security; a reseller revenue-share kicks in on each charge collected through the tenant.
5. **Affiliate** — Booking.com / GetYourGuide / Klook / Aviasales send commission on attributed conversions. Attribution window, click dedup, fraud rules are all configurable.
6. **One-time payments** — tip jar, souvenir marketplace, gift subscriptions, one-off content unlock.

**Architectural invariants** (non-negotiable):

- **Double-entry ledger.** Every monetary movement creates ≥2 ledger entries that sum to zero. `payments`, `refunds`, `b2b_billing_periods`, `affiliate_commissions`, `payouts`, `tips` all post to `revenue_recognition_ledger`. No money exists only on a `subscriptions.amount` column.
- **NUMERIC(20,4) for all amounts.** Never FLOAT. Currencies stored separately (`CHAR(3)`, ISO-4217). Exchange rate captured at charge time as a *snapshot* row, never recomputed.
- **Idempotency end-to-end.** Every webhook keyed by `(provider, provider_event_id)`. Every internal mutation that issues a charge keyed by a UUID `idempotency_key` supplied by the caller. Retries are safe by construction.
- **Entitlement at request time must be <5 ms p99.** Achieved by Redis hash per user (`ent:{tenant_id}:{user_id}` → `{feature_key: tier}`), populated from materialised view, invalidated on subscription state-transition events.
- **Dynamic everything.** Plans, prices, features, taxes, payment-method allow-list, dunning timings, trial length, paywall copy — admin-editable. Code reads from DB, never literals.
- **Multi-tenancy is row-level.** A single PostgreSQL cluster, one logical DB, `tenant_id UUID NOT NULL` on every domain table, enforced by RLS policies bound to a session GUC `app.current_tenant`. Schema-per-tenant rejected — see §4.
- **State machines are append-only.** Subscriptions don't mutate in place; transitions emit rows into `subscription_events`. Same for `payment_webhook_events`, `dunning_state`, `b2b_auctions`. The audit trail *is* the truth.
- **Revenue recognition is GAAP/IFRS compliant.** Annual plan revenue is deferred and recognised monthly. Refunds reverse recognition. Snapshots roll into `revenue_snapshots` nightly for MRR/ARR.

The remainder of this document specifies every table, RLS strategy, state machine, webhook contract, auction mechanic, tax engine and risk.

---

## 2. Entity Discovery Report

The discovered entities, grouped by concern:

### 2.1 Tenancy & Branding
| Table | Purpose |
|---|---|
| `tenants` | A white-label brand (root: `silklens`; resellers: `visit-tashkent`, `samarkand-guide`, …). |
| `tenant_branding` | Logo, primary color, splash, app-name per locale — admin-editable. |
| `tenant_domains` | Custom hostnames + cert refs per tenant for web/admin. |
| `tenant_locales` | Which languages a tenant enables. |
| `tenant_revenue_share` | Reseller commission % per tenant (default 0 for `silklens`). |
| `tenant_payment_provider_config` | Which payment providers are active per tenant + per-tenant API keys. |

### 2.2 Product Catalogue & Entitlements
| Table | Purpose |
|---|---|
| `products` | Logical products (e.g. `consumer_premium`, `b2b_featured`, `enterprise_api`, `marketplace_souvenir`). |
| `product_plans` | Tiers within a product (`free`, `premium_monthly`, `premium_annual`, `enterprise_pro`, `b2b_featured_basic`, …). |
| `feature_flags` | Global feature definitions (`ar_overlay`, `offline_packs`, `ai_chat`, `audio_unlimited`, `mfa`, `route_planner`, …). |
| `plan_features` | The **admin-configurable entitlement matrix** — `(plan_id, feature_key, value)` where value is bool, integer quota, or JSON limit. |
| `entitlements` | Effective per-user resolved entitlement snapshot (materialised + Redis-cached). |
| `addon_products` | Pay-per-use unlocks (single city pack, single AR-experience, gift) attached to a base sub. |

### 2.3 Pricing & Currency
| Table | Purpose |
|---|---|
| `pricing_zones` | Region groups (`CIS`, `EU`, `NA`, `SEA`, `MENA`, `CN`, `IN`, `LATAM`, `SSA`, …) keyed to PPP. |
| `pricing_zone_countries` | ISO-3166-1 alpha-2 → zone mapping (admin-editable). |
| `currencies` | ISO-4217 list with display rules (decimals, symbol, format). |
| `prices` | `(plan_id, pricing_zone_id, currency, effective_from, effective_to, amount, season_modifier_id?)` — the canonical price ledger. |
| `seasonal_modifiers` | `(name, pricing_zone_id, date_window, percent_adjust)` e.g. "off_season_cis_-50%". |
| `exchange_rate_snapshots` | Append-only rate captures at the time of each charge: `(base, quote, rate, captured_at, source)`. Never updated. |
| `price_experiments` | A/B price tests (group A vs group B per plan/zone). |

### 2.4 Subscriptions & Lifecycle
| Table | Purpose |
|---|---|
| `subscriptions` | One row per active or historical sub. Has `state`, `current_period_start/end`, `cancel_at_period_end`. |
| `subscription_items` | Line items inside a sub (base plan + addons + seats). |
| `subscription_addons` | Active addons (pay-per-use unlocks, extra seats). |
| `subscription_events` | **Append-only** state transitions: `created`, `trial_started`, `activated`, `renewed`, `upgraded`, `downgraded`, `past_due`, `dunning_started`, `canceled`, `reactivated`, `expired`. |
| `trials` | Trial windows separated so they survive sub cancellation (anti-abuse). |
| `gift_subscriptions` | Bought by A, redeemed by B; carries a redemption code + activation window. |
| `proration_calculations` | Cached proration computations for mid-cycle plan changes. |

### 2.5 Payments & Providers
| Table | Purpose |
|---|---|
| `payment_providers` | Admin registry: `stripe`, `paypal`, `payme`, `click`, `apple_iap`, `google_play`. Config + credentials per tenant. |
| `payment_methods` | Saved methods per user (tokenized card, PayPal account ref, Payme account, IAP receipt anchor). |
| `payment_intents` | A pending or completed authorization. One per checkout attempt. |
| `payments` | Settled payment rows; double-entry source. |
| `payment_webhook_events` | **Every** inbound webhook stored raw, idempotent by `(provider, provider_event_id)`. |
| `payment_method_changes` | History of card replacements so subscriptions migrate cleanly. |
| `iap_receipts` | Apple/Google receipts and server-to-server notification log. |
| `iap_receipt_validations` | Each validation call to Apple/Google, with response. |

### 2.6 Invoices, Refunds, Disputes
| Table | Purpose |
|---|---|
| `invoices` | A document number, period, tenant, customer, total. |
| `invoice_lines` | Per item, with unit, qty, tax, discount, currency. |
| `receipts` | PDFs / hashes of generated receipts (CDN URLs). |
| `refunds` | Partial or full reversals. Posts compensating ledger entries. |
| `chargebacks` | Bank-initiated reversals (different from refund). |
| `disputes` | Active disputes with provider, evidence URLs, deadlines. |

### 2.7 Tax & VAT
| Table | Purpose |
|---|---|
| `tax_jurisdictions` | Country/state with applicable tax-rule template (EU OSS, UK VAT, US sales-tax, etc.). |
| `tax_rates` | `(jurisdiction, tax_type, product_class, rate, effective_from)`. |
| `tax_calculations` | Per invoice line, the computed tax result (cached). |
| `vat_validations` | VIES / HMRC VAT-number validation cache for B2B reverse-charge. |
| `tax_exemptions` | Per customer / per jurisdiction exempt certificates. |

### 2.8 Promotions
| Table | Purpose |
|---|---|
| `coupons` | Definition: `(code_pattern, percent_off OR amount_off, currency, max_redemptions, redemptions_used, valid_from/until, plan_scope, region_scope)`. |
| `promo_codes` | Issued codes pointing at a coupon. |
| `coupon_redemptions` | Every successful apply. |
| `referrals` | Referrer → referee link. |
| `referral_credits` | Wallet-style credit earned, redeemable on future invoices. |
| `gift_subscriptions` | (cross-ref §2.4) — gifting flow. |

### 2.9 Dunning & Grace
| Table | Purpose |
|---|---|
| `dunning_state` | Current dunning step per failing sub: `notified_t1`, `retry_t3`, `retry_t7`, `final_t14`, `canceled`. |
| `dunning_attempts` | Each retry attempt + provider response. |
| `grace_periods` | Per-tenant configurable grace window after `past_due`. |

### 2.10 B2B Listings & Auctions
| Table | Purpose |
|---|---|
| `b2b_accounts` | A registered hotel/restaurant/transport company. KYC-verified. |
| `b2b_account_members` | Users who manage that account. |
| `b2b_listing_categories` | Admin-defined categories (`hotel`, `restaurant`, `taxi`, `bus`, `souvenir`, `tour_guide`, …). |
| `b2b_listings` | A listing tied to one or more `heritage_id`s (Agent 1) with content, hours, contact. |
| `b2b_listing_locales` | Translations per listing. |
| `b2b_listing_assets` | Photos/menus, moderated. |
| `b2b_auctions` | One auction per `(heritage_id, slot_position, billing_period_id)`. |
| `b2b_bids` | Sealed bids; reveal at auction close. |
| `b2b_billing_periods` | Calendar of bid windows (e.g. monthly). |
| `b2b_listing_assignments` | Auction winner → slot. |
| `b2b_listing_views` | Impression log (daily partition). |
| `b2b_listing_clicks` | Click log (daily partition) → drives CPC overage. |
| `b2b_listing_invoices` | Monthly invoice covering won-slot price + CPC overage. |

### 2.11 Enterprise API
| Table | Purpose |
|---|---|
| `enterprise_accounts` | A company purchasing the API (turizm agentlik, museum, ministry). |
| `enterprise_seats` | Named users within the account, each with a role. |
| `enterprise_contracts` | Negotiated SLAs, override pricing, custom rate-limits. |
| `api_keys` | Hashed key, prefix shown, owner, scopes, rate-limit class, IP allowlist, status. |
| `api_key_scopes` | `(api_key_id, scope)` many-to-many: `heritage.read`, `vision.classify`, `tts.generate`, `chat.complete`, `route.plan`, `b2b.read`, …. |
| `api_key_rotations` | History of rotation events. |
| `api_usage_records` | Per-request metering: `(api_key_id, endpoint, units, cost_units, request_id, latency_ms, ts)` — **PARTITION BY RANGE (ts) DAILY**. |
| `quotas` | Quota definition per plan or per contract. |
| `quota_usage` | Rolling window counters (also mirrored in Redis). |

### 2.12 Affiliate
| Table | Purpose |
|---|---|
| `affiliate_partners` | Booking.com, GetYourGuide, Klook, Aviasales, Wolt, Yandex Go, … |
| `affiliate_offers` | Offer per partner: commission %, attribution window, allowed regions. |
| `affiliate_links` | A shortlink + UTM payload; tied to a user, listing or heritage page. |
| `affiliate_clicks` | Each outbound click (daily partition). |
| `affiliate_conversions` | Confirmed conversions via partner postback. |
| `affiliate_commissions` | Earned commission, status (`pending`, `confirmed`, `clawed_back`, `paid`). |

### 2.13 Payouts (B2B & Affiliates)
| Table | Purpose |
|---|---|
| `payout_methods` | Bank, Stripe Connect, Payme/Click account per recipient. |
| `payout_batches` | A scheduled batch (weekly/monthly). |
| `payouts` | Individual payout to a B2B account, enterprise reseller, affiliate, or souvenir seller. |
| `payout_ledger` | Pre-payout earnings ledger per recipient. |

### 2.14 Marketplace & Tips
| Table | Purpose |
|---|---|
| `marketplace_items` | Souvenir SKUs, with seller (B2B) and price. |
| `marketplace_orders` | One-time purchases. |
| `marketplace_order_items` | Line items. |
| `marketplace_shipments` | Carrier, tracking, status. |
| `tips` | One-off tips to content creators or local guides. |

### 2.15 Revenue Recognition & Analytics
| Table | Purpose |
|---|---|
| `revenue_recognition_ledger` | **Double-entry GAAP ledger.** Every payment splits into `accounts_receivable`, `deferred_revenue`, `recognized_revenue`, `tax_payable`, `processor_fees`, `refund_liability`. |
| `deferred_revenue_schedule` | For annual plans: monthly recognition schedule. |
| `chart_of_accounts` | Tenant-scoped chart of accounts. |
| `revenue_snapshots` | Nightly rollups: MRR, ARR, churn, expansion, contraction, ARPU, LTV, CAC per channel — per tenant. |
| `cac_attributions` | Marketing channel cost attribution to user signups. |
| `cohort_metrics` | Cohort retention and LTV by signup month. |

**Total: 96 tables.**

---

## 3. Full Table-by-Table Specification

> Conventions:
> - Every monetary table has `tenant_id UUID NOT NULL REFERENCES tenants(id)` and is covered by RLS policy `tenant_isolation`.
> - Every table has `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`, `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`, `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()`.
> - Money columns: `amount NUMERIC(20,4) NOT NULL`, `currency CHAR(3) NOT NULL REFERENCES currencies(code)`.
> - Soft delete via `deleted_at TIMESTAMPTZ NULL` only where retention requires it; financial rows are **never** deleted.
> - State enums implemented as `CHECK` constraints (Postgres) or referenced lookup tables (`*_states`).

### 3.1 Tenancy

```sql
CREATE TABLE tenants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug TEXT NOT NULL UNIQUE,                       -- 'silklens', 'visit-tashkent'
  legal_name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active','suspended','archived','provisioning')),
  parent_tenant_id UUID NULL REFERENCES tenants(id),  -- reseller hierarchies
  default_locale TEXT NOT NULL DEFAULT 'en',
  default_currency CHAR(3) NOT NULL DEFAULT 'USD' REFERENCES currencies(code),
  default_pricing_zone_id UUID NOT NULL REFERENCES pricing_zones(id),
  is_root BOOLEAN NOT NULL DEFAULT FALSE,
  contract_starts_at TIMESTAMPTZ,
  contract_ends_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX ux_tenants_root_singleton ON tenants(is_root) WHERE is_root = TRUE;

CREATE TABLE tenant_branding (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  locale TEXT NOT NULL,
  app_name TEXT NOT NULL,
  logo_light_url TEXT,
  logo_dark_url TEXT,
  splash_url TEXT,
  primary_color TEXT,
  secondary_color TEXT,
  font_family TEXT,
  store_listing_blob JSONB,                        -- per-store metadata
  effective_from TIMESTAMPTZ NOT NULL DEFAULT now(),
  effective_to TIMESTAMPTZ,
  UNIQUE (tenant_id, locale, effective_from)
);

CREATE TABLE tenant_domains (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  hostname TEXT NOT NULL UNIQUE,
  scope TEXT NOT NULL CHECK (scope IN ('web','admin','api')),
  cert_ref TEXT,
  verified_at TIMESTAMPTZ
);

CREATE TABLE tenant_revenue_share (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  recipient_account_id UUID NOT NULL,              -- reseller payout target
  product_id UUID NULL REFERENCES products(id),    -- NULL = all products
  share_percent NUMERIC(7,4) NOT NULL CHECK (share_percent BETWEEN 0 AND 100),
  effective_from TIMESTAMPTZ NOT NULL DEFAULT now(),
  effective_to TIMESTAMPTZ
);

CREATE TABLE tenant_payment_provider_config (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  provider_id UUID NOT NULL REFERENCES payment_providers(id),
  is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  credentials_secret_ref TEXT NOT NULL,            -- pointer to Vault/KMS
  account_ref TEXT,                                -- Stripe account ID, Payme merchant ID, etc.
  webhook_secret_ref TEXT,
  UNIQUE (tenant_id, provider_id)
);
```

### 3.2 Product, Plan, Feature Matrix

```sql
CREATE TABLE products (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  key TEXT NOT NULL,                               -- 'consumer_premium', 'b2b_featured'...
  type TEXT NOT NULL CHECK (type IN ('subscription','one_time','metered','b2b','enterprise','marketplace','tip')),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  UNIQUE (tenant_id, key)
);

CREATE TABLE product_plans (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  product_id UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
  key TEXT NOT NULL,                               -- 'premium_monthly'
  display_name JSONB NOT NULL,                     -- {en:..., uz:..., ru:...}
  billing_interval TEXT CHECK (billing_interval IN ('monthly','annual','weekly','daily','one_time')),
  trial_days INT NOT NULL DEFAULT 0,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  sort_order INT NOT NULL DEFAULT 0,
  UNIQUE (tenant_id, product_id, key)
);

CREATE TABLE feature_flags (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  key TEXT NOT NULL UNIQUE,                        -- global key, e.g. 'ar_overlay'
  description TEXT,
  value_type TEXT NOT NULL CHECK (value_type IN ('bool','int','json')),
  category TEXT                                    -- 'ai','ar','offline','social','b2b'
);

CREATE TABLE plan_features (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  plan_id UUID NOT NULL REFERENCES product_plans(id) ON DELETE CASCADE,
  feature_flag_id UUID NOT NULL REFERENCES feature_flags(id),
  value JSONB NOT NULL,                            -- true | {"limit": 100} | etc.
  UNIQUE (tenant_id, plan_id, feature_flag_id)
);

CREATE TABLE entitlements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  user_id UUID NOT NULL,                           -- → Agent 2 users.id
  feature_key TEXT NOT NULL,
  value JSONB NOT NULL,
  source_subscription_id UUID REFERENCES subscriptions(id),
  expires_at TIMESTAMPTZ,
  refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, user_id, feature_key)
);
CREATE INDEX ix_entitlements_user ON entitlements (tenant_id, user_id);

CREATE TABLE addon_products (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  parent_product_id UUID REFERENCES products(id),
  key TEXT NOT NULL,
  display_name JSONB NOT NULL,
  unlocks_feature_key TEXT NOT NULL REFERENCES feature_flags(key),
  unit TEXT,                                       -- 'city_pack', 'ar_experience'
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  UNIQUE (tenant_id, key)
);
```

### 3.3 Pricing & Currency

```sql
CREATE TABLE currencies (
  code CHAR(3) PRIMARY KEY,                        -- ISO 4217
  name TEXT NOT NULL,
  symbol TEXT NOT NULL,
  decimals SMALLINT NOT NULL DEFAULT 2,
  is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE pricing_zones (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  key TEXT NOT NULL UNIQUE,                        -- 'CIS','EU','NA','SEA',...
  description TEXT,
  ppp_index NUMERIC(10,4),                         -- relative purchasing power
  base_currency CHAR(3) NOT NULL REFERENCES currencies(code)
);

CREATE TABLE pricing_zone_countries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pricing_zone_id UUID NOT NULL REFERENCES pricing_zones(id),
  country_code CHAR(2) NOT NULL,                   -- ISO 3166-1 alpha-2
  UNIQUE (country_code)
);

CREATE TABLE seasonal_modifiers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  name TEXT NOT NULL,
  pricing_zone_id UUID REFERENCES pricing_zones(id), -- NULL = all zones
  date_window TSTZRANGE NOT NULL,
  percent_adjust NUMERIC(7,4) NOT NULL,            -- -50.0000 = 50% off
  is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE prices (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  plan_id UUID NOT NULL REFERENCES product_plans(id),
  pricing_zone_id UUID NOT NULL REFERENCES pricing_zones(id),
  currency CHAR(3) NOT NULL REFERENCES currencies(code),
  amount NUMERIC(20,4) NOT NULL,
  effective_from TIMESTAMPTZ NOT NULL DEFAULT now(),
  effective_to TIMESTAMPTZ,
  experiment_id UUID REFERENCES price_experiments(id),
  EXCLUDE USING gist (
    tenant_id WITH =,
    plan_id WITH =,
    pricing_zone_id WITH =,
    currency WITH =,
    tstzrange(effective_from, COALESCE(effective_to,'infinity')) WITH &&
  ) WHERE (experiment_id IS NULL)
);

CREATE TABLE price_experiments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  plan_id UUID NOT NULL REFERENCES product_plans(id),
  pricing_zone_id UUID NOT NULL REFERENCES pricing_zones(id),
  hypothesis TEXT,
  bucket_ratios JSONB NOT NULL,                    -- {"A":0.5,"B":0.5}
  status TEXT NOT NULL CHECK (status IN ('draft','running','concluded','aborted')),
  started_at TIMESTAMPTZ,
  ended_at TIMESTAMPTZ
);

CREATE TABLE exchange_rate_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  base CHAR(3) NOT NULL REFERENCES currencies(code),
  quote CHAR(3) NOT NULL REFERENCES currencies(code),
  rate NUMERIC(24,10) NOT NULL,
  source TEXT NOT NULL,                            -- 'ecb','openexchangerates','manual'
  captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  payment_intent_id UUID REFERENCES payment_intents(id)
);
CREATE INDEX ix_xrate_lookup ON exchange_rate_snapshots (base, quote, captured_at DESC);
```

### 3.4 Subscriptions

```sql
CREATE TABLE subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  user_id UUID NOT NULL,                           -- → Agent 2 users.id
  product_id UUID NOT NULL REFERENCES products(id),
  plan_id UUID NOT NULL REFERENCES product_plans(id),
  state TEXT NOT NULL CHECK (state IN (
    'incomplete','trialing','active','past_due','grace','canceled','expired','paused'
  )),
  current_period_start TIMESTAMPTZ NOT NULL,
  current_period_end TIMESTAMPTZ NOT NULL,
  cancel_at_period_end BOOLEAN NOT NULL DEFAULT FALSE,
  canceled_at TIMESTAMPTZ,
  trial_end TIMESTAMPTZ,
  payment_method_id UUID REFERENCES payment_methods(id),
  provider_id UUID NOT NULL REFERENCES payment_providers(id),
  provider_subscription_ref TEXT,                  -- 'sub_xxx' on Stripe
  currency CHAR(3) NOT NULL REFERENCES currencies(code),
  pricing_zone_id UUID NOT NULL REFERENCES pricing_zones(id),
  current_price_id UUID NOT NULL REFERENCES prices(id),
  collection_method TEXT NOT NULL DEFAULT 'charge_automatically'
    CHECK (collection_method IN ('charge_automatically','send_invoice')),
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_subscriptions_user ON subscriptions (tenant_id, user_id, state);
CREATE INDEX ix_subscriptions_renewal ON subscriptions (current_period_end) WHERE state IN ('active','trialing');

CREATE TABLE subscription_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  subscription_id UUID NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
  plan_id UUID REFERENCES product_plans(id),
  addon_id UUID REFERENCES addon_products(id),
  quantity INT NOT NULL DEFAULT 1,
  unit_amount NUMERIC(20,4) NOT NULL,
  currency CHAR(3) NOT NULL REFERENCES currencies(code),
  added_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  removed_at TIMESTAMPTZ,
  CHECK ( (plan_id IS NOT NULL) <> (addon_id IS NOT NULL) )
);

CREATE TABLE subscription_addons (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  subscription_id UUID NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
  addon_id UUID NOT NULL REFERENCES addon_products(id),
  state TEXT NOT NULL CHECK (state IN ('active','expired','revoked')),
  expires_at TIMESTAMPTZ
);

CREATE TABLE subscription_events (
  id BIGSERIAL PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  subscription_id UUID NOT NULL REFERENCES subscriptions(id),
  event_type TEXT NOT NULL,                        -- 'created','trial_started','activated','renewed','upgraded','downgraded','past_due','dunning_started','dunning_succeeded','canceled','reactivated','expired','paused','resumed'
  from_state TEXT,
  to_state TEXT,
  reason TEXT,
  actor_type TEXT CHECK (actor_type IN ('user','system','admin','webhook')),
  actor_id UUID,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  payload JSONB
) PARTITION BY RANGE (occurred_at);

CREATE TABLE trials (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  user_id UUID NOT NULL,
  plan_id UUID NOT NULL REFERENCES product_plans(id),
  subscription_id UUID REFERENCES subscriptions(id),
  starts_at TIMESTAMPTZ NOT NULL,
  ends_at TIMESTAMPTZ NOT NULL,
  consumed BOOLEAN NOT NULL DEFAULT FALSE,
  UNIQUE (tenant_id, user_id, plan_id)             -- one trial per plan per user
);

CREATE TABLE gift_subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  buyer_user_id UUID NOT NULL,
  recipient_email TEXT,
  recipient_user_id UUID,
  plan_id UUID NOT NULL REFERENCES product_plans(id),
  duration_months SMALLINT NOT NULL,
  redemption_code TEXT NOT NULL UNIQUE,
  payment_id UUID REFERENCES payments(id),
  state TEXT NOT NULL CHECK (state IN ('purchased','sent','redeemed','expired','refunded')),
  redeemed_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE proration_calculations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  subscription_id UUID NOT NULL REFERENCES subscriptions(id),
  from_plan_id UUID NOT NULL REFERENCES product_plans(id),
  to_plan_id UUID NOT NULL REFERENCES product_plans(id),
  days_used INT NOT NULL,
  days_remaining INT NOT NULL,
  credit_amount NUMERIC(20,4) NOT NULL,
  debit_amount NUMERIC(20,4) NOT NULL,
  net_amount NUMERIC(20,4) NOT NULL,
  currency CHAR(3) NOT NULL REFERENCES currencies(code),
  applied_at TIMESTAMPTZ
);
```

### 3.5 Payments

```sql
CREATE TABLE payment_providers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  key TEXT NOT NULL UNIQUE,                        -- 'stripe','paypal','payme','click','apple_iap','google_play'
  display_name TEXT NOT NULL,
  capabilities JSONB NOT NULL,                     -- ['cards','wallets','iap','recurring','refunds','3ds']
  status TEXT NOT NULL CHECK (status IN ('active','degraded','disabled'))
);

CREATE TABLE payment_methods (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  user_id UUID NOT NULL,
  provider_id UUID NOT NULL REFERENCES payment_providers(id),
  type TEXT NOT NULL CHECK (type IN ('card','wallet','bank','iap_apple','iap_google','payme','click','paypal')),
  brand TEXT,
  last4 CHAR(4),
  exp_month SMALLINT,
  exp_year SMALLINT,
  provider_token_ref TEXT NOT NULL,                -- never the raw card
  fingerprint TEXT,
  is_default BOOLEAN NOT NULL DEFAULT FALSE,
  status TEXT NOT NULL CHECK (status IN ('active','expired','removed','requires_action')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_pm_user ON payment_methods (tenant_id, user_id, status);

CREATE TABLE payment_intents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  user_id UUID,
  b2b_account_id UUID REFERENCES b2b_accounts(id),
  enterprise_account_id UUID REFERENCES enterprise_accounts(id),
  subscription_id UUID REFERENCES subscriptions(id),
  invoice_id UUID REFERENCES invoices(id),
  amount NUMERIC(20,4) NOT NULL,
  currency CHAR(3) NOT NULL REFERENCES currencies(code),
  amount_base NUMERIC(20,4),                       -- in tenant base currency
  base_currency CHAR(3),
  exchange_rate_snapshot_id UUID REFERENCES exchange_rate_snapshots(id),
  provider_id UUID NOT NULL REFERENCES payment_providers(id),
  provider_intent_ref TEXT,
  status TEXT NOT NULL CHECK (status IN ('requires_action','processing','succeeded','failed','canceled','expired')),
  idempotency_key TEXT NOT NULL,
  client_secret TEXT,
  failure_reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, idempotency_key)
);
CREATE INDEX ix_pi_provider ON payment_intents (provider_id, provider_intent_ref);

CREATE TABLE payments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  payment_intent_id UUID NOT NULL REFERENCES payment_intents(id),
  invoice_id UUID REFERENCES invoices(id),
  subscription_id UUID REFERENCES subscriptions(id),
  amount_gross NUMERIC(20,4) NOT NULL,
  amount_fee NUMERIC(20,4) NOT NULL DEFAULT 0,
  amount_net NUMERIC(20,4) NOT NULL,
  currency CHAR(3) NOT NULL REFERENCES currencies(code),
  provider_id UUID NOT NULL REFERENCES payment_providers(id),
  provider_payment_ref TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('succeeded','refunded','partially_refunded','disputed','reversed')),
  captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (provider_id, provider_payment_ref)
);

CREATE TABLE payment_webhook_events (
  id BIGSERIAL PRIMARY KEY,
  provider_id UUID NOT NULL REFERENCES payment_providers(id),
  provider_event_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  signature TEXT,
  raw_payload JSONB NOT NULL,
  received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  processed_at TIMESTAMPTZ,
  processed_state TEXT NOT NULL DEFAULT 'pending'
    CHECK (processed_state IN ('pending','processing','succeeded','failed','skipped')),
  attempts INT NOT NULL DEFAULT 0,
  last_error TEXT,
  UNIQUE (provider_id, provider_event_id)
);
CREATE INDEX ix_webhook_unprocessed ON payment_webhook_events (processed_state, received_at)
  WHERE processed_state IN ('pending','failed');

CREATE TABLE payment_method_changes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  subscription_id UUID NOT NULL REFERENCES subscriptions(id),
  old_payment_method_id UUID REFERENCES payment_methods(id),
  new_payment_method_id UUID REFERENCES payment_methods(id),
  changed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  reason TEXT
);

CREATE TABLE iap_receipts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  user_id UUID NOT NULL,
  provider TEXT NOT NULL CHECK (provider IN ('apple','google')),
  bundle_id TEXT NOT NULL,
  original_transaction_id TEXT NOT NULL,
  latest_transaction_id TEXT NOT NULL,
  receipt_blob TEXT NOT NULL,                      -- base64 (Apple) or purchase token (Google)
  product_identifier TEXT NOT NULL,
  expires_at TIMESTAMPTZ,
  auto_renew BOOLEAN,
  environment TEXT CHECK (environment IN ('sandbox','production')),
  subscription_id UUID REFERENCES subscriptions(id),
  UNIQUE (provider, original_transaction_id)
);

CREATE TABLE iap_receipt_validations (
  id BIGSERIAL PRIMARY KEY,
  iap_receipt_id UUID NOT NULL REFERENCES iap_receipts(id),
  validated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  status_code INT,
  response_blob JSONB,
  notification_type TEXT                           -- DID_RENEW, EXPIRED, GRACE_PERIOD_EXPIRED...
);
```

### 3.6 Invoices, Refunds, Disputes

```sql
CREATE TABLE invoices (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  number TEXT NOT NULL,                            -- 'SLN-2026-0001234'
  customer_user_id UUID,
  b2b_account_id UUID REFERENCES b2b_accounts(id),
  enterprise_account_id UUID REFERENCES enterprise_accounts(id),
  subscription_id UUID REFERENCES subscriptions(id),
  status TEXT NOT NULL CHECK (status IN ('draft','open','paid','past_due','void','uncollectible')),
  period_start TIMESTAMPTZ,
  period_end TIMESTAMPTZ,
  subtotal NUMERIC(20,4) NOT NULL,
  tax_total NUMERIC(20,4) NOT NULL,
  discount_total NUMERIC(20,4) NOT NULL DEFAULT 0,
  total NUMERIC(20,4) NOT NULL,
  currency CHAR(3) NOT NULL REFERENCES currencies(code),
  due_at TIMESTAMPTZ,
  finalized_at TIMESTAMPTZ,
  paid_at TIMESTAMPTZ,
  pdf_url TEXT,
  UNIQUE (tenant_id, number)
);

CREATE TABLE invoice_lines (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
  description TEXT NOT NULL,
  quantity NUMERIC(20,4) NOT NULL DEFAULT 1,
  unit_amount NUMERIC(20,4) NOT NULL,
  amount NUMERIC(20,4) NOT NULL,
  tax_amount NUMERIC(20,4) NOT NULL DEFAULT 0,
  tax_calculation_id UUID REFERENCES tax_calculations(id),
  plan_id UUID REFERENCES product_plans(id),
  addon_id UUID REFERENCES addon_products(id),
  b2b_listing_assignment_id UUID REFERENCES b2b_listing_assignments(id),
  api_usage_period_start TIMESTAMPTZ,
  api_usage_period_end TIMESTAMPTZ,
  currency CHAR(3) NOT NULL REFERENCES currencies(code)
);

CREATE TABLE receipts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  invoice_id UUID NOT NULL REFERENCES invoices(id),
  pdf_url TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  issued_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE refunds (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  payment_id UUID NOT NULL REFERENCES payments(id),
  amount NUMERIC(20,4) NOT NULL,
  currency CHAR(3) NOT NULL REFERENCES currencies(code),
  reason TEXT,
  initiator TEXT CHECK (initiator IN ('user','admin','system','provider')),
  status TEXT NOT NULL CHECK (status IN ('pending','succeeded','failed')),
  provider_refund_ref TEXT,
  refunded_at TIMESTAMPTZ
);

CREATE TABLE chargebacks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  payment_id UUID NOT NULL REFERENCES payments(id),
  amount NUMERIC(20,4) NOT NULL,
  currency CHAR(3) NOT NULL REFERENCES currencies(code),
  network_code TEXT,
  reason_code TEXT,
  received_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE disputes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  payment_id UUID NOT NULL REFERENCES payments(id),
  provider_dispute_ref TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('warning_needs_response','needs_response','under_review','won','lost')),
  evidence_due_by TIMESTAMPTZ,
  evidence_urls JSONB,
  resolution_amount NUMERIC(20,4),
  closed_at TIMESTAMPTZ
);
```

### 3.7 Tax

```sql
CREATE TABLE tax_jurisdictions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  country_code CHAR(2) NOT NULL,
  region_code TEXT,                                -- US state, CA province
  template TEXT NOT NULL CHECK (template IN ('eu_oss','uk_vat','us_sales_tax','uz_vat','generic','exempt')),
  UNIQUE (country_code, region_code)
);

CREATE TABLE tax_rates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  jurisdiction_id UUID NOT NULL REFERENCES tax_jurisdictions(id),
  tax_type TEXT NOT NULL,                          -- 'vat','gst','sales_tax'
  product_class TEXT NOT NULL,                     -- 'digital_service','physical_good','shipping'
  rate NUMERIC(7,4) NOT NULL,                      -- 0.2000 = 20%
  effective_from DATE NOT NULL,
  effective_to DATE
);

CREATE TABLE tax_calculations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  jurisdiction_id UUID NOT NULL REFERENCES tax_jurisdictions(id),
  tax_rate_id UUID NOT NULL REFERENCES tax_rates(id),
  taxable_amount NUMERIC(20,4) NOT NULL,
  tax_amount NUMERIC(20,4) NOT NULL,
  reverse_charge BOOLEAN NOT NULL DEFAULT FALSE,
  computed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE vat_validations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  vat_number TEXT NOT NULL,
  country_code CHAR(2) NOT NULL,
  is_valid BOOLEAN NOT NULL,
  raw_response JSONB,
  validated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ,
  UNIQUE (vat_number, country_code)
);

CREATE TABLE tax_exemptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  jurisdiction_id UUID NOT NULL REFERENCES tax_jurisdictions(id),
  scope TEXT NOT NULL CHECK (scope IN ('user','b2b_account','enterprise_account')),
  scope_ref UUID NOT NULL,
  certificate_url TEXT,
  effective_from DATE NOT NULL,
  effective_to DATE
);
```

### 3.8 Promotions

```sql
CREATE TABLE coupons (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  code TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('percent','amount','free_trial_extend')),
  percent_off NUMERIC(7,4),
  amount_off NUMERIC(20,4),
  currency CHAR(3) REFERENCES currencies(code),
  max_redemptions INT,
  redemptions_used INT NOT NULL DEFAULT 0,
  valid_from TIMESTAMPTZ,
  valid_until TIMESTAMPTZ,
  plan_scope UUID[] DEFAULT '{}',                  -- empty = all
  pricing_zone_scope UUID[] DEFAULT '{}',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  UNIQUE (tenant_id, code)
);

CREATE TABLE promo_codes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  coupon_id UUID NOT NULL REFERENCES coupons(id),
  code TEXT NOT NULL UNIQUE,
  single_use_for_user_id UUID,
  is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE coupon_redemptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  coupon_id UUID NOT NULL REFERENCES coupons(id),
  user_id UUID NOT NULL,
  subscription_id UUID REFERENCES subscriptions(id),
  invoice_id UUID REFERENCES invoices(id),
  applied_amount NUMERIC(20,4) NOT NULL,
  currency CHAR(3) NOT NULL REFERENCES currencies(code),
  redeemed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, coupon_id, user_id)           -- one redeem per user per coupon
);

CREATE TABLE referrals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  referrer_user_id UUID NOT NULL,
  referee_user_id UUID NOT NULL,
  referral_code TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('pending','qualified','rewarded','revoked')),
  qualified_at TIMESTAMPTZ,
  rewarded_at TIMESTAMPTZ,
  UNIQUE (tenant_id, referee_user_id)              -- a user can only be referred once
);

CREATE TABLE referral_credits (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  user_id UUID NOT NULL,
  amount NUMERIC(20,4) NOT NULL,
  currency CHAR(3) NOT NULL REFERENCES currencies(code),
  source TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('available','consumed','expired')),
  expires_at TIMESTAMPTZ,
  consumed_invoice_id UUID REFERENCES invoices(id)
);
```

### 3.9 Dunning

```sql
CREATE TABLE dunning_state (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  subscription_id UUID NOT NULL REFERENCES subscriptions(id) UNIQUE,
  step TEXT NOT NULL,                              -- 'notified_t1','retry_t3','retry_t7','final_t14','canceled'
  next_action_at TIMESTAMPTZ NOT NULL,
  attempts_made INT NOT NULL DEFAULT 0,
  last_attempted_at TIMESTAMPTZ,
  resolved_at TIMESTAMPTZ
);

CREATE TABLE dunning_attempts (
  id BIGSERIAL PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  subscription_id UUID NOT NULL REFERENCES subscriptions(id),
  payment_intent_id UUID REFERENCES payment_intents(id),
  attempted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  outcome TEXT NOT NULL CHECK (outcome IN ('succeeded','failed','requires_action','soft_decline','hard_decline')),
  failure_code TEXT,
  failure_message TEXT
);

CREATE TABLE grace_periods (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  plan_id UUID NOT NULL REFERENCES product_plans(id),
  grace_days INT NOT NULL DEFAULT 7,
  UNIQUE (tenant_id, plan_id)
);
```

### 3.10 B2B Listings & Auctions

```sql
CREATE TABLE b2b_accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  legal_name TEXT NOT NULL,
  display_name TEXT NOT NULL,
  country_code CHAR(2) NOT NULL,
  tax_id TEXT,
  vat_validation_id UUID REFERENCES vat_validations(id),
  contact_email CITEXT NOT NULL,
  contact_phone TEXT,
  status TEXT NOT NULL CHECK (status IN ('pending_kyc','active','suspended','banned')),
  kyc_data JSONB,
  default_payout_method_id UUID REFERENCES payout_methods(id),
  approved_at TIMESTAMPTZ
);

CREATE TABLE b2b_account_members (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  b2b_account_id UUID NOT NULL REFERENCES b2b_accounts(id),
  user_id UUID NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('owner','admin','manager','billing','viewer')),
  UNIQUE (b2b_account_id, user_id)
);

CREATE TABLE b2b_listing_categories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  key TEXT NOT NULL,                               -- 'hotel','restaurant','taxi','bus','souvenir','tour_guide'
  display_name JSONB NOT NULL,
  parent_id UUID REFERENCES b2b_listing_categories(id),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  UNIQUE (tenant_id, key)
);

CREATE TABLE b2b_listings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  b2b_account_id UUID NOT NULL REFERENCES b2b_accounts(id),
  category_id UUID NOT NULL REFERENCES b2b_listing_categories(id),
  primary_heritage_id UUID NOT NULL,               -- → Agent 1 heritage_objects.id
  geo POINT,
  name TEXT NOT NULL,
  short_description TEXT,
  contact_email CITEXT,
  contact_phone TEXT,
  url TEXT,
  status TEXT NOT NULL CHECK (status IN ('draft','pending_review','published','rejected','paused','archived')),
  moderation_notes TEXT,
  published_at TIMESTAMPTZ
);

CREATE TABLE b2b_listing_heritage_links (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  listing_id UUID NOT NULL REFERENCES b2b_listings(id) ON DELETE CASCADE,
  heritage_id UUID NOT NULL,                       -- → Agent 1
  distance_meters INT,
  UNIQUE (listing_id, heritage_id)
);

CREATE TABLE b2b_listing_locales (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  listing_id UUID NOT NULL REFERENCES b2b_listings(id) ON DELETE CASCADE,
  locale TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  menu_url TEXT,
  UNIQUE (listing_id, locale)
);

CREATE TABLE b2b_listing_assets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  listing_id UUID NOT NULL REFERENCES b2b_listings(id) ON DELETE CASCADE,
  kind TEXT NOT NULL CHECK (kind IN ('photo','video','menu_pdf','logo','interior_360')),
  url TEXT NOT NULL,
  moderation_status TEXT NOT NULL DEFAULT 'pending'
    CHECK (moderation_status IN ('pending','approved','rejected'))
);

CREATE TABLE b2b_billing_periods (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  period_starts_at TIMESTAMPTZ NOT NULL,
  period_ends_at TIMESTAMPTZ NOT NULL,
  bidding_closes_at TIMESTAMPTZ NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('upcoming','bidding','settled','invoiced','closed')),
  UNIQUE (tenant_id, period_starts_at)
);

CREATE TABLE b2b_auctions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  billing_period_id UUID NOT NULL REFERENCES b2b_billing_periods(id),
  heritage_id UUID NOT NULL,                       -- → Agent 1
  slot_position SMALLINT NOT NULL CHECK (slot_position BETWEEN 1 AND 5),
  category_id UUID NOT NULL REFERENCES b2b_listing_categories(id),
  minimum_bid NUMERIC(20,4) NOT NULL,
  currency CHAR(3) NOT NULL REFERENCES currencies(code),
  status TEXT NOT NULL CHECK (status IN ('open','closed','settled','voided')),
  closes_at TIMESTAMPTZ NOT NULL,
  winning_bid_id UUID,                             -- FK after settlement
  UNIQUE (tenant_id, billing_period_id, heritage_id, slot_position, category_id)
);

CREATE TABLE b2b_bids (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  auction_id UUID NOT NULL REFERENCES b2b_auctions(id),
  b2b_account_id UUID NOT NULL REFERENCES b2b_accounts(id),
  listing_id UUID NOT NULL REFERENCES b2b_listings(id),
  amount NUMERIC(20,4) NOT NULL,
  currency CHAR(3) NOT NULL REFERENCES currencies(code),
  is_sealed BOOLEAN NOT NULL DEFAULT TRUE,
  submitted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  withdrawn_at TIMESTAMPTZ,
  ip INET,
  fraud_score NUMERIC(5,2),
  UNIQUE (auction_id, b2b_account_id)              -- one bid per account per auction
);
ALTER TABLE b2b_auctions
  ADD CONSTRAINT fk_b2b_auctions_winning_bid
  FOREIGN KEY (winning_bid_id) REFERENCES b2b_bids(id);

CREATE TABLE b2b_listing_assignments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  auction_id UUID NOT NULL REFERENCES b2b_auctions(id),
  listing_id UUID NOT NULL REFERENCES b2b_listings(id),
  b2b_account_id UUID NOT NULL REFERENCES b2b_accounts(id),
  heritage_id UUID NOT NULL,
  slot_position SMALLINT NOT NULL,
  starts_at TIMESTAMPTZ NOT NULL,
  ends_at TIMESTAMPTZ NOT NULL,
  flat_rate_amount NUMERIC(20,4) NOT NULL,
  cpc_rate NUMERIC(20,4),
  currency CHAR(3) NOT NULL REFERENCES currencies(code),
  status TEXT NOT NULL CHECK (status IN ('scheduled','active','expired','revoked'))
);
CREATE INDEX ix_assignment_heritage_active ON b2b_listing_assignments (heritage_id, status, ends_at);

CREATE TABLE b2b_listing_views (
  id BIGSERIAL,
  tenant_id UUID NOT NULL,
  assignment_id UUID NOT NULL,
  listing_id UUID NOT NULL,
  user_id UUID,
  device_id TEXT,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
) PARTITION BY RANGE (occurred_at);

CREATE TABLE b2b_listing_clicks (
  id BIGSERIAL,
  tenant_id UUID NOT NULL,
  assignment_id UUID NOT NULL,
  listing_id UUID NOT NULL,
  user_id UUID,
  device_id TEXT,
  ip INET,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  is_billable BOOLEAN NOT NULL DEFAULT TRUE,       -- de-duped server-side
  fraud_score NUMERIC(5,2)
) PARTITION BY RANGE (occurred_at);

CREATE TABLE b2b_listing_invoices (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  invoice_id UUID NOT NULL REFERENCES invoices(id),
  b2b_account_id UUID NOT NULL REFERENCES b2b_accounts(id),
  billing_period_id UUID NOT NULL REFERENCES b2b_billing_periods(id),
  flat_total NUMERIC(20,4) NOT NULL,
  cpc_billable_clicks INT NOT NULL,
  cpc_total NUMERIC(20,4) NOT NULL
);
```

### 3.11 Enterprise API

```sql
CREATE TABLE enterprise_accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  legal_name TEXT NOT NULL,
  primary_contact_email CITEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('active','suspended','closed')),
  tier TEXT NOT NULL CHECK (tier IN ('startup','growth','enterprise','government')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE enterprise_seats (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  enterprise_account_id UUID NOT NULL REFERENCES enterprise_accounts(id),
  user_id UUID NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('owner','admin','developer','billing','viewer')),
  status TEXT NOT NULL CHECK (status IN ('active','invited','revoked')),
  UNIQUE (enterprise_account_id, user_id)
);

CREATE TABLE enterprise_contracts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  enterprise_account_id UUID NOT NULL REFERENCES enterprise_accounts(id),
  starts_at DATE NOT NULL,
  ends_at DATE NOT NULL,
  committed_spend NUMERIC(20,4),
  overage_unit_price NUMERIC(20,4),
  currency CHAR(3) NOT NULL REFERENCES currencies(code),
  sla_uptime_pct NUMERIC(5,2),
  custom_terms_url TEXT,
  signed_at TIMESTAMPTZ
);

CREATE TABLE api_keys (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  owner_type TEXT NOT NULL CHECK (owner_type IN ('user','enterprise_account','b2b_account')),
  owner_id UUID NOT NULL,
  key_prefix TEXT NOT NULL,                        -- 'sl_live_abcd1234' (visible)
  key_hash BYTEA NOT NULL,                         -- HMAC-SHA256 hash; raw never stored
  label TEXT,
  rate_limit_class TEXT NOT NULL DEFAULT 'standard',
  ip_allowlist CIDR[] DEFAULT '{}',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  last_used_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ,
  created_by UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  rotated_from UUID REFERENCES api_keys(id),
  revoked_at TIMESTAMPTZ
);
CREATE UNIQUE INDEX ux_api_keys_hash ON api_keys (key_hash);

CREATE TABLE api_key_scopes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  api_key_id UUID NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
  scope TEXT NOT NULL,                             -- 'heritage.read','vision.classify',...
  UNIQUE (api_key_id, scope)
);

CREATE TABLE api_key_rotations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  api_key_id UUID NOT NULL REFERENCES api_keys(id),
  rotated_by UUID,
  rotated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  reason TEXT
);

CREATE TABLE api_usage_records (
  id BIGSERIAL,
  tenant_id UUID NOT NULL,
  api_key_id UUID NOT NULL,
  endpoint TEXT NOT NULL,
  method TEXT NOT NULL,
  status_code INT,
  units NUMERIC(10,2) NOT NULL DEFAULT 1,           -- billing units
  cost_units NUMERIC(20,4) NOT NULL DEFAULT 0,      -- AI cost passthrough — see Agent 3
  latency_ms INT,
  ip INET,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  request_id UUID
) PARTITION BY RANGE (occurred_at);

CREATE TABLE quotas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  scope TEXT NOT NULL CHECK (scope IN ('plan','contract','api_key','user')),
  scope_ref UUID NOT NULL,
  endpoint_pattern TEXT NOT NULL,
  window TEXT NOT NULL CHECK (window IN ('minute','hour','day','month')),
  limit_units NUMERIC(20,4) NOT NULL,
  hard_or_soft TEXT NOT NULL CHECK (hard_or_soft IN ('hard','soft')),
  effective_from TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE quota_usage (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL,
  quota_id UUID NOT NULL REFERENCES quotas(id),
  window_start TIMESTAMPTZ NOT NULL,
  window_end TIMESTAMPTZ NOT NULL,
  used_units NUMERIC(20,4) NOT NULL DEFAULT 0,
  UNIQUE (quota_id, window_start)
);
```

### 3.12 Affiliate

```sql
CREATE TABLE affiliate_partners (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  key TEXT NOT NULL,
  display_name TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('active','paused','terminated')),
  postback_secret_ref TEXT,
  UNIQUE (tenant_id, key)
);

CREATE TABLE affiliate_offers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  partner_id UUID NOT NULL REFERENCES affiliate_partners(id),
  commission_kind TEXT NOT NULL CHECK (commission_kind IN ('percent','flat')),
  commission_value NUMERIC(20,4) NOT NULL,
  currency CHAR(3) REFERENCES currencies(code),
  attribution_window_hours INT NOT NULL DEFAULT 72,
  allowed_country_codes CHAR(2)[] DEFAULT '{}',
  effective_from TIMESTAMPTZ NOT NULL DEFAULT now(),
  effective_to TIMESTAMPTZ
);

CREATE TABLE affiliate_links (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  offer_id UUID NOT NULL REFERENCES affiliate_offers(id),
  target_url TEXT NOT NULL,
  short_code TEXT NOT NULL UNIQUE,
  utm_payload JSONB NOT NULL,
  context_heritage_id UUID,
  context_listing_id UUID REFERENCES b2b_listings(id),
  created_by_user_id UUID
);

CREATE TABLE affiliate_clicks (
  id BIGSERIAL,
  tenant_id UUID NOT NULL,
  link_id UUID NOT NULL,
  user_id UUID,
  device_id TEXT,
  ip INET,
  user_agent TEXT,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
) PARTITION BY RANGE (occurred_at);

CREATE TABLE affiliate_conversions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  partner_id UUID NOT NULL REFERENCES affiliate_partners(id),
  link_id UUID REFERENCES affiliate_links(id),
  partner_conversion_ref TEXT NOT NULL,
  user_id UUID,
  conversion_amount NUMERIC(20,4) NOT NULL,
  currency CHAR(3) NOT NULL REFERENCES currencies(code),
  status TEXT NOT NULL CHECK (status IN ('pending','confirmed','clawed_back','rejected')),
  occurred_at TIMESTAMPTZ NOT NULL,
  UNIQUE (partner_id, partner_conversion_ref)
);

CREATE TABLE affiliate_commissions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  conversion_id UUID NOT NULL REFERENCES affiliate_conversions(id),
  offer_id UUID NOT NULL REFERENCES affiliate_offers(id),
  amount NUMERIC(20,4) NOT NULL,
  currency CHAR(3) NOT NULL REFERENCES currencies(code),
  status TEXT NOT NULL CHECK (status IN ('pending','confirmed','clawed_back','paid')),
  recipient_user_id UUID,                          -- for creator/influencer share
  paid_payout_id UUID REFERENCES payouts(id)
);
```

### 3.13 Payouts

```sql
CREATE TABLE payout_methods (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  owner_type TEXT NOT NULL CHECK (owner_type IN ('b2b_account','enterprise_account','user','affiliate_partner')),
  owner_id UUID NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('stripe_connect','bank','payme','click','paypal')),
  provider_account_ref TEXT NOT NULL,
  is_default BOOLEAN NOT NULL DEFAULT FALSE,
  verified_at TIMESTAMPTZ,
  status TEXT NOT NULL CHECK (status IN ('active','pending_verification','disabled'))
);

CREATE TABLE payout_batches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  period_start DATE NOT NULL,
  period_end DATE NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('open','processing','completed','failed')),
  total_amount NUMERIC(20,4) NOT NULL DEFAULT 0,
  currency CHAR(3) NOT NULL REFERENCES currencies(code),
  initiated_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ
);

CREATE TABLE payouts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  batch_id UUID REFERENCES payout_batches(id),
  recipient_method_id UUID NOT NULL REFERENCES payout_methods(id),
  amount NUMERIC(20,4) NOT NULL,
  currency CHAR(3) NOT NULL REFERENCES currencies(code),
  status TEXT NOT NULL CHECK (status IN ('pending','processing','paid','failed','reversed')),
  provider_payout_ref TEXT,
  failure_reason TEXT,
  initiated_at TIMESTAMPTZ,
  paid_at TIMESTAMPTZ
);

CREATE TABLE payout_ledger (
  id BIGSERIAL PRIMARY KEY,
  tenant_id UUID NOT NULL,
  owner_type TEXT NOT NULL,
  owner_id UUID NOT NULL,
  source TEXT NOT NULL,                            -- 'b2b_listing','affiliate','marketplace','tip','revenue_share'
  source_ref UUID NOT NULL,
  amount NUMERIC(20,4) NOT NULL,
  currency CHAR(3) NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('accrued','reserved','paid','clawed_back')),
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 3.14 Marketplace & Tips

```sql
CREATE TABLE marketplace_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  b2b_account_id UUID NOT NULL REFERENCES b2b_accounts(id),
  sku TEXT NOT NULL,
  name JSONB NOT NULL,
  description JSONB,
  primary_heritage_id UUID,
  unit_price NUMERIC(20,4) NOT NULL,
  currency CHAR(3) NOT NULL REFERENCES currencies(code),
  inventory INT NOT NULL DEFAULT 0,
  ships_internationally BOOLEAN NOT NULL DEFAULT FALSE,
  status TEXT NOT NULL CHECK (status IN ('draft','published','out_of_stock','archived')),
  UNIQUE (tenant_id, b2b_account_id, sku)
);

CREATE TABLE marketplace_orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  buyer_user_id UUID NOT NULL,
  invoice_id UUID REFERENCES invoices(id),
  shipping_address JSONB NOT NULL,
  subtotal NUMERIC(20,4) NOT NULL,
  shipping_amount NUMERIC(20,4) NOT NULL,
  tax_amount NUMERIC(20,4) NOT NULL,
  total NUMERIC(20,4) NOT NULL,
  currency CHAR(3) NOT NULL REFERENCES currencies(code),
  status TEXT NOT NULL CHECK (status IN ('pending','paid','shipped','delivered','canceled','refunded'))
);

CREATE TABLE marketplace_order_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  order_id UUID NOT NULL REFERENCES marketplace_orders(id) ON DELETE CASCADE,
  item_id UUID NOT NULL REFERENCES marketplace_items(id),
  quantity INT NOT NULL,
  unit_price NUMERIC(20,4) NOT NULL,
  currency CHAR(3) NOT NULL REFERENCES currencies(code)
);

CREATE TABLE marketplace_shipments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  order_id UUID NOT NULL REFERENCES marketplace_orders(id),
  carrier TEXT,
  tracking_number TEXT,
  status TEXT NOT NULL CHECK (status IN ('label_created','shipped','in_transit','delivered','returned'))
);

CREATE TABLE tips (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  payer_user_id UUID NOT NULL,
  recipient_user_id UUID,                          -- creator
  recipient_b2b_account_id UUID REFERENCES b2b_accounts(id),
  amount NUMERIC(20,4) NOT NULL,
  currency CHAR(3) NOT NULL REFERENCES currencies(code),
  payment_id UUID REFERENCES payments(id),
  message TEXT,
  status TEXT NOT NULL CHECK (status IN ('pending','succeeded','refunded'))
);
```

### 3.15 Revenue Recognition & Analytics

```sql
CREATE TABLE chart_of_accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  code TEXT NOT NULL,                              -- '4000-Revenue','2050-Deferred','1100-AR','5200-ProcessorFees'
  name TEXT NOT NULL,
  account_type TEXT NOT NULL CHECK (account_type IN ('asset','liability','equity','revenue','expense','contra_revenue')),
  UNIQUE (tenant_id, code)
);

CREATE TABLE revenue_recognition_ledger (
  id BIGSERIAL PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  txn_id UUID NOT NULL,                            -- groups balanced entries
  account_id UUID NOT NULL REFERENCES chart_of_accounts(id),
  source TEXT NOT NULL,                            -- 'payment','refund','recognition','accrual','payout'
  source_ref UUID NOT NULL,
  debit NUMERIC(20,4) NOT NULL DEFAULT 0,
  credit NUMERIC(20,4) NOT NULL DEFAULT 0,
  currency CHAR(3) NOT NULL REFERENCES currencies(code),
  amount_base NUMERIC(20,4),
  base_currency CHAR(3),
  exchange_rate_snapshot_id UUID REFERENCES exchange_rate_snapshots(id),
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK ( (debit = 0) <> (credit = 0) )
) PARTITION BY RANGE (occurred_at);
CREATE INDEX ix_rrl_txn ON revenue_recognition_ledger (txn_id);

CREATE TABLE deferred_revenue_schedule (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  subscription_id UUID NOT NULL REFERENCES subscriptions(id),
  invoice_id UUID NOT NULL REFERENCES invoices(id),
  period_starts_at DATE NOT NULL,
  period_ends_at DATE NOT NULL,
  amount NUMERIC(20,4) NOT NULL,
  currency CHAR(3) NOT NULL REFERENCES currencies(code),
  recognized BOOLEAN NOT NULL DEFAULT FALSE,
  recognized_at TIMESTAMPTZ,
  recognition_txn_id UUID
);

CREATE TABLE revenue_snapshots (
  id BIGSERIAL PRIMARY KEY,
  tenant_id UUID NOT NULL,
  snapshot_date DATE NOT NULL,
  mrr NUMERIC(20,4) NOT NULL,
  arr NUMERIC(20,4) NOT NULL,
  new_mrr NUMERIC(20,4) NOT NULL,
  expansion_mrr NUMERIC(20,4) NOT NULL,
  contraction_mrr NUMERIC(20,4) NOT NULL,
  churned_mrr NUMERIC(20,4) NOT NULL,
  active_subscriptions INT NOT NULL,
  paying_customers INT NOT NULL,
  arpu NUMERIC(20,4),
  ltv_estimate NUMERIC(20,4),
  base_currency CHAR(3) NOT NULL,
  UNIQUE (tenant_id, snapshot_date)
);

CREATE TABLE cac_attributions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  user_id UUID NOT NULL,
  channel TEXT NOT NULL,
  campaign TEXT,
  attributed_cost NUMERIC(20,4) NOT NULL,
  currency CHAR(3) NOT NULL REFERENCES currencies(code),
  attributed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE cohort_metrics (
  id BIGSERIAL PRIMARY KEY,
  tenant_id UUID NOT NULL,
  cohort_month DATE NOT NULL,
  age_months INT NOT NULL,
  retained_customers INT NOT NULL,
  revenue NUMERIC(20,4) NOT NULL,
  currency CHAR(3) NOT NULL,
  UNIQUE (tenant_id, cohort_month, age_months)
);
```

---

## 4. Multi-Tenancy Strategy

**Decision: row-level multi-tenancy with PostgreSQL Row-Level Security (RLS), single logical database.**

### 4.1 Why row-level, not schema-per-tenant

| Concern | Schema-per-tenant | Row-level (chosen) |
|---|---|---|
| New tenant provisioning time | Run all migrations on new schema (minutes) | One `INSERT INTO tenants` (ms) |
| Cross-tenant analytics (root admin sees MRR across all whitelabels) | Hard — must UNION 100+ schemas | Trivial — single query with no `tenant_id` filter via root role |
| Schema migration cost | O(tenants × tables) | O(tables) |
| Connection pool fragmentation | Severe (search_path per session) | None |
| Maximum tenants | ~hundreds | ~hundreds of thousands |
| Hot tenant noisy-neighbour | Mitigated by separate schema | Must mitigate via DB-level rate limiting per tenant |
| Data isolation guarantee | Strong (separate schema) | Strong **iff** RLS is enforced + tests prove no leak |

White-label viability requires onboarding a brand in **5 minutes** (Q50). Schema-per-tenant cannot achieve this. Reseller hierarchies (Q19 — agencies that resell SilkLens) require easy cross-tenant rollups for revenue share. Row-level wins.

### 4.2 Connection contract

Every connection sets a session-scoped GUC before any query:

```sql
SET LOCAL app.current_tenant = '<uuid>';
SET LOCAL app.current_actor  = '<user_uuid_or_service>';
SET LOCAL app.current_role_set = '{owner,billing}';
```

Application code uses one of two DB roles:

- `silklens_app` — application role, RLS enforced. **Cannot bypass.**
- `silklens_admin` — root admin / analytics role. Can `SET app.bypass_tenant = true` (logged, alerted). Used only by central admin tooling and nightly rollups.

### 4.3 RLS policy template

For every table with `tenant_id`:

```sql
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_select ON subscriptions
  FOR SELECT TO silklens_app
  USING (tenant_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY tenant_isolation_modify ON subscriptions
  FOR ALL TO silklens_app
  USING (tenant_id = current_setting('app.current_tenant')::uuid)
  WITH CHECK (tenant_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY admin_bypass ON subscriptions
  FOR ALL TO silklens_admin
  USING (
    current_setting('app.bypass_tenant', true) = 'true'
    OR tenant_id = current_setting('app.current_tenant')::uuid
  );
```

A migration test gate **fails CI if any table with a `tenant_id` column lacks an RLS policy.**

### 4.4 Reseller hierarchies

`tenants.parent_tenant_id` defines a tree. A reseller can be granted scoped visibility via `app.tenant_scope = '<parent_uuid>'` and a relaxed policy:

```sql
CREATE POLICY reseller_subtree ON subscriptions
  FOR SELECT TO silklens_app
  USING (
    tenant_id IN (
      SELECT id FROM tenants
      WHERE id = current_setting('app.current_tenant')::uuid
         OR parent_tenant_id = current_setting('app.current_tenant')::uuid
    )
  );
```

### 4.5 Cross-tenant prohibitions

Foreign keys never span tenants. Every cross-tenant query is mediated by the central revenue-share job which runs as `silklens_admin` with `bypass_tenant=true`, posts entries into the *target* tenant's ledger, then `RESET app.bypass_tenant`.

---

## 5. Entitlement Lookup (<5 ms p99)

### 5.1 The problem

Every UI render and every API request must answer: *"does user U on tenant T currently have feature F?"* — at multi-thousand QPS. A SQL JOIN through `subscriptions → plan_features → feature_flags` is correct but ~10–30 ms. We need <5 ms.

### 5.2 Three-tier resolution

**Tier 1 — Redis hot cache (target <1 ms):**

```
KEY:   ent:{tenant_id}:{user_id}
TYPE:  HASH
FIELD: feature_key
VALUE: json {"v": <value>, "exp": <epoch>, "src": "<subscription_id|trial|coupon>"}
TTL:   300 seconds (sliding) — but also explicitly invalidated on subscription_events
```

Plus a tenant-level fallback for free-tier defaults:

```
KEY:   ent:default:{tenant_id}
TYPE:  HASH
```

**Tier 2 — Materialised view (target <5 ms cache miss):**

```sql
CREATE MATERIALIZED VIEW user_entitlements_mv AS
SELECT
  s.tenant_id,
  s.user_id,
  ff.key AS feature_key,
  pf.value AS value,
  s.id AS subscription_id,
  s.current_period_end AS expires_at
FROM subscriptions s
JOIN plan_features pf ON pf.plan_id = s.plan_id AND pf.tenant_id = s.tenant_id
JOIN feature_flags ff ON ff.id = pf.feature_flag_id
WHERE s.state IN ('active','trialing','grace')
UNION ALL
SELECT
  t.tenant_id, t.user_id, ff.key, pf.value, NULL, t.ends_at
FROM trials t
JOIN product_plans pp ON pp.id = t.plan_id
JOIN plan_features pf ON pf.plan_id = pp.id AND pf.tenant_id = t.tenant_id
JOIN feature_flags ff ON ff.id = pf.feature_flag_id
WHERE t.ends_at > now() AND NOT t.consumed;

CREATE UNIQUE INDEX ux_uemv ON user_entitlements_mv (tenant_id, user_id, feature_key);
```

Refreshed `CONCURRENTLY` every minute, plus event-driven refresh of a single user via the `entitlements` table.

**Tier 3 — Authoritative SQL (correctness check / cold start):**

Resolves through the live tables. Used on cache miss only.

### 5.3 Invalidation flow

Any insert into `subscription_events` (`activated`, `canceled`, `upgraded`, `downgraded`, `past_due`, `reactivated`) emits a NOTIFY:

```sql
NOTIFY entitlement_changed, '{"tenant":"...","user":"..."}';
```

A small Go listener consumes NOTIFY, deletes `ent:{tenant}:{user}` from Redis, and enqueues a background refresh job that recomputes and re-warms.

### 5.4 API contract

```python
async def is_entitled(tenant_id: UUID, user_id: UUID, feature_key: str) -> Entitlement:
    cached = await redis.hget(f"ent:{tenant_id}:{user_id}", feature_key)
    if cached and cached["exp"] > now():
        return Entitlement.from_json(cached)
    # cache miss path — read MV, warm cache, return
```

### 5.5 Hard-quota check (separate path)

Quotas (audio/month, AR sessions/day) are not `is_entitled` calls. They use Redis `INCRBY` against a sliding window key:

```
KEY:   quota:{tenant}:{user}:{feature}:{window_start}
INCR:  per request
LIMIT: from plan_features.value.limit
```

Atomic and persisted nightly into `quota_usage`.

---

## 6. Subscription State Machine

### 6.1 States

| State | Meaning | Entitlement |
|---|---|---|
| `incomplete` | Created but first payment not confirmed | None |
| `trialing` | Inside trial window, no card or card not yet charged | Full plan |
| `active` | Paid, current | Full plan |
| `past_due` | Renewal failed, dunning in progress | Full plan during grace, then degraded |
| `grace` | After dunning exhausted but grace days remain | Free tier only |
| `canceled` | User canceled at period end (or admin canceled) | Full until `current_period_end`, then expired |
| `expired` | Period ended without renewal | None |
| `paused` | Admin/user paused (e.g. military leave) | None, but kept |

### 6.2 Transitions

```
                ┌──────────────┐
       create   │ incomplete   │
   ───────────▶ │              │
                └──────┬───────┘
                       │ first_payment_succeeded
                       ▼
        ┌────────────────────────────┐
        │           trialing         │  (if trial_days > 0)
        └──────────────┬─────────────┘
                       │ trial_end OR pay_now
                       ▼
                ┌──────────────┐
   reactivate   │   active     │ ◀──── renew_succeeded ────┐
   ─────────────▶              │                            │
                └──┬───────┬───┘                            │
        cancel_at_period_end  │ renewal_failed              │
                    │         ▼                             │
                    │   ┌──────────┐  retry_succeeded       │
                    │   │ past_due │────────────────────────┘
                    │   └────┬─────┘
                    │        │ dunning_exhausted
                    │        ▼
                    │   ┌──────────┐  pay_now / new_card
                    │   │  grace   │──────────────────────▶ active
                    │   └────┬─────┘
                    │        │ grace_expired
                    ▼        ▼
                ┌──────────────┐         ┌──────────┐
                │  canceled    │────────▶│ expired  │
                └──────────────┘ p_end   └──────────┘
                       ▲
                       │ user_pauses
                       │
                ┌──────────────┐
                │   paused     │
                └──────────────┘
```

Every transition writes to `subscription_events` (append-only) and fires `entitlement_changed` NOTIFY.

### 6.3 Configurable timings

Per-tenant per-plan in `dunning_state.step` table + `grace_periods`:

| Step | Default |
|---|---|
| t0 | Charge attempted |
| t+1d | Retry #1 + email |
| t+3d | Retry #2 + push |
| t+7d | Retry #3 + final notice |
| t+14d | Cancel + start grace |
| grace_days | 7 |

All admin-editable.

### 6.4 Mid-cycle plan changes

Upgrade: prorate immediately, charge difference now, period continues.
Downgrade: schedule at `current_period_end`. Entitlement reduces then.
Stored in `proration_calculations`.

---

## 7. Webhook Idempotency

### 7.1 Contract

Every provider POSTs to `/webhooks/{provider}`. The endpoint:

1. **Verify signature** using `tenant_payment_provider_config.webhook_secret_ref`.
2. **Insert raw event** into `payment_webhook_events` with `(provider_id, provider_event_id)` UNIQUE — duplicates 200-OK immediately with no processing.
3. **Enqueue a background job** (Celery) keyed by event ID. Returns 200 within 50 ms.
4. Background worker advances `processed_state`: `pending` → `processing` → (`succeeded` | `failed`).
5. **Retries:** failures left at `failed`, retried with exponential backoff up to 10 attempts. Each attempt increments `attempts` and records `last_error`.
6. **Out-of-order handling:** every event carries provider timestamp; processor checks the current state of the affected resource and skips if a later event already advanced it.

### 7.2 Stripe-specific

Stripe re-sends events for up to 3 days. Our DB UNIQUE constraint dedupes. `Stripe-Signature` header verified with `webhook_secret_ref` per tenant.

### 7.3 Apple/Google IAP

Apple sends App Store Server Notifications v2 (signed JWT). Google sends Pub/Sub messages. Both routed through `payment_webhook_events` with `provider='apple'|'google'`. `provider_event_id` is the notification UUID (Apple) or `message.messageId` (Google).

Receipts validated on `DID_RENEW` / `SUBSCRIPTION_RENEWED` against Apple's `verifyReceipt`/`/subscriptions/{id}` and Google's Play Developer API. Cached in `iap_receipt_validations`.

### 7.4 Local provider quirks

- **Payme** uses JSON-RPC with method names `CheckPerformTransaction`, `CreateTransaction`, `PerformTransaction`, `CancelTransaction`. Each `transaction_id` is `provider_event_id`. Idempotency via `(provider_id='payme', provider_event_id=transaction_id)`.
- **Click** uses prepare/complete two-step with `click_trans_id`. Same UNIQUE pattern.

---

## 8. Multi-Currency & Dynamic Pricing

### 8.1 Resolution order at checkout

```
inputs: user.country_code, plan_id, tenant_id, now()
1. zone = pricing_zone_countries[country_code] OR tenant.default_pricing_zone_id
2. row = prices WHERE plan_id=? AND pricing_zone_id=? AND currency=user.preferred_currency
         AND effective_from <= now() < COALESCE(effective_to, infinity)
         AND (experiment_id IS NULL OR user_in_experiment_bucket)
3. amount = row.amount
4. for each m in seasonal_modifiers WHERE pricing_zone_id IN (?, NULL)
     AND now() <@ m.date_window:
   amount = amount * (1 + m.percent_adjust/100)
5. apply coupons / referral credits at invoice line level
6. snapshot exchange rate, persist in exchange_rate_snapshots, link from payment_intent
```

### 8.2 Snapshot, never recompute

When user pays in UZS but tenant reports MRR in USD, the rate is captured at charge time:

```sql
INSERT INTO exchange_rate_snapshots(base, quote, rate, source, payment_intent_id)
VALUES ('UZS','USD', 0.0000814, 'openexchangerates', :pi_id);
```

Subsequent reporting **never** re-derives the rate. This is the only way MRR is reproducible.

### 8.3 PPP zones (illustrative defaults)

| Zone | Countries | PPP index | Default plan price (USD-equiv) |
|---|---|---|---|
| CIS | UZ, KZ, KG, TJ, TM | 0.30 | $0.99 |
| MENA | EG, MA, TN | 0.45 | $1.99 |
| SEA | TH, VN, ID, PH | 0.50 | $1.99 |
| LATAM | MX, BR, CO, AR | 0.60 | $2.99 |
| EU | DE, FR, ES, IT, PL | 1.00 | $4.99 |
| NA | US, CA | 1.10 | $4.99 |
| UK | GB | 1.05 | £3.99 |
| CN | CN | 0.70 | ¥15 |
| IN | IN | 0.35 | ₹99 |

All editable in admin. Country→zone mapping editable. Adding a new zone is one row.

### 8.4 Seasonal modifier example

```sql
INSERT INTO seasonal_modifiers(tenant_id, name, pricing_zone_id, date_window, percent_adjust)
VALUES (:slm, 'off_season_cis_2026', :zone_cis,
        '[2026-11-01,2027-03-01)', -50.0);
```

Stacks multiplicatively only if `policy.stack_allowed`; otherwise the strongest modifier wins (configurable).

---

## 9. B2B Featured Listing Auction

### 9.1 Auction model

**First-price sealed-bid, single-round, per `(heritage_id, slot_position, category_id, billing_period)`** (Q19).

Why first-price not second-price? Because:
- Easier for B2B advertisers to understand ("I bid X, I pay X if I win").
- Mitigates ring/coordination by sealed-bid.
- Avoids 2nd-price gaming where bidders pad bids.

Slot positions 1–5 per heritage. Position 1 commands the highest auto-rotated visibility; positions 2–5 rotate.

### 9.2 Lifecycle

```
1. Admin opens period N+1 → b2b_billing_periods row created, status='bidding'.
2. Auctions auto-generated for every (eligible heritage_id × slot × category).
   Minimum bid derived from heritage popularity (views last 30d) + category base.
3. Sealed bids accepted until bidding_closes_at (typically 5d before period start).
4. At close: settlement job runs.
   For each auction:
     winners = bids ORDER BY amount DESC LIMIT 1 (slot_position=1), etc.
     Tiebreak: earlier submitted_at wins.
   Create b2b_listing_assignments. Mark losing bids 'lost'.
5. Generate b2b_listing_invoices (flat). Stripe charges (or invoice if NET-30 enterprise).
6. During period: CPC overage accumulates from b2b_listing_clicks.
7. At period end: append CPC overage to next month's invoice.
```

### 9.3 Anti-fraud

- **Same B2B cannot bid against itself:** UNIQUE `(auction_id, b2b_account_id)`. Multi-account abuse caught by IP + KYC + payout-method fingerprinting → `fraud_score`.
- **Bid ceiling:** soft cap = 5× minimum bid; bids above flagged for review.
- **Click fraud:** `is_billable` set false if same `device_id` within 60s, IP velocity exceeds threshold, or user-agent flagged. CPC only bills `is_billable=true`.
- **Refund-then-rebid attack:** refunding within a period invalidates the assignment; next-highest bidder is promoted only if they accept within 48h.
- **Bid sniping:** sealed-bid removes sniping by definition; if open-bid ever introduced, last-minute bids extend close by 2 min (soft close).

### 9.4 CPC pricing

CPC rate is in `b2b_listing_assignments.cpc_rate` and is *separate* from flat bid. Default rate per category, overridden per assignment. Daily aggregation:

```sql
INSERT INTO payout_ledger (owner, source, ...) -- nothing (this is owed TO us)
-- but at month end:
INSERT INTO b2b_listing_invoices(flat_total, cpc_billable_clicks, cpc_total) ...
```

---

## 10. Enterprise API Keys

### 10.1 Key shape

```
sl_live_<env>_<base32_22chars>     # raw shown once
└── prefix: sl_live_env_aaaaaa     # stored, visible in UI
└── hash: HMAC-SHA256(server_secret, raw)  # stored in api_keys.key_hash
```

Lookup uses `key_hash`, not the raw key. Constant-time compare. Raw key never logged.

### 10.2 Scopes

Hierarchical dotted scopes, e.g.:

| Scope | Allows |
|---|---|
| `heritage.read` | Read heritage metadata |
| `heritage.write` | Create/update (enterprise only) |
| `vision.classify` | POST a photo, get an obida match |
| `tts.generate` | Synthesize audio |
| `chat.complete` | LLM chat about an object |
| `route.plan` | AI itinerary planner |
| `b2b.read` | Read B2B listings |
| `b2b.write` | Manage own listings |
| `analytics.read` | Read aggregated analytics |
| `admin.*` | Tenant-scoped admin (rare) |

Scope check is `O(1)` set membership at the gateway, before any heavy work.

### 10.3 Rate limits

Per `rate_limit_class`:

| Class | RPS | Burst | Daily |
|---|---|---|---|
| `free` | 1 | 5 | 1,000 |
| `standard` | 10 | 50 | 100,000 |
| `pro` | 50 | 200 | 1,000,000 |
| `enterprise` | per-contract | per-contract | per-contract |

Enforced by Redis token-bucket per `api_key_id`. Headers returned: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`.

### 10.4 Quotas (monthly units)

Independent of rate limits. Set in `quotas`, tracked in `quota_usage` (also Redis). Soft quota → 200 with `X-Quota-Exceeded: soft`; hard quota → 429.

### 10.5 Rotation

`POST /v1/api-keys/{id}/rotate` issues a new key, links via `rotated_from`. Old key remains valid for 7 days (configurable) → smooth migration. `api_key_rotations` records the act.

### 10.6 IP allowlist

`api_keys.ip_allowlist CIDR[]`. Empty = allow all. Non-empty = strict allow. Gateway checks before scope check. Logged on deny.

---

## 11. White-Label / Reseller

### 11.1 Tenant propagation rules

- **Every** domain row carries `tenant_id` (already in §3).
- **Cross-tenant FKs are illegal.** A `subscription` cannot reference a `user` in a different tenant. If a user wants to use multiple white-label brands, they have one row per tenant in Agent 2's `users` keyed by a global `identity_id`.
- **Cache keys are tenant-prefixed:** `ent:{tenant_id}:...`, `quota:{tenant_id}:...`.
- **Webhook routing:** each provider configured per tenant. Inbound webhook URL is `/webhooks/{provider}/{tenant_slug}`. The handler sets `app.current_tenant` from path.
- **Storage paths** (MinIO): `/{tenant_id}/{kind}/{id}.{ext}`.
- **Search index** (Elasticsearch): index per tenant (`heritage_{tenant_slug}`) since RLS doesn't apply there.

### 11.2 Reseller economics

A reseller is a `tenant` with `parent_tenant_id` and a row in `tenant_revenue_share`:

```
tenant 'visit-tashkent', parent='silklens', share=70.0000 (% to reseller, % to platform = 30)
```

On every settled payment under tenant `visit-tashkent`:

1. Net (after processor fees and refunds reserve) calculated.
2. Reseller share posted to `payout_ledger(owner=visit-tashkent_account, source='revenue_share')` as `accrued`.
3. Monthly payout batch promotes accrued → paid.
4. Double-entry: debit revenue, credit reseller-payable.

### 11.3 Tenant suspension

Admin sets `tenants.status='suspended'`. RLS-aware middleware blocks all writes (`is_active_tenant()` check), but reads still work for export. Payouts paused. Subscriptions retained — they resume on un-suspend.

### 11.4 Tenant migration (rare)

To move a user/data from one tenant to another (e.g. visit-tashkent acquired by another reseller), a `migrations` operational tool:
- Runs as `silklens_admin` with `bypass_tenant=true`.
- Updates `tenant_id` on every related row inside one transaction.
- Re-issues entitlement cache.
- Logs every row touched into an audit table.

---

## 12. Affiliate Revenue Share

### 12.1 Attribution

Click → conversion attribution is **last-click within window**:

1. User taps an affiliate link → row in `affiliate_clicks`. Set cookie/local `aff_link_id` with TTL = `affiliate_offers.attribution_window_hours`.
2. Partner postback fires when user converts (Booking.com sends after stay date).
3. Postback handler:
   - Verifies HMAC signature (`postback_secret_ref`).
   - Inserts `affiliate_conversions` (UNIQUE on `(partner_id, partner_conversion_ref)` → idempotent).
   - Looks up last click within window for that user/device.
   - If found, sets `link_id`, computes commission per `affiliate_offers`, inserts `affiliate_commissions` with status `pending`.
4. Partner subsequently confirms or claws back (e.g. user canceled booking). Status moves `pending → confirmed | clawed_back`.

### 12.2 Anti-fraud

- **Click flooding:** dedup per `(link_id, device_id, 60s)`.
- **Self-referral:** a user's own clicks → their own conversions excluded.
- **Postback signature mandatory.** Unsigned postbacks rejected.
- **Clawback window:** 90 days. Confirmed commissions still movable to `clawed_back`; if already paid out, recorded as a `payout` reversal.

### 12.3 Creator share

If a click came from a `affiliate_links.created_by_user_id` (UGC creator), `affiliate_commissions.recipient_user_id` is set and a portion is credited to that user via `payout_ledger`. This is the influencer monetization path.

---

## 13. Tax & Compliance

### 13.1 Rule templates

| Template | Where | Behaviour |
|---|---|---|
| `eu_oss` | EU member states | Charge customer's country VAT for B2C; reverse-charge for valid VAT-ID B2B; remit via OSS quarterly. |
| `uk_vat` | UK | Standard UK VAT 20% B2C; reverse-charge B2B; HMRC quarterly. |
| `us_sales_tax` | US | Nexus-based; lookup table per state; Stripe Tax recommended for now. |
| `uz_vat` | UZ | 12% VAT on digital services; tax-included pricing. |
| `generic` | Default | No tax added, displayed prices are gross. |
| `exempt` | Diplomatic / NGO | Zero-rate with certificate. |

### 13.2 Calculation flow

```
1. Customer's billing country resolved (from card BIN, IP, declared address — Stripe Tax style).
2. Look up tax_jurisdiction.
3. For each invoice line:
     - product_class derived from product type (digital_service / shipping / physical)
     - find tax_rates row effective on invoice date
     - apply rate
     - check VAT-ID for reverse-charge override
4. tax_calculations row stored; invoice_lines.tax_amount set.
```

### 13.3 VAT-ID validation

`vat_validations` cache. VIES (EU) lookup once per quarter or on input; cache 90 days. If valid + B2B context → `reverse_charge=true`, tax 0, line includes "Reverse charge applies".

### 13.4 Compliance artefacts

- Invoice number sequence per tenant, gap-free, mandated by many jurisdictions.
- Original invoice PDFs stored immutably in MinIO with content hash in `receipts`.
- Audit log (`subscription_events`, `revenue_recognition_ledger`, `payment_webhook_events`) is the source of truth for regulators.

---

## 14. Double-Entry Accounting

### 14.1 Chart of accounts (per tenant)

| Code | Type | Name |
|---|---|---|
| 1100 | asset | Accounts Receivable |
| 1200 | asset | Cash (per provider) |
| 2050 | liability | Deferred Revenue |
| 2100 | liability | Tax Payable |
| 2200 | liability | Reseller Payable |
| 2300 | liability | Refund Reserve |
| 4000 | revenue | Subscription Revenue |
| 4100 | revenue | B2B Listing Revenue |
| 4200 | revenue | API Revenue |
| 4300 | revenue | Marketplace Revenue |
| 4400 | revenue | Affiliate Revenue |
| 4500 | revenue | Tip Revenue |
| 4900 | contra_revenue | Refunds |
| 5200 | expense | Processor Fees |

### 14.2 Booking templates

**Annual subscription paid up front ($120, EU VAT 20%):**
- DR 1200 Cash $144
- CR 4900 (none)
- CR 2100 Tax Payable $24
- CR 2050 Deferred Revenue $120

Each month: DR 2050 Deferred Revenue $10, CR 4000 Subscription Revenue $10 (handled by `deferred_revenue_schedule` job).

**Refund of $30 mid-year (50% used, 50% credited):**
- DR 4900 Refunds $30
- CR 1200 Cash $30
- And reverse remaining deferred recognition.

**B2B featured slot $500 + 12% VAT, paid by hotel:**
- DR 1200 Cash $560
- CR 2100 Tax Payable $60
- CR 4100 B2B Revenue $500

**Reseller share 70% on $100 sub:**
- DR 4000 Revenue (split is reported separately)
- CR 2200 Reseller Payable $70
- Later: DR 2200 Reseller Payable $70, CR 1200 Cash $70 (payout)

### 14.3 Snapshots

Nightly job derives `revenue_snapshots` from the ledger:

- **MRR** = sum of monthly-normalised active subscription prices (annual ÷ 12).
- **ARR** = MRR × 12.
- **Net new MRR** = new + expansion − contraction − churn.
- **Churn $** from canceled subs that didn't reactivate.
- **LTV** = ARPU ÷ monthly churn rate (rolling 3-month).
- **CAC** from `cac_attributions`.

All currency rolled up to `tenant.default_currency` using `exchange_rate_snapshots` (the snapshot at time of each charge, not today's rate).

---

## 15. Risks & Open Questions

### 15.1 Risks

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| R1 | **Apple/Google IAP fee (15-30%) plus required IAP for digital subscriptions on mobile.** A user who buys via Stripe on web cannot legally have their subscription "ported" to be billed via Apple later — and Apple doesn't surface server-side billing changes the same way. Subscription portability across providers is partial at best. | High | Treat each IAP-purchased sub as its own `subscriptions` row tied to `provider='apple'` and `payment_method.type='iap_apple'`. Never co-mingle. Offer "manage subscription on Apple" link in app. Document the asymmetry to users. |
| R2 | **IAP receipt validation race conditions.** App Store Server Notifications can arrive *after* the client's `verifyReceipt` call. Two paths racing to upsert `iap_receipts.original_transaction_id`. | High | UNIQUE `(provider, original_transaction_id)` + advisory lock on that ID during upsert. Notification handler is idempotent. |
| R3 | **B2B auction fraud via shell accounts.** A hotel chain creates 5 accounts and bids against itself to inflate price for competitors. | Medium | KYC + tax-ID dedup + payout-method fingerprint + IP/device clustering → `fraud_score`. Manual review on `fraud_score > 0.7`. UNIQUE on `(auction_id, b2b_account_id)` is necessary but not sufficient. |
| R4 | **Webhook out-of-order processing.** Stripe can send `invoice.paid` before `customer.subscription.updated`. Naive handler creates inconsistent state. | High | Each handler is reentrant and reconciles state from authoritative provider object (re-fetches `sub_xxx` from Stripe on every event), not from the event payload alone. |
| R5 | **Exchange rate drift between charge and refund.** User paid 1,200,000 UZS = $97.68 at then-rate; refunds 6 months later when UZS is weaker → $90 in cash. Reporting mismatch. | Medium | Always refund in original currency, original amount (Stripe behaviour). Ledger uses the *original* snapshot's USD-equiv to keep accounting consistent. |
| R6 | **PPP tier gaming via VPN.** EU users connect via UZ VPN to get $0.99 instead of $4.99. | Medium | Resolve country from `payment_method.country` (card BIN) **not** IP. IAP uses store country (Apple/Google enforce). Web checkout uses billing-address country. |
| R7 | **Tenant data leakage via missed RLS policy.** A developer creates a new table forgetting RLS. | Critical | CI gate: a migration test that enumerates `pg_class` and fails if any table containing `tenant_id` lacks an `ENABLE ROW LEVEL SECURITY` setting. |
| R8 | **PCI scope creep.** Storing raw card data anywhere makes us PCI-DSS level-1. | Critical | We **never** store raw cards. Only tokens (`payment_methods.provider_token_ref`). Stripe Elements / Apple Pay tokenize before our server sees anything. |
| R9 | **Dunning loop hammering declined card.** Repeated charge attempts to a hard-declined card cause issuer-side flags. | Medium | After 2 hard declines, suspend retries until user manually updates the card. Distinguish soft (insufficient funds) vs hard (lost/stolen) declines from issuer response codes. |
| R10 | **Local provider downtime (Payme/Click).** Uzbekistan customers locked out. | Medium | Multi-provider per tenant; UI presents alternative providers when one is degraded. Provider health stored in `payment_providers.status`. |
| R11 | **Revenue-recognition correctness under partial refunds + plan changes + currency drift.** Edge cases multiply. | High | Property-based tests on ledger: for any sequence of events, sum(debits)=sum(credits), sum(recognized)+sum(deferred)+sum(refund_reserve) = sum(cash_in) − sum(cash_out). |
| R12 | **GDPR right-to-be-forgotten conflicts with financial-record retention** (7+ years required). | Medium | PII pseudonymisation: replace user PII fields with hash on RTBF, retain financial transaction rows linked by the hash. Documented in privacy policy. |
| R13 | **Marketplace tax complexity for physical souvenirs shipping internationally** (customs, VAT-on-import, OSS IOSS). | Medium | Initial launch: ship within UZ only. Add IOSS later with an external tax engine (TaxJar / Stripe Tax). |
| R14 | **Affiliate clawbacks landing after payout.** We already paid the influencer; partner claws back. | Medium | 60-day reserve withholding: only pay out commissions older than 60 days. Faster payout only for established partners. |
| R15 | **Cross-tenant query in MRR rollup accidentally exposes one tenant's revenue to another's admin.** | Critical | Rollups run as `silklens_admin` with `bypass_tenant=true` and write to per-tenant snapshot rows. Reseller admin can only read snapshots where `tenant_id IN subtree(parent)`. |

### 15.2 Open Questions for Founder

1. **Default revenue-share with resellers?** Suggest 70/30 (reseller/platform) for tier-1, 60/40 for sub-resellers. Confirm or override.
2. **Trial length per region?** Suggest 7d in CIS, 14d in EU/NA. Admin-editable but need a launch default.
3. **B2B auction cadence — monthly or quarterly?** Monthly higher liquidity, quarterly less load on hotels. Recommend monthly.
4. **Crypto payments?** USDT/USDC requested by some CIS users. Out of scope for v1; add `payment_provider='circle'` later.
5. **Apple/Google IAP price-tier mapping.** Their fixed price tiers don't perfectly hit our PPP targets. Pick closest tier and absorb difference? Or set tier to round figure?
6. **Tip-jar to whom?** UGC content creators only, or also local guides registered via B2B onboarding? Likely both; need policy.
7. **Souvenir marketplace launch country?** Recommend UZ-only at launch (simpler tax/shipping).
8. **B2C → B2G special tariffs?** Government tier with negotiated pricing — modelled as `enterprise_contracts` with `tier='government'`. Confirm.

---

## 16. Cross-Agent Dependencies

| Need | From Agent | Field / Concept |
|---|---|---|
| `user_id` for every subscription, entitlement, IAP receipt | Agent 2 (Identity) | `users.id`, plus `tenant_id` link |
| `heritage_id` for B2B listings, slot auctions, affiliate context, marketplace items | Agent 1 (Heritage/Content) | `heritage_objects.id` |
| `ai_cost_units` for enterprise API metering (passthrough cost) | Agent 3 (AI) | `ai_cost_ledger` per inference call |
| Push/email/in-app delivery for dunning, trial-ending, invoice-paid, payout-paid notifications | Agent 7 (Notifications) | notification templates, delivery API |
| Analytics events (`paywall_view`, `checkout_start`, `subscribe_success`) | Agent 4 / Agent 8 (Analytics) | event taxonomy, funnel ingestion |
| Audit logging of admin price/plan changes | Agent 5 (Admin/Audit) | central audit log table |
| Heritage popularity (views/30d) feeding auction minimum bids | Agent 1 / Agent 4 | aggregated metric |

---

*Document version: 1.0 | Author: Agent 6 — Monetization & Enterprise Architect | Date: 2026-05-18*
