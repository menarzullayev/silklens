"""Fine-tuning dataset infrastructure integration tests.

FAZA 7 — Wave-8 Agent-6.

Covers:
  1. Seeded datasets visible on list endpoint (3 expected)
  2. Dataset detail by slug
  3. Add manual example → appears in pending list
  4. Approve example → is_approved=true, absent from pending
  5. Export JSONL format correct (messages key, user/assistant roles)
  6. Export returns empty body for dataset with no approved examples
  7. Job creation (scaffold only, status=pending)
  8. Job status retrieval
  9. Unknown dataset slug → 404
  10. Double-approve → 409
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _email() -> str:
    return f"finetuning-{uuid.uuid4().hex[:10]}@silklens-test.com"


async def _register(http: AsyncClient) -> dict[str, Any]:
    resp = await http.post(
        "/v1/auth/register",
        json={"email": _email(), "password": "FinetunePass12345"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _h(auth: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {auth['tokens']['access_token']}"}


async def _grant_super_admin(db: AsyncSession, pub_id: str) -> None:
    await db.execute(
        text(
            """
            INSERT INTO user_roles (
                user_id, residency_region, role_id, scope_tenant_id, granted_by
            )
            SELECT u.id, u.residency_region, r.id, NULL,
                   '00000000-0000-0000-0000-000000000002'::uuid
            FROM users u, roles r
            WHERE u.pub_id = :pub_id AND r.slug = 'super_admin'
            """
        ),
        {"pub_id": pub_id},
    )
    await db.commit()


@pytest.fixture
async def admin(http: AsyncClient, db_session: AsyncSession) -> dict[str, Any]:
    auth = await _register(http)
    await _grant_super_admin(db_session, auth["user"]["pub_id"])
    return auth


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_datasets_returns_seeded_three(http: AsyncClient, admin: dict[str, Any]) -> None:
    """Migration seeds 3 datasets; all 3 must appear in the list endpoint."""
    resp = await http.get("/v1/admin/finetuning/datasets", headers=_h(admin))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data) >= 3, f"Expected ≥ 3 seeded datasets, got {len(data)}"
    slugs = {d["slug"] for d in data}
    assert "heritage_qa_uz_en" in slugs
    assert "cultural_classification_v1" in slugs
    assert "audio_guide_style_silk_road" in slugs


@pytest.mark.asyncio
async def test_get_dataset_by_slug(http: AsyncClient, admin: dict[str, Any]) -> None:
    """Dataset detail endpoint returns correct metadata."""
    resp = await http.get("/v1/admin/finetuning/datasets/heritage_qa_uz_en", headers=_h(admin))
    assert resp.status_code == 200, resp.text
    d = resp.json()
    assert d["slug"] == "heritage_qa_uz_en"
    assert d["purpose"] == "heritage_qa"
    assert d["target_model_kind"] == "llm"
    assert d["status"] == "collecting"


@pytest.mark.asyncio
async def test_add_manual_example_appears_in_pending(
    http: AsyncClient, admin: dict[str, Any]
) -> None:
    """A newly added manual example must appear in the pending list."""
    # Add
    add_resp = await http.post(
        "/v1/admin/finetuning/datasets/heritage_qa_uz_en/examples",
        headers=_h(admin),
        json={
            "input_text": "Samarqandning eng mashhur obidasi qaysi?",
            "output_text": "Registon maydonidagi uch madrasadir.",
            "language": "uz",
        },
    )
    assert add_resp.status_code == 201, add_resp.text
    example = add_resp.json()
    assert example["is_approved"] is False
    assert example["source_kind"] == "manual"
    example_id = example["id"]

    # Verify in pending list
    pending_resp = await http.get(
        "/v1/admin/finetuning/datasets/heritage_qa_uz_en/examples/pending",
        headers=_h(admin),
    )
    assert pending_resp.status_code == 200, pending_resp.text
    pending_ids = {ex["id"] for ex in pending_resp.json()}
    assert example_id in pending_ids


@pytest.mark.asyncio
async def test_approve_example(http: AsyncClient, admin: dict[str, Any]) -> None:
    """Approving an example sets is_approved=true and removes it from pending."""
    # Add
    add_resp = await http.post(
        "/v1/admin/finetuning/datasets/heritage_qa_uz_en/examples",
        headers=_h(admin),
        json={
            "input_text": "Ibn Sino qayerda tavallud topgan?",
            "output_text": "Afshona qishlog'ida, Buxoro yaqinida.",
            "language": "uz",
        },
    )
    assert add_resp.status_code == 201
    example_id = add_resp.json()["id"]

    # Approve
    approve_resp = await http.post(
        f"/v1/admin/finetuning/examples/{example_id}/approve",
        headers=_h(admin),
    )
    assert approve_resp.status_code == 200, approve_resp.text
    approved = approve_resp.json()
    assert approved["is_approved"] is True
    assert approved["approved_by"] is not None
    assert approved["approved_at"] is not None

    # Must no longer appear in pending
    pending_resp = await http.get(
        "/v1/admin/finetuning/datasets/heritage_qa_uz_en/examples/pending",
        headers=_h(admin),
    )
    pending_ids = {ex["id"] for ex in pending_resp.json()}
    assert example_id not in pending_ids


@pytest.mark.asyncio
async def test_export_jsonl_format(http: AsyncClient, admin: dict[str, Any]) -> None:
    """Exported JSONL must use the messages/user/assistant schema."""
    # Add + approve one example
    add_resp = await http.post(
        "/v1/admin/finetuning/datasets/heritage_qa_uz_en/examples",
        headers=_h(admin),
        json={
            "input_text": "Temuriylar sulolasi qachon tashkil topgan?",
            "output_text": "1370-yilda Amir Temur tomonidan.",
            "language": "uz",
        },
    )
    assert add_resp.status_code == 201
    example_id = add_resp.json()["id"]

    await http.post(
        f"/v1/admin/finetuning/examples/{example_id}/approve",
        headers=_h(admin),
    )

    export_resp = await http.get(
        "/v1/admin/finetuning/datasets/heritage_qa_uz_en/export",
        headers=_h(admin),
    )
    assert export_resp.status_code == 200, export_resp.text
    assert "application/x-ndjson" in export_resp.headers.get("content-type", "")

    lines = [ln for ln in export_resp.text.strip().splitlines() if ln.strip()]
    assert len(lines) >= 1

    # Every line must be valid JSON with messages list
    for line in lines:
        record = json.loads(line)
        assert "messages" in record, f"Missing 'messages' key in: {record}"
        messages = record["messages"]
        roles = [m["role"] for m in messages]
        assert "user" in roles, f"Missing 'user' role in: {messages}"
        assert "assistant" in roles, f"Missing 'assistant' role in: {messages}"
        for msg in messages:
            assert "content" in msg


@pytest.mark.asyncio
async def test_export_empty_dataset_returns_empty_body(
    http: AsyncClient, admin: dict[str, Any]
) -> None:
    """Exporting a dataset with no approved examples returns an empty body."""
    # cultural_classification_v1 has no examples yet in tests
    resp = await http.get(
        "/v1/admin/finetuning/datasets/cultural_classification_v1/export",
        headers=_h(admin),
    )
    assert resp.status_code == 200, resp.text
    assert resp.text.strip() == ""


@pytest.mark.asyncio
async def test_create_job_scaffold(http: AsyncClient, admin: dict[str, Any]) -> None:
    """Job creation returns status=pending without hitting any real provider API."""
    # Fetch dataset id
    ds_resp = await http.get("/v1/admin/finetuning/datasets/heritage_qa_uz_en", headers=_h(admin))
    dataset_id = ds_resp.json()["id"]

    job_resp = await http.post(
        "/v1/admin/finetuning/jobs",
        headers=_h(admin),
        json={
            "dataset_id": dataset_id,
            "provider": "openai",
            "base_model_slug": "gpt-4o-mini-2024-07-18",
            "job_kind": "supervised",
            "hyperparams": {"n_epochs": 3, "batch_size": 16},
        },
    )
    assert job_resp.status_code == 201, job_resp.text
    job = job_resp.json()
    assert job["status"] == "pending"
    assert job["provider"] == "openai"
    assert job["provider_job_id"] is None  # not submitted yet
    assert job["hyperparams"]["n_epochs"] == 3


@pytest.mark.asyncio
async def test_get_job_status(http: AsyncClient, admin: dict[str, Any]) -> None:
    """GET /jobs/{id} returns the same job that was just created."""
    ds_resp = await http.get("/v1/admin/finetuning/datasets/heritage_qa_uz_en", headers=_h(admin))
    dataset_id = ds_resp.json()["id"]

    create_resp = await http.post(
        "/v1/admin/finetuning/jobs",
        headers=_h(admin),
        json={
            "dataset_id": dataset_id,
            "provider": "anthropic",
            "base_model_slug": "claude-haiku-20240307",
            "job_kind": "lora_adapter",
            "hyperparams": {},
        },
    )
    assert create_resp.status_code == 201
    job_id = create_resp.json()["id"]

    get_resp = await http.get(f"/v1/admin/finetuning/jobs/{job_id}", headers=_h(admin))
    assert get_resp.status_code == 200, get_resp.text
    assert get_resp.json()["id"] == job_id
    assert get_resp.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_unknown_slug_returns_404(http: AsyncClient, admin: dict[str, Any]) -> None:
    """Requesting a non-existent dataset slug returns 404."""
    resp = await http.get("/v1/admin/finetuning/datasets/does_not_exist_xyz", headers=_h(admin))
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "dataset_not_found"


@pytest.mark.asyncio
async def test_double_approve_returns_409(http: AsyncClient, admin: dict[str, Any]) -> None:
    """Approving an already-approved example returns 409 AlreadyApproved."""
    add_resp = await http.post(
        "/v1/admin/finetuning/datasets/heritage_qa_uz_en/examples",
        headers=_h(admin),
        json={
            "input_text": "Navruz nima?",
            "output_text": "Navruz — Markaziy Osiyoda yangi yil bayrami.",
            "language": "uz",
        },
    )
    example_id = add_resp.json()["id"]

    first = await http.post(
        f"/v1/admin/finetuning/examples/{example_id}/approve",
        headers=_h(admin),
    )
    assert first.status_code == 200

    second = await http.post(
        f"/v1/admin/finetuning/examples/{example_id}/approve",
        headers=_h(admin),
    )
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "example_already_approved"
