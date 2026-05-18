"""Heritage CRUD integration tests.

Covers: anonymous list/get, RBAC-gated create, validation errors, audit-side
revision row, outbox event emission.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.integration


def _unique_email() -> str:
    return f"heritage-{uuid.uuid4().hex[:10]}@silklens-test.com"


def _strong_password() -> str:
    return "HeritageTest1234"


async def _register(http: AsyncClient) -> dict[str, Any]:
    response = await http.post(
        "/v1/auth/register",
        json={"email": _unique_email(), "password": _strong_password()},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _grant_super_admin(db_session: AsyncSession, user_pub_id: str) -> None:
    """Grant the super_admin role to a freshly-registered test user."""
    await db_session.execute(
        text(
            """
            INSERT INTO user_roles (
                user_id, residency_region, role_id, scope_tenant_id, granted_by
            )
            SELECT
                u.id, u.residency_region, r.id, NULL,
                '00000000-0000-0000-0000-000000000002'::uuid
            FROM users u, roles r
            WHERE u.pub_id = :pub_id AND r.slug = 'super_admin'
            """
        ),
        {"pub_id": user_pub_id},
    )
    await db_session.commit()


# --- Public read paths -------------------------------------------------------


@pytest.mark.asyncio
async def test_list_heritage_empty_ok(http: AsyncClient) -> None:
    response = await http.get("/v1/heritage")
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert "total" in body
    assert body["limit"] == 20
    assert body["offset"] == 0


@pytest.mark.asyncio
async def test_list_supports_filters(http: AsyncClient) -> None:
    response = await http.get("/v1/heritage?kind=madrasa&country=UZ&limit=5")
    assert response.status_code == 200
    body = response.json()
    assert body["limit"] == 5


@pytest.mark.asyncio
async def test_get_unknown_pub_id_returns_404(http: AsyncClient) -> None:
    response = await http.get("/v1/heritage/does-not-exist")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "heritage.not_found"


# --- Create: RBAC ------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_requires_authentication(http: AsyncClient) -> None:
    response = await http.post(
        "/v1/heritage",
        json={
            "kind_slug": "madrasa",
            "name": {"en": "Test"},
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_requires_permission(http: AsyncClient) -> None:
    """New user without heritage:create role gets 403."""
    auth = await _register(http)
    response = await http.post(
        "/v1/heritage",
        json={"kind_slug": "madrasa", "name": {"en": "Test"}},
        headers={"Authorization": f"Bearer {auth['tokens']['access_token']}"},
    )
    assert response.status_code == 403
    body = response.json()
    assert body["detail"]["code"] == "identity.permission_denied"
    assert body["detail"]["permission"] == "heritage:create"


# --- Create: happy path ------------------------------------------------------


@pytest.mark.asyncio
async def test_create_with_super_admin_role(http: AsyncClient, db_session: AsyncSession) -> None:
    auth = await _register(http)
    await _grant_super_admin(db_session, auth["user"]["pub_id"])

    response = await http.post(
        "/v1/heritage",
        json={
            "kind_slug": "madrasa",
            "name": {"en": "Test Madrasa", "uz": "Sinov madrasasi"},
            "summary_md": {"en": "Beautiful 15th century building"},
            "country_code": "uz",
            "latitude": "39.654389",
            "longitude": "66.975278",
            "period_start_year": 1417,
            "status": "draft",
        },
        headers={"Authorization": f"Bearer {auth['tokens']['access_token']}"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["pub_id"]
    assert body["kind_slug"] == "madrasa"
    assert body["name"]["en"] == "Test Madrasa"
    assert body["country_code"] == "UZ"
    assert body["revision"] == 1
    assert body["status"] == "draft"


@pytest.mark.asyncio
async def test_create_emits_revision_and_outbox_event(
    http: AsyncClient, db_session: AsyncSession
) -> None:
    auth = await _register(http)
    await _grant_super_admin(db_session, auth["user"]["pub_id"])

    response = await http.post(
        "/v1/heritage",
        json={"kind_slug": "mosque", "name": {"en": "Test Mosque"}},
        headers={"Authorization": f"Bearer {auth['tokens']['access_token']}"},
    )
    assert response.status_code == 201
    pub_id = response.json()["pub_id"]

    # Revision row must exist
    revision = (
        await db_session.execute(
            text(
                """
                SELECT count(*) FROM heritage_revisions r
                JOIN heritage_objects h ON h.id = r.heritage_id
                WHERE h.pub_id = :pub_id
                """
            ),
            {"pub_id": pub_id},
        )
    ).scalar_one()
    assert int(revision) == 1

    # Outbox event must have been emitted
    event = (
        await db_session.execute(
            text(
                """
                SELECT event_name FROM event_outbox
                WHERE aggregate_id IN (
                    SELECT id FROM heritage_objects WHERE pub_id = :pub_id
                )
                """
            ),
            {"pub_id": pub_id},
        )
    ).scalar_one_or_none()
    assert event == "heritage.created.v1"


# --- Create: validation ------------------------------------------------------


@pytest.mark.asyncio
async def test_create_rejects_unknown_kind(http: AsyncClient, db_session: AsyncSession) -> None:
    auth = await _register(http)
    await _grant_super_admin(db_session, auth["user"]["pub_id"])

    response = await http.post(
        "/v1/heritage",
        json={"kind_slug": "not_a_kind", "name": {"en": "Test"}},
        headers={"Authorization": f"Bearer {auth['tokens']['access_token']}"},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "heritage.invalid_kind"


@pytest.mark.asyncio
async def test_create_rejects_no_name(http: AsyncClient, db_session: AsyncSession) -> None:
    auth = await _register(http)
    await _grant_super_admin(db_session, auth["user"]["pub_id"])

    response = await http.post(
        "/v1/heritage",
        json={"kind_slug": "mosque", "name": {}},
        headers={"Authorization": f"Bearer {auth['tokens']['access_token']}"},
    )
    # Pydantic rejects empty dict at min_length=1 → 422
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_rejects_name_without_en_or_uz(
    http: AsyncClient, db_session: AsyncSession
) -> None:
    auth = await _register(http)
    await _grant_super_admin(db_session, auth["user"]["pub_id"])

    response = await http.post(
        "/v1/heritage",
        json={"kind_slug": "mosque", "name": {"fr": "Test"}},
        headers={"Authorization": f"Bearer {auth['tokens']['access_token']}"},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["detail"]["code"] == "heritage.validation_failed"


# --- Get round-trip ---------------------------------------------------------


@pytest.mark.asyncio
async def test_create_then_fetch_round_trip(http: AsyncClient, db_session: AsyncSession) -> None:
    auth = await _register(http)
    await _grant_super_admin(db_session, auth["user"]["pub_id"])

    create = await http.post(
        "/v1/heritage",
        json={"kind_slug": "mausoleum", "name": {"en": "Gur-Emir"}},
        headers={"Authorization": f"Bearer {auth['tokens']['access_token']}"},
    )
    pub_id = create.json()["pub_id"]

    fetch = await http.get(f"/v1/heritage/{pub_id}")
    assert fetch.status_code == 200
    body = fetch.json()
    assert body["pub_id"] == pub_id
    assert body["name"]["en"] == "Gur-Emir"
