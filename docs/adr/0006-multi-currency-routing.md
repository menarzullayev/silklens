# ADR 0006 — Multi-Currency Payment-Provider Routing

> Status: **Accepted** · 2026-05-18 · Extends [ADR-0005](0005-provider-switching.md).

## Context

FAZA 5 unlocks paid plans for three audience tiers that don't all live inside
Stripe's coverage map:

* **Uzbek users (UZS)** — Stripe doesn't process UZS. Local rails are
  **Payme** (paycom.uz, JSON-RPC + Basic-Auth webhooks, amounts in tiyin) and
  **Click** (click.uz, form-encoded callbacks + MD5/HMAC-SHA1 signatures).
* **EU / US users (EUR / USD)** — Stripe.
* **Everyone else (CNY / RUB / SGD / …)** — **PayPal** as the catch-all so we
  don't have to add a new provider per minor currency.

ADR-0005 chose one provider per deployment (settings-driven, soft-falling-back
to the mock). That model breaks the moment we want UZS users on Payme and USD
users on Stripe **in the same deployment**.

## Decision

We adopt **per-currency provider routing** with the following layered
resolution:

```
1. user.preferred_currency  (or plan.currency if user is silent)
2. system_settings.billing.provider_by_currency.<CCY>           ← admin override
3. system_settings.billing.provider_by_currency.default         ← admin override
4. factory.DEFAULT_PROVIDER_BY_CURRENCY[CCY]                    ← code default
5. SILKLENS_PAYMENT_PROVIDER (build-time env)                   ← deployment default
6. MockPaymentProvider                                          ← always-safe terminal
```

Steps 2-3 are loaded at request time from `system_settings` (cheap, single
SELECT) so admins can flip routing for a single tenant without redeploying.
Step 4 is the code-side compile-time table:

```python
DEFAULT_PROVIDER_BY_CURRENCY = {
    "UZS": "payme",
    "USD": "stripe",
    "EUR": "stripe",
    "GBP": "stripe",
    "RUB": "stripe",
}
```

A **single shared factory** (`build_payment_provider_for_currency`) materialises
the correct provider. Each provider self-reports unavailability through
`ProviderUnavailable` at call-time so the factory only needs to confirm
**some** concrete `PaymentProvider` comes back — a partially configured
deployment (e.g. PayPal client_id set but PayPal webhook_id not yet seeded)
degrades to `MockPaymentProvider` with a structured warning rather than
crashing a request.

## Webhook verification per provider

| Provider | Verification mechanism                                                           |
| -------- | -------------------------------------------------------------------------------- |
| Stripe   | `Stripe-Signature` HMAC-SHA256 via SDK (`stripe.Webhook.construct_event`)        |
| Payme    | `Authorization: Basic base64(merchant_id:secret)` + JSON-RPC method whitelist    |
| Click    | Form-encoded body, MD5 over `click_trans_id+service_id+secret_key+…`             |
| PayPal   | 5 `PayPal-*` headers + `/v1/notifications/verify-webhook-signature` (SDK)        |

All four converge into the same `payment_webhook_events` table with the
existing `UNIQUE(provider, provider_event_id)` index doing idempotency. A
replay returns `{"received": true, "duplicate": true}` regardless of provider.

## Sandbox-shape for Payme / Click

Real Payme + Click integration requires merchant accounts that take weeks to
provision. We ship the adapters with **production-faithful wire envelopes**
(Basic-Auth verification, MD5 sign-string verification, tiyin conversion,
JSON-RPC method routing) but route the actual confirmation through a private
`MockPaymentProvider` underneath until `PAYME_MERCHANT_ID` /
`CLICK_SERVICE_ID` are populated. This matches the Stripe pattern from
ADR-0005 and lets us:

* Run the entire `start_subscription` flow in CI with no live keys.
* Exercise the webhook router's signature paths in unit tests.
* Drop in real charge-creation calls as a single-method change per provider
  once the merchant account is live.

## Trade-offs

**Pro — local-currency UX wins LTV.** Uzbek users are 4-6× more likely to
convert on Payme/Click than a Stripe USD prompt with implicit FX. Same
intuition for PayPal in CN/RU/IN.

**Pro — admin agility.** Routing flips per tenant via `system_settings`
without a deploy; useful when a payment rail goes down (e.g. Payme outage →
switch UZS to Click in 10 seconds).

**Con — cross-currency settlement risk.** A user who pays in UZS via Payme
and the underlying plan is priced in USD will accumulate FX drift. We mitigate
this in two ways:

1. Plans have per-currency price rows (`prices.currency`). The factory picks
   the provider for **the price's currency**, never the plan's nominal
   currency. There's no implicit conversion at the gateway boundary.
2. Reconciliation happens in the warehouse (BigQuery / DuckDB), not at
   request time. The platform booking currency stays USD; the gateway
   transaction stays in its native currency. Accounting reconciles via
   daily FX snapshots.

**Con — webhook complexity multiplies.** Each provider's verification path
is a new attack surface. We mitigate with:

* Explicit allow-list of provider slugs (`_VALID_WEBHOOK_PROVIDERS` in the
  router) — anything else returns 404 before any verification logic runs.
* Provider-specific signature classes (`InvalidWebhookSignature` →
  uniform 401) — the router never inspects raw bytes after dispatch.
* Idempotency lives at the DB layer, not the verification layer — a verified
  replay still returns `{"duplicate": true}`.

**Con — testing surface area.** Each provider needs its own protocol +
verification unit tests. Tracked in `test_multi_currency_providers.py` (≥10
tests, no live keys).

## Implementation notes

* All five providers (`mock`, `stripe`, `payme`, `click`, `paypal`) implement
  the same `PaymentProvider` Protocol from
  `src/domain/billing/service.py`. Structural-conformance is asserted in the
  test suite.
* `build_payment_provider_for_currency(currency, overrides)` is the only new
  factory entry-point; the legacy `build_payment_provider(settings)` keeps
  its FAZA-1 signature for callers that don't yet thread `currency` through.
* Migration `0082_provider_routing` seeds the platform-default rows in
  `system_settings`; admin UI work to expose per-tenant overrides is FAZA 5
  follow-up.
* PayPal SDK is `paypalserversdk>=1.0` in the `[billing]` extra; the lazy
  import keeps `[billing]`-less CI runs unaffected.

## Consequences

* The factory's contract — "always return **some** `PaymentProvider`, never
  raise on misconfiguration" — extends to all four real providers, not just
  Stripe.
* New currency support is a code-side `DEFAULT_PROVIDER_BY_CURRENCY` row
  plus a `system_settings` seed — no new entrypoint required.
* Cross-provider analytics (revenue dashboards, dunning state machines)
  must read the `provider` column on `payments` / `payment_webhook_events`
  to disambiguate; same provider per intent is guaranteed by the factory's
  currency-locked resolution.

## References

* [ADR-0005 — Provider Switching](0005-provider-switching.md)
* `services/api/src/infrastructure/billing/factory.py`
* `services/api/src/infrastructure/billing/{payme,click,paypal}_provider.py`
* Payme JSON-RPC spec — https://developer.help.paycom.uz
* Click Merchant API — https://docs.click.uz
* PayPal webhook verification — https://developer.paypal.com/api/rest/webhooks/rest/
