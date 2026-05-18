"""Partnership & SLA API integration tests.

Covers:
  - Public partner list (only active returned)
  - Public uptime status contains required fields
  - Admin list requires reseller:read permission
  - Unauthenticated admin list returns 403
  - Create agreement (super_admin) returns 201 with correct shape
  - SLA report generated with uptime_pct in valid range
  - Issue badge returns 201 with badge_kind
  - Duplicate active badge returns 409
  - SLA report with swapped dates returns 422
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.integration

DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"


def _email() -> str:
    return f"partner-test-{uuid.uuid4().hex[:10]}@silklens-test.com"


async def _register(http: AsyncClient) -> tuple[dict[str, Any], str]:
    """Return (response_json, email) so callers can log in later."""
    email = _email()
    resp = await http.post(
        "/v1/auth/register",
        json={"email": email, "password": "PartnerTest12345"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json(), email


async def _grant_super_admin(db_session: AsyncSession, user_pub_id: str) -> None:
    await db_session.execute(
        text(
            """
            INSERT INTO user_roles (
                user_id, residency_region, role_id, scope_tenant_id, granted_by
            )
            SELECT u.id, u.residency_region, r.id, NULL,
                   '00000000-0000-0000-0000-000000000002'::uuid
            FROM users u, roles r
            WHERE u.pub_id = :pub_id AND r.slug = 'super_admin'
            """
        ),
        {"pub_id": user_pub_id},
    )
    await db_session.commit()


async def _admin_token(http: AsyncClient, db_session: AsyncSession) -> str:
    response, email = await _register(http)
    await _grant_super_admin(db_session, response["user"]["pub_id"])
    login = await http.post(
        "/v1/auth/login",
        json={"email": email, "password": "PartnerTest12345"},
    )
    assert login.status_code == 200, login.text
    return login.json()["tokens"]["access_token"]


def _agreement_body(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "partner_name": f"Test Partner {uuid.uuid4().hex[:6]}",
        "partner_kind": "academic",
        "tier_slug": "premium_partner",
        "contact_name": "Dr. Test",
        "contact_email": f"contact-{uuid.uuid4().hex[:6]}@example.com",
        "annual_value_usd": "12000.00",
        "notes_md": "Integration test agreement.",
        "auto_renew": False,
    }
    body.update(overrides)
    return body


# ------------------------------------------------------------------ #
#  Public endpoints                                                   #
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_public_partner_list_returns_only_active(http: AsyncClient) -> None:
    resp = await http.get("/v1/partnerships")
    assert resp.status_code == 200, resp.text
    partners = resp.json()
    assert isinstance(partners, list)
    for p in partners:
        assert p["status"] == "active"
        assert "partner_name" in p
        assert "partner_kind" in p


@pytest.mark.asyncio
async def test_uptime_endpoint_returns_status_dict(http: AsyncClient) -> None:
    resp = await http.get("/v1/partnerships/uptime")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "uptime_pct" in body
    assert "service_status" in body
    assert "open_incidents" in body
    assert "computed_at" in body
    assert "recent_windows" in body
    uptime = float(body["uptime_pct"])
    assert 0.0 <= uptime <= 100.0
    assert body["service_status"] in {"operational", "degraded", "outage"}


# ------------------------------------------------------------------ #
#  Admin — auth guards                                               #
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_admin_list_requires_auth(http: AsyncClient) -> None:
    resp = await http.get("/v1/admin/partnerships")
    assert resp.status_code in (401, 403), resp.text


@pytest.mark.asyncio
async def test_admin_list_requires_permission(http: AsyncClient) -> None:
    """A registered user without admin role must get 403."""
    _response, email = await _register(http)
    login = await http.post(
        "/v1/auth/login",
        json={"email": email, "password": "PartnerTest12345"},
    )
    token = login.json()["tokens"]["access_token"]
    resp = await http.get(
        "/v1/admin/partnerships",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (401, 403), resp.text


# ------------------------------------------------------------------ #
#  Admin — create agreement                                           #
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_admin_create_agreement_returns_201(
    http: AsyncClient, db_session: AsyncSession
) -> None:
    token = await _admin_token(http, db_session)
    resp = await http.post(
        "/v1/admin/partnerships",
        json=_agreement_body(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "draft"
    assert body["partner_kind"] == "academic"
    assert body["tier_slug"] == "premium_partner"
    assert "id" in body


@pytest.mark.asyncio
async def test_admin_create_agreement_invalid_tier_returns_422(
    http: AsyncClient, db_session: AsyncSession
) -> None:
    token = await _admin_token(http, db_session)
    resp = await http.post(
        "/v1/admin/partnerships",
        json=_agreement_body(tier_slug="nonexistent_tier"),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422, resp.text


# ------------------------------------------------------------------ #
#  Admin — SLA report                                                #
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_admin_generate_sla_report(http: AsyncClient, db_session: AsyncSession) -> None:
    token = await _admin_token(http, db_session)
    # Create agreement first
    create_resp = await http.post(
        "/v1/admin/partnerships",
        json=_agreement_body(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_resp.status_code == 201, create_resp.text
    agreement_id = create_resp.json()["id"]

    period_start = (date.today() - timedelta(days=30)).isoformat()
    period_end = date.today().isoformat()
    resp = await http.get(
        f"/v1/admin/partnerships/{agreement_id}/sla-report",
        params={"period_start": period_start, "period_end": period_end},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "measured_uptime_pct" in body
    uptime = float(body["measured_uptime_pct"])
    assert 0.0 <= uptime <= 100.0
    assert body["agreement_id"] == agreement_id


@pytest.mark.asyncio
async def test_sla_report_invalid_date_range_returns_422(
    http: AsyncClient, db_session: AsyncSession
) -> None:
    token = await _admin_token(http, db_session)
    create_resp = await http.post(
        "/v1/admin/partnerships",
        json=_agreement_body(),
        headers={"Authorization": f"Bearer {token}"},
    )
    agreement_id = create_resp.json()["id"]

    resp = await http.get(
        f"/v1/admin/partnerships/{agreement_id}/sla-report",
        params={
            "period_start": date.today().isoformat(),
            "period_end": (date.today() - timedelta(days=1)).isoformat(),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422, resp.text


# ------------------------------------------------------------------ #
#  Admin — badges                                                    #
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_admin_issue_badge_returns_201(http: AsyncClient, db_session: AsyncSession) -> None:
    token = await _admin_token(http, db_session)
    create_resp = await http.post(
        "/v1/admin/partnerships",
        json=_agreement_body(),
        headers={"Authorization": f"Bearer {token}"},
    )
    agreement_id = create_resp.json()["id"]

    resp = await http.post(
        f"/v1/admin/partnerships/{agreement_id}/badges",
        json={"badge_kind": "academic"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["badge_kind"] == "academic"
    assert body["is_active"] is True
    assert body["agreement_id"] == agreement_id


@pytest.mark.asyncio
async def test_admin_duplicate_badge_returns_409(
    http: AsyncClient, db_session: AsyncSession
) -> None:
    token = await _admin_token(http, db_session)
    create_resp = await http.post(
        "/v1/admin/partnerships",
        json=_agreement_body(),
        headers={"Authorization": f"Bearer {token}"},
    )
    agreement_id = create_resp.json()["id"]

    for _ in range(2):
        resp = await http.post(
            f"/v1/admin/partnerships/{agreement_id}/badges",
            json={"badge_kind": "heritage_champion"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 409, resp.text
