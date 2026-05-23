"""Compliance API surface.

Public:
- GET  /v1/legal/{kind}                   — latest policy in caller's locale
- POST /v1/public/cookie-consent          — anonymous cookie banner choice

Authenticated (self-service):
- GET    /v1/me/consents                  — list consents
- POST   /v1/me/consents                  — record consent for current policy
- DELETE /v1/me/consents/{doc_id}         — withdraw a consent
- POST   /v1/me/data-export               — schedule export
- GET    /v1/me/data-export/{request_id}  — export status / download URL
- POST   /v1/me/account/delete            — schedule deletion at +30d
- POST   /v1/me/account/delete/cancel     — cancel pending deletion (in grace)

Admin (`tenant:manage` / `gdpr:approve`):
- GET  /v1/legal/{kind}/history
- POST /v1/legal/{kind}
- POST /v1/admin/gdpr-requests/{id}/process
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.domain.compliance.entities import (
    ConsentBasis,
    CookieCategories,
    GdprRequestKind,
    GdprRequestStatus,
    LegalDocumentKind,
)
from src.domain.compliance.errors import ComplianceError
from src.domain.compliance.service import ComplianceService
from src.infrastructure.compliance.repository import SqlComplianceRepository
from src.infrastructure.compliance.tasks import InMemoryTaskQueue
from src.middleware.auth import AuthContext, CurrentUserDep, require_permission, require_recent_mfa

router = APIRouter(tags=["compliance"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

# Module-level task queue stub so tests can introspect it. Production wiring
# will swap this for a Celery-backed queue inside ``create_app``.
_TASK_QUEUE = InMemoryTaskQueue()


def get_task_queue() -> InMemoryTaskQueue:
    return _TASK_QUEUE


TaskQueueDep = Annotated[InMemoryTaskQueue, Depends(get_task_queue)]


def _service(db: AsyncSession, tasks: InMemoryTaskQueue) -> ComplianceService:
    return ComplianceService(repository=SqlComplianceRepository(db), tasks=tasks)


def _raise(exc: ComplianceError) -> None:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": str(exc)},
    ) from exc


def _parse_locale(accept_language: str | None) -> str:
    if not accept_language:
        return "en"
    # very lenient: first token, strip quality
    primary = accept_language.split(",")[0].split(";")[0].strip().lower()
    return primary[:2] if primary else "en"


def _parse_kind(kind: str) -> LegalDocumentKind:
    try:
        return LegalDocumentKind(kind)
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "compliance.unknown_kind", "message": f"unknown kind '{kind}'"},
        ) from exc


# --- Schemas -------------------------------------------------------------


class LegalDocumentOut(BaseModel):
    id: UUID
    kind: LegalDocumentKind
    version: str
    language_tag: str
    sha256: str
    effective_from: datetime
    content_md: str


class LegalDocumentSummary(BaseModel):
    id: UUID
    kind: LegalDocumentKind
    version: str
    language_tag: str
    sha256: str
    effective_from: datetime
    effective_until: datetime | None


class PublishPolicyIn(BaseModel):
    version: str = Field(min_length=1, max_length=64)
    language_tag: str = Field(min_length=2, max_length=12, pattern=r"^[a-z]{2}(-[A-Za-z0-9]+)*$")
    content_md: str = Field(min_length=8, max_length=2_000_000)


class ConsentIn(BaseModel):
    legal_document_id: UUID
    basis: ConsentBasis = ConsentBasis.CONSENT
    purpose: str | None = Field(default=None, max_length=128)


class ConsentOut(BaseModel):
    id: UUID
    legal_document_id: UUID
    basis: ConsentBasis
    granted_at: datetime
    withdrawn_at: datetime | None
    source: str


class GdprRequestOut(BaseModel):
    id: UUID
    request_kind: GdprRequestKind
    status: GdprRequestStatus
    scheduled_for: datetime | None
    completed_at: datetime | None
    payload_url: str | None
    created_at: datetime


class DeletionRequestIn(BaseModel):
    reason: str | None = Field(default=None, max_length=2048)


class CancelDeletionIn(BaseModel):
    request_id: UUID


class CookieConsentIn(BaseModel):
    session_cookie_id: str = Field(min_length=4, max_length=128)
    strictly_necessary: bool = True
    analytics: bool = False
    marketing: bool = False
    ad_targeting: bool = False
    region: str | None = Field(default=None, max_length=8)


class CookieConsentOut(BaseModel):
    id: UUID
    session_cookie_id: str
    categories: dict[str, bool]
    region: str | None
    given_at: datetime


class AdminProcessIn(BaseModel):
    payload_url: str | None = Field(default=None, max_length=1024)
    decision_note: str | None = Field(default=None, max_length=2048)

    @field_validator("payload_url")
    @classmethod
    def _require_https(cls, v: str | None) -> str | None:
        """SEC-W56-006: only https:// URLs stored — prevents file:// / javascript: XSS."""
        if v is not None and not v.startswith("https://"):
            raise ValueError("payload_url must use the https:// scheme")
        return v


