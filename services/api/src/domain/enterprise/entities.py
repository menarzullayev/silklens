"""Enterprise SLA domain entities — pure Python, framework-free.

Mirrors 0091_enterprise_sla migration tables. All entities are immutable
frozen dataclasses; mutations go through EnterpriseService only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID


class SubscriptionStatus(StrEnum):
    TRIAL = "trial"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    EXPIRED = "expired"


class BillingPeriod(StrEnum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class IncidentSeverity(StrEnum):
    P1 = "p1"
    P2 = "p2"
    P3 = "p3"
    P4 = "p4"


class IncidentStatus(StrEnum):
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    MONITORING = "monitoring"
    RESOLVED = "resolved"


@dataclass(slots=True, frozen=True)
class EnterpriseSLATier:
    """SLA tier catalogue row (e.g. starter / professional / enterprise / strategic)."""

    id: UUID
    slug: str
    name: dict[str, str]
    monthly_price_usd: Decimal | None
    uptime_commitment_pct: Decimal
    support_response_hours: int
    dedicated_csm: bool
    custom_domain: bool
    max_seats: int | None
    api_rate_limit_per_min: int
    analytics_retention_days: int
    includes_white_label: bool
    white_label_subdomains: int
    created_at: datetime


@dataclass(slots=True, frozen=True)
class EnterpriseSubscription:
    """Active SLA contract between an enterprise account and a tier."""

    id: UUID
    enterprise_account_id: UUID
    sla_tier_id: UUID
    status: SubscriptionStatus
    billing_period: BillingPeriod
    started_at: datetime
    current_period_end: datetime
    mrr_usd: Decimal
    trial_ends_at: datetime | None = None
    contracted_annual_usd: Decimal | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    # Denormalised tier info for convenience
    tier_slug: str | None = None
    tier_name: dict[str, str] = field(default_factory=dict)
    uptime_commitment_pct: Decimal | None = None


@dataclass(slots=True, frozen=True)
class SLAIncident:
    """P1-P4 incident record, may be platform-wide (enterprise_account_id=None)."""

    id: UUID
    title: str
    severity: IncidentSeverity
    affected_services: list[str]
    status: IncidentStatus
    started_at: datetime
    public_visible: bool
    created_at: datetime
    updated_at: datetime
    enterprise_account_id: UUID | None = None
    resolved_at: datetime | None = None
    root_cause: str | None = None
    remediation_md: str | None = None
    post_mortem_url: str | None = None


@dataclass(slots=True, frozen=True)
class EnterpriseUsageSnapshot:
    """Daily usage roll-up for a single enterprise account."""

    id: UUID
    enterprise_account_id: UUID
    snapshot_date: Any  # date
    api_calls: int
    successful_calls: int
    error_calls: int
    avg_latency_ms: Decimal
    p95_latency_ms: Decimal
    data_exported_mb: Decimal
    active_seats: int
    created_at: datetime


@dataclass(slots=True, frozen=True)
class EnterpriseSLAStatus:
    """Computed SLA health for an account (or platform-wide)."""

    uptime_pct: Decimal
    """Computed uptime % for current calendar month."""
    committed_pct: Decimal
    """Tier commitment."""
    open_incidents: list[SLAIncident]
    """Currently open/investigating incidents visible to the account."""
    total_api_calls_this_period: int
    active_seats: int
    sla_met: bool
    credit_owed_usd: Decimal = Decimal("0")
