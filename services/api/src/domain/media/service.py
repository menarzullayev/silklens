"""Media application service.

Coordinates the repository, MinIO client, and license catalog so the router
can stay thin. Storage is treated as an external dependency injected via the
``MediaStorage`` protocol — tests can swap it for an in-memory fake.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID

from src.domain.media.entities import (
    MediaAsset,
    MediaKind,
    MediaSignedUrl,
    MediaUploadDraft,
)
from src.domain.media.errors import (
    InvalidMediaPayload,
    MediaAlreadyDeleted,
    MediaForbidden,
    MediaNotFound,
    MediaUnsupportedMime,
    UnknownLicenseType,
)
from src.domain.media.repository import MediaRepository

# 50 MiB cap for now; raise once chunked uploads land.
MAX_UPLOAD_BYTES = 50 * 1024 * 1024

# Allow-list of accepted MIME types. Keep in sync with the model/3D viewer
# pipeline and the audio/video transcoder. Anything else gets a 415.
ALLOWED_MIME_TYPES: frozenset[str] = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
        "image/avif",
        "video/mp4",
        "video/quicktime",
        "audio/mpeg",
        "audio/aac",
        "audio/ogg",
        "audio/wav",
        "application/pdf",
        "model/gltf-binary",
    }
)

# libmagic on glTF / model files reports application/octet-stream; treat that
# as "unknown" and only diverge when the top-level types actually differ.
_MIME_SNIFF_BUFFER = 8 * 1024  # first 8 KiB

# audio/wav has multiple historical encodings — libmagic frequently reports
# audio/x-wav. Normalise via this alias map before the divergence check.
_MIME_ALIASES: dict[str, str] = {
    "audio/x-wav": "audio/wav",
    "audio/wave": "audio/wav",
    "audio/x-m4a": "audio/aac",
    "audio/mp4": "audio/aac",
    "image/jpg": "image/jpeg",
    "model/gltf+json": "model/gltf-binary",
}


class MediaStorage(Protocol):
    """Subset of ``minio_client`` interface the service depends on.

    Kept as a Protocol so unit tests can pass an in-memory fake without
    monkey-patching at module level.
    """

    def upload(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str,
    ) -> str: ...

    def presigned_get(self, bucket: str, key: str, ttl_seconds: int) -> str: ...


@dataclass(slots=True, frozen=True)
class UploadResult:
    asset: MediaAsset
    signed_get_url: str


class MediaService:
    def __init__(
        self,
        *,
        repository: MediaRepository,
        storage: MediaStorage,
        primary_bucket: str,
    ) -> None:
        self._repo = repository
        self._storage = storage
        self._bucket = primary_bucket

    async def upload(self, draft: MediaUploadDraft) -> UploadResult:
        # --- validation ---------------------------------------------------
        if not draft.content:
            raise InvalidMediaPayload("file", "empty body")
        if draft.byte_size != len(draft.content):
            raise InvalidMediaPayload("byte_size", "does not match content length")
        if draft.byte_size > MAX_UPLOAD_BYTES:
            raise InvalidMediaPayload("byte_size", "exceeds upload limit")

        # --- MIME magic-byte validation -----------------------------------
        # Defence against client-supplied content-type spoofing: never trust
        # the multipart Content-Type. Sniff libmagic against the first 8 KiB,
        # reject if the claimed type diverges into a different top-level
        # family (image vs application, etc.), and reject anything outside
        # the explicit allow-list. See HIGH-3 / SEC-011.
        _validate_mime(draft.mime_type, draft.content)

        if not await self._repo.license_type_exists(draft.license_type_slug):
            raise UnknownLicenseType(draft.license_type_slug)

        # --- hashing ------------------------------------------------------
        sha256 = hashlib.sha256(draft.content).hexdigest()

        # Dedup: same content hash → return existing row (if not deleted).
        existing = await self._repo.get_by_content_hash(sha256)
        if existing is not None and existing.deleted_at is None:
            signed = self._storage.presigned_get(
                existing.storage_bucket, existing.storage_key, 3600
            )
            return UploadResult(asset=existing, signed_get_url=signed)

        # --- perceptual hash for images (optional) ------------------------
        phash_hex: str | None = None
        phash_bucket: int | None = None
        if draft.kind is MediaKind.IMAGE:
            phash_hex, phash_bucket = _compute_perceptual_hash(draft.content)

        # --- storage ------------------------------------------------------
        # Two-level prefix ('ab/cd/<sha>') keeps S3-compatible listings cheap.
        storage_key = f"{sha256[:2]}/{sha256[2:4]}/{sha256}"
        etag = self._storage.upload(
            bucket=self._bucket,
            key=storage_key,
            data=draft.content,
            content_type=draft.mime_type,
        )

        asset = await self._repo.create_asset(
            tenant_id=draft.tenant_id,
            owner_user_id=draft.owner_user_id,
            kind=draft.kind,
            mime_type=draft.mime_type,
            byte_size=draft.byte_size,
            content_hash_hex=sha256,
            perceptual_hash_hex=phash_hex,
            perceptual_hash_bucket=phash_bucket,
            storage_bucket=self._bucket,
            storage_key=storage_key,
            storage_etag=etag,
            original_filename=draft.original_filename,
            license_type_slug=draft.license_type_slug,
        )

        signed_url = self._storage.presigned_get(self._bucket, storage_key, 3600)
        return UploadResult(asset=asset, signed_get_url=signed_url)

    async def get(
        self,
        asset_id: UUID,
        *,
        caller_tenant_id: UUID | None = None,
        bypass_tenant_check: bool = False,
    ) -> MediaAsset:
        """Fetch a media asset for a caller scoped to ``caller_tenant_id``.

        Fixes SEC-003 / BOLA: cross-tenant metadata leakage. Callers from the
        admin/moderation path pass ``bypass_tenant_check=True`` explicitly.
        """
        repo_tenant = None if bypass_tenant_check else caller_tenant_id
        asset = await self._repo.get_by_id(asset_id, tenant_id=repo_tenant)
        if asset is None or asset.deleted_at is not None:
            raise MediaNotFound(str(asset_id))
        return asset

    async def request_signed_url(
        self,
        *,
        asset_id: UUID,
        requester_id: UUID,
        caller_tenant_id: UUID,
        is_moderator: bool,
        client_ip: str | None,
        ttl_seconds: int = 3600,
    ) -> MediaSignedUrl:
        asset = await self.get(
            asset_id,
            caller_tenant_id=caller_tenant_id,
            bypass_tenant_check=is_moderator,
        )
        if asset.owner_user_id != requester_id and not is_moderator:
            raise MediaForbidden("requester does not own asset")
        url = self._storage.presigned_get(asset.storage_bucket, asset.storage_key, ttl_seconds)
        expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
        await self._repo.record_signed_url_grant(
            asset_id=asset.id,
            grantee_user_id=requester_id,
            purpose="api_signed_url",
            expires_at=expires_at,
            max_uses=None,
            client_ip=client_ip,
        )
        return MediaSignedUrl(asset_id=asset.id, url=url, expires_at=expires_at)

    async def soft_delete(
        self,
        *,
        asset_id: UUID,
        requester_id: UUID,
        caller_tenant_id: UUID,
        is_moderator: bool,
    ) -> MediaAsset:
        repo_tenant = None if is_moderator else caller_tenant_id
        asset = await self._repo.get_by_id(asset_id, tenant_id=repo_tenant)
        if asset is None:
            raise MediaNotFound(str(asset_id))
        if asset.deleted_at is not None:
            raise MediaAlreadyDeleted(str(asset_id))
        if asset.owner_user_id != requester_id and not is_moderator:
            raise MediaForbidden("requester does not own asset")
        return await self._repo.soft_delete(asset_id=asset.id, actor=requester_id)


def _compute_perceptual_hash(content: bytes) -> tuple[str | None, int | None]:
    """Best-effort perceptual hash via PIL+imagehash.

    ``imagehash`` is optional — when missing we return (None, None) so the
    DB columns stay NULL. ``PIL`` ships in pyproject, but the hash library
    doesn't. We import lazily and swallow ImportError to keep the call cheap.
    """
    try:  # pragma: no cover - optional dependency
        import io

        import imagehash  # type: ignore[import-not-found]
        from PIL import Image
    except ImportError:
        return None, None

    try:
        with Image.open(io.BytesIO(content)) as image:
            phash = imagehash.phash(image)
        raw = phash.hash.flatten()
        # Pack the 64-bit boolean array into bytes for storage.
        as_int = 0
        for bit in raw:
            as_int = (as_int << 1) | int(bool(bit))
        hex_value = f"{as_int:016x}"
        bucket = (as_int >> 48) & 0xFFFF
        return hex_value, _to_signed_16(bucket)
    except Exception:
        return None, None


def _to_signed_16(value: int) -> int:
    """Convert an unsigned 16-bit int to its signed (smallint) representation."""
    return value - 0x10000 if value >= 0x8000 else value


def _normalise_mime(mime: str) -> str:
    base = mime.split(";", 1)[0].strip().lower()
    return _MIME_ALIASES.get(base, base)


def _validate_mime(claimed: str, content: bytes) -> None:
    """Reject spoofed/disallowed MIME types.

    Raises ``MediaUnsupportedMime`` (HTTP 415) when:
      * the caller's claimed MIME isn't in :data:`ALLOWED_MIME_TYPES`;
      * libmagic sniffs a top-level type that diverges from the claim
        (``image/`` vs ``application/`` etc.). Within-family disagreement is
        allowed because libmagic regularly reports e.g. ``image/jpeg`` for
        every JPEG flavour while the browser sends ``image/pjpeg``.

    libmagic is loaded lazily so the rest of the service can still be unit-
    tested on hosts without ``libmagic1`` installed (CI installs it via the
    Dockerfile + Makefile note).
    """
    claimed_norm = _normalise_mime(claimed)
    if claimed_norm not in ALLOWED_MIME_TYPES:
        raise MediaUnsupportedMime(
            claimed=claimed, sniffed=None, reason="claimed MIME not in allow-list"
        )

    try:  # pragma: no cover - libmagic absent is exceptional in production
        import magic  # type: ignore[import-untyped]
    except ImportError as exc:
        raise MediaUnsupportedMime(
            claimed=claimed,
            sniffed=None,
            reason="server cannot verify MIME (python-magic unavailable)",
        ) from exc

    sniffed = magic.from_buffer(content[:_MIME_SNIFF_BUFFER], mime=True) or ""
    sniffed_norm = _normalise_mime(sniffed)

    # libmagic returns 'application/octet-stream' for unknown formats — that
    # is not an active divergence, just an absence of signal. Treat it as a
    # soft pass *only* when the claimed type itself isn't an executable.
    if sniffed_norm in ("", "application/octet-stream"):
        # Still allow GLB / glTF binary because the magic database doesn't
        # always carry it. Anything else with no signature gets rejected.
        if claimed_norm == "model/gltf-binary":
            return
        raise MediaUnsupportedMime(
            claimed=claimed,
            sniffed=sniffed or None,
            reason="unable to sniff a signature from the uploaded bytes",
        )

    claimed_top = claimed_norm.split("/", 1)[0]
    sniffed_top = sniffed_norm.split("/", 1)[0]
    if claimed_top != sniffed_top:
        raise MediaUnsupportedMime(
            claimed=claimed,
            sniffed=sniffed,
            reason="claimed top-level type does not match sniffed bytes",
        )
