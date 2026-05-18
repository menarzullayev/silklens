"""Celery tasks for the ingestion pipeline.

Like the search Celery module, this is import-safe: Celery is only
instantiated through ``get_celery_app()`` and the actual task definitions
are registered via ``register_tasks(app)`` at worker boot time.

Two tasks ship:

  * ``silklens.ingestion.ingest_country(country_code, limit, actor)`` — runs
    the SPARQL discovery query and imports every result.
  * ``silklens.ingestion.ingest_qid(qid, actor)`` — imports a single Q-id
    end-to-end (used by the admin "single import" endpoint).
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from src.core.logging import get_logger
from src.core.settings import get_settings

log = get_logger("silklens.ingestion.celery")


async def _run_ingest_country(country_code: str, limit: int, actor: UUID) -> dict[str, Any]:
    from src.core.database import get_sessionmaker
    from src.infrastructure.ingestion.heritage_importer import WikidataHeritageImporter
    from src.infrastructure.ingestion.wikidata import WikidataClient
    from src.infrastructure.ingestion.wikipedia import WikipediaClient

    settings = get_settings()
    tenant_id = UUID(settings.default_tenant_id)
    factory = get_sessionmaker()
    wd = WikidataClient()
    wp = WikipediaClient()
    try:
        async with factory() as session:
            importer = WikidataHeritageImporter(session, wd, wp, default_tenant_id=tenant_id)
            outcome = await importer.import_batch(
                country_code=country_code, limit=limit, requested_by=actor
            )
            return {
                "discovered": outcome.discovered,
                "created": outcome.created,
                "skipped": outcome.skipped,
                "failed": outcome.failed,
            }
    finally:
        await wd.close()
        await wp.close()


async def _run_ingest_qid(qid: str, actor: UUID) -> dict[str, Any]:
    from src.core.database import get_sessionmaker
    from src.infrastructure.ingestion.heritage_importer import WikidataHeritageImporter
    from src.infrastructure.ingestion.wikidata import WikidataClient
    from src.infrastructure.ingestion.wikipedia import WikipediaClient

    settings = get_settings()
    tenant_id = UUID(settings.default_tenant_id)
    factory = get_sessionmaker()
    wd = WikidataClient()
    wp = WikipediaClient()
    try:
        item = await wd.fetch_qid(qid)
        if item is None:
            return {"qid": qid, "found": False, "created": False}
        async with factory() as session:
            importer = WikidataHeritageImporter(session, wd, wp, default_tenant_id=tenant_id)
            outcome = await importer.import_one(item, requested_by=actor)
            return {
                "qid": qid,
                "found": True,
                "created": outcome.created,
                "heritage_id": str(outcome.heritage_id),
                "pub_id": outcome.pub_id,
            }
    finally:
        await wd.close()
        await wp.close()


def register_tasks(app: Any) -> None:
    @app.task(name="silklens.ingestion.ingest_country")
    def ingest_country(country_code: str, limit: int, actor: str) -> dict[str, Any]:
        return asyncio.run(_run_ingest_country(country_code, limit, UUID(actor)))

    @app.task(name="silklens.ingestion.ingest_qid")
    def ingest_qid(qid: str, actor: str) -> dict[str, Any]:
        return asyncio.run(_run_ingest_qid(qid, UUID(actor)))

    app.silklens_ingest_country = ingest_country
    app.silklens_ingest_qid = ingest_qid


__all__ = ["_run_ingest_country", "_run_ingest_qid", "register_tasks"]
