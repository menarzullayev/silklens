"""Media-domain errors."""
# ruff: noqa: N818

from __future__ import annotations


class MediaError(Exception):
    code: str = "media.unknown"
    status_code: int = 400


class MediaNotFound(MediaError):
    code = "media.not_found"
    status_code = 404


class MediaAlreadyDeleted(MediaError):
    code = "media.already_deleted"
    status_code = 410


class MediaForbidden(MediaError):
    code = "media.forbidden"
    status_code = 403


class InvalidMediaPayload(MediaError):
    code = "media.invalid_payload"
    status_code = 422

    def __init__(self, field: str, reason: str) -> None:
        super().__init__(f"{field}: {reason}")
        self.field = field
        self.reason = reason


class UnknownLicenseType(MediaError):
    code = "media.unknown_license"
    status_code = 422

    def __init__(self, slug: str) -> None:
        super().__init__(f"license slug '{slug}' is not registered")
        self.slug = slug


class MediaStorageError(MediaError):
    code = "media.storage_failed"
    status_code = 502
