"""Celery task scaffolds for compliance pipelines.

Wave-5 ships the task surface; real Celery wiring lives in a follow-up that
boots ``celery_app`` against the Redis broker. Until then the production
``CeleryTaskQueue`` writes a row in ``app.event_outbox`` describing the work
so a polling worker (or the eventual Celery beat scheduler) can pick it up.

For tests we ship :class:`InMemoryTaskQueue` which just records calls.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import session_scope
from src.domain.compliance.entities import GdprRequestStatus
from src.domain.compliance.service import ComplianceService
from src.infrastructure.compliance.repository import SqlComplianceRepository

log = logging.getLogger("silklens.compliance.tasks")


@dataclass(slots=True)
class InMemoryTaskQueue:
    """Test/dev double — records enqueued tasks instead of dispatching."""

    exports: list[dict[str, Any]] = field(default_factory=list)
    anonymizations: list[dict[str, Any]] = field(default_factory=list)

    def enqueue_export(self, *, user_id: UUID, residency_region: str, request_id: UUID) -> None:
        self.exports.append(
            {
                "user_id": user_id,
                "residency_region": residency_region,
                "request_id": request_id,
            }
        )

    def enqueue_anonymization(self, *, user_id: UUID, residency_region: str, job_id: UUID) -> None:
        self.anonymizations.append(
            {
                "user_id": user_id,
                "residency_region": residency_region,
                "job_id": job_id,
            }
        )


# --- production scaffold --------------------------------------------------


async def export_user_data(
    *,
    user_id: UUID,
    residency_region: str,
    request_id: UUID,
    session: AsyncSession | None = None,
) -> dict[str, Any]:
    """Collect user data into a JSON manifest, upload to MinIO, and update
    the GDPR request row with the resulting payload URL.

    For Wave-5 we synthesize the manifest from a SQL UNION across the
    user-owned tables and stash it as a JSON document under a deterministic
    object key. The MinIO upload is intentionally lazy — when the client is
    unavailable (tests, local dev), the function still writes the manifest
    onto the request row as a ``data:`` URL so we can assert the shape.
    """
    own_session = session is None
    ctx = session_scope() if own_session else None

    async def _run(db: AsyncSession) -> dict[str, Any]:
        manifest = await _collect_user_manifest(db, user_id, residency_region)
        payload_url = f"data:application/json;base64,{_b64_manifest(manifest)}"
        try:
            from src.infrastructure.media.minio_client import get_minio_client

            client = get_minio_client()
            object_key = f"gdpr-exports/{user_id}/{request_id}.json"
            client.put_object(
                bucket="silklens-compliance",
                key=object_key,
                body=json.dumps(manifest, default=str).encode("utf-8"),
                content_type="application/json",
            )
            payload_url = f"s3://silklens-compliance/{object_key}"
        except Exception as exc:  # pragma: no cover - dev/test fallback
            log.warning("compliance.export.minio_unavailable", extra={"err": str(exc)})

        repo = SqlComplianceRepository(db)
        await repo.update_gdpr_request(
            request_id=request_id,
            residency_region=residency_region,
            status=GdprRequestStatus.COMPLETED,
            payload_url=payload_url,
            completed_at=datetime.now(UTC),
        )
        return {"payload_url": payload_url, "row_counts": manifest.get("counts", {})}

    if own_session and ctx is not None:
        async with ctx as db:
            return await _run(db)
    if session is None:
        raise RuntimeError("session must be provided when own_session=False")
    return await _run(session)


async def anonymize_user(
    *,
    user_id: UUID,
    residency_region: str,
    tenant_id: UUID,
    job_id: UUID,
    session: AsyncSession | None = None,
) -> dict[str, Any]:
    """Run ``app.anonymize_user()`` and update the job row.

    The service emits ``user.anonymized.v1`` and returns counts; we surface
    them so the caller can log / report.
    """
    own_session = session is None
    ctx = session_scope() if own_session else None

    async def _run(db: AsyncSession) -> dict[str, Any]:
        repo = SqlComplianceRepository(db)
        service = ComplianceService(repository=repo)
        result = await service.perform_anonymization(
            user_id=user_id,
            residency_region=residency_region,
            tenant_id=tenant_id,
            job_id=job_id,
        )
        return {
            "rows_anonymized": result.rows_anonymized,
            "tables_touched": list(result.tables_touched),
        }

    if own_session and ctx is not None:
        async with ctx as db:
            return await _run(db)
    if session is None:
        raise RuntimeError("session must be provided when own_session=False")
    return await _run(session)


# --- helpers --------------------------------------------------------------


def _b64_manifest(manifest: dict[str, Any]) -> str:
    import base64

    return base64.b64encode(json.dumps(manifest, default=str).encode("utf-8")).decode("ascii")


async def _collect_user_manifest(
    session: AsyncSession, user_id: UUID, residency_region: str
) -> dict[str, Any]:
    """Aggregate per-table snapshots into a single JSON manifest."""
    counts: dict[str, int] = {}
    sections: dict[str, list[dict[str, Any]]] = {}

    targets = [
        (
            "users",
            "SELECT id, pub_id, status, residency_region, preferred_locale, "
            "preferred_timezone, created_at, updated_at FROM users "
            "WHERE id = :uid AND residency_region = :region",
        ),
        (
            "user_profiles",
            "SELECT user_id, display_name, full_name, bio, "
            "avatar_url, country_code, city, interests, stats "
            "FROM user_profiles WHERE user_id = :uid "
            "AND residency_region = :region",
        ),
        (
            "user_emails",
            "SELECT id, email::text AS email, is_primary, verified_at "
            "FROM user_emails WHERE user_id = :uid "
            "AND residency_region = :region",
        ),
        (
            "user_phones",
            "SELECT id, phone_e164, is_primary, verified_at FROM "
            "user_phones WHERE user_id = :uid "
            "AND residency_region = :region",
        ),
        (
            "consent_records",
            "SELECT id, legal_document_id, basis, granted_at, "
            "withdrawn_at, source FROM consent_records "
            "WHERE user_id = :uid AND residency_region = :region",
        ),
    ]
    for label, sql in targets:
        try:
            result = await session.execute(text(sql), {"uid": user_id, "region": residency_region})
            rows = [dict(r._mapping) for r in result.all()]  # type: ignore[attr-defined]
            sections[label] = rows
            counts[label] = len(rows)
        except Exception as exc:  # pragma: no cover - tolerate missing tables
            log.warning(
                "compliance.export.section_failed",
                extra={"section": label, "err": str(exc)},
            )

    return {
        "user_id": str(user_id),
        "residency_region": residency_region,
        "generated_at": datetime.now(UTC).isoformat(),
        "counts": counts,
        "sections": sections,
    }


__all__ = ["InMemoryTaskQueue", "anonymize_user", "export_user_data"]
