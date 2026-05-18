"""Heritage-domain errors."""
# ruff: noqa: N818

from __future__ import annotations


class HeritageError(Exception):
    code: str = "heritage.unknown"
    status_code: int = 400


class HeritageNotFound(HeritageError):
    code = "heritage.not_found"
    status_code = 404


class DuplicatePubId(HeritageError):
    code = "heritage.duplicate_pub_id"
    status_code = 409


class InvalidHeritageKind(HeritageError):
    code = "heritage.invalid_kind"
    status_code = 422

    def __init__(self, kind: str) -> None:
        super().__init__(f"heritage kind '{kind}' is not registered")
        self.kind = kind


class HeritageValidationError(HeritageError):
    code = "heritage.validation_failed"
    status_code = 422

    def __init__(self, field: str, reason: str) -> None:
        super().__init__(f"{field}: {reason}")
        self.field = field
        self.reason = reason
