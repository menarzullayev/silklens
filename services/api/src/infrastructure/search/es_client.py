"""Async Elasticsearch client wrapper.

The real `elasticsearch[async]` client is heavyweight; this module wraps it in
a tiny facade so:

  1. tests can substitute an in-memory implementation through DI;
  2. the rest of the application doesn't import from ``elasticsearch.*`` and we
     keep a single seam to swap to OpenSearch if that ever becomes necessary;
  3. construction errors surface as a single ``ElasticsearchUnavailable``.

Configuration reads ``SILKLENS_ELASTICSEARCH_URL`` (defaults to localhost:9200
per the dev Docker stack).
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from src.core.logging import get_logger
from src.core.settings import get_settings

log = get_logger("silklens.search.es_client")


class ElasticsearchUnavailable(RuntimeError):  # noqa: N818 - cluster-state name reads better
    """Raised when the ES cluster cannot be reached.

    Callers should treat this as a soft-fail in request paths and a hard-fail
    in admin / scheduled ingestion paths.
    """


class ElasticsearchClient:
    """Thin async facade over the official AsyncElasticsearch client.

    All methods are tiny so tests can subclass + override individual calls
    without instantiating the real transport.
    """

    def __init__(self, url: str | None = None) -> None:
        self._url = url or get_settings().elasticsearch_url
        self._inner: Any | None = None

    async def _get(self) -> Any:
        if self._inner is None:
            try:
                from elasticsearch import AsyncElasticsearch
            except ImportError as exc:  # pragma: no cover - hard dep
                raise ElasticsearchUnavailable("elasticsearch[async] not installed") from exc
            self._inner = AsyncElasticsearch(hosts=[self._url], request_timeout=10)
        return self._inner

    async def close(self) -> None:
        if self._inner is not None:
            await self._inner.close()
            self._inner = None

    # --- Index lifecycle ---------------------------------------------------

    async def index_exists(self, name: str) -> bool:
        client = await self._get()
        try:
            return bool(await client.indices.exists(index=name))
        except Exception as exc:
            raise ElasticsearchUnavailable(str(exc)) from exc

    async def create_index(self, name: str, body: dict[str, Any]) -> None:
        client = await self._get()
        try:
            await client.indices.create(index=name, body=body, ignore=[400])
        except Exception as exc:
            raise ElasticsearchUnavailable(str(exc)) from exc

    async def delete_index(self, name: str) -> None:
        client = await self._get()
        try:
            await client.indices.delete(index=name, ignore_unavailable=True)
        except Exception as exc:
            raise ElasticsearchUnavailable(str(exc)) from exc

    async def refresh(self, name: str) -> None:
        client = await self._get()
        try:
            await client.indices.refresh(index=name)
        except Exception as exc:
            raise ElasticsearchUnavailable(str(exc)) from exc

    async def count(self, name: str) -> int:
        client = await self._get()
        try:
            response = await client.count(index=name, ignore_unavailable=True)
            return int(response.get("count", 0))
        except Exception as exc:
            raise ElasticsearchUnavailable(str(exc)) from exc

    # --- Documents ---------------------------------------------------------

    async def index_doc(self, index: str, doc_id: str, body: dict[str, Any]) -> None:
        client = await self._get()
        try:
            await client.index(index=index, id=doc_id, document=body)
        except Exception as exc:
            raise ElasticsearchUnavailable(str(exc)) from exc

    async def delete_doc(self, index: str, doc_id: str) -> None:
        client = await self._get()
        try:
            await client.delete(index=index, id=doc_id, ignore=[404])
        except Exception as exc:
            raise ElasticsearchUnavailable(str(exc)) from exc

    async def bulk(self, actions: Iterable[dict[str, Any]]) -> dict[str, Any]:
        client = await self._get()
        operations = list(actions)
        if not operations:
            return {"items": [], "errors": False}
        try:
            return dict(await client.bulk(operations=operations))
        except Exception as exc:
            raise ElasticsearchUnavailable(str(exc)) from exc

    async def search(self, index: str, body: dict[str, Any]) -> dict[str, Any]:
        client = await self._get()
        try:
            return dict(await client.search(index=index, body=body))
        except Exception as exc:
            raise ElasticsearchUnavailable(str(exc)) from exc


_singleton: ElasticsearchClient | None = None


def get_es_client() -> ElasticsearchClient:
    """Process-wide singleton; closed in FastAPI lifespan shutdown if needed."""
    global _singleton
    if _singleton is None:
        _singleton = ElasticsearchClient()
    return _singleton


def reset_es_client(client: ElasticsearchClient | None = None) -> None:
    """Test helper — replace or clear the singleton."""
    global _singleton
    _singleton = client
