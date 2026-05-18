# ADR 0005 — Provider Switching: Mock vs Real (Stripe + Anthropic)

> Status: **Accepted** · 2026-05-18 · Supersedes inline notes in FAZA-1 stubs.

## Context

SilkLens depends on two paid third-party providers:

* **Stripe** for global card payments (see `06-monetization-enterprise.md`).
* **Anthropic** for the Claude-family LLM used in chat, descriptions and the
  upcoming agent layer.

During FAZA-1 we shipped deterministic in-memory mocks for both so
development, CI, and round-trip tests can run with zero external dependencies
and zero API spend. FAZA-4 introduces real provider paths; we need a single,
predictable switching pattern so the same codebase serves test, dev, staging
and prod without runtime forking in business code.

## Decision

We adopt a **settings-driven provider factory** pattern with **soft-fallback
to mocks** when credentials are missing.

### 1. Settings flags (build-time, env-only)

```text
SILKLENS_PAYMENT_PROVIDER   ∈ {"mock","stripe"}   default "mock"
SILKLENS_STRIPE_SECRET_KEY  SecretStr             default ""
SILKLENS_STRIPE_WEBHOOK_SECRET SecretStr          default ""
SILKLENS_AI_USE_MOCK_PROVIDERS  bool              default true
SILKLENS_ANTHROPIC_MODEL_DEFAULT str              default "claude-opus-4-7"
ANTHROPIC_API_KEY           env (no SILKLENS_ prefix, sourced from SDK)
```

These are **build-time** flags — never used to drive product behaviour.
Product rules (plan A/B, pricing zone selection, RBAC) live in Postgres.

### 2. Factory protocol

`src/infrastructure/billing/factory.py::build_payment_provider(settings)`
returns the active payment provider. The rule is:

```
if payment_provider == "stripe" AND stripe_secret_key not empty
   → StripeProvider(...)
else
   → MockPaymentProvider()
```

The factory **never raises** on misconfiguration; it logs a structured
warning and degrades to the mock. This is intentional: a half-deployed env
should not take requests down.

`is_real_stripe_active(settings)` is a cheap predicate used by the webhook
router to choose between Stripe-signature verification and the
shared-secret fallback. Real Stripe requires **both** the secret key **and**
the webhook secret to be populated.

### 3. AI provider chain

`ProviderResolver` walks `ai_fallback_chains` (Postgres) and instantiates
the matching provider class. When `ai_use_mock_providers=true` the DB is
bypassed and a single mock is returned per task type.

In real mode, if `ANTHROPIC_API_KEY` is present, the resolver **prepends**
an `AnthropicLlmProvider` to the chain for `TEXT` tasks and **appends** a
`MockLlmProvider` as a final safety net so a transient 5xx never takes the
whole request down. The same pattern will apply to vision/TTS once the GPU
provider classes ship.

### 4. Webhook router

Two-path verification in `POST /v1/billing/webhooks/{provider}`:

* **Stripe-verified path** — `is_real_stripe_active()` true *and* the
  `Stripe-Signature` header is present → verify via the SDK's
  `Webhook.construct_event`. On success, bypass the shared-secret check and
  dispatch to typed `BillingService` handlers
  (`handle_payment_succeeded`, `mark_payment_failed`,
  `mark_subscription_canceled_external`, `handle_invoice_event`).
* **Shared-secret fallback** — every other case (non-Stripe providers, dev
  envs without stripe keys) requires `X-Silklens-Webhook-Secret` ==
  `SILKLENS_WEBHOOK_SHARED_SECRET` (HMAC-equal compare).

Idempotency is enforced uniformly via
`payment_webhook_events.UNIQUE(provider, provider_event_id)`.

### 5. Error mapping

Real providers translate their typed errors to our domain errors at the
adapter boundary:

| Stripe class                 | Domain error                          |
|------------------------------|---------------------------------------|
| `CardError`                  | `PaymentFailed(reason=code)`          |
| `RateLimitError`             | `ProviderUnavailable`                 |
| `AuthenticationError`        | `ProviderUnavailable`                 |
| `APIConnectionError`/`APIError` | `ProviderUnavailable`              |
| `SignatureVerificationError` | `InvalidWebhookSignature`             |

Anthropic 429/5xx are retried via `tenacity` (3 attempts, exponential
backoff). After exhaustion the provider raises `AiProviderUnavailable`,
which lets the resolver chain walk to the next provider (mock final).

## Consequences

**Positive**

* Tests stay hermetic — no flags need to change between unit / integration
  test runs.
* Production never crashes mid-request because of a half-deployed env; it
  degrades to mock + a loud warning that ops can alert on.
* Adding a third real provider (PayPal, Payme, Click) is a copy of the
  Stripe pattern: a new class + factory branch + router-side verifier.

**Negative**

* The factory's soft-fallback can mask a misconfigured production deploy if
  ops ignores the warning logs. Mitigation: a Prometheus metric
  `billing_factory_fallback_total` (FAZA-5 SLO) plus a CI check that
  prod-targeted manifests must include all four Stripe envs.
* Two webhook auth paths is more surface area than one. Mitigation: the
  router's two branches are unit-tested and the Stripe path is the
  preferred one as soon as the keys land.

## Alternatives Considered

1. **Always require Stripe in prod, no fallback.** Rejected: a transient
   secret-store outage would otherwise turn into a full billing outage.
2. **Runtime DB flag instead of env.** Rejected: the secret values are
   build-time anyway (rotated by ops, not admins) and an env flip is faster
   to roll back than a DB row.
3. **Single provider per process.** Rejected: makes tests harder; we want
   one process to serve both Stripe-real prod traffic and mocked-in-tests
   pytest sessions.

## Compliance & Security

* Stripe keys are stored in `SecretStr` and never logged.
* Webhook signature verification uses Stripe's recommended
  `construct_event` (timestamp + HMAC tolerance) — no hand-rolled HMAC.
* `ANTHROPIC_API_KEY` is read from the environment (no DB row); rotation is
  ops-only.

## References

* `services/api/src/infrastructure/billing/factory.py`
* `services/api/src/infrastructure/billing/stripe_provider.py`
* `services/api/src/infrastructure/ai/anthropic_provider.py`
* `services/api/src/api/routers/billing.py`
* `docs/architecture/06-monetization-enterprise.md` §§2.5, 5
