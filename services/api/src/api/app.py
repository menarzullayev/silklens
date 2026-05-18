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
    gamification,
    health,
    heritage,
    media,
    notifications,
    public_meta,
    reviews,
    social,
)
from src.core.database import dispose_engine
from src.core.logging import configure_logging, get_logger
from src.core.settings import get_settings
from src.infrastructure.media.minio_client import get_minio_client
from src.middleware.auth import BearerContextMiddleware


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    log = get_logger("silklens.lifespan")
    settings = get_settings()
    log.info("api.startup", version=__version__)
    # Bootstrap the primary media bucket; non-fatal so tests/dev keep working
    # when the MinIO container is offline or a fake client is injected.
    try:
        get_minio_client().ensure_bucket(settings.minio_bucket_media)
    except Exception as exc:
        log.warning("media.minio.bucket_bootstrap_failed", error=str(exc))
    try:
        yield
    finally:
        await dispose_engine()
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

    app.include_router(health.router)
    app.include_router(auth.router)
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

    return app
