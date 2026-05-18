"""Thin wrapper around the ``minio`` SDK.

The async API layer never talks to MinIO directly; it goes through this class
so tests can monkey-patch behaviour without spinning up a real bucket. Reads
its credentials from ``Settings`` (``SILKLENS_MINIO_*``).
"""

from __future__ import annotations

import io
from datetime import timedelta

from minio import Minio  # type: ignore[import-untyped]
from minio.error import S3Error  # type: ignore[import-untyped]

from src.core.logging import get_logger
from src.core.settings import Settings, get_settings
from src.domain.media.errors import MediaStorageError

log = get_logger("silklens.media.minio")


class MinioClient:
    """Synchronous MinIO wrapper.

    The MinIO Python SDK is blocking; we keep this synchronous and let
    FastAPI run it on the threadpool (uploads of <50 MiB are quick enough
    to skip explicit threadpool offloading in this pass).
    """

    def __init__(self, settings: Settings | None = None) -> None:
        s = settings or get_settings()
        self._client = Minio(
            endpoint=s.minio_endpoint,
            access_key=s.minio_access_key.get_secret_value(),
            secret_key=s.minio_secret_key.get_secret_value(),
            secure=s.minio_secure,
        )
        self._default_bucket = s.minio_bucket_media

    @property
    def default_bucket(self) -> str:
        return self._default_bucket

    def ensure_bucket(self, name: str) -> None:
        """Create a bucket if missing. Idempotent."""
        try:
            if not self._client.bucket_exists(name):
                self._client.make_bucket(name)
                log.info("media.minio.bucket_created", bucket=name)
        except S3Error as exc:
            log.error("media.minio.bucket_failed", bucket=name, error=str(exc))
            raise MediaStorageError(f"could not ensure bucket {name}: {exc}") from exc

    def upload(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str,
    ) -> str:
        """Upload bytes and return the storage etag."""
        try:
            result = self._client.put_object(
                bucket_name=bucket,
                object_name=key,
                data=io.BytesIO(data),
                length=len(data),
                content_type=content_type,
            )
            return str(result.etag)
        except S3Error as exc:
            log.error("media.minio.upload_failed", bucket=bucket, key=key, error=str(exc))
            raise MediaStorageError(f"upload failed: {exc}") from exc

    def presigned_get(self, bucket: str, key: str, ttl_seconds: int) -> str:
        """Return a presigned GET URL valid for ``ttl_seconds``."""
        try:
            return self._client.presigned_get_object(
                bucket_name=bucket,
                object_name=key,
                expires=timedelta(seconds=ttl_seconds),
            )
        except S3Error as exc:
            log.error("media.minio.presign_failed", bucket=bucket, key=key, error=str(exc))
            raise MediaStorageError(f"presign failed: {exc}") from exc


# Singleton-style accessor mirroring the engine pattern in core/database.py.
_client: MinioClient | None = None


def get_minio_client() -> MinioClient:
    global _client
    if _client is None:
        _client = MinioClient()
    return _client


def set_minio_client(client: MinioClient | None) -> None:
    """Test-only seam: inject a fake client (or reset to None)."""
    global _client
    _client = client
