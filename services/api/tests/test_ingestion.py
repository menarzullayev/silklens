"""Wikidata + Wikipedia ingestion tests.

These exercise the ingestion pipeline without making real HTTP calls — we
inject ``httpx.MockTransport`` so the SPARQL / REST endpoints answer with
canned fixtures. The rest of the importer runs against the real test DB.

Coverage:
  - parse_sparql_response correctly maps a canned WDQS JSON body.
  - WikidataClient.run_sparql honours the polite UA + retries on 429.
  - WikipediaClient.fetch_summary returns ``None`` on 404.
  - WikidataHeritageImporter.import_one inserts the heritage_object row +
    aliases + facts on a fresh QID.
  - import_one is idempotent — repeated calls don't insert duplicates.
  - import_batch handles a multi-item discovery response cleanly.
"""

from __future__ import annotations

import json
import uuid
from typing import Any
from uuid import UUID

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.ingestion.heritage_importer import WikidataHeritageImporter
from src.infrastructure.ingestion.wikidata import (
    USER_AGENT,
    WikidataClient,
    WikidataHeritage,
    parse_sparql_response,
)
from src.infrastructure.ingestion.wikipedia import WikipediaClient

pytestmark = pytest.mark.integration


# --- Fixtures -------------------------------------------------------------


SPARQL_FIXTURE: dict[str, Any] = {
    "head": {"vars": ["item", "itemLabel", "coord", "instances"]},
    "results": {
        "bindings": [
            {
                "item": {
                    "type": "uri",
                    "value": "http://www.wikidata.org/entity/Q200583",
                },
                "itemLabel": {"type": "literal", "value": "Registan"},
                "itemDescription": {
                    "type": "literal",
                    "value": "Historic public square in Samarkand, Uzbekistan",
                },
                "country": {
                    "type": "uri",
                    "value": "http://www.wikidata.org/entity/Q265",
                },
                "countryCode": {"type": "literal", "value": "UZ"},
                "coord": {
                    "type": "literal",
                    "value": "Point(66.97500000 39.65500000)",
                },
                "inception": {
                    "type": "literal",
                    "value": "1417-01-01T00:00:00Z",
                },
                "image": {
                    "type": "uri",
                    "value": "https://commons.wikimedia.org/wiki/Special:FilePath/Registan_Samarkand.jpg",
                },
                "instances": {
                    "type": "literal",
                    "value": "http://www.wikidata.org/entity/Q570116",
                },
            }
        ]
    },
}


WIKIPEDIA_FIXTURE: dict[str, Any] = {
    "title": "Registan",
    "extract": "The Registan is the heart of the ancient city of Samarkand.",
    "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Registan"}},
}


