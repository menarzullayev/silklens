"""Wave-8 Agent 1 — Silk Road corridor heritage seed integration tests.

Asserts the FAZA 6 Silk Road starter set lands as expected:
- ≥ 30 CN, ≥ 30 IR, ≥ 30 TR, ≥ 30 IN heritage rows.
- ≥ 12 UNESCO inscriptions across the four countries.
- ≥ 24 Silk Road corridor cities seeded (CN:11 + IR:11 + TR:10 + IN:10 = 42).
- CNY, TRY, INR currencies present (IRR included).
- ``silk_road_corridor`` pricing zone with PPP 0.55 covering CN/IR/TR/IN.
- Premium monthly priced at $2.99 USD against the silk_road_corridor zone.
- Premium yearly priced at $29.99 USD against the silk_road_corridor zone.

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


# --- Heritage counts per country -----------------------------------------------


@pytest.mark.asyncio
async def test_china_heritage_count(db_session: AsyncSession) -> None:
    count = await _scalar(
        db_session,
        """
        SELECT count(*) FROM heritage_objects
        WHERE country_code = 'CN' AND deleted_at IS NULL
          AND pub_id LIKE 'cn-%'
        """,
    )
    assert count is not None
    assert int(count) >= 30, f"Expected >= 30 CN heritage, got {count}"


@pytest.mark.asyncio
async def test_iran_heritage_count(db_session: AsyncSession) -> None:
    count = await _scalar(
        db_session,
        """
        SELECT count(*) FROM heritage_objects
        WHERE country_code = 'IR' AND deleted_at IS NULL
          AND pub_id LIKE 'ir-%'
        """,
    )
    assert count is not None
    assert int(count) >= 30, f"Expected >= 30 IR heritage, got {count}"


@pytest.mark.asyncio
async def test_turkey_heritage_count(db_session: AsyncSession) -> None:
    count = await _scalar(
        db_session,
        """
        SELECT count(*) FROM heritage_objects
        WHERE country_code = 'TR' AND deleted_at IS NULL
          AND pub_id LIKE 'tr-%'
        """,
    )
    assert count is not None
    assert int(count) >= 30, f"Expected >= 30 TR heritage, got {count}"


@pytest.mark.asyncio
async def test_india_heritage_count(db_session: AsyncSession) -> None:
    count = await _scalar(
        db_session,
        """
        SELECT count(*) FROM heritage_objects
        WHERE country_code = 'IN' AND deleted_at IS NULL
          AND pub_id LIKE 'in-%'
        """,
    )
    assert count is not None
    assert int(count) >= 30, f"Expected >= 30 IN heritage, got {count}"


# --- UNESCO inscriptions -------------------------------------------------------


@pytest.mark.asyncio
async def test_unesco_inscriptions_silk_road(db_session: AsyncSession) -> None:
    """At least 12 UNESCO inscriptions total, with at least 3 per country."""
    rows = (
        await db_session.execute(
            text(
                """
                SELECT ho.country_code, count(*)
                FROM unesco_inscriptions ui
                JOIN heritage_objects ho ON ho.id = ui.heritage_id
                WHERE ui.deleted_at IS NULL
                  AND ho.country_code IN ('CN','IR','TR','IN')
                  AND (
                    ho.pub_id LIKE 'cn-%' OR ho.pub_id LIKE 'ir-%'
                    OR ho.pub_id LIKE 'tr-%' OR ho.pub_id LIKE 'in-%'
                  )
                GROUP BY ho.country_code
                ORDER BY ho.country_code
                """
            )
        )
    ).all()
    by_cc = {row[0]: int(row[1]) for row in rows}
    assert set(by_cc) >= {"CN", "IR", "TR", "IN"}, f"Missing UNESCO countries: {by_cc}"
    assert sum(by_cc.values()) >= 12, f"Expected >= 12 UNESCO total, got {by_cc}"
    for cc in ("CN", "IR", "TR", "IN"):
        assert by_cc.get(cc, 0) >= 3, f"{cc} has < 3 UNESCO inscriptions: {by_cc}"


# --- Cities -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_silk_road_cities_seeded(db_session: AsyncSession) -> None:
    count = await _scalar(
        db_session,
        """
        SELECT count(*) FROM cities
        WHERE country_code IN ('CN','IR','TR','IN')
          AND deleted_at IS NULL
        """,
    )
    assert count is not None
    assert int(count) >= 24, f"Expected >= 24 Silk Road corridor cities, got {count}"


# --- Currencies ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_silk_road_currencies_present(db_session: AsyncSession) -> None:
    rows = (
        await db_session.execute(
            text(
                """
                SELECT code FROM currencies
                WHERE code IN ('CNY','IRR','TRY','INR')
                ORDER BY code
                """
            )
        )
    ).all()
    codes = {row[0] for row in rows}
    assert codes == {"CNY", "IRR", "TRY", "INR"}, f"Missing currencies: {codes}"


# --- Pricing zone -------------------------------------------------------------


@pytest.mark.asyncio
async def test_silk_road_corridor_pricing_zone(db_session: AsyncSession) -> None:
    row = (
        await db_session.execute(
            text(
                """
                SELECT slug, country_codes, default_currency, purchasing_power_index
                FROM pricing_zones
                WHERE slug = 'silk_road_corridor'
                """
            )
        )
    ).first()
    assert row is not None, "silk_road_corridor pricing zone missing"
    slug, country_codes, default_currency, ppp = row
    assert slug == "silk_road_corridor"
    assert default_currency == "USD"
    assert abs(float(ppp) - 0.55) < 0.001
    assert set(country_codes) >= {"CN", "IR", "TR", "IN"}


@pytest.mark.asyncio
async def test_premium_monthly_price_silk_road(db_session: AsyncSession) -> None:
    amount = await _scalar(
        db_session,
        """
        SELECT p.amount
        FROM prices p
        JOIN product_plans pp ON pp.id = p.plan_id
        JOIN pricing_zones pz ON pz.id = p.pricing_zone_id
        WHERE pp.slug = 'premium_monthly'
          AND pz.slug = 'silk_road_corridor'
          AND p.currency = 'USD'
          AND p.is_active
        """,
    )
    assert amount is not None, "No silk_road_corridor premium_monthly price row"
    assert abs(float(amount) - 2.99) < 0.001, f"Expected $2.99, got {amount}"


@pytest.mark.asyncio
async def test_premium_yearly_price_silk_road(db_session: AsyncSession) -> None:
    amount = await _scalar(
        db_session,
        """
        SELECT p.amount
        FROM prices p
        JOIN product_plans pp ON pp.id = p.plan_id
        JOIN pricing_zones pz ON pz.id = p.pricing_zone_id
        WHERE pp.slug = 'premium_yearly'
          AND pz.slug = 'silk_road_corridor'
          AND p.currency = 'USD'
          AND p.is_active
        """,
    )
    assert amount is not None, "No silk_road_corridor premium_yearly price row"
    assert abs(float(amount) - 29.99) < 0.001, f"Expected $29.99, got {amount}"


# --- Provenance facts ---------------------------------------------------------


@pytest.mark.asyncio
async def test_silk_road_unesco_provenance_facts(db_session: AsyncSession) -> None:
    """Every Wave-8 UNESCO seed has a winning heritage_facts row tied to the
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
            ho.pub_id LIKE 'cn-%' OR ho.pub_id LIKE 'ir-%'
            OR ho.pub_id LIKE 'tr-%' OR ho.pub_id LIKE 'in-%'
          )
        """,
    )
    assert count is not None
    assert int(count) >= 12, f"Expected >= 12 UNESCO provenance facts, got {count}"
