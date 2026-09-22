"""External ingestion pipelines for SilkLens.

Wikidata SPARQL + Wikipedia REST clients plus the orchestrator that turns
their output into ``heritage_objects`` / ``heritage_facts`` /
``heritage_aliases`` rows.

The clients are HTTP-only (no SQL). The orchestrator (``heritage_importer``)
is the seam that touches both — it reads from the clients and writes via
plain SQL into our schema.
"""

from __future__ import annotations

from src.infrastructure.ingestion.heritage_importer import (
    ImportResult,
    WikidataHeritageImporter,
)
from src.infrastructure.ingestion.wikidata import (
    WikidataClient,
    WikidataHeritage,
    parse_sparql_response,
)
from src.infrastructure.ingestion.wikipedia import WikipediaClient

__all__ = [
    "ImportResult",
    "WikidataClient",
    "WikidataHeritage",
    "WikidataHeritageImporter",
    "WikipediaClient",
    "parse_sparql_response",
]
