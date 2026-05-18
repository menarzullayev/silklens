"""Wave-6 Agent A — Central Asia heritage seed integration tests.

Asserts the FAZA 5 Central Asia starter set lands as expected:
- ≥ 30 KZ, ≥ 25 TJ, ≥ 20 TM, ≥ 20 KG heritage rows (the migration ships exactly
  these counts; ≥ matches future re-runs after Wikidata ingestion top-ups).
- ≥ 9 UNESCO inscriptions across the four countries (at least 1 per country).
- ≥ 20 Central Asia cities seeded (KZ:7 + TJ:5 + TM:6 + KG:4 = 22).
- KZT, TJS, TMT, KGS currencies present.
- ``central_asia`` pricing zone with PPP 0.42 covering UZ/KZ/KG/TJ/TM.
- Premium monthly priced at $1.99 USD against the central_asia zone.
- API list filter by country returns expected counts.

These are integration tests against the live test Postgres (port 5434 /
``silklens_test``). They skip cleanly when Docker is unreachable.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.integration


async def _scalar(session: AsyncSession, sql: str, **params: object) -> object:
    result = await session.execute(text(sql), params)
    return result.scalar()


# --- Heritage counts per country ---------------------------------------------


@pytest.mark.asyncio
async def test_kazakhstan_heritage_count(db_session: AsyncSession) -> None:
    count = await _scalar(
        db_session,
        """
        SELECT count(*) FROM heritage_objects
        WHERE country_code = 'KZ' AND deleted_at IS NULL
          AND pub_id LIKE 'kz-%'
        """,
    )
    assert count is not None
    assert int(count) >= 30, f"Expected >= 30 KZ heritage, got {count}"


@pytest.mark.asyncio
async def test_tajikistan_heritage_count(db_session: AsyncSession) -> None:
    count = await _scalar(
        db_session,
        """
        SELECT count(*) FROM heritage_objects
        WHERE country_code = 'TJ' AND deleted_at IS NULL
          AND pub_id LIKE 'tj-%'
        """,
    )
    assert count is not None
    assert int(count) >= 25, f"Expected >= 25 TJ heritage, got {count}"


@pytest.mark.asyncio
async def test_turkmenistan_heritage_count(db_session: AsyncSession) -> None:
    count = await _scalar(
        db_session,
        """
        SELECT count(*) FROM heritage_objects
        WHERE country_code = 'TM' AND deleted_at IS NULL
          AND pub_id LIKE 'tm-%'
        """,
    )
    assert count is not None
    assert int(count) >= 20, f"Expected >= 20 TM heritage, got {count}"


@pytest.mark.asyncio
async def test_kyrgyzstan_heritage_count(db_session: AsyncSession) -> None:
    count = await _scalar(
        db_session,
        """
        SELECT count(*) FROM heritage_objects
        WHERE country_code = 'KG' AND deleted_at IS NULL
          AND pub_id LIKE 'kg-%'
        """,
    )
    assert count is not None
    assert int(count) >= 20, f"Expected >= 20 KG heritage, got {count}"


# --- UNESCO inscriptions -----------------------------------------------------


@pytest.mark.asyncio
async def test_unesco_inscriptions_central_asia(db_session: AsyncSession) -> None:
    """At least one UNESCO inscription per country, with ≥ 9 total tied to the
    Wave-6 Agent A seed (KZ:3, TJ:2, TM:3, KG:1)."""
    rows = (
        await db_session.execute(
            text(
                """
                SELECT ho.country_code, count(*)
                FROM unesco_inscriptions ui
                JOIN heritage_objects ho ON ho.id = ui.heritage_id
                WHERE ui.deleted_at IS NULL
                  AND ho.country_code IN ('KZ','TJ','TM','KG')
                  AND (
                    ho.pub_id LIKE 'kz-%' OR ho.pub_id LIKE 'tj-%'
                    OR ho.pub_id LIKE 'tm-%' OR ho.pub_id LIKE 'kg-%'
                  )
                GROUP BY ho.country_code
                ORDER BY ho.country_code
                """
            )
        )
    ).all()
    by_cc = {row[0]: int(row[1]) for row in rows}
    assert set(by_cc) == {"KZ", "TJ", "TM", "KG"}, f"Missing UNESCO countries: {by_cc}"
    assert sum(by_cc.values()) >= 9, f"Expected >= 9 UNESCO total, got {by_cc}"
    for cc, n in by_cc.items():
        assert n >= 1, f"{cc} has zero UNESCO inscriptions"


# --- Cities ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_central_asia_cities_seeded(db_session: AsyncSession) -> None:
    count = await _scalar(
        db_session,
        """
        SELECT count(*) FROM cities
        WHERE country_code IN ('KZ','TJ','TM','KG')
          AND deleted_at IS NULL
        """,
    )
    assert count is not None
    assert int(count) >= 20, f"Expected >= 20 CA cities, got {count}"


# --- API filter --------------------------------------------------------------


@pytest.mark.asyncio
async def test_kazakhstan_heritage_filter_via_api(http) -> None:
    """GET /v1/heritage?country=KZ must surface the Wave-6 Agent A KZ seed.

    Page through results since list endpoints cap ``limit`` at 100; we need at
    least 30 KZ entries to land in the API."""
    resp = await http.get("/v1/heritage", params={"country": "KZ", "limit": 100})
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    items = payload.get("items") if isinstance(payload, dict) else payload
    assert isinstance(items, list)
    kz_only = [it for it in items if (it.get("country_code") or "").upper() == "KZ"]
    total = payload.get("total") if isinstance(payload, dict) else None
    assert total is None or int(total) >= 30, (
        f"Expected total >= 30 KZ items in API, got total={total}"
    )
    assert len(kz_only) >= 30, f"Expected >= 30 KZ items in API page, got {len(kz_only)}"


# --- Currencies / pricing zone ------------------------------------------------


@pytest.mark.asyncio
async def test_central_asia_currencies_present(db_session: AsyncSession) -> None:
    rows = (
        await db_session.execute(
            text(
                """
                SELECT code FROM currencies
                WHERE code IN ('KZT','TJS','TMT','KGS')
                ORDER BY code
                """
            )
        )
    ).all()
    codes = {row[0] for row in rows}
    assert codes == {"KZT", "TJS", "TMT", "KGS"}, f"Missing: {codes}"


@pytest.mark.asyncio
async def test_central_asia_pricing_zone(db_session: AsyncSession) -> None:
    row = (
        await db_session.execute(
            text(
                """
                SELECT slug, country_codes, default_currency, purchasing_power_index
                FROM pricing_zones
                WHERE slug = 'central_asia'
                """
            )
        )
    ).first()
    assert row is not None, "central_asia pricing zone missing"
    slug, country_codes, default_currency, ppp = row
    assert slug == "central_asia"
    assert default_currency == "USD"
    assert float(ppp) == 0.42
    assert set(country_codes) == {"UZ", "KZ", "KG", "TJ", "TM"}


@pytest.mark.asyncio
async def test_premium_monthly_price_central_asia(db_session: AsyncSession) -> None:
    amount = await _scalar(
        db_session,
        """
        SELECT p.amount
        FROM prices p
        JOIN product_plans pp ON pp.id = p.plan_id
        JOIN pricing_zones pz ON pz.id = p.pricing_zone_id
        WHERE pp.slug = 'premium_monthly'
          AND pz.slug = 'central_asia'
          AND p.currency = 'USD'
          AND p.is_active
        """,
    )
    assert amount is not None, "No central_asia premium_monthly price row"
    assert float(amount) == 1.99, f"Expected $1.99, got {amount}"


@pytest.mark.asyncio
async def test_premium_yearly_price_central_asia(db_session: AsyncSession) -> None:
    amount = await _scalar(
        db_session,
        """
        SELECT p.amount
        FROM prices p
        JOIN product_plans pp ON pp.id = p.plan_id
        JOIN pricing_zones pz ON pz.id = p.pricing_zone_id
        WHERE pp.slug = 'premium_yearly'
          AND pz.slug = 'central_asia'
          AND p.currency = 'USD'
          AND p.is_active
        """,
    )
    assert amount is not None, "No central_asia premium_yearly price row"
    assert float(amount) == 19.99, f"Expected $19.99, got {amount}"


# --- Provenance facts wired up -----------------------------------------------


@pytest.mark.asyncio
async def test_unesco_provenance_facts(db_session: AsyncSession) -> None:
    """Every Wave-6 UNESCO seed has a winning heritage_facts row tied to the
    unesco_whc provenance entry."""
    count = await _scalar(
        db_session,
        """
        SELECT count(*)
        FROM heritage_facts hf
        JOIN heritage_objects ho ON ho.id = hf.heritage_id
        JOIN fact_provenance fp ON fp.fact_id = hf.id
        JOIN heritage_provenance hp ON hp.id = fp.provenance_id
        WHERE hf.predicate = 'unesco_inscription_year'
          AND hf.is_winning
          AND hf.superseded_at IS NULL
          AND hp.slug = 'unesco_whc'
          AND (
            ho.pub_id LIKE 'kz-%' OR ho.pub_id LIKE 'tj-%'
            OR ho.pub_id LIKE 'tm-%' OR ho.pub_id LIKE 'kg-%'
          )
        """,
    )
    assert count is not None
    assert int(count) >= 9, f"Expected >= 9 UNESCO provenance facts, got {count}"
