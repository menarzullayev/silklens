"""Celery tasks for the search pipeline.

The Celery app is lazy-instantiated so importing this module never touches
Redis (tests that don't need Celery can import safely). The tasks are thin
sync wrappers that call ``asyncio.run`` on the async indexer / consumer —
the heavy lifting stays async.
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from src.core.logging import get_logger
from src.core.settings import get_settings

log = get_logger("silklens.search.celery")

_celery_app: Any | None = None


def get_celery_app() -> Any:
    """Return (and cache) the shared Celery app."""
    global _celery_app
    if _celery_app is None:
        from celery import Celery  # type: ignore[import-untyped]

        settings = get_settings()
        _celery_app = Celery(
            "silklens",
            broker=settings.redis_url,
            backend=settings.redis_url,
        )
        _celery_app.conf.task_default_queue = "silklens"
        _celery_app.conf.task_acks_late = True
        _celery_app.conf.worker_prefetch_multiplier = 1
        _celery_app.conf.beat_schedule = {
            "search-drain-outbox": {
                "task": "silklens.search.drain_outbox",
                "schedule": 5.0,
            }
        }
    return _celery_app


# Module-level decorator wiring uses Celery's `shared_task` lookalike pattern:
# we register the task once `get_celery_app()` has been invoked. To stay
# import-safe (no Redis at import time) we expose plain async fns + a
# ``register_tasks(app)`` helper that the worker entrypoint calls.


async def _run_index_heritage(heritage_id: UUID) -> dict[str, int]:
    from src.core.database import get_sessionmaker
    from src.infrastructure.search.es_client import get_es_client
    from src.infrastructure.search.indexer import HeritageIndexer

    factory = get_sessionmaker()
    async with factory() as session:
        indexer = HeritageIndexer(session, get_es_client())
        result = await indexer.index_one(heritage_id)
        return {"indexed": result.indexed, "skipped": result.skipped, "failed": result.failed}


async def _run_bulk_reindex_all() -> dict[str, int]:
    from src.core.database import get_sessionmaker
    from src.infrastructure.search.es_client import get_es_client
    from src.infrastructure.search.indexer import HeritageIndexer

    factory = get_sessionmaker()
    async with factory() as session:
        indexer = HeritageIndexer(session, get_es_client())
        result = await indexer.bulk_reindex()
        return {"indexed": result.indexed, "skipped": result.skipped, "failed": result.failed}


async def _run_drain_outbox() -> dict[str, int]:
    from src.core.database import get_sessionmaker
    from src.infrastructure.search.consumer import OutboxConsumer
    from src.infrastructure.search.es_client import get_es_client
    from src.infrastructure.search.indexer import HeritageIndexer

    factory = get_sessionmaker()
    async with factory() as session:
        indexer = HeritageIndexer(session, get_es_client())
        consumer = OutboxConsumer(session, indexer)
        result = await consumer.drain()
        return {
            "processed": result.processed,
            "indexed": result.indexed,
            "deleted": result.deleted,
            "failed": result.failed,
        }


def register_tasks(app: Any) -> None:
    """Bind the async helpers above to Celery task names.

    Called from the worker entry point. Tests can invoke ``index_heritage``
    etc. by name through ``app.tasks``.
    """

    @app.task(name="silklens.search.index_heritage")
    def index_heritage(heritage_id: str) -> dict[str, int]:
        return asyncio.run(_run_index_heritage(UUID(heritage_id)))

    @app.task(name="silklens.search.bulk_reindex_all")
    def bulk_reindex_all() -> dict[str, int]:
        return asyncio.run(_run_bulk_reindex_all())

    @app.task(name="silklens.search.drain_outbox")
    def drain_outbox() -> dict[str, int]:
        return asyncio.run(_run_drain_outbox())

    # Surface for callers / tests.
    app.silklens_index_heritage = index_heritage
    app.silklens_bulk_reindex_all = bulk_reindex_all
    app.silklens_drain_outbox = drain_outbox


__all__ = [
    "_run_bulk_reindex_all",
    "_run_drain_outbox",
    "_run_index_heritage",
    "get_celery_app",
    "register_tasks",
]
