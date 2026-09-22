"""Notification integration tests."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.integration


def _email() -> str:
    return f"notif-{uuid.uuid4().hex[:10]}@silklens-test.com"


async def _register(http: AsyncClient) -> dict[str, Any]:
    response = await http.post(
        "/v1/auth/register",
        json={"email": _email(), "password": "NotifTest12345"},
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
async def template_seed(db_session: AsyncSession) -> dict[str, str]:
    """Seed a single template + version we can hit from tests."""
    template_slug = f"test_welcome_{uuid.uuid4().hex[:6]}"
    await db_session.execute(
        text(
            """
            INSERT INTO notification_templates (
                slug, category_slug, channels, default_priority, is_active, name
            ) VALUES (
                :slug, 'social_activity', ARRAY['in_app','email']::text[], 5, true,
                '{"en":"Welcome"}'::jsonb
            )
            """
        ),
        {"slug": template_slug},
    )
    await db_session.execute(
        text(
            """
            INSERT INTO notification_template_versions (
                template_id, version, language_tag, subject, body_md, push_title, push_body
            )
            SELECT t.id, 1, 'en', 'Welcome ${name}',
                   'Hello ${name}, welcome to SilkLens', 'Welcome', 'Hello ${name}'
            FROM notification_templates t WHERE t.slug = :slug
            """
        ),
        {"slug": template_slug},
    )
    await db_session.commit()
    return {"template_slug": template_slug}


# --- Inbox ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_inbox_empty_for_new_user(http: AsyncClient) -> None:
    auth = await _register(http)
    response = await http.get(
        "/v1/notifications",
        headers={"Authorization": f"Bearer {auth['tokens']['access_token']}"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["items"] == []
    assert body["has_more"] is False


@pytest.mark.asyncio
async def test_send_templated_creates_inbox_entry(
    http: AsyncClient, db_session: AsyncSession, template_seed: dict[str, str]
) -> None:
    auth = await _register(http)

    # Send via the service directly because templated send is currently an
    # internal API; the inbox endpoint reads the same `notifications` table.
    from uuid import UUID

    from src.domain.notifications.service import NotificationService
    from src.infrastructure.notifications.repository import (
        SqlNotificationRepository,
    )

    service = NotificationService(repository=SqlNotificationRepository(db_session))
    await service.send_templated(
        template_slug=template_seed["template_slug"],
        recipient_user_id=UUID(auth["user"]["id"]),
        residency_region=auth["user"]["residency_region"],
        language_tag="en",
        variables={"name": "Alisher"},
    )

    response = await http.get(
        "/v1/notifications",
        headers={"Authorization": f"Bearer {auth['tokens']['access_token']}"},
    )
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["title"] == "Welcome"
    assert "Alisher" in body["items"][0]["body_md"]


@pytest.mark.asyncio
async def test_mark_read_flow(
    http: AsyncClient, db_session: AsyncSession, template_seed: dict[str, str]
) -> None:
    auth = await _register(http)
    from uuid import UUID

    from src.domain.notifications.service import NotificationService
    from src.infrastructure.notifications.repository import SqlNotificationRepository

    service = NotificationService(repository=SqlNotificationRepository(db_session))
    await service.send_templated(
        template_slug=template_seed["template_slug"],
        recipient_user_id=UUID(auth["user"]["id"]),
        residency_region=auth["user"]["residency_region"],
        variables={"name": "Sanjar"},
    )

    headers = {"Authorization": f"Bearer {auth['tokens']['access_token']}"}
    listing = await http.get("/v1/notifications", headers=headers)
    nid = listing.json()["items"][0]["id"]
    mark = await http.post(f"/v1/notifications/{nid}/read", headers=headers)
    assert mark.status_code == 200, mark.text
    assert mark.json()["is_read"] is True


# --- Preferences ---------------------------------------------------------


@pytest.mark.asyncio
async def test_preferences_refuse_disable_critical(http: AsyncClient) -> None:
    auth = await _register(http)
    response = await http.patch(
        "/v1/notifications/preferences",
        headers={"Authorization": f"Bearer {auth['tokens']['access_token']}"},
        json=[
            {
                "category_slug": "account_security",
                "channel": "email",
                "enabled": False,
            }
        ],
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "notifications.critical_no_opt_out"


@pytest.mark.asyncio
async def test_preferences_disable_non_critical_ok(http: AsyncClient) -> None:
    auth = await _register(http)
    response = await http.patch(
        "/v1/notifications/preferences",
        headers={"Authorization": f"Bearer {auth['tokens']['access_token']}"},
        json=[
            {"category_slug": "marketing", "channel": "email", "enabled": False},
        ],
    )
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert any(
        i["category_slug"] == "marketing" and i["channel"] == "email" and i["enabled"] is False
        for i in items
    )


# --- Push devices ---------------------------------------------------------


@pytest.mark.asyncio
async def test_register_and_unregister_push_device(http: AsyncClient) -> None:
    auth = await _register(http)
    headers = {"Authorization": f"Bearer {auth['tokens']['access_token']}"}
    iid = f"inst-{uuid.uuid4().hex[:10]}"
    reg = await http.post(
        "/v1/notifications/push-devices",
        headers=headers,
        json={
            "platform": "android",
            "installation_id": iid,
            "fcm_token": "fcm-abc",
        },
    )
    assert reg.status_code == 201, reg.text
    assert reg.json()["installation_id"] == iid

    unreg = await http.delete(
        f"/v1/notifications/push-devices/{iid}",
        headers=headers,
    )
    assert unreg.status_code == 200
    assert unreg.json() == {"removed": True}


# --- Quiet hours --------------------------------------------------------


@pytest.mark.asyncio
async def test_quiet_hours_rejects_bad_weekday(http: AsyncClient) -> None:
    auth = await _register(http)
    response = await http.put(
        "/v1/notifications/quiet-hours",
        headers={"Authorization": f"Bearer {auth['tokens']['access_token']}"},
        json={
            "timezone": "Asia/Tashkent",
            "start_time": "22:00",
            "end_time": "08:00",
            "weekdays": [0, 1, 2, 9],
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_quiet_hours_accepts_valid_payload(http: AsyncClient) -> None:
    auth = await _register(http)
    response = await http.put(
        "/v1/notifications/quiet-hours",
        headers={"Authorization": f"Bearer {auth['tokens']['access_token']}"},
        json={
            "timezone": "Asia/Tashkent",
            "start_time": "22:00",
            "end_time": "08:00",
            "weekdays": [0, 1, 2, 3, 4],
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["timezone"] == "Asia/Tashkent"
    assert body["start_time"] == "22:00"
    assert body["weekdays"] == [0, 1, 2, 3, 4]
