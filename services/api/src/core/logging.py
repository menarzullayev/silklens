"""Structured logging configuration via structlog.

JSON in prod/staging, human-readable in dev. Correlation IDs (request_id,
trace_id, user_id, tenant_id) are bound from middleware.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from src.core.settings import get_settings


def _add_service_context(_logger: object, _name: str, event_dict: EventDict) -> EventDict:
    settings = get_settings()
    event_dict.setdefault("service", settings.service_name)
    event_dict.setdefault("env", settings.env)
    return event_dict


def configure_logging() -> None:
    settings = get_settings()
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        _add_service_context,
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.env == "dev":
        renderer: Processor = structlog.dev.ConsoleRenderer(colors=sys.stdout.isatty())
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, settings.log_level)),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Route stdlib loggers (uvicorn, sqlalchemy) through structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=settings.log_level,
    )
    for noisy in ("uvicorn.access", "watchfiles.main"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str | None = None, **initial_context: Any) -> structlog.stdlib.BoundLogger:
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name).bind(**initial_context)  # type: ignore[assignment]
    return logger
