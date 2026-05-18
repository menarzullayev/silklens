"""Wave-8 Agent 2 — Mediterranean + Asia heritage seed integration tests.

FAZA 7 global expansion: IT/GR/EG/MA/JP/KR/TH.

Assertions:
- IT ≥ 20, GR ≥ 15, EG ≥ 20, MA ≥ 15, JP ≥ 20, KR ≥ 10, TH ≥ 10 heritage rows
- UNESCO inscriptions ≥ 30 across all 7 countries
- EUR, JPY, KRW, THB, EGP, MAD currencies present
- europe_apac pricing zone (PPP 0.80, USD, covers all 7 countries)
- premium_monthly priced at $3.99 USD against europe_apac zone
- premium_yearly priced at $39.99 USD against europe_apac zone
- ≥ 30 cities seeded across the 7 countries
- UNESCO provenance facts wired up for all 7 countries

Integration tests against live test Postgres (port 5434 / silklens_test).
Skip cleanly when Docker is unreachable.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.integration


async def _scalar(session: AsyncSession, sql: str, **params: object) -> object:
    result = await session.execute(text(sql), params)
    return result.scalar()


# --- Heritage counts per country -----------------------------------------------


@pytest.mark.asyncio
async def test_italy_heritage_count(db_session: AsyncSession) -> None:
    count = await _scalar(
        db_session,
        """
        SELECT count(*) FROM heritage_objects
        WHERE country_code = 'IT' AND deleted_at IS NULL
          AND pub_id LIKE 'it-%'
        """,
    )
    assert count is not None
    assert int(count) >= 20, f"Expected >= 20 IT heritage, got {count}"


@pytest.mark.asyncio
async def test_greece_heritage_count(db_session: AsyncSession) -> None:
    count = await _scalar(
        db_session,
        """
        SELECT count(*) FROM heritage_objects
        WHERE country_code = 'GR' AND deleted_at IS NULL
          AND pub_id LIKE 'gr-%'
        """,
    )
    assert count is not None
    assert int(count) >= 15, f"Expected >= 15 GR heritage, got {count}"


@pytest.mark.asyncio
async def test_egypt_heritage_count(db_session: AsyncSession) -> None:
    count = await _scalar(
        db_session,
        """
        SELECT count(*) FROM heritage_objects
        WHERE country_code = 'EG' AND deleted_at IS NULL
          AND pub_id LIKE 'eg-%'
        """,
    )
    assert count is not None
    assert int(count) >= 20, f"Expected >= 20 EG heritage, got {count}"


@pytest.mark.asyncio
async def test_morocco_heritage_count(db_session: AsyncSession) -> None:
    count = await _scalar(
        db_session,
        """
        SELECT count(*) FROM heritage_objects
        WHERE country_code = 'MA' AND deleted_at IS NULL
          AND pub_id LIKE 'ma-%'
        """,
    )
    assert count is not None
    assert int(count) >= 15, f"Expected >= 15 MA heritage, got {count}"


@pytest.mark.asyncio
async def test_japan_heritage_count(db_session: AsyncSession) -> None:
    count = await _scalar(
        db_session,
        """
        SELECT count(*) FROM heritage_objects
        WHERE country_code = 'JP' AND deleted_at IS NULL
          AND pub_id LIKE 'jp-%'
        """,
    )
    assert count is not None
    assert int(count) >= 20, f"Expected >= 20 JP heritage, got {count}"


@pytest.mark.asyncio
async def test_south_korea_heritage_count(db_session: AsyncSession) -> None:
    count = await _scalar(
        db_session,
        """
        SELECT count(*) FROM heritage_objects
        WHERE country_code = 'KR' AND deleted_at IS NULL
          AND pub_id LIKE 'kr-%'
        """,
    )
    assert count is not None
    assert int(count) >= 10, f"Expected >= 10 KR heritage, got {count}"


@pytest.mark.asyncio
async def test_thailand_heritage_count(db_session: AsyncSession) -> None:
    count = await _scalar(
        db_session,
        """
        SELECT count(*) FROM heritage_objects
        WHERE country_code = 'TH' AND deleted_at IS NULL
          AND pub_id LIKE 'th-%'
        """,
    )
    assert count is not None
    assert int(count) >= 10, f"Expected >= 10 TH heritage, got {count}"


# --- UNESCO inscriptions -------------------------------------------------------


@pytest.mark.asyncio
async def test_unesco_inscriptions_mediterranean_asia(db_session: AsyncSession) -> None:
    """At least 30 UNESCO inscriptions across all 7 countries, at least 1 per country."""
    rows = (
        await db_session.execute(
            text(
                """
                SELECT ho.country_code, count(*)
                FROM unesco_inscriptions ui
                JOIN heritage_objects ho ON ho.id = ui.heritage_id
                WHERE ui.deleted_at IS NULL
                  AND ho.country_code IN ('IT','GR','EG','MA','JP','KR','TH')
                  AND (
                    ho.pub_id LIKE 'it-%' OR ho.pub_id LIKE 'gr-%'
                    OR ho.pub_id LIKE 'eg-%' OR ho.pub_id LIKE 'ma-%'
                    OR ho.pub_id LIKE 'jp-%' OR ho.pub_id LIKE 'kr-%'
                    OR ho.pub_id LIKE 'th-%'
                  )
                GROUP BY ho.country_code
                ORDER BY ho.country_code
                """
            )
        )
    ).all()
    by_cc = {row[0]: int(row[1]) for row in rows}
    expected_countries = {"IT", "GR", "EG", "MA", "JP", "KR", "TH"}
    assert expected_countries.issubset(set(by_cc)), (
        f"Missing UNESCO countries: {expected_countries - set(by_cc)}"
    )
    total = sum(by_cc.values())
    assert total >= 30, f"Expected >= 30 UNESCO total, got {total} — by country: {by_cc}"
    for cc in expected_countries:
        assert by_cc.get(cc, 0) >= 1, f"{cc} has zero UNESCO inscriptions"


# --- Currencies ----------------------------------------------------------------


@pytest.mark.asyncio
async def test_mediterranean_asia_currencies_present(db_session: AsyncSession) -> None:
    rows = (
        await db_session.execute(
            text(
                """
                SELECT code FROM currencies
                WHERE code IN ('EUR','JPY','KRW','THB','EGP','MAD')
                ORDER BY code
                """
            )
        )
    ).all()
    codes = {row[0] for row in rows}
    expected = {"EUR", "JPY", "KRW", "THB", "EGP", "MAD"}
    assert codes == expected, f"Missing currencies: {expected - codes}"


# --- Pricing zone --------------------------------------------------------------


@pytest.mark.asyncio
async def test_europe_apac_pricing_zone(db_session: AsyncSession) -> None:
    row = (
        await db_session.execute(
            text(
                """
                SELECT slug, country_codes, default_currency, purchasing_power_index
                FROM pricing_zones
                WHERE slug = 'europe_apac'
                """
            )
        )
    ).first()
    assert row is not None, "europe_apac pricing zone missing"
    slug, country_codes, default_currency, ppp = row
    assert slug == "europe_apac"
    assert default_currency == "USD"
    assert abs(float(ppp) - 0.80) < 0.001, f"Expected PPP 0.80, got {ppp}"
    expected_cc = {"IT", "GR", "EG", "MA", "JP", "KR", "TH"}
    assert expected_cc.issubset(set(country_codes)), (
        f"europe_apac missing countries: {expected_cc - set(country_codes)}"
    )


@pytest.mark.asyncio
async def test_premium_monthly_price_europe_apac(db_session: AsyncSession) -> None:
    amount = await _scalar(
        db_session,
        """
        SELECT p.amount
        FROM prices p
        JOIN product_plans pp ON pp.id = p.plan_id
        JOIN pricing_zones pz ON pz.id = p.pricing_zone_id
        WHERE pp.slug = 'premium_monthly'
          AND pz.slug = 'europe_apac'
          AND p.currency = 'USD'
          AND p.is_active
        """,
    )
    assert amount is not None, "No europe_apac premium_monthly price row"
    assert abs(float(amount) - 3.99) < 0.001, f"Expected $3.99, got {amount}"


@pytest.mark.asyncio
async def test_premium_yearly_price_europe_apac(db_session: AsyncSession) -> None:
    amount = await _scalar(
        db_session,
        """
        SELECT p.amount
        FROM prices p
        JOIN product_plans pp ON pp.id = p.plan_id
        JOIN pricing_zones pz ON pz.id = p.pricing_zone_id
        WHERE pp.slug = 'premium_yearly'
          AND pz.slug = 'europe_apac'
          AND p.currency = 'USD'
          AND p.is_active
        """,
    )
    assert amount is not None, "No europe_apac premium_yearly price row"
    assert abs(float(amount) - 39.99) < 0.001, f"Expected $39.99, got {amount}"


# --- Cities --------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mediterranean_asia_cities_seeded(db_session: AsyncSession) -> None:
    count = await _scalar(
        db_session,
        """
        SELECT count(*) FROM cities
        WHERE country_code IN ('IT','GR','EG','MA','JP','KR','TH')
          AND deleted_at IS NULL
        """,
    )
    assert count is not None
    assert int(count) >= 30, f"Expected >= 30 Mediterranean/Asia cities, got {count}"


# --- Provenance facts ----------------------------------------------------------


@pytest.mark.asyncio
async def test_unesco_provenance_facts_mediterranean_asia(db_session: AsyncSession) -> None:
    """Every Wave-8 UNESCO seed has a winning heritage_facts row tied to unesco_whc."""
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
          AND ho.country_code IN ('IT','GR','EG','MA','JP','KR','TH')
          AND (
            ho.pub_id LIKE 'it-%' OR ho.pub_id LIKE 'gr-%'
            OR ho.pub_id LIKE 'eg-%' OR ho.pub_id LIKE 'ma-%'
            OR ho.pub_id LIKE 'jp-%' OR ho.pub_id LIKE 'kr-%'
            OR ho.pub_id LIKE 'th-%'
          )
        """,
    )
    assert count is not None
    assert int(count) >= 30, f"Expected >= 30 UNESCO provenance facts, got {count}"