# --- Routes: public legal ---------------------------------------------


@router.get("/v1/legal/{kind}", response_model=LegalDocumentOut)
async def get_current_policy(
    kind: str,
    db: SessionDep,
    accept_language: Annotated[str | None, Header(alias="Accept-Language")] = None,
) -> LegalDocumentOut:
    parsed = _parse_kind(kind)
    lang = _parse_locale(accept_language)
    tasks = get_task_queue()
    try:
        doc = await _service(db, tasks).current_policy(kind=parsed, language_tag=lang)
    except ComplianceError as exc:
        _raise(exc)
        raise
    return LegalDocumentOut(
        id=doc.id,
        kind=doc.kind,
        version=doc.version,
        language_tag=doc.language_tag,
        sha256=doc.sha256,
        effective_from=doc.effective_from,
        content_md=doc.content_md,
    )


@router.get(
    "/v1/legal/{kind}/history",
    response_model=list[LegalDocumentSummary],
)
async def list_policy_history(
    kind: str,
    db: SessionDep,
    _ctx: Annotated[object, Depends(require_permission("tenant:manage"))],
) -> list[LegalDocumentSummary]:
    parsed = _parse_kind(kind)
    tasks = get_task_queue()
    docs = await _service(db, tasks).list_policy_history(kind=parsed)
    return [
        LegalDocumentSummary(
            id=d.id,
            kind=d.kind,
            version=d.version,
            language_tag=d.language_tag,
            sha256=d.sha256,
            effective_from=d.effective_from,
            effective_until=d.effective_until,
        )
        for d in docs
    ]


@router.post(
    "/v1/legal/{kind}",
    response_model=LegalDocumentOut,
    status_code=status.HTTP_201_CREATED,
)
async def publish_policy(
    kind: str,
    payload: PublishPolicyIn,
    db: SessionDep,
    ctx: Annotated[AuthContext, Depends(require_permission("tenant:manage"))],
) -> LegalDocumentOut:
    parsed = _parse_kind(kind)
    tasks = get_task_queue()
    try:
        doc = await _service(db, tasks).publish_policy(
            kind=parsed,
            version=payload.version,
            language_tag=payload.language_tag,
            content_md=payload.content_md,
            tenant_id=None,
            actor=ctx.user_id,
        )
    except ComplianceError as exc:
        _raise(exc)
        raise
    return LegalDocumentOut(
        id=doc.id,
        kind=doc.kind,
        version=doc.version,
        language_tag=doc.language_tag,
        sha256=doc.sha256,
        effective_from=doc.effective_from,
        content_md=doc.content_md,
    )


# --- Routes: self-service consents -----------------------------------


