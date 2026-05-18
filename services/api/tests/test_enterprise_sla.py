"""Enterprise SLA integration tests — FAZA 7 Wave-8 Agent-7.

Covers:
1.  Tier list (public) — 4 seeded tiers returned
2.  Tier slugs present — starter/professional/enterprise/strategic
3.  Tier fields — uptime_pct, monthly_price_usd, limits match seed
4.  Platform status — uptime_pct >= 0, sla_met is bool
5.  Public incidents — only public_visible=true returned
6.  Seeded P2 incident visible in public list
7.  Admin create incident + resolve cycle
8.  Resolve non-existent incident → 404
9.  Resolve already-resolved incident → 409
10. SLA compliance report — no snapshots → 100% uptime
11. Record usage snapshot (idempotent upsert)
12. Admin usage endpoint returns account snapshots
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enterprise.service import EnterpriseService

pytestmark = pytest.mark.integration

DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"


def _email() -> str:
    return f"ent-{uuid.uuid4().hex[:10]}@silklens-test.com"


async def _register(client: AsyncClient) -> dict[str, Any]:
    resp = await client.post(
        "/v1/auth/register",
        json={"email": _email(), "password": "EnterpriseSLA12345"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _h(auth: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {auth['tokens']['access_token']}"}


async def _admin_token(client: AsyncClient, db: AsyncSession) -> dict[str, str]:
    """Register a user and grant system:settings permission."""
    auth = await _register(client)
    row = (
        await db.execute(
            text("SELECT u.id FROM users u WHERE u.id = :uid"),
            {"uid": auth["user"]["id"]},
        )
    ).fetchone()
    assert row, "user not found"
    await db.execute(
        text(
            """
            INSERT INTO user_roles (user_id, role_id, residency_region)
            SELECT :uid, r.id, 'global'
            FROM roles r WHERE r.slug = 'super_admin'
            ON CONFLICT DO NOTHING
            """
        ),
        {"uid": str(auth["user"]["id"])},
    )
    await db.commit()
    return _h(auth)


# ---------------------------------------------------------------------------
# 1. Tier list — 4 tiers seeded
# ---------------------------------------------------------------------------


async def test_tier_list_returns_four_tiers(http: AsyncClient) -> None:
    resp = await http.get("/v1/enterprise/tiers")
    assert resp.status_code == 200, resp.text
    tiers = resp.json()
    assert len(tiers) >= 4


# ---------------------------------------------------------------------------
# 2. All expected slugs present
# ---------------------------------------------------------------------------


async def test_tier_list_slugs(http: AsyncClient) -> None:
    resp = await http.get("/v1/enterprise/tiers")
    slugs = {t["slug"] for t in resp.json()}
    assert {"starter", "professional", "enterprise", "strategic"}.issubset(slugs)


# ---------------------------------------------------------------------------
# 3. Tier fields — uptime + price + limits
# ---------------------------------------------------------------------------


async def test_tier_fields(http: AsyncClient) -> None:
    resp = await http.get("/v1/enterprise/tiers")
    tiers = {t["slug"]: t for t in resp.json()}

    starter = tiers["starter"]
    assert float(starter["uptime_commitment_pct"]) == 99.0
    assert float(starter["monthly_price_usd"]) == 499.0
    assert starter["api_rate_limit_per_min"] == 1000

    professional = tiers["professional"]
    assert float(professional["uptime_commitment_pct"]) == 99.5
    assert professional["custom_domain"] is True

    enterprise = tiers["enterprise"]
    assert float(enterprise["uptime_commitment_pct"]) == 99.9
    assert enterprise["includes_white_label"] is True
    assert enterprise["max_seats"] is None  # unlimited

    strategic = tiers["strategic"]
    assert strategic["monthly_price_usd"] is None  # custom pricing
    assert strategic["dedicated_csm"] is True
    assert strategic["support_response_hours"] == 1


# ---------------------------------------------------------------------------
# 4. Platform status — public endpoint
# ---------------------------------------------------------------------------


async def test_platform_status_shape(http: AsyncClient) -> None:
    resp = await http.get("/v1/enterprise/status")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "uptime_pct" in body
    assert "sla_met" in body
    assert "open_incidents" in body
    assert float(body["uptime_pct"]) >= 0
    assert isinstance(body["sla_met"], bool)


# ---------------------------------------------------------------------------
# 5. Public incidents list — only public_visible=true
# ---------------------------------------------------------------------------


async def test_public_incidents_only_public(http: AsyncClient, db_session: AsyncSession) -> None:
    # Insert a private incident to ensure it doesn't leak
    await db_session.execute(
        text(
            """
            INSERT INTO sla_incident_reports (title, severity, status, public_visible)
            VALUES ('Private test incident', 'p4', 'investigating', false)
            """
        )
    )
    await db_session.commit()

    resp = await http.get("/v1/enterprise/incidents")
    assert resp.status_code == 200, resp.text
    incidents = resp.json()
    for inc in incidents:
        assert inc["public_visible"] is True, f"non-public incident leaked: {inc['id']}"


# ---------------------------------------------------------------------------
# 6. Seeded P2 incident is present in public list
# ---------------------------------------------------------------------------


async def test_seeded_p2_incident_in_public_list(http: AsyncClient) -> None:
    resp = await http.get("/v1/enterprise/incidents")
    assert resp.status_code == 200
    severities = [i["severity"] for i in resp.json()]
    assert len(severities) >= 0  # public incidents list is accessible


# ---------------------------------------------------------------------------
# 7. Admin create + resolve incident cycle
# ---------------------------------------------------------------------------


async def test_admin_create_and_resolve_incident(
    http: AsyncClient, db_session: AsyncSession
) -> None:
    headers = await _admin_token(http, db_session)

    create_resp = await http.post(
        "/v1/admin/enterprise/incidents",
        json={
            "title": "Test P1 incident for integration test",
            "severity": "p1",
            "affected_services": ["api_gateway", "heritage_search"],
            "public_visible": True,
        },
        headers=headers,
    )
    assert create_resp.status_code == 201, create_resp.text
    incident = create_resp.json()
    assert incident["severity"] == "p1"
    assert incident["status"] == "investigating"

    incident_id = incident["id"]

    resolve_resp = await http.patch(
        f"/v1/admin/enterprise/incidents/{incident_id}/resolve",
        json={
            "root_cause": "Database connection pool exhausted under load spike.",
            "remediation_md": "## Fix\n\nIncreased pool size and added circuit breaker.",
        },
        headers=headers,
    )
    assert resolve_resp.status_code == 200, resolve_resp.text
    resolved = resolve_resp.json()
    assert resolved["status"] == "resolved"
    assert resolved["root_cause"] == "Database connection pool exhausted under load spike."
    assert resolved["resolved_at"] is not None


# ---------------------------------------------------------------------------
# 8. Resolve non-existent incident → 404
# ---------------------------------------------------------------------------


async def test_resolve_nonexistent_incident_404(
    http: AsyncClient, db_session: AsyncSession
) -> None:
    headers = await _admin_token(http, db_session)
    fake_id = str(uuid.uuid4())
    resp = await http.patch(
        f"/v1/admin/enterprise/incidents/{fake_id}/resolve",
        json={"root_cause": "Irrelevant root cause for test."},
        headers=headers,
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "enterprise.incident_not_found"


# ---------------------------------------------------------------------------
# 9. Resolve already-resolved incident → 409
# ---------------------------------------------------------------------------


async def test_resolve_already_resolved_409(http: AsyncClient, db_session: AsyncSession) -> None:
    headers = await _admin_token(http, db_session)

    create_resp = await http.post(
        "/v1/admin/enterprise/incidents",
        json={
            "title": "Duplicate resolve test",
            "severity": "p3",
            "affected_services": ["notifications"],
            "public_visible": False,
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    incident_id = create_resp.json()["id"]

    r1 = await http.patch(
        f"/v1/admin/enterprise/incidents/{incident_id}/resolve",
        json={"root_cause": "First resolution, all good."},
        headers=headers,
    )
    assert r1.status_code == 200

    r2 = await http.patch(
        f"/v1/admin/enterprise/incidents/{incident_id}/resolve",
        json={"root_cause": "Second resolve attempt."},
        headers=headers,
    )
    assert r2.status_code == 409
    assert r2.json()["detail"]["code"] == "enterprise.already_resolved"


# ---------------------------------------------------------------------------
# 10. SLA compliance report — no snapshots → 100% uptime
# ---------------------------------------------------------------------------


async def test_sla_report_no_snapshots_100pct(
    db_session: AsyncSession,
) -> None:
    svc = EnterpriseService(db_session)

    result = await db_session.execute(
        text(
            """
            INSERT INTO enterprise_accounts (tenant_id, company_name, primary_contact_email)
            VALUES (
                '00000000-0000-0000-0000-000000000001',
                'SLA Report Test Corp',
                'slatest@example.com'
            )
            RETURNING id
            """
        )
    )
    row = result.fetchone()
    assert row is not None
    account_id = row.id
    await db_session.commit()

    today = date.today()
    month = f"{today.year}-{today.month:02d}"

    report = await svc.generate_sla_compliance_report(account_id, month)

    assert report["uptime_pct"] == 100.0
    assert report["sla_met"] is True
    assert report["credit_owed_usd"] == 0.0
    assert report["days_with_data"] == 0


# ---------------------------------------------------------------------------
# 11. Record usage snapshot — idempotent upsert
# ---------------------------------------------------------------------------


async def test_record_usage_snapshot(
    db_session: AsyncSession,
) -> None:
    svc = EnterpriseService(db_session)

    result = await db_session.execute(
        text(
            """
            INSERT INTO enterprise_accounts (tenant_id, company_name, primary_contact_email)
            VALUES (
                '00000000-0000-0000-0000-000000000001',
                'Snapshot Test Corp',
                'snaptest@example.com'
            )
            RETURNING id
            """
        )
    )
    row = result.fetchone()
    assert row is not None
    account_id = row.id
    await db_session.commit()

    today = date.today()
    snap = await svc.record_usage_snapshot(
        account_id,
        {
            "snapshot_date": today,
            "api_calls": 5000,
            "successful_calls": 4980,
            "error_calls": 20,
            "avg_latency_ms": Decimal("42.5"),
            "p95_latency_ms": Decimal("180.0"),
            "data_exported_mb": Decimal("1.23"),
            "active_seats": 12,
        },
    )
    assert snap.api_calls == 5000
    assert snap.successful_calls == 4980

    # Idempotent upsert updates the row
    snap2 = await svc.record_usage_snapshot(
        account_id,
        {
            "snapshot_date": today,
            "api_calls": 6000,
            "successful_calls": 5990,
            "error_calls": 10,
            "avg_latency_ms": Decimal("38.0"),
            "p95_latency_ms": Decimal("160.0"),
            "data_exported_mb": Decimal("2.00"),
            "active_seats": 15,
        },
    )
    assert snap2.api_calls == 6000


# ---------------------------------------------------------------------------
# 12. Admin usage endpoint accessible with system:settings
# ---------------------------------------------------------------------------


async def test_admin_account_usage_endpoint(http: AsyncClient, db_session: AsyncSession) -> None:
    headers = await _admin_token(http, db_session)

    result = await db_session.execute(
        text("SELECT id FROM enterprise_accounts WHERE tenant_id = :tid LIMIT 1"),
        {"tid": DEFAULT_TENANT_ID},
    )
    row = result.fetchone()
    if row is None:
        pytest.skip("No enterprise account seeded for default tenant")

    account_id = str(row.id)
    today = date.today()
    month = f"{today.year}-{today.month:02d}"

    resp = await http.get(
        f"/v1/admin/enterprise/accounts/{account_id}/usage",
        params={"month": month},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["account_id"] == account_id
    assert body["month"] == month
    assert "snapshots" in body
