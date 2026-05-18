"""Heritage write-extras integration tests.

Covers PATCH, DELETE, alias-add, revision list, and the state-machine
transitions exposed in ``POST /v1/heritage/{pub_id}/transitions``.

All tests reuse ``http`` and ``db_session`` fixtures from conftest.py and
follow the same _register / _grant_super_admin helpers as test_heritage.py.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.integration


# --- Helpers ----------------------------------------------------------------


def _unique_email() -> str:
    return f"hwrites-{uuid.uuid4().hex[:10]}@silklens-test.com"


async def _register(http: AsyncClient) -> dict[str, Any]:
    response = await http.post(
        "/v1/auth/register",
        json={"email": _unique_email(), "password": "HeritageWrites1234"},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _grant_role(db_session: AsyncSession, user_pub_id: str, role_slug: str) -> None:
    await db_session.execute(
        text(
            """
            INSERT INTO user_roles (
                user_id, residency_region, role_id, scope_tenant_id, granted_by
            )
            SELECT u.id, u.residency_region, r.id, NULL,
                   '00000000-0000-0000-0000-000000000002'::uuid
            FROM users u, roles r
            WHERE u.pub_id = :pub_id AND r.slug = :role
            """
        ),
        {"pub_id": user_pub_id, "role": role_slug},
    )
    await db_session.commit()


async def _create_object(
    http: AsyncClient,
    token: str,
    *,
    kind: str = "mosque",
    name: dict[str, str] | None = None,
) -> dict[str, Any]:
    response = await http.post(
        "/v1/heritage",
        json={"kind_slug": kind, "name": name or {"en": "Writes Test Site"}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _provision_admin(http: AsyncClient, db_session: AsyncSession) -> tuple[str, str]:
    """Returns (token, user_pub_id) for a freshly registered super_admin."""
    auth = await _register(http)
    await _grant_role(db_session, auth["user"]["pub_id"], "super_admin")
    return auth["tokens"]["access_token"], auth["user"]["pub_id"]


# --- PATCH ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_requires_authentication(http: AsyncClient) -> None:
    response = await http.patch("/v1/heritage/does-not-matter", json={"tags": ["foo"]})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_patch_requires_update_permission(
    http: AsyncClient, db_session: AsyncSession
) -> None:
    admin_token, _ = await _provision_admin(http, db_session)
    created = await _create_object(http, admin_token)

    other = await _register(http)
    response = await http.patch(
        f"/v1/heritage/{created['pub_id']}",
        json={"tags": ["forbidden"]},
        headers={"Authorization": f"Bearer {other['tokens']['access_token']}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["permission"] == "heritage:update"


@pytest.mark.asyncio
async def test_patch_partial_update_merges_jsonb_and_bumps_revision(
    http: AsyncClient, db_session: AsyncSession
) -> None:
    admin_token, _ = await _provision_admin(http, db_session)
    created = await _create_object(
        http,
        admin_token,
        name={"en": "Original", "uz": "Asl"},
    )
    pub_id = created["pub_id"]
    initial_revision = created["revision"]

    response = await http.patch(
        f"/v1/heritage/{pub_id}",
        json={
            "name": {"ru": "Исходное"},
            "tags": ["unesco", "samarkand"],
            "country_code": "uz",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    # jsonb merge keeps original keys + adds the new one
    assert body["name"]["en"] == "Original"
    assert body["name"]["uz"] == "Asl"
    assert body["name"]["ru"] == "Исходное"
    assert body["tags"] == ["unesco", "samarkand"]
    assert body["country_code"] == "UZ"
    assert body["revision"] > initial_revision

    # heritage.updated.v1 should have been emitted
    event_count = (
        await db_session.execute(
            text(
                """
                SELECT count(*) FROM event_outbox
                WHERE event_name = 'heritage.updated.v1'
                  AND aggregate_id IN (SELECT id FROM heritage_objects WHERE pub_id = :p)
                """
            ),
            {"p": pub_id},
        )
    ).scalar_one()
    assert int(event_count) >= 1


@pytest.mark.asyncio
async def test_patch_empty_body_rejected(http: AsyncClient, db_session: AsyncSession) -> None:
    admin_token, _ = await _provision_admin(http, db_session)
    created = await _create_object(http, admin_token)
    response = await http.patch(
        f"/v1/heritage/{created['pub_id']}",
        json={},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_patch_unknown_pub_id_returns_404(
    http: AsyncClient, db_session: AsyncSession
) -> None:
    admin_token, _ = await _provision_admin(http, db_session)
    response = await http.patch(
        "/v1/heritage/does-not-exist",
        json={"tags": ["foo"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


# --- DELETE -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_soft_marks_deleted_at_and_emits_event(
    http: AsyncClient, db_session: AsyncSession
) -> None:
    admin_token, _ = await _provision_admin(http, db_session)
    created = await _create_object(http, admin_token)
    pub_id = created["pub_id"]

    response = await http.delete(
        f"/v1/heritage/{pub_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204

    # Public GET hides soft-deleted rows
    public = await http.get(f"/v1/heritage/{pub_id}")
    assert public.status_code == 404

    # DB row still exists with deleted_at set
    deleted_at = (
        await db_session.execute(
            text("SELECT deleted_at FROM heritage_objects WHERE pub_id = :p"),
            {"p": pub_id},
        )
    ).scalar_one()
    assert deleted_at is not None

    # heritage.deleted.v1 event emitted (event_types row auto-inserted)
    event = (
        await db_session.execute(
            text(
                """
                SELECT event_name FROM event_outbox
                WHERE event_name = 'heritage.deleted.v1'
                  AND aggregate_id IN (SELECT id FROM heritage_objects WHERE pub_id = :p)
                """
            ),
            {"p": pub_id},
        )
    ).scalar_one_or_none()
    assert event == "heritage.deleted.v1"


@pytest.mark.asyncio
async def test_delete_requires_delete_permission(
    http: AsyncClient, db_session: AsyncSession
) -> None:
    admin_token, _ = await _provision_admin(http, db_session)
    created = await _create_object(http, admin_token)

    other = await _register(http)
    response = await http.delete(
        f"/v1/heritage/{created['pub_id']}",
        headers={"Authorization": f"Bearer {other['tokens']['access_token']}"},
    )
    assert response.status_code == 403


# --- Aliases ----------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_alias_returns_201_and_persists(
    http: AsyncClient, db_session: AsyncSession
) -> None:
    admin_token, _ = await _provision_admin(http, db_session)
    created = await _create_object(http, admin_token)

    response = await http.post(
        f"/v1/heritage/{created['pub_id']}/aliases",
        json={
            "alias": "Maracanda",
            "language_tag": "grc",
            "kind": "historical",
            "confidence": 70,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["alias"] == "Maracanda"
    assert body["language_tag"] == "grc"
    assert body["kind"] == "historical"


@pytest.mark.asyncio
async def test_add_alias_duplicate_returns_409(http: AsyncClient, db_session: AsyncSession) -> None:
    admin_token, _ = await _provision_admin(http, db_session)
    created = await _create_object(http, admin_token)
    payload = {"alias": "Samarqand", "language_tag": "uz", "kind": "official"}

    first = await http.post(
        f"/v1/heritage/{created['pub_id']}/aliases",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert first.status_code == 201

    second = await http.post(
        f"/v1/heritage/{created['pub_id']}/aliases",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "heritage.duplicate_alias"


# --- Revisions --------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_revisions_paginated(http: AsyncClient, db_session: AsyncSession) -> None:
    admin_token, _ = await _provision_admin(http, db_session)
    created = await _create_object(http, admin_token)
    pub_id = created["pub_id"]

    # Trigger two updates so we have 1 insert + 2 update rows.
    for tag in ("first", "second"):
        await http.patch(
            f"/v1/heritage/{pub_id}",
            json={"tags": [tag]},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    response = await http.get(
        f"/v1/heritage/{pub_id}/revisions?limit=10",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] >= 3
    # Newest revision first
    assert body["items"][0]["revision"] >= body["items"][-1]["revision"]
    assert body["items"][0]["action"] in {"insert", "update"}


# --- Transitions ------------------------------------------------------------


@pytest.mark.asyncio
async def test_transition_draft_to_review_to_published(
    http: AsyncClient, db_session: AsyncSession
) -> None:
    admin_token, _ = await _provision_admin(http, db_session)
    created = await _create_object(http, admin_token)
    pub_id = created["pub_id"]

    review = await http.post(
        f"/v1/heritage/{pub_id}/transitions",
        json={"action": "submit_review"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert review.status_code == 200, review.text
    assert review.json()["status"] == "review"

    published = await http.post(
        f"/v1/heritage/{pub_id}/transitions",
        json={"action": "approve"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert published.status_code == 200
    assert published.json()["status"] == "published"


@pytest.mark.asyncio
async def test_transition_invalid_action_returns_422(
    http: AsyncClient, db_session: AsyncSession
) -> None:
    admin_token, _ = await _provision_admin(http, db_session)
    created = await _create_object(http, admin_token)

    # draft → approve is not in the FSM
    response = await http.post(
        f"/v1/heritage/{created['pub_id']}/transitions",
        json={"action": "approve"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "heritage.invalid_transition"
