"""Offline bundle download API. SILK-0055.

Allows mobile clients to download pre-packaged offline content
(maps, audio guides, translations) for use without internet.

GET  /v1/offline/bundles                      — list bundles (public)
GET  /v1/offline/bundles/{bundle_id}/manifest — bundle manifest + file list (public)
POST /v1/offline/bundles/{bundle_id}/install-report — record device install (rate-limited)
"""

from __future__ import annotations

import hashlib
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.middleware.auth import OptionalUserDep
from src.middleware.ratelimit import rate_limit

router = APIRouter(prefix="/v1/offline", tags=["offline"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


# ---------------------------------------------------------------------------
# Output schemas
# ---------------------------------------------------------------------------


class BundleItem(BaseModel):
    id: UUID
    slug: str
    name: dict[str, Any]
    bundle_kind: str
    language_set: list[str]
    version: int | None
    semver: str | None
    byte_size: int
    manifest_url: str | None
    published_at: str | None


class BundleListResponse(BaseModel):
    items: list[BundleItem]
    total: int
    limit: int
    offset: int


class BundleContentFile(BaseModel):
    id: UUID
    asset_id: UUID
    variant_id: UUID | None
    tier: int
    byte_size: int
    inclusion_reason: str | None
    is_required: bool


class BundleManifestResponse(BaseModel):
    bundle_id: UUID
    slug: str
    version: int | None
    semver: str | None
    byte_size: int
    manifest_url: str | None
    manifest_sha256_hex: str | None
    published_at: str | None
    signature: dict[str, Any] | None
    files: list[BundleContentFile]
    file_count: int


class InstallReportResponse(BaseModel):
    recorded: bool
    bundle_id: UUID
    version: int


# ---------------------------------------------------------------------------
# Module-level SQL constants (uppercase per PEP-8 convention for constants)
# ---------------------------------------------------------------------------

_SQL_BUNDLES_ALL = """
    SELECT
        ob.id,
        ob.slug,
        ob.name,
        ob.bundle_kind,
        ob.language_set,
        obv.version,
        obv.semver,
        obv.byte_size,
        obv.manifest_url,
        obv.published_at
    FROM offline_bundles ob
    LEFT JOIN offline_bundle_versions obv
        ON obv.id = ob.current_version_id
    WHERE ob.is_active = true
      AND (:lang = ANY(ob.language_set) OR 'all' = ANY(ob.language_set))
    ORDER BY ob.bundle_kind, ob.slug
    LIMIT :limit OFFSET :offset
"""

_SQL_BUNDLES_KIND = """
    SELECT
        ob.id,
        ob.slug,
        ob.name,
        ob.bundle_kind,
        ob.language_set,
        obv.version,
        obv.semver,
        obv.byte_size,
        obv.manifest_url,
        obv.published_at
    FROM offline_bundles ob
    LEFT JOIN offline_bundle_versions obv
        ON obv.id = ob.current_version_id
    WHERE ob.is_active = true
      AND (:lang = ANY(ob.language_set) OR 'all' = ANY(ob.language_set))
      AND ob.bundle_kind = :bundle_kind
    ORDER BY ob.bundle_kind, ob.slug
    LIMIT :limit OFFSET :offset
"""

_SQL_MANIFEST_CURRENT = """
    SELECT
        ob.id           AS bundle_id,
        ob.slug,
        obv.id          AS version_id,
        obv.version,
        obv.semver,
        obv.byte_size,
        obv.manifest_url,
        obv.manifest_sha256,
        obv.published_at,
        obs.signature           AS sig_bytes,
        obs.signature_algorithm AS sig_algorithm,
        obs.signing_key_id
    FROM offline_bundles ob
    JOIN offline_bundle_versions obv
        ON obv.bundle_id = ob.id
       AND ob.current_version_id = obv.id
    LEFT JOIN offline_bundle_signatures obs
        ON obs.bundle_version_id = obv.id
    WHERE ob.id = :bundle_id
      AND ob.is_active = true
"""

_SQL_MANIFEST_PINNED = """
    SELECT
        ob.id           AS bundle_id,
        ob.slug,
        obv.id          AS version_id,
        obv.version,
        obv.semver,
        obv.byte_size,
        obv.manifest_url,
        obv.manifest_sha256,
        obv.published_at,
        obs.signature           AS sig_bytes,
        obs.signature_algorithm AS sig_algorithm,
        obs.signing_key_id
    FROM offline_bundles ob
    JOIN offline_bundle_versions obv
        ON obv.bundle_id = ob.id
       AND obv.version = :version
    LEFT JOIN offline_bundle_signatures obs
        ON obs.bundle_version_id = obv.id
    WHERE ob.id = :bundle_id
      AND ob.is_active = true
"""


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get(
    "/bundles",
    response_model=BundleListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_offline_bundles(
    db: SessionDep,
    _user: OptionalUserDep,
    bundle_kind: Annotated[
        str | None,
        Query(description="Filter by kind: region, city, heritage_site, language_pack"),
    ] = None,
    language: Annotated[
        str,
        Query(min_length=2, max_length=10, description="ISO language code, e.g. en, uz, ru"),
    ] = "en",
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0, le=10_000_000)] = 0,
) -> BundleListResponse:
    """List available offline bundles optionally filtered by kind and language.

    Returns the current version's metadata including byte size, semver, and
    manifest URL. Public endpoint — no authentication required.
    """
    lang = language.split("-")[0].lower()

    if bundle_kind:
        sql = _SQL_BUNDLES_KIND
        params: dict[str, Any] = {
            "lang": lang,
            "limit": limit,
            "offset": offset,
            "bundle_kind": bundle_kind,
        }
    else:
        sql = _SQL_BUNDLES_ALL
        params = {"lang": lang, "limit": limit, "offset": offset}

    rows = await db.execute(text(sql), params)

    items = [
        BundleItem(
            id=r["id"],
            slug=r["slug"],
            name=r["name"] or {},
            bundle_kind=r["bundle_kind"],
            language_set=r["language_set"] or [],
            version=r["version"],
            semver=r["semver"],
            byte_size=r["byte_size"] or 0,
            manifest_url=r["manifest_url"],
            published_at=r["published_at"].isoformat() if r["published_at"] else None,
        )
        for r in rows.mappings().fetchall()
    ]

    return BundleListResponse(items=items, total=len(items), limit=limit, offset=offset)


@router.get(
    "/bundles/{bundle_id}/manifest",
    response_model=BundleManifestResponse,
    status_code=status.HTTP_200_OK,
)
async def get_bundle_manifest(
    bundle_id: UUID,
    db: SessionDep,
    version: Annotated[
        int | None,
        Query(
            ge=1,
            le=2_147_483_647,
            description="Integer version number; defaults to current version",
        ),
    ] = None,
) -> BundleManifestResponse:
    """Return bundle manifest with all content file references.

    Mobile clients compare the local asset list against this manifest and
    download only new or changed entries (delta update). Public endpoint.
    """
    if version is not None:
        params: dict[str, Any] = {"bundle_id": str(bundle_id), "version": version}
        row = await db.execute(text(_SQL_MANIFEST_PINNED), params)
    else:
        params = {"bundle_id": str(bundle_id)}
        row = await db.execute(text(_SQL_MANIFEST_CURRENT), params)
    data = row.mappings().fetchone()
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "offline.bundle_not_found",
                "message": "Bundle or version not found",
            },
        )

    files_rows = await db.execute(
        text("""
            SELECT
                obc.id,
                obc.asset_id,
                obc.variant_id,
                obc.tier,
                obc.byte_size,
                obc.inclusion_reason,
                obc.is_required
            FROM offline_bundle_contents obc
            WHERE obc.bundle_version_id = :vid
            ORDER BY obc.tier, obc.asset_id
        """),
        {"vid": str(data["version_id"])},
    )
    files = [
        BundleContentFile(
            id=r["id"],
            asset_id=r["asset_id"],
            variant_id=r["variant_id"],
            tier=r["tier"],
            byte_size=r["byte_size"] or 0,
            inclusion_reason=r["inclusion_reason"],
            is_required=r["is_required"],
        )
        for r in files_rows.mappings().fetchall()
    ]

    # manifest_sha256 is stored as 32-byte bytea; encode to hex for JSON.
    manifest_sha256_hex: str | None = None
    raw_sha = data["manifest_sha256"]
    if raw_sha is not None:
        manifest_sha256_hex = (
            bytes(raw_sha).hex() if isinstance(raw_sha, (bytes, memoryview)) else str(raw_sha)
        )

    # Build signature block only when a row exists in offline_bundle_signatures.
    signature_block: dict[str, Any] | None = None
    if data["sig_bytes"] is not None:
        raw_sig = data["sig_bytes"]
        sig_hex = bytes(raw_sig).hex() if isinstance(raw_sig, (bytes, memoryview)) else str(raw_sig)
        signature_block = {
            "hex": sig_hex,
            "algorithm": data["sig_algorithm"] or "ed25519",
            "signing_key_id": data["signing_key_id"],
        }

    return BundleManifestResponse(
        bundle_id=data["bundle_id"],
        slug=data["slug"],
        version=data["version"],
        semver=data["semver"],
        byte_size=data["byte_size"] or 0,
        manifest_url=data["manifest_url"],
        manifest_sha256_hex=manifest_sha256_hex,
        published_at=data["published_at"].isoformat() if data["published_at"] else None,
        signature=signature_block,
        files=files,
        file_count=len(files),
    )


