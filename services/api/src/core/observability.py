"""Sentry + OpenTelemetry bootstrap.

Two side-effecting initializers, both no-ops when the relevant env-var is
unset so unit tests and offline dev stay quiet:

- :func:`init_sentry` — wires the Sentry SDK with FastAPI / SQLAlchemy /
  Celery integrations, default PII scrubbing **on**, release pulled from
  ``src.__version__``, and ``traces_sample_rate`` from settings.
- :func:`init_tracing` — sets up an OpenTelemetry tracer provider with an
  OTLP/HTTP exporter, then instruments FastAPI, SQLAlchemy, httpx, and
  asyncpg. Idempotent — repeated calls (e.g. in tests) are safe.

Both are invoked from ``src.api.app.lifespan``; nothing else should touch
them. The functions return ``bool`` indicating whether they actually
initialized so the lifespan log can record the outcome.
"""

from __future__ import annotations

import socket
from typing import Any

from src import __version__
from src.core.logging import get_logger
from src.core.settings import get_settings

log = get_logger("silklens.observability")

_TRACING_INITIALIZED = False


def init_sentry() -> bool:
    """Initialize Sentry SDK; no-op when ``SILKLENS_SENTRY_DSN`` is empty.

    Returns ``True`` if Sentry was actually initialized, ``False`` if skipped.
    """

    settings = get_settings()
    dsn = settings.sentry_dsn.get_secret_value().strip()
    if not dsn:
        log.debug("sentry.disabled")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
    except ImportError:
        log.warning("sentry.sdk_missing")
        return False

    server_name = settings.server_name or socket.gethostname()
    sentry_sdk.init(
        dsn=dsn,
        environment=settings.env,
        release=f"silklens-api@{__version__}",
        server_name=server_name,
        traces_sample_rate=settings.sentry_traces_rate,
        send_default_pii=False,  # PII scrubbing on per spec.
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            CeleryIntegration(),
        ],
    )
    log.info(
        "sentry.initialized",
        environment=settings.env,
        release=__version__,
        traces_rate=settings.sentry_traces_rate,
    )
    return True


def init_tracing(app: Any | None = None) -> bool:
    """Initialize OpenTelemetry tracing + auto-instrumentation.

    Idempotent: the global tracer provider is only configured once even if
    repeated app factories construct multiple FastAPI instances (common in
    tests). ``app`` is optional so a Celery worker can call this without
    a FastAPI app.
    """

    global _TRACING_INITIALIZED
    settings = get_settings()

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        log.warning("tracing.sdk_missing")
        return False

    if not _TRACING_INITIALIZED:
        resource = Resource.create(
            {
                "service.name": settings.service_name,
                "service.version": __version__,
                "deployment.environment": settings.env,
            }
        )
        provider = TracerProvider(resource=resource)
        # OTLP exporter is an optional install — span processing still works
        # against the in-memory provider even when the HTTP exporter is absent.
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )

            exporter = OTLPSpanExporter(endpoint=f"{settings.otlp_endpoint}/v1/traces")
            provider.add_span_processor(BatchSpanProcessor(exporter))
        except ImportError:
            log.debug("tracing.exporter_missing")
        except Exception as exc:  # network unreachable in dev / CI
            log.debug("tracing.exporter_unavailable", error=str(exc))
        trace.set_tracer_provider(provider)
        _TRACING_INITIALIZED = True

    # Auto-instrumentation — wrapped in best-effort try/except so a missing
    # optional package never crashes the API.
    if app is not None:
        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

            FastAPIInstrumentor.instrument_app(app)
        except Exception as exc:
            log.debug("tracing.fastapi_skip", error=str(exc))

    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        SQLAlchemyInstrumentor().instrument()
    except Exception as exc:
        log.debug("tracing.sqlalchemy_skip", error=str(exc))

    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        HTTPXClientInstrumentor().instrument()
    except Exception as exc:
        log.debug("tracing.httpx_skip", error=str(exc))

    try:
        from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor

        AsyncPGInstrumentor().instrument()
    except Exception as exc:
        log.debug("tracing.asyncpg_skip", error=str(exc))

    log.info("tracing.initialized", endpoint=settings.otlp_endpoint)
    return True


__all__ = ["init_sentry", "init_tracing"]
