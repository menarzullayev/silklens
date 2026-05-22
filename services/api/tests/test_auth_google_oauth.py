"""Tests for /v1/auth/google — OAuth login via Google access token.

Mocks the Google tokeninfo + userinfo endpoints with httpx.MockTransport.
Covers three paths:
  1. New user (no existing email, no existing identity)
  2. Existing user matched by email (links identity, marks email verified)
  3. Existing identity (returning Google user)

Plus failure paths: bad token, missing email, missing subject.
"""

from __future__ import annotations

import uuid

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.integration


def _google_sub() -> str:
    return f"google-sub-{uuid.uuid4().hex[:12]}"


def _email() -> str:
    return f"google-{uuid.uuid4().hex[:10]}@silklens-test.com"


def _make_handler(
    *,
    tokeninfo_status: int = 200,
    tokeninfo_body: dict | None = None,
    userinfo_status: int = 200,
    userinfo_body: dict | None = None,
):
    """Build an httpx mock handler that routes tokeninfo + userinfo separately."""

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "tokeninfo" in url:
            return httpx.Response(tokeninfo_status, json=tokeninfo_body or {})
        if "userinfo" in url:
            return httpx.Response(userinfo_status, json=userinfo_body or {})
        return httpx.Response(404, json={"error": "unmocked"})

    return handler


@pytest.fixture
def mock_google(monkeypatch):
    """Yields a function that installs a Google mock for the duration of one test."""

    def install(handler):
        from src.api.routers import auth as auth_router

        transport = httpx.MockTransport(handler)
        real_async_client = httpx.AsyncClient
        monkeypatch.setattr(
            auth_router.httpx if hasattr(auth_router, "httpx") else httpx,
            "AsyncClient",
            lambda **kw: real_async_client(transport=transport, **kw),
        )

    return install


# --- Path 1: new user -------------------------------------------------------


