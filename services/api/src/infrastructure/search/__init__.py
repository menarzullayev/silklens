"""Elasticsearch infrastructure for SilkLens.

Per Agent 7 architecture §8 (outbox-driven indexing) and §9 (search relevance).
The domain layer never imports from here; instead it emits events into the
``event_outbox`` table and the consumer in this package translates those into
ES bulk operations.

Public API:
    * ``ElasticsearchClient`` — thin async wrapper around the official client.
    * ``HeritageIndexer``    — bootstrap / index_one / bulk_reindex.
    * ``OutboxConsumer``     — drains ``event_outbox`` rows for heritage.* events.
    * ``HERITAGE_INDICES``   — frozen set of tier-1 + tier-2 index aliases.
"""

from __future__ import annotations

from src.infrastructure.search.es_client import ElasticsearchClient, get_es_client
from src.infrastructure.search.indexer import HeritageIndexer
from src.infrastructure.search.mappings import HERITAGE_INDICES, mapping_for

__all__ = [
    "HERITAGE_INDICES",
    "ElasticsearchClient",
    "HeritageIndexer",
    "get_es_client",
    "mapping_for",
]
