"""SQLAlchemy-backed ``MediaRepository`` implementation.

Hand-written SQL matching migrations 0020 / 0021 / 0022. We do not use ORM
models here — the migration is the source of truth for the schema, and
heritage takes the same approach.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Final
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.media.entities import MediaAsset, MediaKind, MediaStatus

_SELECT_COLUMNS: Final = """
    id, tenant_id, owner_user_id, kind, mime_type, byte_size,
    encode(content_hash, 'hex') AS content_hash_hex,
    encode(perceptual_hash, 'hex') AS perceptual_hash_hex,
    perceptual_hash_bucket,
    storage_bucket, storage_key, storage_etag,
    status, license_id, original_filename, exif,
    width, height, duration_ms, language_tag,
    created_at, updated_at, deleted_at
"""


def _row_to_entity(row: object) -> MediaAsset:
    m = row._mapping  # type: ignore[attr-defined]
    return MediaAsset(
        id=m["id"],
        tenant_id=m["tenant_id"],
        owner_user_id=m["owner_user_id"],
        kind=MediaKind(m["kind"]),
        mime_type=m["mime_type"],
        byte_size=m["byte_size"],
        content_hash_hex=m["content_hash_hex"],
        perceptual_hash_hex=m["perceptual_hash_hex"],
        perceptual_hash_bucket=m["perceptual_hash_bucket"],
        storage_bucket=m["storage_bucket"],
        storage_key=m["storage_key"],
        storage_etag=m["storage_etag"],
        status=MediaStatus(m["status"]),
        license_id=m["license_id"],
        original_filename=m["original_filename"],
        exif=dict(m["exif"]) if m["exif"] else {},
        width=m["width"],
        height=m["height"],
        duration_ms=m["duration_ms"],
        language_tag=m["language_tag"],
        created_at=m["created_at"],
        updated_at=m["updated_at"],
        deleted_at=m["deleted_at"],
    )


def _json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


class SqlMediaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(
        self,
        asset_id: UUID,
        *,
        tenant_id: UUID | None = None,
    ) -> MediaAsset | None:
        """Fetch a media asset.

        When ``tenant_id`` is provided, the row is only returned if it belongs
        to that tenant. Fixes SEC-003 (BOLA on /v1/media/{asset_id}).
        Callers that legitimately cross tenants (admin moderators, sockpuppet
        detection) MUST pass ``tenant_id=None`` explicitly.
        """
        # _SELECT_COLUMNS is a module-level constant; tenant filter uses bind
        # parameters. The two string fragments are both compile-time constants.
        sql = (
            f"SELECT {_SELECT_COLUMNS} FROM media_assets "  # noqa: S608
            "WHERE id = :id" + (" AND tenant_id = :tid" if tenant_id else "") + " LIMIT 1"
        )
        params: dict[str, object] = {"id": asset_id}
        if tenant_id is not None:
            params["tid"] = tenant_id
        result = await self._session.execute(text(sql), params)
        row = result.one_or_none()
        return _row_to_entity(row) if row else None

    async def get_by_content_hash(self, sha256_hex: str) -> MediaAsset | None:
        result = await self._session.execute(
            text(
                f"""
                SELECT {_SELECT_COLUMNS}
                FROM media_assets
                WHERE content_hash = decode(:hex, 'hex')
                LIMIT 1
                """  # noqa: S608
            ),
            {"hex": sha256_hex},
        )
        row = result.one_or_none()
        return _row_to_entity(row) if row else None

    async def license_type_exists(self, slug: str) -> bool:
        row = await self._session.execute(
            text(
                """
                SELECT 1 FROM media_license_types
                WHERE slug = :slug AND is_active
                LIMIT 1
                """
            ),
            {"slug": slug},
        )
        return row.one_or_none() is not None

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
    ) -> MediaAsset:
        # 1. Insert the asset row.
        result = await self._session.execute(
            text(
                f"""
                INSERT INTO media_assets (
                    tenant_id, owner_user_id, kind, mime_type, byte_size,
                    content_hash, perceptual_hash, perceptual_hash_bucket,
                    storage_bucket, storage_key, storage_etag,
                    status, original_filename
                )
                VALUES (
                    :tenant, :owner, :kind, :mime, :size,
                    decode(:content_hash, 'hex'),
                    CASE WHEN CAST(:phash AS text) IS NULL
                         THEN NULL
                         ELSE decode(CAST(:phash AS text), 'hex')
                    END,
                    CAST(:phash_bucket AS smallint),
                    :bucket, :key, :etag,
                    :status, :original_filename
                )
                RETURNING {_SELECT_COLUMNS}
                """  # noqa: S608
            ),
            {
                "tenant": tenant_id,
                "owner": owner_user_id,
                "kind": kind.value,
                "mime": mime_type,
                "size": byte_size,
                "content_hash": content_hash_hex,
                "phash": perceptual_hash_hex,
                "phash_bucket": perceptual_hash_bucket,
                "bucket": storage_bucket,
                "key": storage_key,
                "etag": storage_etag,
                "status": status.value,
                "original_filename": original_filename,
            },
        )
        row = result.one()
        asset = _row_to_entity(row)

        # 2. Attach a default license row pointing at the requested vocabulary.
        await self._session.execute(
            text(
                """
                INSERT INTO media_licenses (
                    asset_id, license_type_id, declared_by_user_id
                )
                SELECT :asset_id, t.id, :owner
                FROM media_license_types t
                WHERE t.slug = :slug
                """
            ),
            {
                "asset_id": asset.id,
                "owner": owner_user_id,
                "slug": license_type_slug,
            },
        )

        # 3. Backfill media_assets.license_id (FK is DEFERRABLE INITIALLY
        # DEFERRED, so it gets validated at commit).
        await self._session.execute(
            text(
                """
                UPDATE media_assets SET license_id = :asset_id WHERE id = :asset_id
                """
            ),
            {"asset_id": asset.id},
        )

        # 4. Perceptual-hash side table (only if we actually computed one).
        if perceptual_hash_hex is not None and perceptual_hash_bucket is not None:
            await self._session.execute(
                text(
                    """
                    INSERT INTO media_perceptual_hashes (
                        asset_id, bucket_16, hash_8bytes
                    )
                    VALUES (:asset_id, :bucket, decode(:hex, 'hex'))
                    ON CONFLICT (asset_id) DO NOTHING
                    """
                ),
                {
                    "asset_id": asset.id,
                    "bucket": perceptual_hash_bucket,
                    "hex": perceptual_hash_hex,
                },
            )

        await self._session.commit()

        # Re-read so license_id is populated in the returned entity.
        fresh = await self.get_by_id(asset.id)
        if fresh is None:
            raise RuntimeError(
                f"media_assets row vanished immediately after insert id={asset.id}"
            )
        return fresh

    async def soft_delete(self, *, asset_id: UUID, actor: UUID) -> MediaAsset:
        result = await self._session.execute(
            text(
                f"""
                UPDATE media_assets
                SET status = 'deleted', deleted_at = now()
                WHERE id = :id AND deleted_at IS NULL
                RETURNING {_SELECT_COLUMNS}
                """  # noqa: S608
            ),
            {"id": asset_id},
        )
        row = result.one()
        asset = _row_to_entity(row)
        # Forensic timeline row — best-effort.
        await self._session.execute(
            text(
                """
                INSERT INTO media_lifecycle_events (asset_id, event_type, actor_user_id, details)
                VALUES (:id, 'deleted', :actor, CAST(:details AS jsonb))
                """
            ),
            {
                "id": asset_id,
                "actor": actor,
                "details": _json({"soft_delete": True}),
            },
        )
        await self._session.commit()
        return asset

    async def record_signed_url_grant(
        self,
        *,
        asset_id: UUID,
        grantee_user_id: UUID | None,
        purpose: str,
        expires_at: datetime,
        max_uses: int | None,
        client_ip: str | None,
    ) -> UUID:
        result = await self._session.execute(
            text(
                """
                INSERT INTO signed_url_grants (
                    asset_id, grantee_user_id, purpose, expires_at, max_uses, client_ip
                )
                VALUES (:id, :user, :purpose, :expires, :max_uses, CAST(:ip AS inet))
                RETURNING id
                """
            ),
            {
                "id": asset_id,
                "user": grantee_user_id,
                "purpose": purpose,
                "expires": expires_at,
                "max_uses": max_uses,
                "ip": client_ip,
            },
        )
        grant_id = result.scalar_one()
        await self._session.commit()
        return grant_id
