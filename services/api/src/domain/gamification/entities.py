"""Gamification entities — XP / badges / levels / streaks / leaderboards."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class XpSource(StrEnum):
    VISIT = "visit"
    REVIEW = "review"
    PHOTO = "photo"
    BADGE = "badge"
    STREAK = "streak"
    REFERRAL = "referral"
    CORRECTION = "correction"
    ADMIN_GRANT = "admin_grant"
    CLAWBACK = "clawback"
    HELPFUL_RECEIVED = "helpful_received"
    VELOCITY_THROTTLED = "velocity_throttled"


class LeaderboardPeriod(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    ALLTIME = "alltime"


class LeaderboardScope(StrEnum):
    GLOBAL = "global"
    COUNTRY = "country"
    CITY = "city"
    FRIENDS = "friends"
    REGION = "region"


@dataclass(slots=True, frozen=True)
class XpEvent:
    id: UUID
    user_id: UUID
    residency_region: str
    source_kind: XpSource
    delta: int
    idempotency_key: str
    context: dict[str, Any]
    created_at: datetime
    source_id: UUID | None = None


@dataclass(slots=True, frozen=True)
class XpBalance:
    user_id: UUID
    residency_region: str
    current_xp: int
    lifetime_xp: int
    weekly_xp: int
    monthly_xp: int
    yearly_xp: int
    refreshed_at: datetime
    last_event_at: datetime | None = None
    last_event_id: UUID | None = None


@dataclass(slots=True, frozen=True)
class Level:
    number: int
    slug: str
    name: dict[str, str]
    xp_required: int
    perks: dict[str, Any]


@dataclass(slots=True, frozen=True)
class Badge:
    id: UUID
    slug: str
    category: str
    name: dict[str, str]
    description: dict[str, str]
    criterion_kind: str
    criterion_params: dict[str, Any]
    rarity: str
    xp_reward: int


@dataclass(slots=True, frozen=True)
class UserBadge:
    user_id: UUID
    badge: Badge
    awarded_at: datetime
    progress: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class Streak:
    user_id: UUID
    residency_region: str
    current_streak: int
    longest_streak: int
    timezone_anchor: str
    freeze_credits: int
    updated_at: datetime
    last_active_date: date | None = None
    broken_at: datetime | None = None


@dataclass(slots=True, frozen=True)
class Leaderboard:
    id: UUID
    slug: str
    name: dict[str, str]
    scope: LeaderboardScope
    period: LeaderboardPeriod
    metric: str
    scope_ref: str | None = None
    is_active: bool = True


@dataclass(slots=True, frozen=True)
class LeaderboardEntry:
    rank: int
    user_id: UUID
    user_pub_id: str
    metric_value: int
    display_name: str | None = None
