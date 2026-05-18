"""Media-router integration tests.

We do NOT bring up real MinIO inside the test process — the prompt explicitly
forbids it. Instead, a fake client implementing the same upload / presigned_get
/ ensure_bucket surface is injected via the ``minio_client.set_minio_client``
seam. The fake is module-level monkey-patched so every request in the test
session sees it.
"""

from __future__ import annotations

import io
import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.media import minio_client as minio_module

pytestmark = pytest.mark.integration


# --- Fake MinIO -------------------------------------------------------------


class _FakeMinioClient:
    """Records every operation; presigned URLs are deterministic for asserts."""

    def __init__(self) -> None:
        self.uploaded: dict[tuple[str, str], bytes] = {}
        self.buckets: set[str] = set()
        self.default_bucket = "silklens-media"

    def ensure_bucket(self, name: str) -> None:
        self.buckets.add(name)

    def upload(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str,
    ) -> str:
        self.buckets.add(bucket)
        self.uploaded[(bucket, key)] = data
        return f"etag-{len(data)}"

    def presigned_get(self, bucket: str, key: str, ttl_seconds: int) -> str:
        return f"https://fake-minio.test/{bucket}/{key}?ttl={ttl_seconds}"


@pytest.fixture(autouse=True)
def _fake_minio() -> Any:
    fake = _FakeMinioClient()
    minio_module.set_minio_client(fake)  # type: ignore[arg-type]
    yield fake
    minio_module.set_minio_client(None)


# --- Helpers ----------------------------------------------------------------


def _unique_email() -> str:
    return f"media-{uuid.uuid4().hex[:10]}@silklens-test.com"


