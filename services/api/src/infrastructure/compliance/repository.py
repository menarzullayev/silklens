"""SQL implementation of ``ComplianceRepository``.

Hand-written SQL (per the identity / heritage convention): the canonical
schema lives in migration 0071 and the ORM-on-top duplication has been
avoided across the rest of the codebase.
"""

from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

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
from src.domain.compliance.errors import LegalDocumentVersionExists


def _json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)


# --- row mappers ----------------------------------------------------------


def _row_to_legal_document(row: object) -> LegalDocument:
    m = row._mapping  # type: ignore[attr-defined]
    return LegalDocument(
        id=m["id"],
        kind=LegalDocumentKind(m["kind"]),
        version=m["version"],
        language_tag=m["language_tag"],
        content_md=m["content_md"],
        sha256=m["sha256"],
        effective_from=m["effective_from"],
        effective_until=m["effective_until"],
        tenant_id=m["tenant_id"],
        created_by=m["created_by"],
        created_at=m["created_at"],
    )


def _row_to_consent(row: object) -> ConsentRecord:
    m = row._mapping  # type: ignore[attr-defined]
    return ConsentRecord(
        id=m["id"],
        user_id=m["user_id"],
        residency_region=m["residency_region"],
        tenant_id=m["tenant_id"],
        legal_document_id=m["legal_document_id"],
        basis=ConsentBasis(m["basis"]),
        granted_at=m["granted_at"],
        withdrawn_at=m["withdrawn_at"],
        ip_address=str(m["ip_address"]) if m["ip_address"] is not None else None,
        user_agent=m["user_agent"],
        source=m["source"],
        purpose=m["purpose"],
        created_at=m["created_at"],
    )


def _row_to_request(row: object) -> GdprRequest:
    m = row._mapping  # type: ignore[attr-defined]
    return GdprRequest(
        id=m["id"],
        user_id=m["user_id"],
        residency_region=m["residency_region"],
        tenant_id=m["tenant_id"],
        request_kind=GdprRequestKind(m["request_kind"]),
        status=GdprRequestStatus(m["status"]),
        payload_url=m["payload_url"],
        reason=m["reason"],
        scheduled_for=m["scheduled_for"],
        created_at=m["created_at"],
        completed_at=m["completed_at"],
        requested_by_user_id=m["requested_by_user_id"],
        decided_by_admin_user_id=m["decided_by_admin_user_id"],
        decision_note=m["decision_note"],
    )


def _row_to_job(row: object) -> AnonymizationJob:
    m = row._mapping  # type: ignore[attr-defined]
    return AnonymizationJob(
        id=m["id"],
        user_id=m["user_id"],
        residency_region=m["residency_region"],
        tenant_id=m["tenant_id"],
        gdpr_request_id=m["gdpr_request_id"],
        status=AnonymizationJobStatus(m["status"]),
        scheduled_for=m["scheduled_for"],
        started_at=m["started_at"],
        finished_at=m["finished_at"],
        rows_anonymized=m["rows_anonymized"],
        tables_touched=tuple(m["tables_touched"] or ()),
        error_message=m["error_message"],
        created_at=m["created_at"],
    )


def _row_to_cookie(row: object) -> CookieConsent:
    m = row._mapping  # type: ignore[attr-defined]
    raw = m["categories"] or {}
    cats = CookieCategories(
        strictly_necessary=bool(raw.get("strictly_necessary", True)),
        analytics=bool(raw.get("analytics", False)),
        marketing=bool(raw.get("marketing", False)),
        ad_targeting=bool(raw.get("ad_targeting", False)),
    )
    return CookieConsent(
        id=m["id"],
        session_cookie_id=m["session_cookie_id"],
        categories=cats,
        given_at=m["given_at"],
        region=m["region"],
        ip_hash=m["ip_hash"],
        user_agent=m["user_agent"],
        user_id=m["user_id"],
        tenant_id=m["tenant_id"],
    )


_LEGAL_COLS = (
    "id, tenant_id, kind, version, language_tag, content_md, sha256, "
    "effective_from, effective_until, created_by, created_at, updated_at"
)
_CONSENT_COLS = (
    "id, user_id, residency_region, tenant_id, legal_document_id, basis, "
    "purpose, granted_at, withdrawn_at, ip_address, user_agent, source, created_at"
)
_REQUEST_COLS = (
    "id, user_id, residency_region, tenant_id, request_kind, status, payload_url, "
    "reason, scheduled_for, requested_by_user_id, decided_by_admin_user_id, "
    "decision_note, created_at, completed_at"
)
_JOB_COLS = (
    "id, user_id, residency_region, tenant_id, gdpr_request_id, status, "
    "scheduled_for, started_at, finished_at, rows_anonymized, tables_touched, "
    "error_message, created_at"
)
_COOKIE_COLS = (
    "id, session_cookie_id, user_id, tenant_id, ip_hash, user_agent, categories, region, given_at"
)


class SqlComplianceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    # --- legal docs ---------------------------------------------------

    async def get_current_legal_document(
        self,
        *,
        kind: LegalDocumentKind,
        language_tag: str,
        tenant_id: UUID | None = None,
    ) -> LegalDocument | None:
        # Prefer tenant-specific override, fall back to platform default.
        result = await self._s.execute(
            text(
                f"""
                SELECT {_LEGAL_COLS}
                FROM legal_documents
                WHERE kind = :kind
                  AND language_tag = :lang
                  AND effective_until IS NULL
                  AND (tenant_id = :tenant OR tenant_id IS NULL)
                ORDER BY (tenant_id IS NULL), effective_from DESC
                LIMIT 1
                """  # noqa: S608
            ),
            {"kind": kind.value, "lang": language_tag, "tenant": tenant_id},
        )
        row = result.first()
        return _row_to_legal_document(row) if row else None

    async def list_legal_document_history(
        self,
        *,
        kind: LegalDocumentKind,
        tenant_id: UUID | None = None,
    ) -> tuple[LegalDocument, ...]:
        result = await self._s.execute(
            text(
                f"""
                SELECT {_LEGAL_COLS}
                FROM legal_documents
                WHERE kind = :kind
                  AND (tenant_id = :tenant OR tenant_id IS NULL OR :tenant IS NULL)
                ORDER BY effective_from DESC, version DESC
                """  # noqa: S608
            ),
            {"kind": kind.value, "tenant": tenant_id},
        )
        return tuple(_row_to_legal_document(r) for r in result.all())

    async def insert_legal_document(
        self,
        *,
        kind: LegalDocumentKind,
        version: str,
        language_tag: str,
        content_md: str,
        tenant_id: UUID | None,
        created_by: UUID | None,
    ) -> LegalDocument:
        try:
            result = await self._s.execute(
                text(
                    f"""
                    INSERT INTO legal_documents
                        (kind, version, language_tag, content_md, sha256,
                         tenant_id, created_by, effective_from)
                    VALUES
                        (:kind, :version, :lang, :body,
                         encode(digest(:body, 'sha256'), 'hex'),
                         :tenant, :actor, now())
                    RETURNING {_LEGAL_COLS}
                    """  # noqa: S608
                ),
                {
                    "kind": kind.value,
                    "version": version,
                    "lang": language_tag,
                    "body": content_md,
                    "tenant": tenant_id,
                    "actor": created_by,
                },
            )
            row = result.one()
            await self._s.commit()
            return _row_to_legal_document(row)
        except IntegrityError as exc:
            await self._s.rollback()
            raise LegalDocumentVersionExists(
                f"{kind.value}@{version}/{language_tag} already exists"
            ) from exc

    async def get_legal_document(self, doc_id: UUID) -> LegalDocument | None:
        result = await self._s.execute(
            text(
                f"SELECT {_LEGAL_COLS} FROM legal_documents WHERE id = :id"  # noqa: S608
            ),
            {"id": doc_id},
        )
        row = result.first()
        return _row_to_legal_document(row) if row else None

    # --- consents -----------------------------------------------------

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
    ) -> ConsentRecord:
        result = await self._s.execute(
            text(
                f"""
                INSERT INTO consent_records
                    (user_id, residency_region, tenant_id, legal_document_id,
                     basis, ip_address, user_agent, source)
                VALUES
                    (:uid, :region, :tenant, :doc, :basis,
                     CAST(NULLIF(:ip, '') AS inet), :ua, :source)
                RETURNING {_CONSENT_COLS}
                """  # noqa: S608
            ),
            {
                "uid": user_id,
                "region": residency_region,
                "tenant": tenant_id,
                "doc": legal_document_id,
                "basis": basis.value,
                "ip": ip_address or "",
                "ua": user_agent,
                "source": source,
            },
        )
        row = result.one()
        await self._s.commit()
        return _row_to_consent(row)

    async def withdraw_consent(
        self,
        *,
        user_id: UUID,
        residency_region: str,
        legal_document_id: UUID,
    ) -> ConsentRecord | None:
        result = await self._s.execute(
            text(
                f"""
                UPDATE consent_records
                SET withdrawn_at = now()
                WHERE user_id = :uid
                  AND residency_region = :region
                  AND legal_document_id = :doc
                  AND withdrawn_at IS NULL
                RETURNING {_CONSENT_COLS}
                """  # noqa: S608
            ),
            {"uid": user_id, "region": residency_region, "doc": legal_document_id},
        )
        rows = result.all()
        await self._s.commit()
        if not rows:
            return None
        # Most-recent record wins for the return; we updated all matching rows.
        return _row_to_consent(rows[0])

    async def list_consents(
        self,
        *,
        user_id: UUID,
        residency_region: str,
    ) -> tuple[ConsentRecord, ...]:
        result = await self._s.execute(
            text(
                f"""
                SELECT {_CONSENT_COLS}
                FROM consent_records
                WHERE user_id = :uid AND residency_region = :region
                ORDER BY granted_at DESC
                """  # noqa: S608
            ),
            {"uid": user_id, "region": residency_region},
        )
        return tuple(_row_to_consent(r) for r in result.all())

    # --- gdpr requests -----------------------------------------------

    async def insert_gdpr_request(
        self,
        *,
        user_id: UUID,
        residency_region: str,
        tenant_id: UUID,
        request_kind: GdprRequestKind,
        scheduled_for: datetime | None,
        reason: str | None,
    ) -> GdprRequest:
        result = await self._s.execute(
            text(
                f"""
                INSERT INTO gdpr_requests
                    (user_id, residency_region, tenant_id, request_kind,
                     status, scheduled_for, reason, requested_by_user_id)
                VALUES
                    (:uid, :region, :tenant, :kind, 'submitted',
                     :scheduled, :reason, :uid)
                RETURNING {_REQUEST_COLS}
                """  # noqa: S608
            ),
            {
                "uid": user_id,
                "region": residency_region,
                "tenant": tenant_id,
                "kind": request_kind.value,
                "scheduled": scheduled_for,
                "reason": reason,
            },
        )
        row = result.one()
        await self._s.commit()
        return _row_to_request(row)

    async def get_gdpr_request(
        self,
        *,
        request_id: UUID,
        residency_region: str,
    ) -> GdprRequest | None:
        result = await self._s.execute(
            text(
                f"""
                SELECT {_REQUEST_COLS}
                FROM gdpr_requests
                WHERE id = :id AND residency_region = :region
                """  # noqa: S608
            ),
            {"id": request_id, "region": residency_region},
        )
        row = result.first()
        return _row_to_request(row) if row else None

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
    ) -> GdprRequest:
        sets: list[str] = []
        params: dict[str, object] = {"id": request_id, "region": residency_region}
        if status is not None:
            sets.append("status = :status")
            params["status"] = status.value
        if payload_url is not None:
            sets.append("payload_url = :url")
            params["url"] = payload_url
        if completed_at is not None:
            sets.append("completed_at = :done_at")
            params["done_at"] = completed_at
        if decided_by_admin_user_id is not None:
            sets.append("decided_by_admin_user_id = :admin")
            params["admin"] = decided_by_admin_user_id
        if decision_note is not None:
            sets.append("decision_note = :note")
            params["note"] = decision_note
        if not sets:
            row = await self._s.execute(
                text(
                    f"SELECT {_REQUEST_COLS} FROM gdpr_requests "  # noqa: S608
                    "WHERE id = :id AND residency_region = :region"
                ),
                params,
            )
            return _row_to_request(row.one())
        update_result = await self._s.execute(
            text(
                f"""
                UPDATE gdpr_requests
                SET {", ".join(sets)}
                WHERE id = :id AND residency_region = :region
                RETURNING {_REQUEST_COLS}
                """  # noqa: S608
            ),
            params,
        )
        updated_row = update_result.one()
        await self._s.commit()
        return _row_to_request(updated_row)

    async def find_pending_delete_request(
        self,
        *,
        user_id: UUID,
        residency_region: str,
    ) -> GdprRequest | None:
        result = await self._s.execute(
            text(
                f"""
                SELECT {_REQUEST_COLS}
                FROM gdpr_requests
                WHERE user_id = :uid
                  AND residency_region = :region
                  AND request_kind = 'delete'
                  AND status IN ('submitted','processing')
                LIMIT 1
                """  # noqa: S608
            ),
            {"uid": user_id, "region": residency_region},
        )
        row = result.first()
        return _row_to_request(row) if row else None

    # --- anonymization ----------------------------------------------

    async def insert_anonymization_job(
        self,
        *,
        user_id: UUID,
        residency_region: str,
        tenant_id: UUID,
        gdpr_request_id: UUID | None,
        scheduled_for: datetime,
    ) -> AnonymizationJob:
        result = await self._s.execute(
            text(
                f"""
                INSERT INTO anonymization_jobs
                    (user_id, residency_region, tenant_id, gdpr_request_id,
                     status, scheduled_for)
                VALUES
                    (:uid, :region, :tenant, :req, 'pending', :sched)
                RETURNING {_JOB_COLS}
                """  # noqa: S608
            ),
            {
                "uid": user_id,
                "region": residency_region,
                "tenant": tenant_id,
                "req": gdpr_request_id,
                "sched": scheduled_for,
            },
        )
        row = result.one()
        await self._s.commit()
        return _row_to_job(row)

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
    ) -> AnonymizationJob:
        sets: list[str] = []
        params: dict[str, object] = {"id": job_id, "region": residency_region}
        if status is not None:
            sets.append("status = :status")
            params["status"] = status.value
        if rows_anonymized is not None:
            sets.append("rows_anonymized = :rows")
            params["rows"] = rows_anonymized
        if tables_touched is not None:
            sets.append("tables_touched = :tables")
            params["tables"] = list(tables_touched)
        if started_at is not None:
            sets.append("started_at = :start")
            params["start"] = started_at
        if finished_at is not None:
            sets.append("finished_at = :finish")
            params["finish"] = finished_at
        if error_message is not None:
            sets.append("error_message = :err")
            params["err"] = error_message
        if not sets:
            row = await self._s.execute(
                text(
                    f"SELECT {_JOB_COLS} FROM anonymization_jobs "  # noqa: S608
                    "WHERE id = :id AND residency_region = :region"
                ),
                params,
            )
            return _row_to_job(row.one())
        update_result = await self._s.execute(
            text(
                f"""
                UPDATE anonymization_jobs
                SET {", ".join(sets)}
                WHERE id = :id AND residency_region = :region
                RETURNING {_JOB_COLS}
                """  # noqa: S608
            ),
            params,
        )
        updated_row = update_result.one()
        await self._s.commit()
        return _row_to_job(updated_row)

    async def cancel_anonymization_for_request(
        self,
        *,
        gdpr_request_id: UUID,
        residency_region: str,
    ) -> int:
        result = await self._s.execute(
            text(
                """
                UPDATE anonymization_jobs
                SET status = 'cancelled', finished_at = now()
                WHERE gdpr_request_id = :req
                  AND residency_region = :region
                  AND status IN ('pending','running')
                """
            ),
            {"req": gdpr_request_id, "region": residency_region},
        )
        await self._s.commit()
        return result.rowcount or 0  # type: ignore[attr-defined]

    async def run_anonymize_sql(
        self,
        *,
        user_id: UUID,
        residency_region: str,
    ) -> tuple[int, tuple[str, ...]]:
        result = await self._s.execute(
            text("SELECT app.anonymize_user(:uid, :region)"),
            {"uid": user_id, "region": residency_region},
        )
        payload = result.scalar_one()
        if isinstance(payload, str):
            payload = json.loads(payload)
        rows_map = payload.get("rows", {}) if isinstance(payload, dict) else {}
        tables = payload.get("tables_touched", []) if isinstance(payload, dict) else []
        total = sum(int(v) for v in rows_map.values())
        await self._s.commit()
        return total, tuple(tables)

    # --- cookies ----------------------------------------------------

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
    ) -> CookieConsent:
        result = await self._s.execute(
            text(
                f"""
                INSERT INTO cookie_consents
                    (session_cookie_id, categories, region, ip_hash, user_agent,
                     user_id, tenant_id)
                VALUES
                    (:sid, CAST(:cats AS jsonb), :region, :iph, :ua, :uid, :tenant)
                RETURNING {_COOKIE_COLS}
                """  # noqa: S608
            ),
            {
                "sid": session_cookie_id,
                "cats": _json(categories.as_dict()),
                "region": region,
                "iph": ip_hash,
                "ua": user_agent,
                "uid": user_id,
                "tenant": tenant_id,
            },
        )
        row = result.one()
        await self._s.commit()
        return _row_to_cookie(row)

    # --- events -----------------------------------------------------

    async def emit_event(
        self,
        *,
        tenant_id: UUID,
        event_name: str,
        aggregate_type: str,
        aggregate_id: UUID,
        payload: dict[str, object],
    ) -> None:
        await self._s.execute(
            text(
                """
                SELECT app.emit_event(
                    :tenant, :name, :agg_type, :agg_id,
                    CAST(:payload AS jsonb)
                )
                """
            ),
            {
                "tenant": tenant_id,
                "name": event_name,
                "agg_type": aggregate_type,
                "agg_id": aggregate_id,
                "payload": _json(payload),
            },
        )
        await self._s.commit()


__all__ = ["SqlComplianceRepository"]
