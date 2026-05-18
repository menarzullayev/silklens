"""Async Wikidata SPARQL client.

Targets the public WDQS endpoint at https://query.wikidata.org/sparql. The
query template selects heritage sites in a given country (ISO 3166-1 alpha-2)
along with multilingual labels, coordinates, inception year, country, the
``instance_of`` (P31) tree, and a Wikimedia Commons image URL.

Three responsibilities:

  1. Build the SPARQL query (Jinja-free; format-string + escape).
  2. POST it with a polite UA header + 1 req/sec rate-limit guard.
  3. Parse the WDQS bindings JSON into a list of ``WikidataHeritage``.

We use httpx (already a project dep) and respect the WDQS Terms of Service:
a descriptive User-Agent identifying SilkLens, request timeouts, and the
``Accept: application/sparql-results+json`` header.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

import httpx

from src.core.logging import get_logger

log = get_logger("silklens.ingestion.wikidata")

WDQS_ENDPOINT = "https://query.wikidata.org/sparql"

USER_AGENT = (
    "SilkLens/0.1 (https://silklens.com; contact@silklens.com) wikidata-ingestion +python-httpx"
)

# Country-code -> WD entity Q-id. We only need a handful for FAZA 2; the
# rest are looked up on-demand via the SPARQL ``wdt:P297`` ISO label.
_COUNTRY_Q: dict[str, str] = {
    "UZ": "Q265",
    "KZ": "Q232",
    "KG": "Q813",
    "TJ": "Q863",
    "TM": "Q874",
    "AF": "Q889",
    "CN": "Q148",
    "IR": "Q794",
    "TR": "Q43",
}

# Heritage instance_of (P31) Q-ids we care about. The SPARQL query uses
# ``wdt:P31/wdt:P279*`` so subclasses are matched too.
HERITAGE_INSTANCE_OF = (
    "Q839954",  # archaeological site
    "Q570116",  # tourist attraction
    "Q33506",  # museum
    "Q41176",  # building
    "Q2393314",  # madrasa
    "Q44539",  # temple
    "Q35112127",  # caravanserai
    "Q16970",  # church building
    "Q32815",  # mosque
    "Q23413",  # castle
    "Q1424516",  # fortress
    "Q11303",  # skyscraper
    "Q839954",  # archaeological site
    "Q9259",  # UNESCO World Heritage Site
)


# --- Data classes ---------------------------------------------------------


@dataclass(slots=True, frozen=True)
class WikidataHeritage:
    """One parsed Wikidata item ready for ``heritage_importer``."""

    qid: str
    names: dict[str, str]  # {"en": "...", "uz": "...", ...}
    aliases: tuple[tuple[str, str], ...] = ()  # ((lang, text), ...)
    description: dict[str, str] = field(default_factory=dict)
    country_code: str | None = None
    instance_of: tuple[str, ...] = ()  # P31 q-ids
    latitude: float | None = None
    longitude: float | None = None
    inception_year: int | None = None
    image_url: str | None = None
    wikipedia_urls: dict[str, str] = field(default_factory=dict)


# --- Query template -------------------------------------------------------


def build_country_query(country_code: str, limit: int = 50) -> str:
    """Build the SPARQL query for heritage items in ``country_code``."""
    cc = country_code.upper()
    country_q = _COUNTRY_Q.get(cc)
    if country_q is None:
        country_filter = f'?country wdt:P297 ?cc . FILTER(UCASE(?cc) = "{cc}") '
    else:
        country_filter = f"BIND(wd:{country_q} AS ?country)"

    instance_values = " ".join(f"wd:{q}" for q in HERITAGE_INSTANCE_OF)
    safe_limit = max(1, min(int(limit), 500))

    return f"""
        SELECT DISTINCT ?item ?itemLabel ?itemDescription
                        ?country ?countryCode
                        ?coord ?inception ?image
                        (GROUP_CONCAT(DISTINCT ?instance; separator="|") AS ?instances)
        WHERE {{
          VALUES ?heritageType {{ {instance_values} }}
          ?item wdt:P31/wdt:P279* ?heritageType .
          ?item wdt:P17 ?country .
          {country_filter}
          OPTIONAL {{ ?country wdt:P297 ?countryCode }} .
          OPTIONAL {{ ?item wdt:P625 ?coord }} .
          OPTIONAL {{ ?item wdt:P571 ?inception }} .
          OPTIONAL {{ ?item wdt:P18 ?image }} .
          ?item wdt:P31 ?instance .
          SERVICE wikibase:label {{
            bd:serviceParam wikibase:language "en,uz,ru,zh" .
          }}
        }}
        GROUP BY ?item ?itemLabel ?itemDescription ?country ?countryCode ?coord ?inception ?image
        LIMIT {safe_limit}
    """


# --- Response parser ------------------------------------------------------


def _qid_from_uri(uri: str) -> str:
    return uri.rsplit("/", 1)[-1]


def _parse_point(raw: str) -> tuple[float, float] | None:
    # WDQS coord literal: "Point(longitude latitude)"
    if not raw.startswith("Point(") or not raw.endswith(")"):
        return None
    inner = raw[len("Point(") : -1].strip()
    parts = inner.split()
    if len(parts) != 2:
        return None
    try:
        lng = float(parts[0])
        lat = float(parts[1])
    except ValueError:
        return None
    return lat, lng


def _parse_year(raw: str | None) -> int | None:
    if not raw:
        return None
    # WDQS dates: "1417-01-01T00:00:00Z" or "-0540-01-01T00:00:00Z"
    try:
        if raw.startswith("-"):
            return -int(raw[1:5])
        return int(raw[:4])
    except (ValueError, IndexError):
        return None


def parse_sparql_response(
    body: dict[str, Any], country_code: str | None = None
) -> list[WikidataHeritage]:
    """Parse a WDQS JSON response into our ``WikidataHeritage`` tuples.

    The function is pure (no IO) so unit tests can drive it directly.
    """
    bindings = body.get("results", {}).get("bindings", [])
    out: list[WikidataHeritage] = []
    for row in bindings:
        item_uri = row.get("item", {}).get("value", "")
        if not item_uri:
            continue
        qid = _qid_from_uri(item_uri)
        label = row.get("itemLabel", {}).get("value", "") or ""
        description = row.get("itemDescription", {}).get("value", "") or ""
        cc = (row.get("countryCode", {}).get("value") or country_code or "").upper() or None
        coord_raw = row.get("coord", {}).get("value")
        lat = lng = None
        if coord_raw:
            point = _parse_point(coord_raw)
            if point:
                lat, lng = point
        inception_year = _parse_year(row.get("inception", {}).get("value"))
        # SEC-W56-005 fix: allowlist image URLs to Wikimedia Commons only.
        # Wikidata P18 values are crowd-edited; an arbitrary URL here would
        # become an SSRF vector if a downstream pipeline fetches it.
        _raw_img = row.get("image", {}).get("value") or None
        _allowed = ("https://commons.wikimedia.org/", "https://upload.wikimedia.org/")
        image_url = _raw_img if _raw_img and _raw_img.startswith(_allowed) else None
        instances_raw = row.get("instances", {}).get("value", "")
        instance_qids = tuple(_qid_from_uri(u) for u in instances_raw.split("|") if u)

        out.append(
            WikidataHeritage(
                qid=qid,
                names={"en": label} if label else {},
                description={"en": description} if description else {},
                country_code=cc,
                instance_of=instance_qids,
                latitude=lat,
                longitude=lng,
                inception_year=inception_year,
                image_url=image_url,
            )
        )
    return out


# --- Client ---------------------------------------------------------------


class WikidataClient:
    """Async WDQS client with a 1 req/sec rate limit and exponential backoff."""

    def __init__(
        self,
        *,
        endpoint: str = WDQS_ENDPOINT,
        min_interval_seconds: float = 1.0,
        max_retries: int = 3,
        timeout_seconds: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._endpoint = endpoint
        self._min_interval = min_interval_seconds
        self._max_retries = max_retries
        self._timeout = timeout_seconds
        self._owned_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=timeout_seconds,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/sparql-results+json",
            },
        )
        self._last_call_at = 0.0
        self._lock = asyncio.Lock()

    async def close(self) -> None:
        if self._owned_client:
            await self._client.aclose()

    async def _wait_for_slot(self) -> None:
        async with self._lock:
            now = time.monotonic()
            wait = self._min_interval - (now - self._last_call_at)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_call_at = time.monotonic()

    async def run_sparql(self, query: str) -> dict[str, Any]:
        last_exc: Exception | None = None
        for attempt in range(self._max_retries):
            await self._wait_for_slot()
            try:
                response = await self._client.get(
                    self._endpoint,
                    params={"query": query, "format": "json"},
                )
                if response.status_code == 429:
                    # Honour Retry-After if provided; else exponential backoff.
                    retry_after = response.headers.get("retry-after")
                    delay = float(retry_after) if retry_after else 2.0**attempt
                    log.warning("wikidata.rate_limited", delay=delay)
                    await asyncio.sleep(delay)
                    continue
                response.raise_for_status()
                return dict(response.json())
            except httpx.HTTPError as exc:
                last_exc = exc
                delay = 2.0**attempt
                log.warning("wikidata.retry", error=str(exc), attempt=attempt, delay=delay)
                await asyncio.sleep(delay)
        raise RuntimeError(
            f"wikidata SPARQL failed after {self._max_retries} attempts"
        ) from last_exc

    async def heritage_for_country(
        self, country_code: str, limit: int = 50
    ) -> list[WikidataHeritage]:
        query = build_country_query(country_code, limit=limit)
        body = await self.run_sparql(query)
        return parse_sparql_response(body, country_code=country_code)

    async def fetch_qid(self, qid: str) -> WikidataHeritage | None:
        """Fetch a single entity by Q-id (used by the qid admin endpoint)."""
        safe = qid.strip()
        if not safe.startswith("Q") or not safe[1:].isdigit():
            raise ValueError(f"invalid Wikidata QID: {qid!r}")
        query = f"""
            SELECT ?item ?itemLabel ?itemDescription
                   ?country ?countryCode ?coord ?inception ?image
                   (GROUP_CONCAT(DISTINCT ?instance; separator="|") AS ?instances)
            WHERE {{
              BIND(wd:{safe} AS ?item)
              OPTIONAL {{ ?item wdt:P17 ?country }} .
              OPTIONAL {{ ?country wdt:P297 ?countryCode }} .
              OPTIONAL {{ ?item wdt:P625 ?coord }} .
              OPTIONAL {{ ?item wdt:P571 ?inception }} .
              OPTIONAL {{ ?item wdt:P18 ?image }} .
              OPTIONAL {{ ?item wdt:P31 ?instance }} .
              SERVICE wikibase:label {{
                bd:serviceParam wikibase:language "en,uz,ru,zh"
              }}
            }}
            GROUP BY ?item ?itemLabel ?itemDescription ?country ?countryCode
                     ?coord ?inception ?image
        """
        body = await self.run_sparql(query)
        items: Iterable[WikidataHeritage] = parse_sparql_response(body)
        for item in items:
            return item
        return None
