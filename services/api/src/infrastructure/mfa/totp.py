"""PyOTP-backed TOTP adapter.

Hides ``pyotp`` from the domain so tests can plug in a fake adapter without
the lib installed. The lib is added to ``pyproject.toml`` (`pyotp>=2.9`).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote


class PyOtpTotpAdapter:
    """RFC-6238 TOTP. Tries pyotp, falls back to a stdlib implementation when
    pyotp is not yet installed (so unit tests + CI don't hard-fail before the
    deps are bumped)."""

    def __init__(self) -> None:
        try:
            import pyotp

            self._pyotp: object | None = pyotp
        except Exception:
            self._pyotp = None

    def generate_secret(self) -> str:
        if self._pyotp is not None:
            return self._pyotp.random_base32()  # type: ignore[attr-defined,no-any-return]
        # base32 of 20 random bytes — RFC-4226 §4 recommends ≥160 bit secrets.
        return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")

    def provisioning_uri(
        self,
        *,
        secret_base32: str,
        account_name: str,
        issuer: str,
    ) -> str:
        if self._pyotp is not None:
            return self._pyotp.TOTP(secret_base32).provisioning_uri(  # type: ignore[attr-defined,no-any-return]
                name=account_name, issuer_name=issuer
            )
        # Fallback: hand-crafted otpauth URI matching RFC otp-auth-spec.
        label = quote(f"{issuer}:{account_name}", safe="")
        params = f"secret={secret_base32}&issuer={quote(issuer)}&algorithm=SHA1&digits=6&period=30"
        return f"otpauth://totp/{label}?{params}"

    def verify(self, *, secret_base32: str, code: str, window: int = 1) -> bool:
        if not code or not code.isdigit() or len(code) not in (6, 7, 8):
            return False
        if self._pyotp is not None:
            return bool(
                self._pyotp.TOTP(secret_base32).verify(code, valid_window=window)  # type: ignore[attr-defined]
            )
        # Stdlib HOTP/TOTP fallback (timing-safe compare).
        secret_bytes = _b32_decode(secret_base32)
        counter = int(time.time()) // 30
        target = int(code)
        for offset in range(-window, window + 1):
            generated = _hotp(secret_bytes, counter + offset, digits=len(code))
            if hmac.compare_digest(f"{generated:0{len(code)}d}", f"{target:0{len(code)}d}"):
                return True
        return False


def _b32_decode(s: str) -> bytes:
    # base32 needs padding restored.
    pad = (-len(s)) % 8
    return base64.b32decode(s + ("=" * pad), casefold=True)


def _hotp(secret: bytes, counter: int, *, digits: int = 6) -> int:
    msg = struct.pack(">Q", counter)
    h = hmac.new(secret, msg, hashlib.sha1).digest()
    offset = h[-1] & 0x0F
    binary = (
        (h[offset] & 0x7F) << 24
        | (h[offset + 1] & 0xFF) << 16
        | (h[offset + 2] & 0xFF) << 8
        | (h[offset + 3] & 0xFF)
    )
    return binary % (10**digits)


def current_totp(secret_base32: str) -> str:
    """Test helper: deterministically generate the current 6-digit code."""
    secret_bytes = _b32_decode(secret_base32)
    counter = int(time.time()) // 30
    return f"{_hotp(secret_bytes, counter, digits=6):06d}"
