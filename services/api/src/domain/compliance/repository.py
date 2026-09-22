"""Compliance repository protocol (port).

The service depends on this Protocol; the SQL implementation lives in
``src/infrastructure/compliance/repository.py``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
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


class ComplianceRepository(Protocol):
    # --- legal documents -------------------------------------------------

    async def get_current_legal_document(
        self,
        *,
        kind: LegalDocumentKind,
        language_tag: str,
        tenant_id: UUID | None = None,
    ) -> LegalDocument | None: ...

    async def list_legal_document_history(
        self,
        *,
        kind: LegalDocumentKind,
        tenant_id: UUID | None = None,
    ) -> tuple[LegalDocument, ...]: ...

    async def insert_legal_document(
        self,
        *,
        kind: LegalDocumentKind,
        version: str,
        language_tag: str,
        content_md: str,
        tenant_id: UUID | None,
        created_by: UUID | None,
    ) -> LegalDocument: ...

    async def get_legal_document(self, doc_id: UUID) -> LegalDocument | None: ...

    # --- consents --------------------------------------------------------

    async def insert_consent(
        self,
        *,
        user_id: UUID,
        residency_region: str,
        tenant_id: UUID,
        legal_document_id: UUID,
        basis: ConsentBasis,
        ip_address: str | None,
        user_agent: str | None,
        source: str,
    ) -> ConsentRecord: ...

    async def withdraw_consent(
        self,
        *,
        user_id: UUID,
        residency_region: str,
        legal_document_id: UUID,
    ) -> ConsentRecord | None: ...

    async def list_consents(
        self,
        *,
        user_id: UUID,
        residency_region: str,
    ) -> tuple[ConsentRecord, ...]: ...

    # --- gdpr requests ---------------------------------------------------

    async def insert_gdpr_request(
        self,
        *,
        user_id: UUID,
        residency_region: str,
        tenant_id: UUID,
        request_kind: GdprRequestKind,
        scheduled_for: datetime | None,
        reason: str | None,
    ) -> GdprRequest: ...

    async def get_gdpr_request(
        self,
        *,
        request_id: UUID,
        residency_region: str,
    ) -> GdprRequest | None: ...

    async def update_gdpr_request(
        self,
        *,
        request_id: UUID,
        residency_region: str,
        status: GdprRequestStatus | None = None,
        payload_url: str | None = None,
        completed_at: datetime | None = None,
        decided_by_admin_user_id: UUID | None = None,
        decision_note: str | None = None,
    ) -> GdprRequest: ...

    async def find_pending_delete_request(
        self,
        *,
        user_id: UUID,
        residency_region: str,
    ) -> GdprRequest | None: ...

    # --- anonymization jobs ---------------------------------------------

    async def insert_anonymization_job(
        self,
        *,
        user_id: UUID,
        residency_region: str,
        tenant_id: UUID,
        gdpr_request_id: UUID | None,
        scheduled_for: datetime,
    ) -> AnonymizationJob: ...

    async def update_anonymization_job(
        self,
        *,
        job_id: UUID,
        residency_region: str,
        status: AnonymizationJobStatus | None = None,
        rows_anonymized: int | None = None,
        tables_touched: tuple[str, ...] | None = None,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
        error_message: str | None = None,
    ) -> AnonymizationJob: ...

    async def cancel_anonymization_for_request(
        self,
        *,
        gdpr_request_id: UUID,
        residency_region: str,
    ) -> int: ...

    async def run_anonymize_sql(
        self,
        *,
        user_id: UUID,
        residency_region: str,
    ) -> tuple[int, tuple[str, ...]]: ...

    # --- cookie consents -------------------------------------------------

    async def insert_cookie_consent(
        self,
        *,
        session_cookie_id: str,
        categories: CookieCategories,
        region: str | None,
        ip_hash: str | None,
        user_agent: str | None,
        user_id: UUID | None,
        tenant_id: UUID | None,
    ) -> CookieConsent: ...

    # --- events ----------------------------------------------------------

    async def emit_event(
        self,
        *,
        tenant_id: UUID,
        event_name: str,
        aggregate_type: str,
        aggregate_id: UUID,
        payload: dict[str, object],
    ) -> None: ...
