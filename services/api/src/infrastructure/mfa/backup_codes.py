"""Argon2id-backed backup-code hasher.

Same Argon2 parameters as :class:`Argon2PasswordHasher` but the verify path
is a list-iter so we can match an offered plaintext against the user's full
set without forcing the caller to know the layout.
"""

from __future__ import annotations

from argon2 import PasswordHasher as Argon2Hasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError


class Argon2BackupCodeHasher:
    """Backup codes are short — 12 chars — but Argon2id keeps brute-force
    expensive even if the table leaks."""

    def __init__(self) -> None:
        self._hasher = Argon2Hasher(
            time_cost=2,
            memory_cost=32 * 1024,  # cheaper than passwords because codes are random
            parallelism=2,
            hash_len=32,
            salt_len=16,
        )

    def hash(self, code: str) -> bytes:
        return self._hasher.hash(code).encode("utf-8")

    def verify_any(self, code: str, hashes: list[bytes]) -> int | None:
        for idx, stored in enumerate(hashes):
            try:
                self._hasher.verify(stored.decode("utf-8"), code)
                return idx
            except (VerifyMismatchError, InvalidHashError):
                continue
        return None
