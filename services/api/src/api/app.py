"""FastAPI app factory.

Routers per bounded context are added incrementally as each FAZA lands. At
FAZA 1 only the operational ``/health`` and ``/version`` endpoints exist so
the deployment / Docker Compose stack is verifiable end-to-end.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src import __version__
from src.api.routers import (
    admin,
    ai,
    auth,
    billing,
    compliance,
    gamification,
    health,
    heritage,
    media,
    mfa,
    notifications,
    public_meta,
    reseller,
    reviews,
    search,
    social,
)
from src.core.database import dispose_engine, get_engine
from src.core.logging import configure_logging, get_logger
from src.core.metrics import register_db_pool_metrics
from src.core.observability import init_sentry, init_tracing
from src.core.settings import get_settings
from src.infrastructure.media.minio_client import get_minio_client
from src.middleware.auth import BearerContextMiddleware
from src.middleware.ratelimit import get_rate_limiter, reset_rate_limiter
from src.middleware.trace import TraceContextMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    log = get_logger("silklens.lifespan")
    settings = get_settings()
    log.info("api.startup", version=__version__)

    # Observability bootstrap. Both initializers no-op when DSN/endpoint is
    # unreachable so dev/test stays quiet.
    init_sentry()
    init_tracing(app)

    # Bind SQLAlchemy pool metrics; non-fatal if engine init fails (e.g.
    # offline test runs that never touch the DB).
    try:
        register_db_pool_metrics(get_engine())
    except Exception as exc:
        log.debug("metrics.db_pool_register_failed", error=str(exc))

    # Bootstrap the primary media bucket; non-fatal so tests/dev keep working
    # when the MinIO container is offline or a fake client is injected.
    try:
        get_minio_client().ensure_bucket(settings.minio_bucket_media)
    except Exception as exc:
        log.warning("media.minio.bucket_bootstrap_failed", error=str(exc))

    # Eagerly materialize the rate limiter so the Redis connection failure
    # (if any) shows up at startup rather than on the first 429 path.
    try:
        get_rate_limiter()
    except Exception as exc:
        log.warning("ratelimit.bootstrap_failed", error=str(exc))

    try:
        yield
    finally:
        await dispose_engine()
        # Drop the limiter singleton so a fresh app (e.g. test reload)
        # rebuilds it from current settings.
        reset_rate_limiter()
        log.info("api.shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="SilkLens API",
        version=__version__,
        docs_url="/docs" if settings.env != "prod" else None,
        redoc_url="/redoc" if settings.env != "prod" else None,
        openapi_url="/openapi.json" if settings.env != "prod" else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Bearer-token decoding runs once per request; binds AuthContext to
    # request.state.auth (or None). Public endpoints simply ignore it.
    app.add_middleware(BearerContextMiddleware)
    # Rate-limit middleware sits after the bearer middleware so the global
    # default uses the per-user key when a token is present. SEC-005.
    get_rate_limiter().install(app)
    # Trace ID binding runs outermost so every log line — including auth
    # decode failures — carries trace_id, method, route in structlog context.
    app.add_middleware(TraceContextMiddleware)

    # Prometheus instrumentation. The instrumentator exposes ``/metrics`` and
    # adds RED-method metrics; our custom counters live in src.core.metrics
    # and share the default registry so they're emitted on the same endpoint.
    if settings.metrics_enabled:
        try:
            from prometheus_fastapi_instrumentator import Instrumentator

            Instrumentator(
                should_group_status_codes=False,
                should_ignore_untemplated=True,
            ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
        except Exception:
            # Instrumentator is best-effort — never block app startup on it.
            get_logger("silklens.observability").debug("metrics.instrumentator_failed")

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(mfa.router)
    app.include_router(heritage.router)
    app.include_router(ai.router)
    app.include_router(media.router)
    app.include_router(social.router)
    app.include_router(reviews.router)
    app.include_router(gamification.router)
    app.include_router(billing.router)
    app.include_router(notifications.router)
    app.include_router(admin.router)
    app.include_router(public_meta.router)
    app.include_router(compliance.router)
    app.include_router(search.router)
    app.include_router(reseller.router)

    return app
