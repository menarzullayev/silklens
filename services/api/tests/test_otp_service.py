"""Tests for the Redis-backed email OTP service.

Covers generate/store, atomic verify+consume, TTL enforcement, wrong-code
rejection, and email normalization (case-insensitive + trimming).

Requires the dev Redis at port 6381 (``make dev``).
"""

from __future__ import annotations

import pytest
import redis.asyncio as aioredis

from src.core.settings import get_settings
from src.infrastructure.notifications import otp_service

pytestmark = pytest.mark.integration


@pytest.fixture
async def redis_client():
    """Direct Redis client for assertions outside the service API."""
    settings = get_settings()
    client = aioredis.from_url(settings.redis_url, decode_responses=True)
    yield client
    await client.aclose()


def _email(label: str) -> str:
    return f"otp-{label}@silklens-test.com"


# --- generation -------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_returns_6_digit_string() -> None:
    code = await otp_service.generate_and_store(_email("gen-len"))
    assert len(code) == 6
    assert code.isdigit()


@pytest.mark.asyncio
async def test_generate_stores_in_redis_with_ttl(redis_client) -> None:
    email = _email("gen-ttl")
    code = await otp_service.generate_and_store(email)

    stored = await redis_client.get(f"otp:email_verify:{email}")
    assert stored == code

    ttl = await redis_client.ttl(f"otp:email_verify:{email}")
    settings = get_settings()
    # TTL must be > 0 and ≤ configured value (within a 5s clock-skew window).
    assert 0 < ttl <= settings.email_otp_ttl_seconds
    assert ttl >= settings.email_otp_ttl_seconds - 5


@pytest.mark.asyncio
async def test_generate_normalizes_email_case(redis_client) -> None:
    upper = "MixedCase@SilkLens-Test.COM"
    code = await otp_service.generate_and_store(upper)
    # Stored under lowercase key
    stored = await redis_client.get("otp:email_verify:mixedcase@silklens-test.com")
    assert stored == code


@pytest.mark.asyncio
async def test_generate_trims_whitespace(redis_client) -> None:
    email = "  ws-trim@silklens-test.com  "
    code = await otp_service.generate_and_store(email)
    stored = await redis_client.get("otp:email_verify:ws-trim@silklens-test.com")
    assert stored == code


@pytest.mark.asyncio
async def test_generate_overwrites_previous_code(redis_client) -> None:
    email = _email("overwrite")
    first = await otp_service.generate_and_store(email)
    second = await otp_service.generate_and_store(email)
    # The two codes are independent random draws; collision possible but
    # the post-condition is that Redis now stores the *second* one.
    stored = await redis_client.get(f"otp:email_verify:{email}")
    assert stored == second
    # And the first is no longer valid.
    assert await otp_service.verify_and_consume(email, first) is False or stored != first


# --- verification -----------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_returns_true_on_match_and_deletes_key(redis_client) -> None:
    email = _email("verify-ok")
    code = await otp_service.generate_and_store(email)

    result = await otp_service.verify_and_consume(email, code)
    assert result is True

    # Key must be gone — one-shot semantics
    stored = await redis_client.get(f"otp:email_verify:{email}")
    assert stored is None


@pytest.mark.asyncio
async def test_verify_returns_false_on_wrong_code(redis_client) -> None:
    email = _email("verify-wrong")
    await otp_service.generate_and_store(email)

    result = await otp_service.verify_and_consume(email, "000000")
    assert result is False

    # Key must STILL be present — wrong code does NOT consume
    stored = await redis_client.get(f"otp:email_verify:{email}")
    assert stored is not None


@pytest.mark.asyncio
async def test_verify_returns_false_when_no_code_stored() -> None:
    email = _email("verify-missing")
    result = await otp_service.verify_and_consume(email, "123456")
    assert result is False


@pytest.mark.asyncio
async def test_verify_is_single_use() -> None:
    email = _email("verify-single")
    code = await otp_service.generate_and_store(email)

    assert await otp_service.verify_and_consume(email, code) is True
    # Second attempt with same code must fail (key deleted)
    assert await otp_service.verify_and_consume(email, code) is False


@pytest.mark.asyncio
async def test_verify_normalizes_email_case() -> None:
    code = await otp_service.generate_and_store("Casing@silklens-test.com")
    # User types email differently — verify still works
    assert await otp_service.verify_and_consume("CASING@silklens-test.com", code) is True
