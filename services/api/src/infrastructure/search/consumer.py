"""Outbox → Elasticsearch consumer.

Drains rows from ``event_outbox`` for ``heritage.created.v1``,
``heritage.updated.v1`` and ``heritage.deleted.v1``. Each row is translated
into an index or delete call against the ES cluster and removed from the
outbox once acknowledged.

The consumer is intentionally single-threaded per-call — Celery beat fires it
every few seconds (see ``celery_tasks.drain_outbox``) so concurrency is
handled by the scheduler, not by us. We claim rows with ``FOR UPDATE SKIP
LOCKED`` to remain safe if two workers race.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.infrastructure.search.indexer import HeritageIndexer

log = get_logger("silklens.search.consumer")

HERITAGE_EVENT_NAMES: frozenset[str] = frozenset(
    {"heritage.created.v1", "heritage.updated.v1", "heritage.deleted.v1", "heritage.imported.v1"}
)


@dataclass(slots=True, frozen=True)
class DrainResult:
    processed: int
    indexed: int
    deleted: int
    failed: int


class OutboxConsumer:
    """Drain heritage events from ``event_outbox`` into Elasticsearch."""

    def __init__(self, session: AsyncSession, indexer: HeritageIndexer) -> None:
        self._session = session
        self._indexer = indexer

    async def drain(self, batch_size: int = 100) -> DrainResult:
        rows = (
            await self._session.execute(
                text(
                    """
                    SELECT id, event_name, aggregate_id
                    FROM event_outbox
                    WHERE event_name = ANY(:names)
                    ORDER BY created_at ASC
                    LIMIT :limit
                    FOR UPDATE SKIP LOCKED
                    """
                ),
                {"names": list(HERITAGE_EVENT_NAMES), "limit": batch_size},
            )
        ).all()

        indexed = 0
        deleted = 0
        failed = 0
        processed = 0
        for row in rows:
            outbox_id: UUID = row._mapping["id"]
            event_name: str = row._mapping["event_name"]
            heritage_id: UUID = row._mapping["aggregate_id"]
            processed += 1
            try:
                if event_name == "heritage.deleted.v1":
                    result = await self._indexer.delete_one(heritage_id)
                    deleted += 1
                else:
                    result = await self._indexer.index_one(heritage_id)
                    indexed += result.indexed
            except Exception as exc:
                log.warning(
                    "search.consumer.fail",
                    outbox_id=str(outbox_id),
                    event_name=event_name,
                    error=str(exc),
                )
                failed += 1
                continue
            await self._session.execute(
                text("DELETE FROM event_outbox WHERE id = :oid"),
                {"oid": outbox_id},
            )

        await self._session.commit()
        log.info(
            "search.consumer.drain",
            processed=processed,
            indexed=indexed,
            deleted=deleted,
            failed=failed,
        )
        return DrainResult(processed=processed, indexed=indexed, deleted=deleted, failed=failed)
