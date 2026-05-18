"""Partnership domain entities — pure Python, framework-free.

Mirrors the schema from migration 0089_partnership_sla.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID


class PartnerKind(StrEnum):
    ACADEMIC = "academic"
    GOVERNMENT = "government"
    NGO = "ngo"
    UNESCO = "unesco"
    ICOMOS = "icomos"
    NATIONAL_PARK = "national_park"
    MUSEUM_NETWORK = "museum_network"


class AgreementStatus(StrEnum):
    DRAFT = "draft"
    NEGOTIATING = "negotiating"
    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"
    PAUSED = "paused"

    @property
    def is_terminal(self) -> bool:
        return self in {self.EXPIRED, self.TERMINATED}


class BadgeKind(StrEnum):
    UNESCO_PARTNER = "unesco_partner"
    OFFICIAL_GOV = "official_gov"
    ACADEMIC = "academic"
    VERIFIED_MUSEUM = "verified_museum"
    HERITAGE_CHAMPION = "heritage_champion"
    DATA_PROVIDER = "data_provider"


@dataclass(slots=True, frozen=True)
class PartnershipTier:
    id: UUID
    slug: str
    name: dict[str, str]
    kind: PartnerKind
    benefits: list[str]
    sla_uptime_pct: Decimal
    max_api_calls_per_day: int
    includes_white_label: bool
    revenue_share_pct: Decimal
    created_at: datetime


@dataclass(slots=True, frozen=True)
class PartnershipAgreement:
    id: UUID
    tenant_id: UUID
    partner_name: str
    partner_kind: PartnerKind
    tier_id: UUID
    status: AgreementStatus
    created_at: datetime
    updated_at: datetime
    signed_at: datetime | None = None
    expires_at: datetime | None = None
    auto_renew: bool = False
    annual_value_usd: Decimal | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    notes_md: str | None = None
    mou_url: str | None = None
    # joined from tier (optional, populated by queries that JOIN)
    tier_slug: str | None = None
    tier_name: dict[str, str] | None = None
    tier_sla_uptime_pct: Decimal | None = None


@dataclass(slots=True, frozen=True)
class SlaReport:
    id: UUID
    agreement_id: UUID
    period_start: date
    period_end: date
    measured_uptime_pct: Decimal
    incidents_count: int
    incidents_resolved_in_sla: int
    api_calls_total: int
    data_exports_count: int
    generated_at: datetime
    created_at: datetime
    report_url: str | None = None


@dataclass(slots=True, frozen=True)
class UptimeWindow:
    id: UUID
    started_at: datetime
    kind: str
    severity: str
    is_resolved: bool
    created_at: datetime
    affected_services: list[str] = field(default_factory=lambda: ["api"])
    ended_at: datetime | None = None
    description_md: str | None = None
    resolution_notes: str | None = None


@dataclass(slots=True, frozen=True)
class PartnerBadge:
    id: UUID
    agreement_id: UUID
    badge_kind: BadgeKind
    issued_at: datetime
    is_active: bool
    display_on_heritage: list[str]
    expires_at: datetime | None = None


@dataclass(slots=True, frozen=True)
class UptimeStatus:
    """Aggregated uptime summary for the last 30 days."""

    uptime_pct: Decimal
    total_windows: int
    open_incidents: int
    last_incident_at: datetime | None
    service_status: str  # "operational" | "degraded" | "outage"
    computed_at: datetime
    recent_windows: list[dict[str, Any]]
