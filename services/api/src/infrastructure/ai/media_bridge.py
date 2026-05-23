"""Minimal MediaRepository bridge until Agent A's media service ships.

Implements ``MediaRepositoryProtocol`` against the ``media_assets`` table +
local MinIO so the AI service is end-to-end testable in FAZA 1. When Agent A
lands ``infrastructure/media/repository.py`` this module can be deleted and
the dependency injected from there instead.
"""

from __future__ import annotations

import hashlib
import uuid as uuid_mod
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.core.settings import get_settings
from src.domain.ai.errors import AiProviderUnavailable

log = get_logger("silklens.ai.media_bridge")


class InMemoryMediaBridge:
    """Pure-in-process fake (no MinIO). Used in unit tests."""

    def __init__(self) -> None:
        self._store: dict[UUID, tuple[bytes, str]] = {}

    def put(self, asset_id: UUID, payload: bytes, mime_type: str) -> None:
        self._store[asset_id] = (payload, mime_type)

    async def get_bytes(self, asset_id: UUID) -> tuple[bytes, str]:
        if asset_id not in self._store:
            raise AiProviderUnavailable("media", f"asset {asset_id} not found")
        return self._store[asset_id]

    async def store_generated(
        self,
        *,
        tenant_id: UUID,
        owner_user_id: UUID | None,
        kind: str,
        mime_type: str,
        payload: bytes,
        language_tag: str | None = None,
    ) -> tuple[UUID, str]:
        new_id = uuid_mod.uuid4()
        self._store[new_id] = (payload, mime_type)
        return new_id, f"memory://{new_id}"


class SqlMediaBridge:
    """DB-backed bridge that creates rows in ``media_assets`` and uploads to MinIO.

    ``get_bytes`` reads the bytes from MinIO using ``storage_bucket`` /
    ``storage_key`` from the row. ``store_generated`` inserts a row in
    ``media_assets`` with ``status='ready'`` and returns a presigned URL.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settings = get_settings()
        self._client: Any | None = None

    def _minio(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from minio import Minio
        except ImportError as exc:  # pragma: no cover
            raise AiProviderUnavailable("media", "minio SDK not installed") from exc
        self._client = Minio(
            self._settings.minio_endpoint,
            access_key=self._settings.minio_access_key.get_secret_value(),
            secret_key=self._settings.minio_secret_key.get_secret_value(),
            secure=self._settings.minio_secure,
        )
        return self._client

    async def get_bytes(self, asset_id: UUID) -> tuple[bytes, str]:
        row = (
            await self._session.execute(
                text(
                    """
                    SELECT storage_bucket, storage_key, mime_type
                    FROM media_assets
                    WHERE id = :id AND deleted_at IS NULL
                    """
                ),
                {"id": asset_id},
            )
        ).one_or_none()
        if row is None:
            raise AiProviderUnavailable("media", f"asset {asset_id} not found")
        m = row._mapping
        try:
            client = self._minio()
            resp = client.get_object(m["storage_bucket"], m["storage_key"])
            try:
                data = resp.read()
            finally:
                resp.close()
                resp.release_conn()
        except Exception as exc:  # pragma: no cover — network
            raise AiProviderUnavailable("media", f"minio fetch failed: {exc}") from exc
        return data, m["mime_type"]

    async def store_generated(
        self,
        *,
        tenant_id: UUID,
        owner_user_id: UUID | None,
        kind: str,
        mime_type: str,
        payload: bytes,
        language_tag: str | None = None,
    ) -> tuple[UUID, str]:
        new_id = uuid_mod.uuid4()
        bucket = self._settings.minio_bucket_media
        key = f"ai/{kind}/{new_id}.bin"
        content_hash = hashlib.sha256(payload).digest()

        try:
            client = self._minio()
            from io import BytesIO

            if not client.bucket_exists(bucket):
                client.make_bucket(bucket)
            client.put_object(
                bucket,
                key,
                BytesIO(payload),
                length=len(payload),
                content_type=mime_type,
            )
        except Exception as exc:  # pragma: no cover — network
            raise AiProviderUnavailable("media", f"minio upload failed: {exc}") from exc

        row = (
            await self._session.execute(
                text(
                    """
                    INSERT INTO media_assets (
                        id, tenant_id, owner_user_id, kind, mime_type,
                        byte_size, content_hash,
                        storage_bucket, storage_key, status, language_tag
                    )
                    VALUES (
                        :id, :tenant, :owner, :kind, :mime,
                        :size, :hash,
                        :bucket, :key, 'ready', :lang
                    )
                    RETURNING id
                    """
                ),
                {
                    "id": new_id,
                    "tenant": tenant_id,
                    "owner": owner_user_id,
                    "kind": kind,
                    "mime": mime_type,
                    "size": len(payload),
                    "hash": content_hash,
                    "bucket": bucket,
                    "key": key,
                    "lang": language_tag,
                },
            )
        ).scalar_one()

        # Presigned GET valid for 1 hour
        try:
            from datetime import timedelta

            client = self._minio()
            signed_url = client.presigned_get_object(bucket, key, expires=timedelta(hours=1))
        except Exception:  # pragma: no cover
            signed_url = f"s3://{bucket}/{key}"
        return row, signed_url
