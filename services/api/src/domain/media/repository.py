"""Media repository protocol — interface only."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.domain.media.entities import MediaAsset, MediaKind, MediaStatus


class MediaRepository(Protocol):
    async def get_by_id(self, asset_id: UUID, *, tenant_id: UUID | None = None) -> MediaAsset | None: ...

    async def get_by_content_hash(self, sha256_hex: str) -> MediaAsset | None: ...

    async def create_asset(
        self,
        *,
        tenant_id: UUID,
        owner_user_id: UUID,
        kind: MediaKind,
        mime_type: str,
        byte_size: int,
        content_hash_hex: str,
        perceptual_hash_hex: str | None,
        perceptual_hash_bucket: int | None,
        storage_bucket: str,
        storage_key: str,
        storage_etag: str | None,
        original_filename: str | None,
        license_type_slug: str,
        status: MediaStatus = MediaStatus.READY,
    ) -> MediaAsset: ...

    async def soft_delete(self, *, asset_id: UUID, actor: UUID) -> MediaAsset: ...

    async def record_signed_url_grant(
        self,
        *,
        asset_id: UUID,
        grantee_user_id: UUID | None,
        purpose: str,
        expires_at: datetime,
        max_uses: int | None,
        client_ip: str | None,
    ) -> UUID: ...

    async def license_type_exists(self, slug: str) -> bool: ...
