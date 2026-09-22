"""Tests for ``BearerContextMiddleware`` and protected /me + /logout endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from httpx import AsyncClient

from src.core.settings import get_settings

pytestmark = pytest.mark.integration


def _unique_email() -> str:
    return f"mw-{uuid.uuid4().hex[:10]}@silklens-test.com"


def _strong_password() -> str:
    return "MiddlewareTest1234"


async def _register_and_login(http: AsyncClient) -> dict[str, str]:
    payload = await http.post(
        "/v1/auth/register",
        json={"email": _unique_email(), "password": _strong_password()},
    )
    assert payload.status_code == 201
    body = payload.json()
    return body["tokens"]


# --- /me ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_me_requires_authentication(http: AsyncClient) -> None:
    response = await http.get("/v1/auth/me")
    assert response.status_code == 401
    body = response.json()
    assert body["detail"]["code"] == "identity.unauthenticated"
    assert response.headers.get("WWW-Authenticate") == "Bearer"


@pytest.mark.asyncio
async def test_me_returns_current_user(http: AsyncClient) -> None:
    tokens = await _register_and_login(http)
    response = await http.get(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["user"]["pub_id"]
    assert uuid.UUID(body["session_id"])
    assert body["trust_tier"] == "new"


@pytest.mark.asyncio
async def test_me_rejects_invalid_token(http: AsyncClient) -> None:
    response = await http.get(
        "/v1/auth/me",
        headers={"Authorization": "Bearer this-is-not-a-jwt"},
    )
    assert response.status_code == 401
    body = response.json()
    assert body["detail"]["code"] == "identity.token_invalid"


@pytest.mark.asyncio
async def test_me_rejects_expired_token(http: AsyncClient) -> None:
    settings = get_settings()
    # Mint a token in the past using the same signing key
    past = datetime.now(UTC) - timedelta(hours=1)
    claims = {
        "iss": "silklens.api",
        "sub": str(uuid.uuid4()),
        "sid": str(uuid.uuid4()),
        "tenant": settings.default_tenant_id,
        "residency": "global",
        "trust_tier": "new",
        "iat": int(past.timestamp()),
        "exp": int((past + timedelta(seconds=60)).timestamp()),
    }
    token = jwt.encode(
        claims,
        settings.jwt_secret.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    response = await http.get(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "identity.token_expired"


@pytest.mark.asyncio
async def test_me_ignores_wrong_scheme(http: AsyncClient) -> None:
    # Anything other than "Bearer " is silently ignored; treated as anonymous.
    response = await http.get(
        "/v1/auth/me",
        headers={"Authorization": "Basic Zm9vOmJhcg=="},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "identity.unauthenticated"


# --- /logout -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_logout_revokes_session(http: AsyncClient) -> None:
    tokens = await _register_and_login(http)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    # Confirm /me works while the access token is fresh
    pre = await http.get("/v1/auth/me", headers=headers)
    assert pre.status_code == 200

    logout = await http.post("/v1/auth/logout", headers=headers)
    assert logout.status_code == 200
    assert logout.json()["status"] == "ok"

    # The access token is still cryptographically valid until exp (we don't
    # blacklist), so /me still works briefly. Refresh, however, must be revoked.
    refresh = await http.post(
        "/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh.status_code == 401
    assert refresh.json()["detail"]["code"] == "identity.refresh_token_reused"


@pytest.mark.asyncio
async def test_logout_requires_authentication(http: AsyncClient) -> None:
    response = await http.post("/v1/auth/logout")
    assert response.status_code == 401
