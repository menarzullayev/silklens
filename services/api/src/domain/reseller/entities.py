"""Reseller domain entities — pure Python, framework-free.

Mirrors the schema introduced in migration 0083 (``reseller_application``,
``tenant_revenue_share``). The application_id + tenant_id_assigned forward
references the freshly-minted child tenant on approval; before approval that
field is ``None``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class ApplicationStatus(StrEnum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"

    @property
    def is_terminal(self) -> bool:
        return self in {self.APPROVED, self.REJECTED, self.WITHDRAWN}


class PlanKind(StrEnum):
    TOURISM_AGENCY = "tourism_agency"
    GOVERNMENT = "government"
    ACADEMIC = "academic"
    CORPORATE = "corporate"


@dataclass(slots=True, frozen=True)
class ResellerApplication:
    id: UUID
    applicant_email: str
    applicant_name: str
    company_name: str
    plan_kind: PlanKind
    status: ApplicationStatus
    expected_users: int
    submitted_at: datetime
    created_at: datetime
    updated_at: datetime
    country_code: str | None = None
    tax_id: str | None = None
    message: str | None = None
    notes: str | None = None
    reviewed_at: datetime | None = None
    reviewed_by: UUID | None = None
    tenant_id_assigned: UUID | None = None


@dataclass(slots=True, frozen=True)
class ResellerApplicationDraft:
    """Input bundle for a public application submission."""

    applicant_email: str
    applicant_name: str
    company_name: str
    plan_kind: PlanKind
    expected_users: int = 0
    country_code: str | None = None
    tax_id: str | None = None
    message: str | None = None


@dataclass(slots=True, frozen=True)
class TenantRevenueShare:
    parent_tenant_id: UUID
    child_tenant_id: UUID
    percentage: Decimal
    effective_from: datetime
    effective_until: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True, frozen=True)
class TenantChain:
    """A tenant + its parent chain (root first → caller's tenant last)."""

    tenant_id: UUID
    slug: str
    display_name: dict[str, str]
    plan_tier: str
    status: str
    parent_chain: tuple[UUID, ...]