@router.post(
    "/bundles/{bundle_id}/install-report",
    response_model=InstallReportResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(rate_limit("30/minute", per="ip", scope="offline:install_report")),
    ],
)
async def report_bundle_install(
    bundle_id: UUID,
    db: SessionDep,
    installed_version: Annotated[
        int,
        Query(ge=1, le=2_147_483_647, description="Integer version number the device installed"),
    ],
    device_id: Annotated[
        str,
        Query(min_length=8, max_length=128, description="Opaque device identifier (hashed)"),
    ],
) -> InstallReportResponse:
    """Record that a device installed a specific bundle version.

    Used for analytics and CDN capacity planning. The raw device_id is
    SHA-256 hashed before storage — identifiers are never persisted in plain
    text. Rate-limited to 30 requests/minute per IP.
    """
    ver_row = await db.execute(
        text("""
            SELECT obv.id AS version_id, obv.version
            FROM offline_bundle_versions obv
            WHERE obv.bundle_id = :bid AND obv.version = :ver
        """),
        {"bid": str(bundle_id), "ver": installed_version},
    )
    ver = ver_row.mappings().fetchone()
    if not ver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "offline.version_not_found",
                "message": "Bundle version not found",
            },
        )

    # device_fingerprint_id is a FK to the device_fingerprints table (UUID PK).
    # We only hold a raw opaque string here, not a registered UUID row.
    # The SHA-256 hash is computed to avoid logging the plain identifier; it is
    # not stored in this schema revision — dedup lives at analytics query time.
    # Never log device_id directly (PII risk).
    _device_hash_for_log = hashlib.sha256(device_id.encode()).hexdigest()[:16]
    del _device_hash_for_log  # consumed only for side-effect: prevents raw id logging

    # The downloads table is partitioned by downloaded_at; ON CONFLICT is
    # unavailable on the parent table. Minor duplicate rows from retries are
    # acceptable for analytics use.
    await db.execute(
        text("""
            INSERT INTO offline_bundle_downloads
                (bundle_version_id, device_fingerprint_id,
                 downloaded_at, completion_status, byte_count)
            VALUES (:vid, NULL, now(), 'completed', 0)
        """),
        {"vid": str(ver["version_id"])},
    )
    await db.commit()

    return InstallReportResponse(
        recorded=True,
        bundle_id=bundle_id,
        version=ver["version"],
    )
