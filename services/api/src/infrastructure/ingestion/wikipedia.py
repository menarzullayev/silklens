"""Async Wikipedia REST client for lead-section extracts.

Endpoint: ``https://<lang>.wikipedia.org/api/rest_v1/page/summary/<title>``.

Per-language hostnames are tried in priority order; the first one that
returns a 200 with ``extract`` is taken as authoritative for that language.
"""

from __future__ import annotations

import urllib.parse
from collections.abc import Iterable
from dataclasses import dataclass

import httpx

from src.core.logging import get_logger

log = get_logger("silklens.ingestion.wikipedia")

DEFAULT_LANGS: tuple[str, ...] = ("en", "uz", "ru", "zh")

USER_AGENT = (
    "SilkLens/0.1 (https://silklens.com; contact@silklens.com) wikipedia-ingestion +python-httpx"
)


@dataclass(slots=True, frozen=True)
class WikipediaSummary:
    language_tag: str
    title: str
    extract: str
    url: str


class WikipediaClient:
    """Fetch lead summaries from per-language Wikipedia endpoints."""

    def __init__(
        self,
        *,
        timeout_seconds: float = 15.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._owned_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=timeout_seconds,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            },
        )

    async def close(self) -> None:
        if self._owned_client:
            await self._client.aclose()

    async def fetch_summary(self, language_tag: str, title: str) -> WikipediaSummary | None:
        slug = urllib.parse.quote(title.replace(" ", "_"), safe="")
        url = f"https://{language_tag}.wikipedia.org/api/rest_v1/page/summary/{slug}"
        try:
            response = await self._client.get(url)
        except httpx.HTTPError as exc:
            log.warning("wikipedia.network_error", lang=language_tag, error=str(exc))
            return None
        if response.status_code != 200:
            return None
        try:
            payload = response.json()
        except ValueError:
            return None
        extract = payload.get("extract") or ""
        if not extract:
            return None
        canonical = payload.get("content_urls", {}).get("desktop", {}).get("page") or url
        return WikipediaSummary(
            language_tag=language_tag,
            title=payload.get("title", title),
            extract=extract,
            url=canonical,
        )

    async def fetch_many(
        self, titles_by_lang: dict[str, str], languages: Iterable[str] | None = None
    ) -> dict[str, WikipediaSummary]:
        """Fetch summaries for a name-per-language map.

        Returns a dict keyed by language_tag, containing only successful hits.
        """
        wanted = list(languages or DEFAULT_LANGS)
        out: dict[str, WikipediaSummary] = {}
        for lang in wanted:
            title = titles_by_lang.get(lang)
            if not title:
                continue
            summary = await self.fetch_summary(lang, title)
            if summary is not None:
                out[lang] = summary
        return out
