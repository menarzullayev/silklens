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
from src.api.routers import auth, health, heritage
from src.core.database import dispose_engine
from src.core.logging import configure_logging, get_logger
from src.core.settings import get_settings
from src.middleware.auth import BearerContextMiddleware


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    log = get_logger("silklens.lifespan")
    log.info("api.startup", version=__version__)
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
        openapi_url="/openapi.json",
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

    return app