@router.get("/v1/me/consents", response_model=list[ConsentOut])
async def list_my_consents(ctx: CurrentUserDep, db: SessionDep) -> list[ConsentOut]:
    tasks = get_task_queue()
    consents = await _service(db, tasks).list_consents(
        user_id=ctx.user_id, residency_region=ctx.residency_region.value
    )
    return [
        ConsentOut(
            id=c.id,
            legal_document_id=c.legal_document_id,
            basis=c.basis,
            granted_at=c.granted_at,
            withdrawn_at=c.withdrawn_at,
            source=c.source,
        )
        for c in consents
    ]


@router.post("/v1/me/consents", response_model=ConsentOut, status_code=status.HTTP_201_CREATED)
async def record_my_consent(
    payload: ConsentIn,
    request: Request,
    ctx: CurrentUserDep,
    db: SessionDep,
) -> ConsentOut:
    tasks = get_task_queue()
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    try:
        consent = await _service(db, tasks).record_consent(
            user_id=ctx.user_id,
            residency_region=ctx.residency_region.value,
            tenant_id=ctx.tenant_id,
            legal_document_id=payload.legal_document_id,
            basis=payload.basis,
            ip_address=ip,
            user_agent=ua,
            source="settings",
        )
    except ComplianceError as exc:
        _raise(exc)
        raise
    return ConsentOut(
        id=consent.id,
        legal_document_id=consent.legal_document_id,
        basis=consent.basis,
        granted_at=consent.granted_at,
        withdrawn_at=consent.withdrawn_at,
        source=consent.source,
    )


@router.delete("/v1/me/consents/{doc_id}", response_model=ConsentOut)
async def withdraw_my_consent(doc_id: UUID, ctx: CurrentUserDep, db: SessionDep) -> ConsentOut:
    tasks = get_task_queue()
    try:
        consent = await _service(db, tasks).withdraw_consent(
            user_id=ctx.user_id,
            residency_region=ctx.residency_region.value,
            tenant_id=ctx.tenant_id,
            legal_document_id=doc_id,
        )
    except ComplianceError as exc:
        _raise(exc)
        raise
    return ConsentOut(
        id=consent.id,
        legal_document_id=consent.legal_document_id,
        basis=consent.basis,
        granted_at=consent.granted_at,
        withdrawn_at=consent.withdrawn_at,
        source=consent.source,
    )


# --- Routes: data export -------------------------------------------


