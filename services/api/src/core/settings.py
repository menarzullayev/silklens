"""Runtime settings loaded from environment.

Settings that the user/operator may change at runtime live in the database
(see ``system_settings``, ``feature_flags``, ``ai_models`` etc. per the
architecture docs). This module is reserved for build/deploy-time values:
DSNs, secrets, ports.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Build-time configuration; never used for product behaviour."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="SILKLENS_",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Identity ---
    env: Literal["dev", "test", "staging", "prod"] = "dev"
    service_name: str = "silklens-api"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # --- Database (DSN parsed by SQLAlchemy/asyncpg; kept as str for tooling ergonomics) ---
    database_url: str = Field(
        default="postgresql+psycopg://silklens:silklens_dev@localhost:5434/silklens",
        description="SQLAlchemy DSN. asyncpg form derived in database_url_async.",
    )
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_pool_timeout: int = 30
    database_echo: bool = False

    # --- Redis ---
    redis_url: str = Field(default="redis://localhost:6381/0")

    # --- MinIO ---
    minio_endpoint: str = "localhost:9000"
    minio_access_key: SecretStr = SecretStr("silklens")
    minio_secret_key: SecretStr = SecretStr("silklens_dev_minio")
    minio_secure: bool = False
    minio_bucket_media: str = "silklens-media"
    minio_bucket_offline_bundles: str = "silklens-offline-bundles"

    # --- Elasticsearch ---
    elasticsearch_url: str = "http://localhost:9200"

    # --- Redpanda / Kafka ---
    kafka_bootstrap_servers: str = "localhost:19092"

    # --- JWT ---
    jwt_secret: SecretStr = SecretStr("dev-only-secret-replace-in-production")
    jwt_access_token_ttl_seconds: int = 60 * 15  # 15 minutes
    jwt_refresh_token_ttl_seconds: int = 60 * 60 * 24 * 30  # 30 days
    jwt_algorithm: str = "HS256"

    # --- Audit chain HMAC key (rotated via KMS in prod) ---
    audit_hmac_key: SecretStr = SecretStr("dev-only-audit-hmac-key")

    # --- Webhook shared secret (dev/staging fallback for non-Stripe providers) ---
    webhook_shared_secret: SecretStr = SecretStr("dev-only-webhook-shared-secret")

    # --- Payment provider selection (FAZA 4 / FAZA 5) ---
    # ``mock`` keeps the deterministic in-memory adapter (dev/test/CI default).
    # ``stripe``  → real Stripe (USD/EUR card path)
    # ``payme``   → Uzbek Payme (UZS, JSON-RPC, Basic-Auth webhook)
    # ``click``   → Uzbek Click (UZS, form-encoded, HMAC-SHA1 webhook)
    # ``paypal``  → PayPal (multi-currency, signed-webhook verification)
    # If the matching keys are absent BillingService.factory soft-falls-back to
    # MockProvider so the system never crashes mid-request on a partial env.
    payment_provider: Literal["mock", "stripe", "payme", "click", "paypal"] = "mock"
    stripe_secret_key: SecretStr = SecretStr("")
    stripe_webhook_secret: SecretStr = SecretStr("")

    # Payme — Uzbek payment provider. Amounts travel in tiyin (1 UZS = 100 tiyin).
    # Webhook auth: ``Authorization: Basic <base64(merchant_id:secret)>``.
    payme_merchant_id: str = ""
    payme_secret_key: SecretStr = SecretStr("")
    payme_endpoint: str = "https://checkout.paycom.uz"

    # Click — Uzbek payment provider. Webhook is form-encoded, HMAC-SHA1 over
    # click_trans_id+service_id+click_paydoc_id+amount+action+sign_time+merchant_user_id+secret_key.
    click_service_id: str = ""
    click_merchant_id: str = ""
    click_secret_key: SecretStr = SecretStr("")
    click_endpoint: str = "https://my.click.uz/services/pay"

    # PayPal — multi-currency, official SDK (``paypalserversdk``). When
    # client_id/secret are absent the factory soft-falls back to MockProvider.
    paypal_client_id: str = ""
    paypal_client_secret: SecretStr = SecretStr("")
    paypal_webhook_id: str = ""
    paypal_environment: Literal["sandbox", "live"] = "sandbox"

    # --- API ---
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # --- Tenancy ---
    default_tenant_id: str = "00000000-0000-0000-0000-000000000001"

    # --- Rate limiting (SEC-005) ---
    # Master switch — unit tests that don't care about 429 behaviour can
    # set ``SILKLENS_RATE_LIMIT_ENABLED=false`` to skip enforcement
    # entirely. Production must keep this true.
    rate_limit_enabled: bool = True
    # SEC-W56-004 fix: default to empty list so XFF is NOT trusted unless
    # the operator explicitly configures the load-balancer egress CIDRs.
    # Dev docker stack works fine with an empty list (rate limits key on
    # request.client.host which is the Docker bridge IP, not spoofable
    # from outside the container network).
    # Example prod value: "10.100.0.1/32,10.100.0.2/32" (ingress node IPs).
    trusted_proxy_cidrs: list[str] = Field(default_factory=list)
    # Failed-login lockout window (per Agent 2 §4). After
    # ``login_lockout_max_failures`` failures from the same identifier+IP
    # inside ``login_lockout_window_seconds``, the auth service returns
    # HTTP 423 LOCKED for ``login_lockout_duration_seconds``.
    login_lockout_max_failures: int = 5
    login_lockout_window_seconds: int = 600  # 10 minutes
    login_lockout_duration_seconds: int = 900  # 15 minutes

    # --- MFA (FAZA 5) ---
    # Symmetric key used by pgcrypto's ``pgp_sym_encrypt`` to wrap TOTP shared
    # secrets and other at-rest MFA material. Live key lives in KMS; the dev
    # default is just enough to keep the migration round-trip green.
    mfa_at_rest_key: SecretStr = SecretStr("dev-only-mfa-rest-key")
    # WebAuthn relying-party identifiers. The RP ID must be a registrable
    # domain or its subdomain (FIDO2 §5.4). Origin list is admin + mobile.
    webauthn_rp_id: str = "localhost"
    webauthn_rp_name: str = "SilkLens"
    webauthn_origin: str = "http://localhost:3000"
    # MFA challenge TTL (seconds). Architecture §8.5 calls for 5 minutes.
    mfa_challenge_ttl_seconds: int = 300
    # How long a satisfied MFA challenge stays "fresh" for step-up gating.
    mfa_step_up_freshness_seconds: int = 300

    # --- AI ---
    # When true, the provider resolver always returns deterministic mock
    # providers (LLaVA / Kokoro / NLLB / Anthropic stubs). Set to false in
    # prod once the GPU server is reachable + ANTHROPIC_API_KEY is wired.
    ai_use_mock_providers: bool = True
    # Default Anthropic model slug. Mirrors the row in ai_models so the
    # resolver picks up the model_id consistently between code and DB.
    anthropic_model_default: str = "claude-opus-4-7"

    # --- Observability ---
    # Empty DSN keeps Sentry as a no-op (dev/test default).
    sentry_dsn: SecretStr = SecretStr("")
    # 10% of traces by default; bump in staging, lower in steady-state prod.
    sentry_traces_rate: float = 0.1
    # OTLP HTTP collector endpoint (Tempo / OTel collector). HTTP/4318 default.
    otlp_endpoint: str = "http://localhost:4318"
    # Toggle to disable /metrics + Prometheus instrumentation entirely.
    metrics_enabled: bool = True
    # Hostname tag for Sentry; falls back to socket.gethostname() if unset.
    server_name: str | None = None

    @field_validator("api_cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v: object) -> object:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def database_url_sync(self) -> str:
        """Synchronous DSN used by Alembic (no asyncpg driver)."""
        return self.database_url.replace("postgresql+asyncpg", "postgresql+psycopg")

    @property
    def database_url_async(self) -> str:
        """Async DSN used by SQLAlchemy AsyncEngine."""
        return self.database_url.replace("postgresql+psycopg", "postgresql+asyncpg")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
