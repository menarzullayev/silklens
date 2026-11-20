"""Redis-backed email OTP service.

Generates a 6-digit code, stores it with a TTL, and verifies it in one
atomic operation (verify + delete on match).
"""

from __future__ import annotations

import secrets

import redis.asyncio as aioredis

from src.core.logging import get_logger
from src.core.settings import get_settings

log = get_logger("silklens.notifications.otp")

_KEY_PREFIX = "otp:email_verify:"


def _key(email: str) -> str:
    return f"{_KEY_PREFIX}{email.lower().strip()}"


def _client() -> aioredis.Redis:
    settings = get_settings()
    return aioredis.from_url(settings.redis_url, decode_responses=True)


async def generate_and_store(email: str) -> str:
    """Generate a 6-digit OTP, store it in Redis with TTL, and return it."""
    settings = get_settings()
    code = f"{secrets.randbelow(1_000_000):06d}"
    async with _client() as r:
        await r.setex(_key(email), settings.email_otp_ttl_seconds, code)
    log.info("otp.generated", email=email)
    return code


async def verify_and_consume(email: str, code: str) -> bool:
    """Return True and delete the key if the code matches; False otherwise."""
    async with _client() as r:
        stored = await r.get(_key(email))
        if stored is None:
            log.warning("otp.expired_or_missing", email=email)
            return False
        if stored != code:
            log.warning("otp.wrong_code", email=email)
            return False
        await r.delete(_key(email))
    log.info("otp.verified", email=email)
    return True