@router.post(
    "/v1/me/data-export",
    response_model=GdprRequestOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_data_export(ctx: CurrentUserDep, db: SessionDep) -> GdprRequestOut:
    tasks = get_task_queue()
    req = await _service(db, tasks).request_export(
        user_id=ctx.user_id,
        residency_region=ctx.residency_region.value,
        tenant_id=ctx.tenant_id,
    )
    return _request_to_out(req)


@router.get("/v1/me/data-export/{request_id}", response_model=GdprRequestOut)
async def get_data_export(request_id: UUID, ctx: CurrentUserDep, db: SessionDep) -> GdprRequestOut:
    tasks = get_task_queue()
    try:
        req = await _service(db, tasks).get_request(
            request_id=request_id,
            residency_region=ctx.residency_region.value,
            user_id=ctx.user_id,
        )
    except ComplianceError as exc:
        _raise(exc)
        raise
    return _request_to_out(req)


# --- Routes: account deletion --------------------------------------


@router.post(
    "/v1/me/account/delete",
    response_model=GdprRequestOut,
    status_code=status.HTTP_202_ACCEPTED,
    # Self-service account deletion: when the user has an active MFA factor we
    # require a fresh step-up. Users who never enrolled MFA are accepted but
    # rely on the 30-day grace window + cancel endpoint + the
    # ``account_deletion_scheduled`` notification as the real safety net.
    # Admin-driven GDPR processing (below) keeps the stricter gate.
    dependencies=[Depends(require_recent_mfa(seconds=300, allow_first_setup=True))],
)
async def schedule_account_deletion(
    payload: DeletionRequestIn,
    ctx: CurrentUserDep,
    db: SessionDep,
) -> GdprRequestOut:
    tasks = get_task_queue()
    try:
        req = await _service(db, tasks).request_deletion(
            user_id=ctx.user_id,
            residency_region=ctx.residency_region.value,
            tenant_id=ctx.tenant_id,
            reason=payload.reason,
        )
    except ComplianceError as exc:
        _raise(exc)
        raise
    return _request_to_out(req)


@router.post("/v1/me/account/delete/cancel", response_model=GdprRequestOut)
async def cancel_account_deletion(
    payload: CancelDeletionIn,
    ctx: CurrentUserDep,
    db: SessionDep,
) -> GdprRequestOut:
    tasks = get_task_queue()
    try:
        req = await _service(db, tasks).cancel_deletion(
            user_id=ctx.user_id,
            residency_region=ctx.residency_region.value,
            tenant_id=ctx.tenant_id,
            request_id=payload.request_id,
        )
    except ComplianceError as exc:
        _raise(exc)
        raise
    return _request_to_out(req)


# --- Routes: cookie consent ----------------------------------------


@router.post(
    "/v1/public/cookie-consent",
    response_model=CookieConsentOut,
    status_code=status.HTTP_201_CREATED,
)
async def record_cookie_consent(
    payload: CookieConsentIn, request: Request, db: SessionDep
) -> CookieConsentOut:
    tasks = get_task_queue()
    ip = request.client.host if request.client else ""
    ip_hash = hashlib.sha256(ip.encode("utf-8")).hexdigest() if ip else None
    ua = request.headers.get("user-agent")
    cats = CookieCategories(
        strictly_necessary=True,  # always on per ePrivacy
        analytics=payload.analytics,
        marketing=payload.marketing,
        ad_targeting=payload.ad_targeting,
    )
    consent = await _service(db, tasks).record_cookie_consent(
        session_cookie_id=payload.session_cookie_id,
        categories=cats,
        region=payload.region,
        ip_hash=ip_hash,
        user_agent=ua,
        user_id=None,
        tenant_id=None,
    )
    return CookieConsentOut(
        id=consent.id,
        session_cookie_id=consent.session_cookie_id,
        categories=consent.categories.as_dict(),
        region=consent.region,
        given_at=consent.given_at,
    )


# --- Routes: admin -------------------------------------------------


@router.post(
    "/v1/admin/gdpr-requests/{request_id}/process",
    response_model=GdprRequestOut,
    # SEC-W5-007 / C-2 fix: destructive routes refuse to pass through users
    # without a recent MFA proof. Users who never enrolled MFA must enroll
    # first (router returns 403 identity.mfa_step_up_required).
    dependencies=[Depends(require_recent_mfa(seconds=300, allow_first_setup=False))],
)
async def admin_process_request(
    request_id: UUID,
    payload: AdminProcessIn,
    db: SessionDep,
    ctx: Annotated[AuthContext, Depends(require_permission("gdpr:approve"))],
) -> GdprRequestOut:
    tasks = get_task_queue()
    try:
        req = await _service(db, tasks).admin_process_request(
            request_id=request_id,
            residency_region=ctx.residency_region.value,
            admin_user_id=ctx.user_id,
            decision_note=payload.decision_note,
            payload_url=payload.payload_url,
        )
    except ComplianceError as exc:
        _raise(exc)
        raise
    return _request_to_out(req)


# --- helpers --------------------------------------------------------


def _request_to_out(req) -> GdprRequestOut:
    return GdprRequestOut(
        id=req.id,
        request_kind=req.request_kind,
        status=req.status,
        scheduled_for=req.scheduled_for,
        completed_at=req.completed_at,
        payload_url=req.payload_url,
        created_at=req.created_at,
    )
