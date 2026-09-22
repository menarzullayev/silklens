"""End-to-end auth flow tests.

Hits the running ASGI app via httpx; exercises register → login → refresh.
All requires the dev Postgres at port 5434 with migrations at head.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.integration


def _unique_email() -> str:
    return f"e2e-{uuid.uuid4().hex[:10]}@silklens-test.com"


def _strong_password() -> str:
    return "SilkLensTest1234"


# --- registration -----------------------------------------------------------


@pytest.mark.asyncio
async def test_register_creates_user_and_returns_tokens(http: AsyncClient) -> None:
    email = _unique_email()
    response = await http.post(
        "/v1/auth/register",
        json={"email": email, "password": _strong_password()},
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["user"]["pub_id"]
    assert payload["tokens"]["access_token"]
    assert payload["tokens"]["refresh_token"]
    assert payload["tokens"]["token_type"] == "Bearer"
    assert payload["tokens"]["expires_in"] > 0


@pytest.mark.asyncio
async def test_register_rejects_weak_password(http: AsyncClient) -> None:
    response = await http.post(
        "/v1/auth/register",
        json={"email": _unique_email(), "password": "weak"},
    )
    assert response.status_code == 422  # pydantic min_length=12 rejects first


@pytest.mark.asyncio
async def test_register_rejects_password_without_digit(http: AsyncClient) -> None:
    response = await http.post(
        "/v1/auth/register",
        json={"email": _unique_email(), "password": "NoDigitsHereXX"},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["detail"]["code"] == "identity.weak_password"


@pytest.mark.asyncio
async def test_register_rejects_duplicate_email(http: AsyncClient) -> None:
    email = _unique_email()
    first = await http.post(
        "/v1/auth/register",
        json={"email": email, "password": _strong_password()},
    )
    assert first.status_code == 201
    second = await http.post(
        "/v1/auth/register",
        json={"email": email, "password": _strong_password()},
    )
    assert second.status_code == 409
    body = second.json()
    assert body["detail"]["code"] == "identity.email_already_registered"


# --- login ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_returns_tokens_after_registration(http: AsyncClient) -> None:
    email = _unique_email()
    pwd = _strong_password()
    reg = await http.post("/v1/auth/register", json={"email": email, "password": pwd})
    assert reg.status_code == 201

    login = await http.post("/v1/auth/login", json={"email": email, "password": pwd})
    assert login.status_code == 200, login.text
    body = login.json()
    assert body["user"]["pub_id"] == reg.json()["user"]["pub_id"]
    assert body["tokens"]["access_token"]


@pytest.mark.asyncio
async def test_login_rejects_wrong_password(http: AsyncClient) -> None:
    email = _unique_email()
    await http.post(
        "/v1/auth/register",
        json={"email": email, "password": _strong_password()},
    )
    login = await http.post(
        "/v1/auth/login",
        json={"email": email, "password": "WrongPassword1234"},
    )
    assert login.status_code == 401
    assert login.json()["detail"]["code"] == "identity.invalid_credentials"


@pytest.mark.asyncio
async def test_login_rejects_unknown_email(http: AsyncClient) -> None:
    login = await http.post(
        "/v1/auth/login",
        json={"email": _unique_email(), "password": "SomePassword123"},
    )
    assert login.status_code == 401
    assert login.json()["detail"]["code"] == "identity.invalid_credentials"


# --- refresh ----------------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh_rotates_tokens(http: AsyncClient) -> None:
    email = _unique_email()
    pwd = _strong_password()
    reg = await http.post("/v1/auth/register", json={"email": email, "password": pwd})
    refresh_token = reg.json()["tokens"]["refresh_token"]

    refreshed = await http.post(
        "/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refreshed.status_code == 200, refreshed.text
    body = refreshed.json()
    assert body["tokens"]["refresh_token"] != refresh_token  # rotated


@pytest.mark.asyncio
async def test_refresh_replay_revokes_family(http: AsyncClient) -> None:
    email = _unique_email()
    reg = await http.post(
        "/v1/auth/register",
        json={"email": email, "password": _strong_password()},
    )
    refresh_token = reg.json()["tokens"]["refresh_token"]

    # First refresh succeeds
    ok = await http.post("/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert ok.status_code == 200

    # Reusing the original (now consumed) token must fail
    replay = await http.post("/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert replay.status_code == 401
    assert replay.json()["detail"]["code"] == "identity.refresh_token_reused"


# --- audit-side effect ------------------------------------------------------


@pytest.mark.asyncio
async def test_registration_writes_session_row(
    http: AsyncClient,
    db_session: AsyncSession,
) -> None:
    email = _unique_email()
    reg = await http.post(
        "/v1/auth/register",
        json={"email": email, "password": _strong_password()},
    )
    pub_id = reg.json()["user"]["pub_id"]
    count = (
        await db_session.execute(
            text(
                """
                SELECT count(*)
                FROM sessions s
                JOIN users u ON u.id = s.user_id AND u.residency_region = s.residency_region
                WHERE u.pub_id = :pub_id
                """
            ),
            {"pub_id": pub_id},
        )
    ).scalar_one()
    assert int(count) >= 1
