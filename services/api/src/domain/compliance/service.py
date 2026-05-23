"""Compliance application service.

Coordinates legal-document publication, consent records, GDPR request
lifecycle (export / delete / cancel), and the anonymization pipeline. The
service emits domain events (``consent.changed.v1``, ``user.anonymized.v1``)
through the repository so downstream subscribers can react.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Callable, Protocol
from uuid import UUID

from src.domain.compliance.entities import (
    AnonymizationJob,
    AnonymizationJobStatus,
    ConsentBasis,
    ConsentRecord,
    CookieCategories,
    CookieConsent,
    GdprRequest,
    GdprRequestKind,
    GdprRequestStatus,
    LegalDocument,
    LegalDocumentKind,
)
from src.domain.compliance.errors import (
    ComplianceError,
    DeletionAlreadyScheduled,
    GdprRequestNotFound,
    GracePeriodExpired,
    InvalidGdprState,
    LegalDocumentNotFound,
    LegalDocumentVersionExists,
)
from src.domain.compliance.repository import ComplianceRepository

DELETION_GRACE_PERIOD = timedelta(days=30)


class TaskQueue(Protocol):
    """Optional async task dispatcher.

    The service stays usable in unit tests without a real Celery client by
    accepting a Protocol with both methods. Production wiring injects the
    Celery-backed implementation from ``infrastructure/compliance/tasks.py``.
    """

    def enqueue_export(self, *, user_id: UUID, residency_region: str, request_id: UUID) -> None: ...

    def enqueue_anonymization(
        self, *, user_id: UUID, residency_region: str, job_id: UUID
    ) -> None: ...


@dataclass(slots=True, frozen=True)
class AnonymizationResult:
    job: AnonymizationJob
    rows_anonymized: int
    tables_touched: tuple[str, ...]


class ComplianceService:
    def __init__(
        self,
        *,
        repository: ComplianceRepository,
        tasks: TaskQueue | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._repo = repository
        self._tasks = tasks
        self._now = now or (lambda: datetime.now(UTC))

    # ------------------------------------------------------------------
    # legal documents
    # ------------------------------------------------------------------

    async def current_policy(
        self,
        *,
        kind: LegalDocumentKind,
        language_tag: str = "en",
        tenant_id: UUID | None = None,
    ) -> LegalDocument:
        doc = await self._repo.get_current_legal_document(
            kind=kind, language_tag=language_tag, tenant_id=tenant_id
        )
        if doc is None and language_tag != "en":
            doc = await self._repo.get_current_legal_document(
                kind=kind, language_tag="en", tenant_id=tenant_id
            )
        if doc is None:
            raise LegalDocumentNotFound(f"no active {kind.value} document")
        return doc

    async def list_policy_history(
        self,
        *,
        kind: LegalDocumentKind,
        tenant_id: UUID | None = None,
    ) -> tuple[LegalDocument, ...]:
        return await self._repo.list_legal_document_history(kind=kind, tenant_id=tenant_id)

    async def publish_policy(
        self,
        *,
        kind: LegalDocumentKind,
        version: str,
        language_tag: str,
        content_md: str,
        tenant_id: UUID | None,
        actor: UUID,
    ) -> LegalDocument:
        try:
            doc = await self._repo.insert_legal_document(
                kind=kind,
                version=version,
                language_tag=language_tag,
                content_md=content_md,
                tenant_id=tenant_id,
                created_by=actor,
            )
        except LegalDocumentVersionExists:
            raise
        # Best-effort event emission — tenant_id may be NULL for platform-wide
        # documents; we fall back to the system tenant in that case.
        await self._repo.emit_event(
            tenant_id=tenant_id or UUID("00000000-0000-0000-0000-000000000001"),
            event_name="legal_document.published.v1",
            aggregate_type="legal_document",
            aggregate_id=doc.id,
            payload={
                "kind": kind.value,
                "version": version,
                "language_tag": language_tag,
                "sha256": doc.sha256,
                "actor": str(actor),
            },
        )
        return doc

    # ------------------------------------------------------------------
    # consent records
    # ------------------------------------------------------------------

    async def record_consent(
        self,
        *,
        user_id: UUID,
        residency_region: str,
        tenant_id: UUID,
        legal_document_id: UUID,
        basis: ConsentBasis = ConsentBasis.CONSENT,
        ip_address: str | None = None,
        user_agent: str | None = None,
        source: str = "settings",
    ) -> ConsentRecord:
        doc = await self._repo.get_legal_document(legal_document_id)
        if doc is None:
            raise LegalDocumentNotFound(str(legal_document_id))
        consent = await self._repo.insert_consent(
            user_id=user_id,
            residency_region=residency_region,
            tenant_id=tenant_id,
            legal_document_id=legal_document_id,
            basis=basis,
            ip_address=ip_address,
            user_agent=user_agent,
            source=source,
        )
        await self._repo.emit_event(
            tenant_id=tenant_id,
            event_name="consent.changed.v1",
            aggregate_type="user",
            aggregate_id=user_id,
            payload={
                "action": "granted",
                "legal_document_id": str(legal_document_id),
                "doc_kind": doc.kind.value,
                "doc_version": doc.version,
                "language_tag": doc.language_tag,
                "basis": basis.value,
            },
        )
        return consent

    async def withdraw_consent(
        self,
        *,
        user_id: UUID,
        residency_region: str,
        tenant_id: UUID,
        legal_document_id: UUID,
    ) -> ConsentRecord:
        consent = await self._repo.withdraw_consent(
            user_id=user_id,
            residency_region=residency_region,
            legal_document_id=legal_document_id,
        )
        if consent is None:
            from src.domain.compliance.errors import ConsentNotFound

            raise ConsentNotFound(str(legal_document_id))
        await self._repo.emit_event(
            tenant_id=tenant_id,
            event_name="consent.withdrawn.v1",
            aggregate_type="user",
            aggregate_id=user_id,
            payload={
                "legal_document_id": str(legal_document_id),
            },
        )
        return consent

    async def list_consents(
        self,
        *,
        user_id: UUID,
        residency_region: str,
    ) -> tuple[ConsentRecord, ...]:
        return await self._repo.list_consents(user_id=user_id, residency_region=residency_region)

    # ------------------------------------------------------------------
    # GDPR requests
    # ------------------------------------------------------------------

    async def request_export(
        self,
        *,
        user_id: UUID,
        residency_region: str,
        tenant_id: UUID,
    ) -> GdprRequest:
        req = await self._repo.insert_gdpr_request(
            user_id=user_id,
            residency_region=residency_region,
            tenant_id=tenant_id,
            request_kind=GdprRequestKind.EXPORT,
            scheduled_for=None,
            reason=None,
        )
        if self._tasks is not None:
            self._tasks.enqueue_export(
                user_id=user_id, residency_region=residency_region, request_id=req.id
            )
        await self._repo.emit_event(
            tenant_id=tenant_id,
            event_name="gdpr.export_requested.v1",
            aggregate_type="user",
            aggregate_id=user_id,
            payload={"request_id": str(req.id)},
        )
        return req

    async def get_request(
        self,
        *,
        request_id: UUID,
        residency_region: str,
        user_id: UUID,
    ) -> GdprRequest:
        req = await self._repo.get_gdpr_request(
            request_id=request_id, residency_region=residency_region
        )
        if req is None or req.user_id != user_id:
            raise GdprRequestNotFound(str(request_id))
        return req

    async def request_deletion(
        self,
        *,
        user_id: UUID,
        residency_region: str,
        tenant_id: UUID,
        reason: str | None = None,
    ) -> GdprRequest:
        pending = await self._repo.find_pending_delete_request(
            user_id=user_id, residency_region=residency_region
        )
        if pending is not None:
            raise DeletionAlreadyScheduled(str(pending.id))
        scheduled_for = self._now() + DELETION_GRACE_PERIOD
        req = await self._repo.insert_gdpr_request(
            user_id=user_id,
            residency_region=residency_region,
            tenant_id=tenant_id,
            request_kind=GdprRequestKind.DELETE,
            scheduled_for=scheduled_for,
            reason=reason,
        )
        job = await self._repo.insert_anonymization_job(
            user_id=user_id,
            residency_region=residency_region,
            tenant_id=tenant_id,
            gdpr_request_id=req.id,
            scheduled_for=scheduled_for,
        )
        if self._tasks is not None:
            self._tasks.enqueue_anonymization(
                user_id=user_id, residency_region=residency_region, job_id=job.id
            )
        await self._repo.emit_event(
            tenant_id=tenant_id,
            event_name="gdpr.deletion_requested.v1",
            aggregate_type="user",
            aggregate_id=user_id,
            payload={
                "request_id": str(req.id),
                "job_id": str(job.id),
                "scheduled_for": scheduled_for.isoformat(),
                "reason": reason,
            },
        )
        return req

    async def cancel_deletion(
        self,
        *,
        user_id: UUID,
        residency_region: str,
        tenant_id: UUID,
        request_id: UUID,
    ) -> GdprRequest:
        req = await self._repo.get_gdpr_request(
            request_id=request_id, residency_region=residency_region
        )
        if req is None or req.user_id != user_id:
            raise GdprRequestNotFound(str(request_id))
        if req.request_kind != GdprRequestKind.DELETE:
            raise InvalidGdprState("request is not a deletion")
        if req.status not in (GdprRequestStatus.SUBMITTED, GdprRequestStatus.PROCESSING):
            raise InvalidGdprState(f"cannot cancel from status={req.status.value}")
        if req.scheduled_for is not None and req.scheduled_for <= self._now():
            raise GracePeriodExpired(str(request_id))
        updated = await self._repo.update_gdpr_request(
            request_id=request_id,
            residency_region=residency_region,
            status=GdprRequestStatus.CANCELLED,
            completed_at=self._now(),
        )
        await self._repo.cancel_anonymization_for_request(
            gdpr_request_id=request_id, residency_region=residency_region
        )
        await self._repo.emit_event(
            tenant_id=tenant_id,
            event_name="gdpr.deletion_cancelled.v1",
            aggregate_type="user",
            aggregate_id=user_id,
            payload={"request_id": str(request_id)},
        )
        return updated

    async def admin_process_request(
        self,
        *,
        request_id: UUID,
        residency_region: str,
        admin_user_id: UUID,
        decision_note: str | None = None,
        payload_url: str | None = None,
    ) -> GdprRequest:
        req = await self._repo.get_gdpr_request(
            request_id=request_id, residency_region=residency_region
        )
        if req is None:
            raise GdprRequestNotFound(str(request_id))
        return await self._repo.update_gdpr_request(
            request_id=request_id,
            residency_region=residency_region,
            status=GdprRequestStatus.COMPLETED,
            payload_url=payload_url,
            completed_at=self._now(),
            decided_by_admin_user_id=admin_user_id,
            decision_note=decision_note,
        )

    # ------------------------------------------------------------------
    # Anonymization
    # ------------------------------------------------------------------

    async def perform_anonymization(
        self,
        *,
        user_id: UUID,
        residency_region: str,
        tenant_id: UUID,
        job_id: UUID,
    ) -> AnonymizationResult:
        started_at = self._now()
        await self._repo.update_anonymization_job(
            job_id=job_id,
            residency_region=residency_region,
            status=AnonymizationJobStatus.RUNNING,
            started_at=started_at,
        )
        try:
            rows, tables = await self._repo.run_anonymize_sql(
                user_id=user_id, residency_region=residency_region
            )
        except Exception as exc:
            await self._repo.update_anonymization_job(
                job_id=job_id,
                residency_region=residency_region,
                status=AnonymizationJobStatus.FAILED,
                finished_at=self._now(),
                error_message=str(exc),
            )
            raise ComplianceError(f"anonymization failed: {exc}") from exc

        job = await self._repo.update_anonymization_job(
            job_id=job_id,
            residency_region=residency_region,
            status=AnonymizationJobStatus.COMPLETED,
            rows_anonymized=rows,
            tables_touched=tables,
            finished_at=self._now(),
        )
        await self._repo.emit_event(
            tenant_id=tenant_id,
            event_name="user.anonymized.v1",
            aggregate_type="user",
            aggregate_id=user_id,
            payload={
                "job_id": str(job_id),
                "rows": rows,
                "tables_touched": list(tables),
            },
        )
        return AnonymizationResult(job=job, rows_anonymized=rows, tables_touched=tables)

    # ------------------------------------------------------------------
    # cookie consent
    # ------------------------------------------------------------------

    async def record_cookie_consent(
        self,
        *,
        session_cookie_id: str,
        categories: CookieCategories,
        region: str | None,
        ip_hash: str | None,
        user_agent: str | None,
        user_id: UUID | None = None,
        tenant_id: UUID | None = None,
    ) -> CookieConsent:
        return await self._repo.insert_cookie_consent(
            session_cookie_id=session_cookie_id,
            categories=categories,
            region=region,
            ip_hash=ip_hash,
            user_agent=user_agent,
            user_id=user_id,
            tenant_id=tenant_id,
        )


__all__ = [
    "DELETION_GRACE_PERIOD",
    "AnonymizationResult",
    "ComplianceService",
    "TaskQueue",
]
