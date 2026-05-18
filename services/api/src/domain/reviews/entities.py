"""Reviews / reactions / comments / UGC entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID


class ReviewSort(StrEnum):
    HELPFUL = "helpful"
    RECENT = "recent"
    RATING = "rating"


class CommentParentKind(StrEnum):
    HERITAGE = "heritage"
    REVIEW = "review"
    PHOTO = "photo"
    COMMENT = "comment"
    TRIP = "trip"
    JOURNAL = "journal"
    JOURNAL_ENTRY = "journal_entry"


class ReactionTargetKind(StrEnum):
    REVIEW = "review"
    COMMENT = "comment"
    PHOTO = "photo"
    JOURNAL = "journal"
    JOURNAL_ENTRY = "journal_entry"
    HERITAGE = "heritage"


class ReportTargetKind(StrEnum):
    REVIEW = "review"
    COMMENT = "comment"
    PHOTO = "photo"
    VIDEO = "video"
    JOURNAL = "journal"
    JOURNAL_ENTRY = "journal_entry"
    USER = "user"
    HERITAGE = "heritage"
    HERITAGE_FACT = "heritage_fact"
    TRIP = "trip"
    TRIP_CHAT = "trip_chat"


class ReportReason(StrEnum):
    SPAM = "spam"
    NSFW = "nsfw"
    HATE = "hate"
    COPYRIGHT = "copyright"
    MISINFORMATION = "misinformation"
    CULTURAL_INSENSITIVE = "cultural_insensitive"
    IMPERSONATION = "impersonation"
    HARASSMENT = "harassment"
    WRONG_GEOTAG = "wrong_geotag"
    OTHER = "other"


class UgcStatus(StrEnum):
    PENDING = "pending"
    AUTO_APPROVED = "auto_approved"
    AWAITING_HUMAN = "awaiting_human"
    APPROVED = "approved"
    REJECTED = "rejected"
    QUARANTINED = "quarantined"
    SHADOW_BANNED = "shadow_banned"


@dataclass(slots=True, frozen=True)
class ReviewDimension:
    slug: str
    name: dict[str, str]
    weight: Decimal


@dataclass(slots=True, frozen=True)
class ReviewRating:
    dimension_slug: str
    value: int


@dataclass(slots=True, frozen=True)
class Review:
    id: UUID
    tenant_id: UUID
    heritage_id: UUID
    user_id: UUID
    residency_region: str
    language_tag: str
    body_md: str
    is_published: bool
    helpful_count: int
    unhelpful_count: int
    report_count: int
    edited_count: int
    created_at: datetime
    updated_at: datetime
    title: str | None = None
    average_rating: Decimal | None = None
    visited_at: date | None = None
    quality_score: Decimal | None = None
    machine_translated_from: str | None = None
    ratings: tuple[ReviewRating, ...] = field(default_factory=tuple)


@dataclass(slots=True, frozen=True)
class ReviewDraft:
    tenant_id: UUID
    heritage_id: UUID
    user_id: UUID
    residency_region: str
    language_tag: str
    body_md: str
    ratings: tuple[ReviewRating, ...] = field(default_factory=tuple)
    title: str | None = None
    visited_at: date | None = None


@dataclass(slots=True, frozen=True)
class ReviewPage:
    items: tuple[Review, ...]
    total: int
    limit: int
    offset: int


@dataclass(slots=True, frozen=True)
class Reaction:
    id: UUID
    reactor_user_id: UUID
    target_kind: ReactionTargetKind
    target_id: UUID
    reaction_type_slug: str
    created_at: datetime


@dataclass(slots=True, frozen=True)
class Comment:
    id: UUID
    tenant_id: UUID
    parent_kind: CommentParentKind
    parent_id: UUID
    author_user_id: UUID
    author_residency: str
    body_md: str
    language_tag: str
    depth: int
    path: str
    status: str
    reply_count: int
    reaction_count: int
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True, frozen=True)
class UgcSubmission:
    id: UUID
    tenant_id: UUID
    kind: str
    target_id: UUID
    author_user_id: UUID
    author_residency: str
    status: UgcStatus
    payload: dict[str, Any]
    submitted_at: datetime
    user_trust_tier_snapshot: str | None = None
    auto_moderation_score: Decimal | None = None
    ai_decision: str | None = None
