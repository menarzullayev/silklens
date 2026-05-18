"""Argon2id password hashing + JWT token issuance.

These are infrastructure-layer concrete implementations of the domain
protocols ``PasswordHasher`` and ``TokenIssuer``.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from argon2 import PasswordHasher as Argon2Hasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from src.core.settings import get_settings
from src.domain.identity.entities import User


class Argon2PasswordHasher:
    """Argon2id with project-wide parameters. Per ADR-0003 lives in infrastructure."""

    def __init__(
        self,
        *,
        time_cost: int = 3,
        memory_cost: int = 64 * 1024,  # 64 MiB
        parallelism: int = 2,
        hash_len: int = 32,
        salt_len: int = 16,
    ) -> None:
        self._hasher = Argon2Hasher(
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
            hash_len=hash_len,
            salt_len=salt_len,
        )

    @property
    def algorithm(self) -> str:
        return "argon2id"

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, hashed: str, password: str) -> bool:
        try:
            return self._hasher.verify(hashed, password)
        except (VerifyMismatchError, InvalidHashError):
            return False


class JwtTokenIssuer:
    """JWT access tokens + opaque (hashed) refresh tokens.

    Access tokens carry ``sub`` (user_id), ``sid`` (session_id), ``tenant``,
    ``residency``, ``roles`` (omitted at FAZA 1 — fetched server-side via
    ``app.has_permission``), and standard claims (``iat``, ``exp``, ``iss``).
    """

    def __init__(
        self,
        *,
        secret: str | None = None,
        algorithm: str | None = None,
        access_ttl: int | None = None,
        refresh_ttl: int | None = None,
        issuer: str = "silklens.api",
    ) -> None:
        settings = get_settings()
        self._secret = secret or settings.jwt_secret.get_secret_value()
        self._algorithm = algorithm or settings.jwt_algorithm
        self._access_ttl = access_ttl or settings.jwt_access_token_ttl_seconds
        self._refresh_ttl = refresh_ttl or settings.jwt_refresh_token_ttl_seconds
        self._issuer = issuer

    def issue_access(self, *, user: User, session_id: UUID) -> tuple[str, datetime]:
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=self._access_ttl)
        claims = {
            "iss": self._issuer,
            "sub": str(user.id),
            "sid": str(session_id),
            "tenant": str(user.tenant_id),
            "residency": user.residency_region.value,
            "trust_tier": user.trust_tier.value,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
        }
        token = jwt.encode(claims, self._secret, algorithm=self._algorithm)
        return token, expires_at

    def issue_refresh(self) -> tuple[str, bytes, datetime]:
        plain = secrets.token_urlsafe(48)
        hashed = self.hash_refresh(plain)
        expires_at = datetime.now(UTC) + timedelta(seconds=self._refresh_ttl)
        return plain, hashed, expires_at

    def hash_refresh(self, plaintext: str) -> bytes:
        # HMAC-SHA256 keyed with the JWT secret: a DB leak of token_hash alone
        # cannot yield usable refresh tokens without the secret. Fixes SEC-004.
        import hmac as _hmac

        return _hmac.new(
            self._secret.encode("utf-8"),
            plaintext.encode("utf-8"),
            "sha256",
        ).digest()

    def decode_access(self, token: str) -> dict[str, object]:
        """Used by auth middleware. Raises jwt.PyJWTError on invalid tokens."""
        return jwt.decode(
            token,
            self._secret,
            algorithms=[self._algorithm],
            options={"require": ["sub", "sid", "exp", "iat"]},
        )
