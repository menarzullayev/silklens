"""Admin / public meta endpoint integration tests."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.integration


def _email() -> str:
    return f"admin-{uuid.uuid4().hex[:10]}@silklens-test.com"


async def _register(http: AsyncClient) -> dict[str, Any]:
    response = await http.post(
        "/v1/auth/register",
        json={"email": _email(), "password": "AdminTest12345"},
    )
    assert response.status_code == 201, response.text
    return response.json()


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


# --- Tenants ----------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_tenants_requires_permission(http: AsyncClient) -> None:
    auth = await _register(http)
    response = await http.get(
        "/v1/admin/tenants",
        headers={"Authorization": f"Bearer {auth['tokens']['access_token']}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["permission"] == "tenant:read"


@pytest.mark.asyncio
async def test_list_tenants_succeeds_for_super_admin(
    http: AsyncClient, db_session: AsyncSession
) -> None:
    auth = await _register(http)
    await _grant_super_admin(db_session, auth["user"]["pub_id"])
    response = await http.get(
        "/v1/admin/tenants",
        headers={"Authorization": f"Bearer {auth['tokens']['access_token']}"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] >= 1
    assert any(t["slug"] == "default" for t in body["items"])


# --- Branding --------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_branding_requires_permission(http: AsyncClient) -> None:
    auth = await _register(http)
    response = await http.put(
        "/v1/admin/tenants/default/branding",
        headers={"Authorization": f"Bearer {auth['tokens']['access_token']}"},
        json={"app_name": {"en": "Custom"}, "primary_color": "#FF0000"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_branding_persists(http: AsyncClient, db_session: AsyncSession) -> None:
    auth = await _register(http)
    await _grant_super_admin(db_session, auth["user"]["pub_id"])
    headers = {"Authorization": f"Bearer {auth['tokens']['access_token']}"}
    response = await http.put(
        "/v1/admin/tenants/default/branding",
        headers=headers,
        json={
            "app_name": {"en": "Patched Brand"},
            "primary_color": "#112233",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["primary_color"] == "#112233"
    assert response.json()["app_name"]["en"] == "Patched Brand"


# --- System settings -------------------------------------------------------


@pytest.mark.asyncio
async def test_set_and_read_system_setting(http: AsyncClient, db_session: AsyncSession) -> None:
    auth = await _register(http)
    await _grant_super_admin(db_session, auth["user"]["pub_id"])
    headers = {"Authorization": f"Bearer {auth['tokens']['access_token']}"}
    put = await http.put(
        "/v1/admin/system-settings",
        headers=headers,
        json={
            "key": f"app.test_flag_{uuid.uuid4().hex[:6]}",
            "value": "live",
            "value_type": "string",
            "scope": "tenant",
        },
    )
    assert put.status_code == 200, put.text
    settings_list = await http.get("/v1/admin/system-settings", headers=headers)
    assert settings_list.status_code == 200
    assert any(s["key"] == put.json()["key"] for s in settings_list.json())


# --- Feature flags ---------------------------------------------------------


@pytest.mark.asyncio
async def test_feature_flag_toggle(http: AsyncClient, db_session: AsyncSession) -> None:
    auth = await _register(http)
    await _grant_super_admin(db_session, auth["user"]["pub_id"])
    headers = {"Authorization": f"Bearer {auth['tokens']['access_token']}"}
    key = f"flag_{uuid.uuid4().hex[:6]}"
    put = await http.put(
        f"/v1/admin/feature-flags/{key}",
        headers=headers,
        json={
            "enabled": True,
            "rollout_kind": "boolean",
            "rollout_value": {},
        },
    )
    assert put.status_code == 200, put.text
    assert put.json()["enabled"] is True


# --- Public meta endpoints -------------------------------------------------


@pytest.mark.asyncio
async def test_public_branding_returns_default_tenant(http: AsyncClient) -> None:
    response = await http.get("/v1/branding")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["tenant_slug"] == "default"
    assert body["app_name"]


@pytest.mark.asyncio
async def test_public_vocab_languages_list(http: AsyncClient) -> None:
    response = await http.get("/v1/vocab/languages")
    assert response.status_code == 200, response.text
    body = response.json()
    slugs = {t["slug"] for t in body["items"]}
    # Languages seeded in migration 0003 include uz/en/ru/zh.
    assert {"uz", "en", "ru"}.issubset(slugs)


@pytest.mark.asyncio
async def test_public_vocab_unknown_returns_404(http: AsyncClient) -> None:
    response = await http.get("/v1/vocab/this_is_not_a_vocab")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "vocabulary.not_found"