@pytest.mark.asyncio
async def test_google_new_user_signup(
    http: AsyncClient, db_session: AsyncSession, monkeypatch
) -> None:
    email = _email()
    sub = _google_sub()

    handler = _make_handler(
        tokeninfo_body={
            "sub": sub,
            "email": email,
            "email_verified": "true",
        },
        userinfo_body={
            "sub": sub,
            "email": email,
            "email_verified": True,
            "name": "Test User",
            "picture": "https://example.com/avatar.jpg",
        },
    )

    # Patch httpx.AsyncClient inside auth router
    import httpx as _httpx_module

    transport = httpx.MockTransport(handler)
    real_async = _httpx_module.AsyncClient
    monkeypatch.setattr(
        _httpx_module,
        "AsyncClient",
        lambda **kw: real_async(transport=transport, **kw),
    )

    response = await http.post("/v1/auth/google", json={"access_token": "fake_token"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["user"]["pub_id"]
    assert body["user"]["is_verified"] is True
    assert body["tokens"]["access_token"]

    # DB checks: user, user_emails (verified), user_profiles (name+avatar), user_identities
    user_id = body["user"]["id"]
    user_row = (
        await db_session.execute(
            text(
                "SELECT email_verified_at, status FROM users WHERE id = :id"
            ),
            {"id": user_id},
        )
    ).first()
    assert user_row.email_verified_at is not None
    assert user_row.status == "active"

    profile = (
        await db_session.execute(
            text(
                "SELECT display_name, avatar_url FROM user_profiles WHERE user_id = :id"
            ),
            {"id": user_id},
        )
    ).first()
    assert profile.display_name == "Test User"
    assert profile.avatar_url == "https://example.com/avatar.jpg"

    identity = (
        await db_session.execute(
            text(
                "SELECT provider_subject, email_at_link FROM user_identities WHERE user_id = :id"
            ),
            {"id": user_id},
        )
    ).first()
    assert identity.provider_subject == sub
    assert identity.email_at_link == email


# --- Path 2: existing user linked by email ----------------------------------


@pytest.mark.asyncio
async def test_google_links_existing_user_by_email(
    http: AsyncClient, db_session: AsyncSession, monkeypatch
) -> None:
    email = _email()
    sub = _google_sub()

    # First, register via password
    reg = await http.post(
        "/v1/auth/register",
        json={"email": email, "password": "SilkLensTest1234"},
    )
    assert reg.status_code == 201
    user_id = reg.json()["user"]["id"]

    # Now sign in via Google with same email
    handler = _make_handler(
        tokeninfo_body={"sub": sub, "email": email, "email_verified": "true"},
        userinfo_body={
            "sub": sub,
            "email": email,
            "email_verified": True,
            "name": "Linked User",
            "picture": "https://example.com/linked.jpg",
        },
    )
    import httpx as _httpx_module

    transport = httpx.MockTransport(handler)
    real_async = _httpx_module.AsyncClient
    monkeypatch.setattr(
        _httpx_module,
        "AsyncClient",
        lambda **kw: real_async(transport=transport, **kw),
    )

    response = await http.post("/v1/auth/google", json={"access_token": "fake_token"})
    assert response.status_code == 200
    assert response.json()["user"]["id"] == user_id  # same user, not a new one

    # Identity now linked
    identity = (
        await db_session.execute(
            text(
                "SELECT count(*) AS n FROM user_identities WHERE user_id = :id"
            ),
            {"id": user_id},
        )
    ).first()
    assert identity.n == 1


# --- Path 3: returning Google user ------------------------------------------


@pytest.mark.asyncio
async def test_google_returning_user_finds_by_identity(
    http: AsyncClient, db_session: AsyncSession, monkeypatch
) -> None:
    email = _email()
    sub = _google_sub()

    handler = _make_handler(
        tokeninfo_body={"sub": sub, "email": email, "email_verified": "true"},
        userinfo_body={
            "sub": sub,
            "email": email,
            "email_verified": True,
            "name": "First Visit",
        },
    )
    import httpx as _httpx_module

    transport = httpx.MockTransport(handler)
    real_async = _httpx_module.AsyncClient
    monkeypatch.setattr(
        _httpx_module,
        "AsyncClient",
        lambda **kw: real_async(transport=transport, **kw),
    )

    first = await http.post("/v1/auth/google", json={"access_token": "tok1"})
    assert first.status_code == 200
    user_id = first.json()["user"]["id"]

    # Second visit — different access_token, same sub
    second_handler = _make_handler(
        tokeninfo_body={"sub": sub, "email": email, "email_verified": "true"},
        userinfo_body={
            "sub": sub,
            "email": email,
            "email_verified": True,
            # different display name; should NOT overwrite on subsequent visits
            "name": "Return Visit",
        },
    )
    transport2 = httpx.MockTransport(second_handler)
    monkeypatch.setattr(
        _httpx_module,
        "AsyncClient",
        lambda **kw: real_async(transport=transport2, **kw),
    )

    second = await http.post("/v1/auth/google", json={"access_token": "tok2"})
    assert second.status_code == 200
    assert second.json()["user"]["id"] == user_id  # same user

    # display_name should remain "First Visit" — upsert_oauth_identity uses
    # was_inserted flag to preserve user edits on subsequent logins
    profile = (
        await db_session.execute(
            text(
                "SELECT display_name FROM user_profiles WHERE user_id = :id"
            ),
            {"id": user_id},
        )
    ).first()
    assert profile.display_name == "First Visit"


# --- Failure paths ----------------------------------------------------------


@pytest.mark.asyncio
async def test_google_rejects_invalid_token(http: AsyncClient, monkeypatch) -> None:
    handler = _make_handler(tokeninfo_status=400, tokeninfo_body={"error": "invalid"})
    import httpx as _httpx_module

    transport = httpx.MockTransport(handler)
    real_async = _httpx_module.AsyncClient
    monkeypatch.setattr(
        _httpx_module,
        "AsyncClient",
        lambda **kw: real_async(transport=transport, **kw),
    )

    response = await http.post("/v1/auth/google", json={"access_token": "bad"})
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "GOOGLE_TOKEN_INVALID"


@pytest.mark.asyncio
async def test_google_rejects_missing_email(http: AsyncClient, monkeypatch) -> None:
    sub = _google_sub()
    handler = _make_handler(
        tokeninfo_body={"sub": sub, "email_verified": "true"},  # no email
        userinfo_body={"sub": sub},  # no email
    )
    import httpx as _httpx_module

    transport = httpx.MockTransport(handler)
    real_async = _httpx_module.AsyncClient
    monkeypatch.setattr(
        _httpx_module,
        "AsyncClient",
        lambda **kw: real_async(transport=transport, **kw),
    )

    response = await http.post("/v1/auth/google", json={"access_token": "tok"})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "GOOGLE_NO_EMAIL"


@pytest.mark.asyncio
async def test_google_rejects_missing_subject(http: AsyncClient, monkeypatch) -> None:
    email = _email()
    handler = _make_handler(
        tokeninfo_body={"email": email, "email_verified": "true"},  # no sub
        userinfo_body={"email": email},  # no sub
    )
    import httpx as _httpx_module

    transport = httpx.MockTransport(handler)
    real_async = _httpx_module.AsyncClient
    monkeypatch.setattr(
        _httpx_module,
        "AsyncClient",
        lambda **kw: real_async(transport=transport, **kw),
    )

    response = await http.post("/v1/auth/google", json={"access_token": "tok"})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "GOOGLE_NO_SUB"