async def _register(http: AsyncClient) -> dict[str, Any]:
    response = await http.post(
        "/v1/auth/register",
        json={"email": _unique_email(), "password": "MediaTest1234"},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _grant_role(db_session: AsyncSession, user_pub_id: str, role_slug: str) -> None:
    await db_session.execute(
        text(
            """
            INSERT INTO user_roles (
                user_id, residency_region, role_id, scope_tenant_id, granted_by
            )
            SELECT u.id, u.residency_region, r.id, NULL,
                   '00000000-0000-0000-0000-000000000002'::uuid
            FROM users u, roles r
            WHERE u.pub_id = :pub_id AND r.slug = :role
            """
        ),
        {"pub_id": user_pub_id, "role": role_slug},
    )
    await db_session.commit()


def _png_bytes(seed: bytes = b"silklens") -> bytes:
    """Return distinct, valid PNG payloads.

    Real magic bytes + IHDR/IDAT/IEND chunks are required because the service
    sniffs the upload via libmagic (HIGH-3). We embed ``seed`` as a tEXt
    chunk to keep the content_hash distinct across tests without disturbing
    the magic header.
    """
    from PIL import Image

    img = Image.new("RGB", (2, 2), color=(seed[0] % 256, seed[-1] % 256, 0))
    buf = io.BytesIO()
    img.save(
        buf,
        format="PNG",
        pnginfo=_png_text("seed", seed.hex() + uuid.uuid4().hex),
    )
    return buf.getvalue()


def _png_text(key: str, value: str) -> Any:
    from PIL.PngImagePlugin import PngInfo

    info = PngInfo()
    info.add_text(key, value)
    return info


# --- Tests ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_requires_authentication(http: AsyncClient) -> None:
    response = await http.post(
        "/v1/media/uploads",
        files={"file": ("a.png", io.BytesIO(_png_bytes()), "image/png")},
        data={"kind": "image"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_upload_returns_asset_and_signed_url(
    http: AsyncClient, _fake_minio: _FakeMinioClient
) -> None:
    auth = await _register(http)
    token = auth["tokens"]["access_token"]

    response = await http.post(
        "/v1/media/uploads",
        files={"file": ("hero.png", io.BytesIO(_png_bytes()), "image/png")},
        data={"kind": "image", "license_type_slug": "cc_by_sa"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["asset"]["mime_type"] == "image/png"
    assert body["asset"]["kind"] == "image"
    assert body["asset"]["original_filename"] == "hero.png"
    assert body["signed_get_url"].startswith("https://fake-minio.test/")
    # Bytes hit the fake client
    assert len(_fake_minio.uploaded) == 1


@pytest.mark.asyncio
async def test_get_metadata_returns_asset(
    http: AsyncClient,
) -> None:
    auth = await _register(http)
    token = auth["tokens"]["access_token"]

    upload = await http.post(
        "/v1/media/uploads",
        files={"file": ("a.png", io.BytesIO(_png_bytes(b"get-meta")), "image/png")},
        data={"kind": "image"},
        headers={"Authorization": f"Bearer {token}"},
    )
    asset_id = upload.json()["asset"]["id"]

    response = await http.get(
        f"/v1/media/{asset_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == asset_id


@pytest.mark.asyncio
async def test_signed_url_endpoint_returns_url_and_logs_grant(
    http: AsyncClient, db_session: AsyncSession
) -> None:
    auth = await _register(http)
    token = auth["tokens"]["access_token"]

    upload = await http.post(
        "/v1/media/uploads",
        files={"file": ("a.png", io.BytesIO(_png_bytes(b"signed")), "image/png")},
        data={"kind": "image"},
        headers={"Authorization": f"Bearer {token}"},
    )
    asset_id = upload.json()["asset"]["id"]

    response = await http.get(
        f"/v1/media/{asset_id}/signed-url",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["url"].startswith("https://fake-minio.test/")
    assert body["asset_id"] == asset_id

    grant = (
        await db_session.execute(
            text(
                """
                SELECT count(*) FROM signed_url_grants
                WHERE asset_id = CAST(:id AS uuid) AND purpose = 'api_signed_url'
                """
            ),
            {"id": asset_id},
        )
    ).scalar_one()
    assert int(grant) == 1


@pytest.mark.asyncio
async def test_signed_url_rejects_non_owner_without_moderator(
    http: AsyncClient,
) -> None:
    owner = await _register(http)
    upload = await http.post(
        "/v1/media/uploads",
        files={"file": ("a.png", io.BytesIO(_png_bytes(b"other-owner")), "image/png")},
        data={"kind": "image"},
        headers={"Authorization": f"Bearer {owner['tokens']['access_token']}"},
    )
    asset_id = upload.json()["asset"]["id"]

    intruder = await _register(http)
    response = await http.get(
        f"/v1/media/{asset_id}/signed-url",
        headers={"Authorization": f"Bearer {intruder['tokens']['access_token']}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "media.forbidden"


@pytest.mark.asyncio
async def test_delete_owner_succeeds_then_marks_status_deleted(
    http: AsyncClient, db_session: AsyncSession
) -> None:
    auth = await _register(http)
    token = auth["tokens"]["access_token"]

    upload = await http.post(
        "/v1/media/uploads",
        files={"file": ("a.png", io.BytesIO(_png_bytes(b"delete-me")), "image/png")},
        data={"kind": "image"},
        headers={"Authorization": f"Bearer {token}"},
    )
    asset_id = upload.json()["asset"]["id"]

    response = await http.delete(
        f"/v1/media/{asset_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["asset_id"] == asset_id

    row = (
        await db_session.execute(
            text("SELECT status, deleted_at FROM media_assets WHERE id = CAST(:id AS uuid)"),
            {"id": asset_id},
        )
    ).one()
    assert row._mapping["status"] == "deleted"
    assert row._mapping["deleted_at"] is not None


@pytest.mark.asyncio
async def test_upload_rejects_mime_top_level_mismatch(http: AsyncClient) -> None:
    """HIGH-3 / SEC-011: PDF bytes uploaded as image/png must be rejected.

    The router trusts neither the multipart Content-Type nor the file
    extension — libmagic sniffs the first 8 KiB and refuses anything whose
    top-level type diverges from the claim.
    """
    auth = await _register(http)
    token = auth["tokens"]["access_token"]
    # Minimal PDF header — libmagic reports application/pdf.
    pdf_bytes = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"
    response = await http.post(
        "/v1/media/uploads",
        files={"file": ("evil.png", io.BytesIO(pdf_bytes), "image/png")},
        data={"kind": "image"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 415, response.text
    assert response.json()["detail"]["code"] == "media.unsupported_mime"


@pytest.mark.asyncio
async def test_upload_rejects_mime_not_in_allow_list(http: AsyncClient) -> None:
    """HIGH-3: text/html is never accepted, regardless of byte signature."""
    auth = await _register(http)
    token = auth["tokens"]["access_token"]
    response = await http.post(
        "/v1/media/uploads",
        files={"file": ("a.html", io.BytesIO(b"<!doctype html><html></html>"), "text/html")},
        data={"kind": "image"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 415
    assert response.json()["detail"]["code"] == "media.unsupported_mime"


@pytest.mark.asyncio
async def test_unknown_license_slug_returns_422(http: AsyncClient) -> None:
    auth = await _register(http)
    token = auth["tokens"]["access_token"]
    response = await http.post(
        "/v1/media/uploads",
        files={"file": ("a.png", io.BytesIO(_png_bytes(b"unknown-lic")), "image/png")},
        data={"kind": "image", "license_type_slug": "not_a_real_license"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "media.unknown_license"
