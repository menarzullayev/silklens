"""Fundraising domain entities — pure Python, framework-free.

Mirrors the schema introduced in migration 0092 (investor data-room).
All monetary values are Decimal to preserve precision across USD amounts.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class InvestorKind(StrEnum):
    ANGEL = "angel"
    VC = "vc"
    FAMILY_OFFICE = "family_office"
    STRATEGIC = "strategic"
    GOVERNMENT_FUND = "government_fund"
    ACCELERATOR = "accelerator"


class InvestorStatus(StrEnum):
    PROSPECT = "prospect"
    CONTACTED = "contacted"
    NDA_SIGNED = "nda_signed"
    DUE_DILIGENCE = "due_diligence"
    TERM_SHEET = "term_sheet"
    CLOSED = "closed"
    PASSED = "passed"

    @property
    def is_active(self) -> bool:
        """True for statuses that represent an ongoing relationship."""
        return self not in {self.PASSED, self.CLOSED}


class RoundKind(StrEnum):
    SAFE = "safe"
    CONVERTIBLE_NOTE = "convertible_note"
    PRICED = "priced"
    GRANT = "grant"


class RoundStatus(StrEnum):
    PLANNING = "planning"
    OPEN = "open"
    CLOSING = "closing"
    CLOSED = "closed"


class CommitmentStatus(StrEnum):
    VERBAL = "verbal"
    SIGNED = "signed"
    WIRED = "wired"
    RETURNED = "returned"


class DocumentCategory(StrEnum):
    FINANCIALS = "financials"
    LEGAL = "legal"
    PRODUCT = "product"
    TEAM = "team"
    MARKET = "market"
    TECHNICAL = "technical"
    IP = "ip"
    COMPLIANCE = "compliance"


class AccessLevel(StrEnum):
    PUBLIC_TEASER = "public_teaser"
    NDA_REQUIRED = "nda_required"
    DD_ONLY = "dd_only"
    INVESTOR_ONLY = "investor_only"


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class InvestorProfile:
    id: UUID
    tenant_id: UUID
    name: str
    firm_name: str
    kind: InvestorKind
    region: str
    status: InvestorStatus
    created_at: datetime
    updated_at: datetime
    thesis_md: str | None = None
    min_check_size_usd: Decimal | None = None
    max_check_size_usd: Decimal | None = None
    contacted_at: datetime | None = None
    nda_signed_at: datetime | None = None


@dataclass(slots=True, frozen=True)
class FundraisingRound:
    id: UUID
    tenant_id: UUID
    round_name: str
    target_raise_usd: Decimal
    round_kind: RoundKind
    status: RoundStatus
    raised_usd: Decimal
    created_at: datetime
    valuation_cap_usd: Decimal | None = None
    discount_pct: Decimal | None = None
    opened_at: datetime | None = None
    closed_at: datetime | None = None

    @property
    def remaining_usd(self) -> Decimal:
        return self.target_raise_usd - self.raised_usd

    @property
    def fill_pct(self) -> float:
        if self.target_raise_usd == 0:
            return 0.0
        return float(self.raised_usd / self.target_raise_usd * 100)


@dataclass(slots=True, frozen=True)
class Commitment:
    id: UUID
    investor_id: UUID
    round_id: UUID
    committed_usd: Decimal
    status: CommitmentStatus
    created_at: datetime
    actual_usd: Decimal | None = None
    signed_at: datetime | None = None
    wired_at: datetime | None = None


@dataclass(slots=True, frozen=True)
class DataRoomDocument:
    id: UUID
    tenant_id: UUID
    name: str
    category: DocumentCategory
    version: str
    doc_url: str
    access_level: AccessLevel
    is_current: bool
    uploaded_at: datetime
    description_md: str | None = None
    expires_at: datetime | None = None


@dataclass(slots=True, frozen=True)
class DataRoomAccessGrant:
    investor_id: UUID
    document_id: UUID
    granted_by: UUID
    granted_at: datetime
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    accessed_at: datetime | None = None

    @property
    def is_active(self) -> bool:

        if self.revoked_at is not None:
            return False
        if self.expires_at is None:
            return True
        return datetime.now(tz=UTC) < self.expires_at


@dataclass(slots=True, frozen=True)
class KpiSnapshot:
    id: UUID
    tenant_id: UUID
    snapshot_date: date
    mau: int
    dau: int
    paying_users: int
    mrr_usd: Decimal
    arr_usd: Decimal
    heritage_count: int
    countries_count: int
    created_at: datetime
    nps_score: Decimal | None = None
    churn_rate_pct: Decimal | None = None
    ltv_usd: Decimal | None = None
    cac_usd: Decimal | None = None


@dataclass(slots=True, frozen=True)
class InvestorProfileDraft:
    name: str
    firm_name: str
    kind: InvestorKind
    region: str = "global"
    thesis_md: str | None = None
    min_check_size_usd: Decimal | None = None
    max_check_size_usd: Decimal | None = None


@dataclass(slots=True, frozen=True)
class RoundDraft:
    round_name: str
    target_raise_usd: Decimal
    round_kind: RoundKind = RoundKind.SAFE
    valuation_cap_usd: Decimal | None = None
    discount_pct: Decimal | None = None


@dataclass(slots=True, frozen=True)
class KpiSnapshotStats:
    snapshot_date: date
    mau: int
    dau: int
    paying_users: int
    mrr_usd: Decimal
    arr_usd: Decimal
    heritage_count: int
    countries_count: int
    nps_score: Decimal | None = None
    churn_rate_pct: Decimal | None = None
    ltv_usd: Decimal | None = None
    cac_usd: Decimal | None = None
