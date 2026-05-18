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

    # --- Webhook shared secret (FAZA 4 → replaced with per-provider signature) ---
    webhook_shared_secret: SecretStr = SecretStr("dev-only-webhook-shared-secret")

    # --- API ---
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # --- Tenancy ---
    default_tenant_id: str = "00000000-0000-0000-0000-000000000001"

    # --- AI ---
    # When true, the provider resolver always returns deterministic mock
    # providers (LLaVA / Kokoro / NLLB / Anthropic stubs). Set to false in
    # prod once the GPU server is reachable + ANTHROPIC_API_KEY is wired.
    ai_use_mock_providers: bool = True

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
