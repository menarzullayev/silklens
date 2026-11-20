"""Media upload + signed-URL endpoints.

POST   /v1/media/uploads               — multipart upload, authenticated users
GET    /v1/media/{asset_id}            — metadata only
GET    /v1/media/{asset_id}/signed-url — presigned GET URL (owner OR moderator)
DELETE /v1/media/{asset_id}            — soft delete (owner OR moderator)

MinIO is the source of truth for bytes; Postgres for meaning. Bytes are
uploaded synchronously in this pass; chunked / resumable uploads land later.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.settings import get_settings
from src.domain.media.entities import MediaAsset, MediaKind, MediaUploadDraft
from src.domain.media.errors import MediaError
from src.domain.media.service import MediaService, MediaStorage
from src.infrastructure.media.minio_client import get_minio_client
from src.infrastructure.media.repository import SqlMediaRepository
from src.middleware.auth import require_user
from src.middleware.ratelimit import rate_limit

router = APIRouter(prefix="/v1/media", tags=["media"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


# --- Schemas -----------------------------------------------------------------


class MediaOut(BaseModel):
    id: UUID
    tenant_id: UUID
    owner_user_id: UUID | None
    kind: MediaKind
    mime_type: str
    byte_size: int
    content_hash: str
    storage_bucket: str
    storage_key: str
    status: str
    original_filename: str | None
    width: int | None
    height: int | None
    duration_ms: int | None
    license_id: UUID | None
    created_at: datetime


class MediaUploadOut(BaseModel):
    asset: MediaOut
    signed_get_url: str


class SignedUrlOut(BaseModel):
    asset_id: UUID
    url: str
    expires_at: datetime


class MediaDeleteOut(BaseModel):
    asset_id: UUID
    status: str = Field(default="deleted")


# --- Helpers -----------------------------------------------------------------


def _to_out(asset: MediaAsset) -> MediaOut:
    return MediaOut(
        id=asset.id,
        tenant_id=asset.tenant_id,
        owner_user_id=asset.owner_user_id,
        kind=asset.kind,
        mime_type=asset.mime_type,
        byte_size=asset.byte_size,
        content_hash=asset.content_hash_hex,
        storage_bucket=asset.storage_bucket,
        storage_key=asset.storage_key,
        status=asset.status.value,
        original_filename=asset.original_filename,
        width=asset.width,
        height=asset.height,
        duration_ms=asset.duration_ms,
        license_id=asset.license_id,
        created_at=asset.created_at,
    )


def _service(db: AsyncSession, *, storage: MediaStorage | None = None) -> MediaService:
    settings = get_settings()
    return MediaService(
        repository=SqlMediaRepository(db),
        storage=storage or get_minio_client(),
        primary_bucket=settings.minio_bucket_media,
    )


def _raise_media_error(exc: MediaError) -> None:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": str(exc)},
    ) from exc


async def _has_perm(db: AsyncSession, ctx: object, perm: str) -> bool:
    row = await db.execute(
        text("SELECT app.has_permission(:uid, :residency, :perm, :tenant)"),
        {
            "uid": ctx.user_id,
            "residency": ctx.residency_region.value,
            "perm": perm,
            "tenant": ctx.tenant_id,
        },
    )
    return bool(row.scalar_one())


# --- Routes ------------------------------------------------------------------


@router.post(
    "/uploads",
    response_model=MediaUploadOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("20/minute", per="user", scope="media:upload"))],
)
async def upload_media(
    db: SessionDep,
    ctx: Annotated[object, Depends(require_user)],
    file: Annotated[UploadFile, File(description="Asset bytes")],
    kind: Annotated[MediaKind, Form()] = MediaKind.IMAGE,
    license_type_slug: Annotated[str, Form()] = "cc_by_sa",
) -> MediaUploadOut:
    content = await file.read()
    draft = MediaUploadDraft(
        tenant_id=ctx.tenant_id,
        owner_user_id=ctx.user_id,
        kind=kind,
        mime_type=file.content_type or "application/octet-stream",
        byte_size=len(content),
        content=content,
        original_filename=file.filename,
        license_type_slug=license_type_slug,
    )
    try:
        result = await _service(db).upload(draft)
    except MediaError as exc:
        _raise_media_error(exc)
    return MediaUploadOut(
        asset=_to_out(result.asset),
        signed_get_url=result.signed_get_url,
    )


@router.get("/{asset_id}", response_model=MediaOut)
async def get_media(
    asset_id: UUID,
    db: SessionDep,
    ctx: Annotated[object, Depends(require_user)],
) -> MediaOut:
    # SEC-003 fix: enforce tenant scope; moderators bypass.
    is_moderator = await _has_perm(db, ctx, "heritage:moderate")
    try:
        asset = await _service(db).get(
            asset_id,
            caller_tenant_id=ctx.tenant_id,
            bypass_tenant_check=is_moderator,
        )
    except MediaError as exc:
        _raise_media_error(exc)
    return _to_out(asset)


@router.get("/{asset_id}/signed-url", response_model=SignedUrlOut)
async def get_signed_url(
    asset_id: UUID,
    db: SessionDep,
    request: Request,
    ctx: Annotated[object, Depends(require_user)],
) -> SignedUrlOut:
    is_moderator = await _has_perm(db, ctx, "heritage:moderate")
    client_ip = request.client.host if request.client else None
    try:
        grant = await _service(db).request_signed_url(
            asset_id=asset_id,
            requester_id=ctx.user_id,
            caller_tenant_id=ctx.tenant_id,
            is_moderator=is_moderator,
            client_ip=client_ip,
        )
    except MediaError as exc:
        _raise_media_error(exc)
    return SignedUrlOut(
        asset_id=grant.asset_id,
        url=grant.url,
        expires_at=grant.expires_at,
    )


@router.delete("/{asset_id}", response_model=MediaDeleteOut)
async def delete_media(
    asset_id: UUID,
    db: SessionDep,
    ctx: Annotated[object, Depends(require_user)],
) -> MediaDeleteOut:
    is_moderator = await _has_perm(db, ctx, "heritage:moderate")
    try:
        await _service(db).soft_delete(
            asset_id=asset_id,
            requester_id=ctx.user_id,
            caller_tenant_id=ctx.tenant_id,
            is_moderator=is_moderator,
        )
    except MediaError as exc:
        _raise_media_error(exc)
    return MediaDeleteOut(asset_id=asset_id)
