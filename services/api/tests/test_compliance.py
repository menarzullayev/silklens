"""Compliance integration tests — GDPR + UZ PD-law surface.

Covers the legal-document publication path, consent record/withdraw round
trip, GDPR data-export request creation (with Celery task triggered through
the in-memory queue stub), the 30-day deletion grace period, cancel-deletion
inside / outside the grace window, the cookie-consent banner endpoint, and
the ``app.anonymize_user()`` SQL function.

All tests are integration-grade and skip cleanly when the dev DB is offline
(courtesy of conftest.py's ``_apply_migrations`` fixture).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routers import compliance as compliance_router
from src.infrastructure.compliance.tasks import InMemoryTaskQueue

pytestmark = pytest.mark.integration


# --- Helpers ----------------------------------------------------------------


def _email() -> str:
    return f"compliance-{uuid.uuid4().hex[:10]}@silklens-test.com"


async def _register(http: AsyncClient) -> dict[str, Any]:
    response = await http.post(
        "/v1/auth/register",
        json={"email": _email(), "password": "CompliancePwd1234"},
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


async def _provision_admin(http: AsyncClient, db_session: AsyncSession) -> tuple[str, str]:
    auth = await _register(http)
    await _grant_role(db_session, auth["user"]["pub_id"], "super_admin")
    return auth["tokens"]["access_token"], auth["user"]["pub_id"]


@pytest.fixture(autouse=True)
def _reset_task_queue():
    """Each test gets a fresh in-memory task queue.

    Production wiring will swap ``_TASK_QUEUE`` for a Celery client; for tests
    we point it at a clean ``InMemoryTaskQueue`` so we can introspect calls.
    """
    fresh = InMemoryTaskQueue()
    compliance_router._TASK_QUEUE = fresh
    yield fresh
    compliance_router._TASK_QUEUE = InMemoryTaskQueue()


# --- Legal documents --------------------------------------------------------


@pytest.mark.asyncio
async def test_legal_privacy_policy_returns_latest_en_default(http: AsyncClient) -> None:
    response = await http.get("/v1/legal/privacy_policy")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["kind"] == "privacy_policy"
    assert body["language_tag"] == "en"
    assert body["sha256"]
    assert body["version"]


@pytest.mark.asyncio
async def test_legal_policy_falls_back_to_english_when_lang_missing(
    http: AsyncClient,
) -> None:
    # 'fr' has no seeded row; the service falls back to 'en'.
    response = await http.get("/v1/legal/tos", headers={"Accept-Language": "fr"})
    assert response.status_code == 200
    assert response.json()["language_tag"] == "en"


@pytest.mark.asyncio
async def test_legal_unknown_kind_returns_404(http: AsyncClient) -> None:
    response = await http.get("/v1/legal/not_a_kind")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_publish_new_policy_requires_tenant_manage(
    http: AsyncClient, db_session: AsyncSession
) -> None:
    auth = await _register(http)
    response = await http.post(
        "/v1/legal/privacy_policy",
        json={
            "version": "2.0.0",
            "language_tag": "en",
            "content_md": "# v2 policy\n\nupdated terms apply",
        },
        headers={"Authorization": f"Bearer {auth['tokens']['access_token']}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_publish_new_policy_succeeds_for_admin(
    http: AsyncClient, db_session: AsyncSession
) -> None:
    admin_token, _ = await _provision_admin(http, db_session)
    suffix = uuid.uuid4().hex[:6]
    response = await http.post(
        "/v1/legal/privacy_policy",
        json={
            "version": f"2.0.0-{suffix}",
            "language_tag": "en",
            "content_md": "# v2 policy\n\nupdated terms apply",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["version"] == f"2.0.0-{suffix}"
    assert body["sha256"]


# --- Consent records --------------------------------------------------------


@pytest.mark.asyncio
async def test_consent_grant_then_withdraw_round_trip(
    http: AsyncClient,
) -> None:
    auth = await _register(http)
    token = auth["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    policy = await http.get("/v1/legal/privacy_policy")
    doc_id = policy.json()["id"]

    granted = await http.post(
        "/v1/me/consents",
        json={"legal_document_id": doc_id, "basis": "consent"},
        headers=headers,
    )
    assert granted.status_code == 201, granted.text
    assert granted.json()["withdrawn_at"] is None

    listed = await http.get("/v1/me/consents", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) >= 1

    withdrawn = await http.delete(f"/v1/me/consents/{doc_id}", headers=headers)
    assert withdrawn.status_code == 200
    assert withdrawn.json()["withdrawn_at"] is not None


@pytest.mark.asyncio
async def test_withdraw_unknown_consent_returns_404(http: AsyncClient) -> None:
    auth = await _register(http)
    headers = {"Authorization": f"Bearer {auth['tokens']['access_token']}"}
    response = await http.delete(f"/v1/me/consents/{uuid.uuid4()}", headers=headers)
    assert response.status_code == 404


# --- Data export ------------------------------------------------------------


@pytest.mark.asyncio
async def test_data_export_creates_request_and_enqueues_task(
    http: AsyncClient, _reset_task_queue: InMemoryTaskQueue
) -> None:
    auth = await _register(http)
    headers = {"Authorization": f"Bearer {auth['tokens']['access_token']}"}

    response = await http.post("/v1/me/data-export", headers=headers)
    assert response.status_code == 202, response.text
    body = response.json()
    assert body["request_kind"] == "export"
    assert body["status"] == "submitted"

    # The in-memory task queue should have captured the enqueue call.
    assert len(_reset_task_queue.exports) == 1
    captured = _reset_task_queue.exports[0]
    assert str(captured["request_id"]) == body["id"]


@pytest.mark.asyncio
async def test_data_export_status_lookup(http: AsyncClient) -> None:
    auth = await _register(http)
    headers = {"Authorization": f"Bearer {auth['tokens']['access_token']}"}

    created = await http.post("/v1/me/data-export", headers=headers)
    request_id = created.json()["id"]

    fetched = await http.get(f"/v1/me/data-export/{request_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["id"] == request_id


@pytest.mark.asyncio
async def test_data_export_lookup_rejects_other_users_request(
    http: AsyncClient,
) -> None:
    auth_a = await _register(http)
    created = await http.post(
        "/v1/me/data-export",
        headers={"Authorization": f"Bearer {auth_a['tokens']['access_token']}"},
    )
    request_id = created.json()["id"]

    auth_b = await _register(http)
    response = await http.get(
        f"/v1/me/data-export/{request_id}",
        headers={"Authorization": f"Bearer {auth_b['tokens']['access_token']}"},
    )
    assert response.status_code == 404


# --- Account deletion -------------------------------------------------------


@pytest.mark.asyncio
async def test_account_delete_schedules_30_day_anonymization(
    http: AsyncClient, db_session: AsyncSession, _reset_task_queue: InMemoryTaskQueue
) -> None:
    auth = await _register(http)
    headers = {"Authorization": f"Bearer {auth['tokens']['access_token']}"}

    response = await http.post("/v1/me/account/delete", json={"reason": "test"}, headers=headers)
    assert response.status_code == 202, response.text
    body = response.json()
    assert body["request_kind"] == "delete"

    scheduled_for = datetime.fromisoformat(body["scheduled_for"])
    delta = scheduled_for - datetime.now(UTC)
    # +30 days with a generous tolerance window.
    assert timedelta(days=29, hours=23) < delta < timedelta(days=30, hours=1)

    assert len(_reset_task_queue.anonymizations) == 1
    # A pending anonymization_jobs row should exist for the user.
    row = await db_session.execute(
        text(
            """
            SELECT count(*) FROM anonymization_jobs aj
            JOIN users u ON u.id = aj.user_id AND u.residency_region = aj.residency_region
            WHERE u.pub_id = :pub_id AND aj.status = 'pending'
            """
        ),
        {"pub_id": auth["user"]["pub_id"]},
    )
    assert row.scalar_one() == 1


@pytest.mark.asyncio
async def test_account_delete_duplicate_returns_conflict(http: AsyncClient) -> None:
    auth = await _register(http)
    headers = {"Authorization": f"Bearer {auth['tokens']['access_token']}"}

    first = await http.post("/v1/me/account/delete", json={}, headers=headers)
    assert first.status_code == 202

    second = await http.post("/v1/me/account/delete", json={}, headers=headers)
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "compliance.deletion_already_scheduled"


@pytest.mark.asyncio
async def test_cancel_deletion_inside_grace_period(
    http: AsyncClient, db_session: AsyncSession
) -> None:
    auth = await _register(http)
    headers = {"Authorization": f"Bearer {auth['tokens']['access_token']}"}

    created = await http.post("/v1/me/account/delete", json={}, headers=headers)
    request_id = created.json()["id"]

    cancelled = await http.post(
        "/v1/me/account/delete/cancel",
        json={"request_id": request_id},
        headers=headers,
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "cancelled"

    # the anonymization_jobs row should have been cancelled too.
    status_row = await db_session.execute(
        text(
            """
            SELECT status FROM anonymization_jobs
            WHERE gdpr_request_id = :req
            """
        ),
        {"req": uuid.UUID(request_id)},
    )
    assert status_row.scalar_one() == "cancelled"


@pytest.mark.asyncio
async def test_cancel_deletion_outside_grace_fails(
    http: AsyncClient, db_session: AsyncSession
) -> None:
    auth = await _register(http)
    headers = {"Authorization": f"Bearer {auth['tokens']['access_token']}"}

    created = await http.post("/v1/me/account/delete", json={}, headers=headers)
    request_id = created.json()["id"]

    # Backdate the schedule into the past to simulate the grace period
    # elapsing without waiting 30 days.
    await db_session.execute(
        text(
            """
            UPDATE gdpr_requests
            SET scheduled_for = now() - interval '1 day'
            WHERE id = :id
            """
        ),
        {"id": uuid.UUID(request_id)},
    )
    await db_session.commit()

    response = await http.post(
        "/v1/me/account/delete/cancel",
        json={"request_id": request_id},
        headers=headers,
    )
    assert response.status_code == 410
    assert response.json()["detail"]["code"] == "compliance.grace_period_expired"


# --- anonymize_user() SQL function ------------------------------------------


@pytest.mark.asyncio
async def test_anonymize_user_function_scrubs_email_and_profile(
    http: AsyncClient, db_session: AsyncSession
) -> None:
    auth = await _register(http)

    user_row = await db_session.execute(
        text("SELECT id, residency_region FROM users WHERE pub_id = :p"),
        {"p": auth["user"]["pub_id"]},
    )
    user_id, residency = user_row.one()

    original_email = (
        await db_session.execute(
            text("SELECT email::text FROM user_emails WHERE user_id = :u"),
            {"u": user_id},
        )
    ).scalar_one()

    result = await db_session.execute(
        text("SELECT app.anonymize_user(:u, :r)"),
        {"u": user_id, "r": residency},
    )
    payload = result.scalar_one()
    await db_session.commit()

    assert payload is not None
    new_email = (
        await db_session.execute(
            text("SELECT email::text FROM user_emails WHERE user_id = :u"),
            {"u": user_id},
        )
    ).scalar_one()
    assert new_email != original_email
    assert new_email.endswith("@deleted.silklens.invalid")

    user_status = (
        await db_session.execute(
            text("SELECT status, anonymized_at FROM users WHERE id = :u"),
            {"u": user_id},
        )
    ).one()
    assert user_status[0] == "deleted"
    assert user_status[1] is not None

    display_name = (
        await db_session.execute(
            text("SELECT display_name::text FROM user_profiles WHERE user_id = :u"),
            {"u": user_id},
        )
    ).scalar_one()
    assert display_name == "__deleted__"


# --- Cookie consent ---------------------------------------------------------


@pytest.mark.asyncio
async def test_public_cookie_consent_records_choice(http: AsyncClient) -> None:
    sid = f"sid-{uuid.uuid4().hex}"
    response = await http.post(
        "/v1/public/cookie-consent",
        json={
            "session_cookie_id": sid,
            "analytics": True,
            "marketing": False,
            "ad_targeting": False,
            "region": "eu",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["session_cookie_id"] == sid
    assert body["categories"]["strictly_necessary"] is True
    assert body["categories"]["analytics"] is True
    assert body["categories"]["marketing"] is False
    assert body["region"] == "eu"


# --- Admin processing -------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_process_request_marks_completed(
    http: AsyncClient, db_session: AsyncSession
) -> None:
    user_auth = await _register(http)
    user_headers = {"Authorization": f"Bearer {user_auth['tokens']['access_token']}"}
    created = await http.post("/v1/me/data-export", headers=user_headers)
    request_id = created.json()["id"]

    admin_token, _ = await _provision_admin(http, db_session)
    response = await http.post(
        f"/v1/admin/gdpr-requests/{request_id}/process",
        json={"payload_url": "s3://silklens/exports/demo.json", "decision_note": "ok"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "completed"
    assert body["payload_url"] == "s3://silklens/exports/demo.json"


# --- consent emits event ----------------------------------------------------


@pytest.mark.asyncio
async def test_consent_emits_consent_changed_event(
    http: AsyncClient, db_session: AsyncSession
) -> None:
    auth = await _register(http)
    headers = {"Authorization": f"Bearer {auth['tokens']['access_token']}"}

    policy = await http.get("/v1/legal/privacy_policy")
    doc_id = policy.json()["id"]

    response = await http.post(
        "/v1/me/consents",
        json={"legal_document_id": doc_id, "basis": "consent"},
        headers=headers,
    )
    assert response.status_code == 201

    event = (
        await db_session.execute(
            text(
                """
                SELECT event_name FROM event_outbox
                WHERE event_name = 'consent.changed.v1'
                  AND aggregate_id = (SELECT id FROM users WHERE pub_id = :p)
                ORDER BY created_at DESC LIMIT 1
                """
            ),
            {"p": auth["user"]["pub_id"]},
        )
    ).scalar_one_or_none()
    assert event == "consent.changed.v1"
