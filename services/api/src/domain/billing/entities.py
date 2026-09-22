"""Billing domain entities — pure Python, framework-free.

Mirrors the schema introduced in migrations 0050-0052. The denormalized
fields come from `subscriptions`, `payment_intents`, `invoices`, etc.
Entities are immutable dataclasses; mutations go through the service layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID


class Currency(StrEnum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    RUB = "RUB"
    UZS = "UZS"
    KZT = "KZT"
    CNY = "CNY"
    JPY = "JPY"
    TRY = "TRY"
    INR = "INR"
    AED = "AED"


class SubscriptionStatus(StrEnum):
    TRIAL = "trial"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    EXPIRED = "expired"
    PAUSED = "paused"


class PaymentStatus(StrEnum):
    REQUIRES_PAYMENT = "requires_payment"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    CANCELED = "canceled"
    FAILED = "failed"


class InvoiceStatus(StrEnum):
    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    UNCOLLECTIBLE = "uncollectible"
    VOID = "void"


class FeatureKind(StrEnum):
    BOOLEAN = "boolean"
    QUOTA = "quota"
    THRESHOLD = "threshold"


@dataclass(slots=True, frozen=True)
class PlanFeatures:
    """Plan x feature key entitlement row."""

    feature_key: str
    enabled: bool
    limit_value: int | None = None
    soft_limit: int | None = None


@dataclass(slots=True, frozen=True)
class Plan:
    """A billing plan (monthly / yearly variant of a product)."""

    id: UUID
    tenant_id: UUID
    product_id: UUID
    product_slug: str
    slug: str
    name: dict[str, str]
    billing_period: str
    trial_days: int
    is_default: bool
    is_active: bool
    features: tuple[PlanFeatures, ...] = field(default_factory=tuple)


@dataclass(slots=True, frozen=True)
class Price:
    """Effective price for a plan within a pricing zone + currency."""

    plan_id: UUID
    pricing_zone_id: UUID
    pricing_zone_slug: str
    currency: str
    amount: Decimal
    effective_from: datetime


@dataclass(slots=True, frozen=True)
class PricingZone:
    id: UUID
    slug: str
    name: dict[str, str]
    country_codes: tuple[str, ...]
    default_currency: str
    purchasing_power_index: Decimal


@dataclass(slots=True, frozen=True)
class Subscription:
    id: UUID
    tenant_id: UUID
    user_id: UUID
    residency_region: str
    plan_id: UUID
    plan_slug: str
    status: SubscriptionStatus
    current_period_start: datetime
    current_period_end: datetime
    trial_ends_at: datetime | None = None
    cancel_at_period_end: bool = False
    canceled_at: datetime | None = None
    ended_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(slots=True, frozen=True)
class PaymentIntent:
    id: UUID
    tenant_id: UUID
    user_id: UUID
    residency_region: str
    subscription_id: UUID | None
    idempotency_key: str
    amount: Decimal
    currency: str
    status: PaymentStatus
    failure_reason: str | None = None
    provider_charge_id: str | None = None
    client_secret: str | None = None
    created_at: datetime | None = None


@dataclass(slots=True, frozen=True)
class InvoiceLine:
    line_number: int
    description: str
    quantity: int
    unit_amount: Decimal
    total_amount: Decimal
    tax_amount: Decimal = Decimal(0)


@dataclass(slots=True, frozen=True)
class Invoice:
    id: UUID
    tenant_id: UUID
    user_id: UUID
    residency_region: str
    subscription_id: UUID | None
    number: str
    total: Decimal
    currency: str
    status: InvoiceStatus
    period_start: datetime | None = None
    period_end: datetime | None = None
    issued_at: datetime | None = None
    paid_at: datetime | None = None
    pdf_url: str | None = None
    created_at: datetime | None = None
    lines: tuple[InvoiceLine, ...] = field(default_factory=tuple)


@dataclass(slots=True, frozen=True)
class Entitlement:
    user_id: UUID
    residency_region: str
    feature_key: str
    granted: bool
    limit_value: int | None = None
    source: str = "plan"
    source_id: UUID | None = None
    effective_until: datetime | None = None


@dataclass(slots=True, frozen=True)
class EntitlementDecision:
    """Resolved entitlement for a feature key for a user."""

    feature_key: str
    granted: bool
    limit_value: int | None = None
    source: str = "plan"
    reason: str = "ok"
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class StartSubscriptionResult:
    subscription: Subscription
    payment_intent: PaymentIntent | None
