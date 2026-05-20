"""Tests for /v1/auth/verify-email and /v1/auth/resend-verification.

Covers OTP consumption, idempotency, wrong-code rejection, auth gating on
resend, and the DB side-effects (email_verified_at + status='active').
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.notifications import otp_service

pytestmark = pytest.mark.integration


def _email() -> str:
    return f"verify-{uuid.uuid4().hex[:10]}@silklens-test.com"


def _password() -> str:
    return "SilkLensTest1234"


async def _register(http: AsyncClient, email: str) -> dict:
    """Register a user and return the token bundle."""
    response = await http.post(
        "/v1/auth/register",
        json={"email": email, "password": _password()},
    )
    assert response.status_code == 201, response.text
    return response.json()


# --- /v1/auth/verify-email --------------------------------------------------


@pytest.mark.asyncio
async def test_verify_email_marks_user_verified(
    http: AsyncClient, db_session: AsyncSession
) -> None:
    email = _email()
    bundle = await _register(http, email)
    user_id = bundle["user"]["id"]

    # The register endpoint generates a code; grab it directly from Redis.
    code = await _read_otp(email)
    assert code is not None, "register endpoint did not store OTP"

    bearer = bundle["tokens"]["access_token"]
    response = await http.post(
        "/v1/auth/verify-email",
        json={"email": email, "code": code},
        headers={"Authorization": f"Bearer {bearer}"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["verified"] is True

    # DB side-effects
    row = await db_session.execute(
        text(
            "SELECT email_verified_at, status FROM users WHERE id = :id"
        ),
        {"id": user_id},
    )
    user_row = row.first()
    assert user_row.email_verified_at is not None
    assert user_row.status == "active"

    email_row = await db_session.execute(
        text(
            "SELECT verified_at FROM user_emails WHERE user_id = :id AND is_primary = true"
        ),
        {"id": user_id},
    )
    assert email_row.first().verified_at is not None


@pytest.mark.asyncio
async def test_verify_email_rejects_wrong_code(http: AsyncClient) -> None:
    email = _email()
    bundle = await _register(http, email)
    bearer = bundle["tokens"]["access_token"]

    response = await http.post(
        "/v1/auth/verify-email",
        json={"email": email, "code": "000000"},
        headers={"Authorization": f"Bearer {bearer}"},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "OTP_INVALID"


@pytest.mark.asyncio
async def test_verify_email_rejects_expired_code(http: AsyncClient) -> None:
    """No OTP in Redis (already consumed / never generated) → 400."""
    email = _email()
    bundle = await _register(http, email)
    bearer = bundle["tokens"]["access_token"]

    # Drain the OTP first by verifying with the real code
    real_code = await _read_otp(email)
    assert real_code is not None
    first = await http.post(
        "/v1/auth/verify-email",
        json={"email": email, "code": real_code},
        headers={"Authorization": f"Bearer {bearer}"},
    )
    assert first.status_code == 200

    # Second attempt with same code → 400 (one-shot semantics)
    second = await http.post(
        "/v1/auth/verify-email",
        json={"email": email, "code": real_code},
        headers={"Authorization": f"Bearer {bearer}"},
    )
    assert second.status_code == 400
    assert second.json()["detail"]["code"] == "OTP_INVALID"


@pytest.mark.asyncio
async def test_verify_email_requires_authentication(http: AsyncClient) -> None:
    response = await http.post(
        "/v1/auth/verify-email",
        json={"email": _email(), "code": "123456"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_verify_email_rejects_malformed_code(http: AsyncClient) -> None:
    """Pydantic should reject non-6-digit / non-numeric codes."""
    email = _email()
    bundle = await _register(http, email)
    bearer = bundle["tokens"]["access_token"]

    for bad_code in ("12345", "1234567", "abcdef", "12-345"):
        response = await http.post(
            "/v1/auth/verify-email",
            json={"email": email, "code": bad_code},
            headers={"Authorization": f"Bearer {bearer}"},
        )
        assert response.status_code == 422, f"expected 422 for {bad_code!r}"


# --- /v1/auth/resend-verification -------------------------------------------


@pytest.mark.asyncio
async def test_resend_generates_new_otp(http: AsyncClient) -> None:
    email = _email()
    bundle = await _register(http, email)
    bearer = bundle["tokens"]["access_token"]

    original = await _read_otp(email)
    assert original is not None

    response = await http.post(
        "/v1/auth/resend-verification",
        json={"email": email},
        headers={"Authorization": f"Bearer {bearer}"},
    )
    assert response.status_code == 200
    assert response.json()["sent"] is True

    # New OTP must be present (could match original by chance but key still set)
    new_code = await _read_otp(email)
    assert new_code is not None


@pytest.mark.asyncio
async def test_resend_requires_authentication(http: AsyncClient) -> None:
    response = await http.post(
        "/v1/auth/resend-verification",
        json={"email": _email()},
    )
    assert response.status_code == 401


# --- helpers ----------------------------------------------------------------


async def _read_otp(email: str) -> str | None:
    """Read the OTP directly from Redis (bypasses verify which consumes)."""
    import redis.asyncio as aioredis

    from src.core.settings import get_settings

    settings = get_settings()
    client = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        return await client.get(f"otp:email_verify:{email.lower().strip()}")
    finally:
        await client.aclose()
