"""Media domain entities — pure Python, framework-free.

Mirrors the schema introduced in migrations 0020 (media_assets / media_variants
/ media_storage_locations / media_perceptual_hashes), 0021 (signed_url_grants
et al.), and 0022 (media_license_types / media_licenses).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class MediaKind(StrEnum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO_TTS = "audio_tts"
    AUDIO_HUMAN = "audio_human"
    VIDEO_HLS = "video_hls"
    AR_MARKER = "ar_marker"
    AR_OVERLAY = "ar_overlay"
    MODEL_3D = "3d_model"
    DOCUMENT = "document"


class MediaStatus(StrEnum):
    PENDING = "pending"
    SCANNING = "scanning"
    PROCESSING = "processing"
    READY = "ready"
    QUARANTINED = "quarantined"
    DELETED = "deleted"


@dataclass(slots=True, frozen=True)
class MediaAsset:
    id: UUID
    tenant_id: UUID
    owner_user_id: UUID | None
    kind: MediaKind
    mime_type: str
    byte_size: int
    content_hash_hex: str
    storage_bucket: str
    storage_key: str
    status: MediaStatus
    created_at: datetime
    updated_at: datetime
    storage_etag: str | None = None
    perceptual_hash_hex: str | None = None
    perceptual_hash_bucket: int | None = None
    license_id: UUID | None = None
    original_filename: str | None = None
    exif: dict[str, Any] | None = None
    width: int | None = None
    height: int | None = None
    duration_ms: int | None = None
    language_tag: str | None = None
    deleted_at: datetime | None = None


@dataclass(slots=True, frozen=True)
class MediaVariant:
    id: UUID
    asset_id: UUID
    variant_name: str
    mime_type: str
    byte_size: int
    storage_location_id: UUID
    storage_key: str
    width: int | None = None
    height: int | None = None
    duration_ms: int | None = None
    generated_at: datetime | None = None


@dataclass(slots=True, frozen=True)
class MediaUploadDraft:
    """Input bundle for creating a new media asset."""

    tenant_id: UUID
    owner_user_id: UUID
    kind: MediaKind
    mime_type: str
    byte_size: int
    content: bytes
    original_filename: str | None = None
    license_type_slug: str = "cc_by_sa"
    language_tag: str | None = None


@dataclass(slots=True, frozen=True)
class MediaSignedUrl:
    """Result of issuing a presigned GET URL."""

    asset_id: UUID
    url: str
    expires_at: datetime