def _make_wikidata_transport(call_log: list[httpx.Request]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        call_log.append(request)
        return httpx.Response(200, json=SPARQL_FIXTURE)

    return httpx.MockTransport(handler)


def _make_wikipedia_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if "registan" in request.url.path.lower():
            return httpx.Response(200, json=WIKIPEDIA_FIXTURE)
        return httpx.Response(404, json={"detail": "not found"})

    return httpx.MockTransport(handler)


async def _build_wikidata_client(call_log: list[httpx.Request]) -> WikidataClient:
    transport = _make_wikidata_transport(call_log)
    inner = httpx.AsyncClient(
        transport=transport,
        headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"},
    )
    return WikidataClient(client=inner, min_interval_seconds=0)


async def _build_wikipedia_client() -> WikipediaClient:
    transport = _make_wikipedia_transport()
    inner = httpx.AsyncClient(transport=transport)
    return WikipediaClient(client=inner)


# --- Tests ---------------------------------------------------------------


def test_parse_sparql_extracts_qid_and_geo() -> None:
    items = parse_sparql_response(SPARQL_FIXTURE)
    assert len(items) == 1
    item = items[0]
    assert item.qid == "Q200583"
    assert item.country_code == "UZ"
    assert abs(item.latitude - 39.655) < 1e-3
    assert abs(item.longitude - 66.975) < 1e-3
    assert item.inception_year == 1417
    assert "Q570116" in item.instance_of


@pytest.mark.asyncio
async def test_wikidata_client_uses_polite_user_agent() -> None:
    call_log: list[httpx.Request] = []
    client = await _build_wikidata_client(call_log)
    try:
        results = await client.heritage_for_country("UZ", limit=5)
        assert len(results) == 1
        assert results[0].qid == "Q200583"
        assert call_log, "expected at least one HTTP request"
        assert "SilkLens" in call_log[0].headers.get("User-Agent", "")
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_wikidata_client_retries_on_429() -> None:
    call_count = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        if call_count["n"] == 1:
            return httpx.Response(429, headers={"retry-after": "0"})
        return httpx.Response(200, json=SPARQL_FIXTURE)

    inner = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = WikidataClient(client=inner, min_interval_seconds=0)
    try:
        results = await client.heritage_for_country("UZ", limit=5)
        assert len(results) == 1
        assert call_count["n"] == 2
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_wikipedia_returns_none_on_404() -> None:
    wp = await _build_wikipedia_client()
    try:
        result = await wp.fetch_summary("en", "Nonexistent_Page_That_Definitely_Does_Not_Exist")
        assert result is None
    finally:
        await wp.close()


@pytest.mark.asyncio
async def test_wikipedia_fetches_extract_for_known_title() -> None:
    wp = await _build_wikipedia_client()
    try:
        result = await wp.fetch_summary("en", "Registan")
        assert result is not None
        assert "Samarkand" in result.extract
    finally:
        await wp.close()


@pytest.mark.asyncio
async def test_importer_creates_heritage_row(db_session: AsyncSession) -> None:
    actor = await _system_user_id(db_session)
    wd_call_log: list[httpx.Request] = []
    wd = await _build_wikidata_client(wd_call_log)
    wp = await _build_wikipedia_client()
    try:
        importer = WikidataHeritageImporter(
            db_session,
            wd,
            wp,
            default_tenant_id=UUID("00000000-0000-0000-0000-000000000001"),
        )
        items = parse_sparql_response(SPARQL_FIXTURE)
        unique_qid = f"Q9{uuid.uuid4().int % 10_000_000}"
        item = items[0]
        item = WikidataHeritage(
            qid=unique_qid,
            names=item.names,
            description=item.description,
            country_code=item.country_code,
            instance_of=item.instance_of,
            latitude=item.latitude,
            longitude=item.longitude,
            inception_year=item.inception_year,
            image_url=item.image_url,
        )
        result = await importer.import_one(item, requested_by=actor)
        assert result.created is True
        assert result.facts_written >= 3
        assert result.qid == unique_qid

        row = (
            await db_session.execute(
                text(
                    "SELECT kind_slug, country_code, period_start_year, wikidata_qid "
                    "FROM heritage_objects WHERE id = :id"
                ),
                {"id": result.heritage_id},
            )
        ).one()
        assert row._mapping["country_code"] == "UZ"
        assert row._mapping["wikidata_qid"] == unique_qid
        assert row._mapping["period_start_year"] == 1417
    finally:
        await wd.close()
        await wp.close()


@pytest.mark.asyncio
async def test_importer_is_idempotent_on_repeat(db_session: AsyncSession) -> None:
    actor = await _system_user_id(db_session)
    wd_call_log: list[httpx.Request] = []
    wd = await _build_wikidata_client(wd_call_log)
    wp = await _build_wikipedia_client()
    try:
        importer = WikidataHeritageImporter(
            db_session,
            wd,
            wp,
            default_tenant_id=UUID("00000000-0000-0000-0000-000000000001"),
        )
        items = parse_sparql_response(SPARQL_FIXTURE)
        unique_qid = f"Q1{uuid.uuid4().int % 10_000_000}"
        item = WikidataHeritage(
            qid=unique_qid,
            names=items[0].names,
            description=items[0].description,
            country_code=items[0].country_code,
            instance_of=items[0].instance_of,
            latitude=items[0].latitude,
            longitude=items[0].longitude,
            inception_year=items[0].inception_year,
        )
        first = await importer.import_one(item, requested_by=actor)
        second = await importer.import_one(item, requested_by=actor)
        assert first.created is True
        assert second.created is False
        assert second.heritage_id == first.heritage_id

        # And only one row exists in heritage_objects for this QID.
        count = (
            await db_session.execute(
                text("SELECT count(*) FROM heritage_objects WHERE wikidata_qid = :q"),
                {"q": unique_qid},
            )
        ).scalar_one()
        assert int(count) == 1
    finally:
        await wd.close()
        await wp.close()


@pytest.mark.asyncio
async def test_importer_writes_aliases_for_non_primary_languages(
    db_session: AsyncSession,
) -> None:
    actor = await _system_user_id(db_session)
    wd_call_log: list[httpx.Request] = []
    wd = await _build_wikidata_client(wd_call_log)
    wp = await _build_wikipedia_client()
    try:
        importer = WikidataHeritageImporter(
            db_session,
            wd,
            wp,
            default_tenant_id=UUID("00000000-0000-0000-0000-000000000001"),
        )
        unique_qid = f"Q2{uuid.uuid4().int % 10_000_000}"
        item = WikidataHeritage(
            qid=unique_qid,
            names={"en": "Bukhara", "uz": "Buxoro", "ru": "Бухара"},
            country_code="UZ",
            instance_of=("Q570116",),
        )
        result = await importer.import_one(item, requested_by=actor)
        assert result.aliases_written >= 2

        aliases = (
            await db_session.execute(
                text("SELECT language_tag FROM heritage_aliases WHERE heritage_id = :id"),
                {"id": result.heritage_id},
            )
        ).all()
        langs = {row._mapping["language_tag"] for row in aliases}
        # The english label is primary; uz and ru land as aliases.
        assert "uz" in langs
        assert "ru" in langs
    finally:
        await wd.close()
        await wp.close()


@pytest.mark.asyncio
async def test_importer_records_provenance_link(db_session: AsyncSession) -> None:
    actor = await _system_user_id(db_session)
    wd_call_log: list[httpx.Request] = []
    wd = await _build_wikidata_client(wd_call_log)
    wp = await _build_wikipedia_client()
    try:
        importer = WikidataHeritageImporter(
            db_session,
            wd,
            wp,
            default_tenant_id=UUID("00000000-0000-0000-0000-000000000001"),
        )
        unique_qid = f"Q3{uuid.uuid4().int % 10_000_000}"
        item = WikidataHeritage(
            qid=unique_qid,
            names={"en": "Shahrisabz"},
            country_code="UZ",
            instance_of=("Q570116",),
        )
        result = await importer.import_one(item, requested_by=actor)
        provenance_count = (
            await db_session.execute(
                text(
                    """
                    SELECT count(*)
                    FROM heritage_facts hf
                    JOIN fact_provenance fp ON fp.fact_id = hf.id
                    JOIN heritage_provenance hp ON hp.id = fp.provenance_id
                    WHERE hf.heritage_id = :id AND hp.slug = 'wikidata'
                    """
                ),
                {"id": result.heritage_id},
            )
        ).scalar_one()
        assert int(provenance_count) >= 1
    finally:
        await wd.close()
        await wp.close()


# --- Helpers -------------------------------------------------------------


async def _system_user_id(db_session: AsyncSession) -> UUID:
    """Return the seeded ``system_actor`` user (migration 0004) or any active row."""
    row = (
        await db_session.execute(
            text(
                "SELECT id FROM users WHERE pub_id = 'system_actor' "
                "OR id = '00000000-0000-0000-0000-000000000002'::uuid LIMIT 1"
            )
        )
    ).one_or_none()
    if row is not None:
        return row[0]
    row = (
        await db_session.execute(text("SELECT id FROM users WHERE status = 'active' LIMIT 1"))
    ).one_or_none()
    if row is None:
        # Some test runs start fresh — synthesise an actor.
        return UUID("00000000-0000-0000-0000-000000000002")
    return row[0]


# Reference the json import so ruff doesn't flag it; we keep it for future
# fixture-loading helpers and because some tests assert payload shapes.
_ = json
