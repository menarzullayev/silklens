"""Compliance domain entities — pure Python, framework-free.

Per ADR-0003 these are immutable dataclasses with no ORM / FastAPI / external
SDK imports. The infrastructure layer maps them to SQL rows in
``src/infrastructure/compliance/repository.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class LegalDocumentKind(StrEnum):
    PRIVACY_POLICY = "privacy_policy"
    TOS = "tos"
    COOKIES = "cookies"
    DPA = "dpa"


class ConsentBasis(StrEnum):
    """GDPR Art. 6 lawful bases."""

    CONSENT = "consent"
    CONTRACT = "contract"
    LEGITIMATE_INTEREST = "legitimate_interest"
    LEGAL_OBLIGATION = "legal_obligation"
    VITAL = "vital"
    PUBLIC_TASK = "public_task"


class GdprRequestKind(StrEnum):
    EXPORT = "export"
    DELETE = "delete"
    ACCESS = "access"
    RECTIFY = "rectify"
    RESTRICT = "restrict"
    OBJECT = "object"
    PORTABILITY = "portability"


class GdprRequestStatus(StrEnum):
    SUBMITTED = "submitted"
    PROCESSING = "processing"
    COMPLETED = "completed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class AnonymizationJobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(slots=True, frozen=True)
class LegalDocument:
    id: UUID
    kind: LegalDocumentKind
    version: str
    language_tag: str
    content_md: str
    sha256: str
    effective_from: datetime
    effective_until: datetime | None = None
    tenant_id: UUID | None = None
    created_by: UUID | None = None
    created_at: datetime | None = None


@dataclass(slots=True, frozen=True)
class ConsentRecord:
    id: UUID
    user_id: UUID
    residency_region: str
    tenant_id: UUID
    legal_document_id: UUID
    basis: ConsentBasis
    granted_at: datetime
    withdrawn_at: datetime | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    source: str = "settings"
    purpose: str | None = None
    created_at: datetime | None = None


@dataclass(slots=True, frozen=True)
class GdprRequest:
    id: UUID
    user_id: UUID
    residency_region: str
    tenant_id: UUID
    request_kind: GdprRequestKind
    status: GdprRequestStatus
    created_at: datetime
    payload_url: str | None = None
    reason: str | None = None
    scheduled_for: datetime | None = None
    completed_at: datetime | None = None
    requested_by_user_id: UUID | None = None
    decided_by_admin_user_id: UUID | None = None
    decision_note: str | None = None


@dataclass(slots=True, frozen=True)
class AnonymizationJob:
    id: UUID
    user_id: UUID
    residency_region: str
    tenant_id: UUID
    status: AnonymizationJobStatus
    scheduled_for: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    rows_anonymized: int = 0
    tables_touched: tuple[str, ...] = field(default_factory=tuple)
    gdpr_request_id: UUID | None = None
    error_message: str | None = None
    created_at: datetime | None = None


@dataclass(slots=True, frozen=True)
class CookieCategories:
    strictly_necessary: bool = True
    analytics: bool = False
    marketing: bool = False
    ad_targeting: bool = False

    def as_dict(self) -> dict[str, bool]:
        return {
            "strictly_necessary": self.strictly_necessary,
            "analytics": self.analytics,
            "marketing": self.marketing,
            "ad_targeting": self.ad_targeting,
        }


@dataclass(slots=True, frozen=True)
class CookieConsent:
    id: UUID
    session_cookie_id: str
    categories: CookieCategories
    given_at: datetime
    region: str | None = None
    ip_hash: str | None = None
    user_agent: str | None = None
    user_id: UUID | None = None
    tenant_id: UUID | None = None
