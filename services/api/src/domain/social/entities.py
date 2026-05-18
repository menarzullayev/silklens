"""Social-graph domain entities — pure Python.

Mirrors migrations 0040 (follows, friendships, friend_invitations, block_list,
mutes, close_friends, whale_users, activity_events, activity_fanout).

All user FKs are composite ``(id, residency_region)`` per the users
residency-partition contract from migration 0004/0009. Entities therefore
carry residency alongside the user id.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class ActivityVerb(StrEnum):
    CREATED = "created"
    REVIEWED = "reviewed"
    VISITED = "visited"
    LIKED = "liked"
    FOLLOWED = "followed"
    EARNED_BADGE = "earned_badge"
    JOINED_TRIP = "joined_trip"
    COMMENTED = "commented"
    REACTED = "reacted"
    PHOTOGRAPHED = "photographed"
    JOURNAL_PUBLISHED = "journal_published"


class FriendshipStatus(StrEnum):
    INVITED = "invited"
    ACCEPTED = "accepted"
    BLOCKED = "blocked"


class InvitationStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"
    REVOKED = "revoked"


class FanoutMode(StrEnum):
    PULL = "pull"
    PUSH = "push"
    HYBRID = "hybrid"


@dataclass(slots=True, frozen=True)
class Follow:
    follower_user_id: UUID
    follower_residency: str
    followee_user_id: UUID
    followee_residency: str
    created_at: datetime


@dataclass(slots=True, frozen=True)
class Friendship:
    user_a_id: UUID
    user_a_residency: str
    user_b_id: UUID
    user_b_residency: str
    status: FriendshipStatus
    invited_at: datetime
    accepted_at: datetime | None = None


@dataclass(slots=True, frozen=True)
class FriendInvitation:
    id: UUID
    from_user_id: UUID
    from_residency: str
    token: str
    status: InvitationStatus
    created_at: datetime
    expires_at: datetime
    to_user_id: UUID | None = None
    to_residency: str | None = None
    to_email: str | None = None
    message: str | None = None
    responded_at: datetime | None = None


@dataclass(slots=True, frozen=True)
class Block:
    blocker_user_id: UUID
    blocker_residency: str
    blocked_user_id: UUID
    blocked_residency: str
    created_at: datetime
    reason: str | None = None


@dataclass(slots=True, frozen=True)
class Mute:
    muter_user_id: UUID
    muter_residency: str
    muted_user_id: UUID
    muted_residency: str
    created_at: datetime
    reason: str | None = None
    expires_at: datetime | None = None


@dataclass(slots=True, frozen=True)
class ActivityEvent:
    """Append-only verb log row (actor verb object [target])."""

    id: UUID
    actor_user_id: UUID
    actor_residency: str
    verb: ActivityVerb
    object_kind: str
    object_id: UUID
    visibility: str
    payload: dict[str, Any]
    created_at: datetime
    target_kind: str | None = None
    target_id: UUID | None = None


@dataclass(slots=True, frozen=True)
class ActivityFeedItem:
    """A delivered feed row (pre-fanned-out or pulled live)."""

    event_id: UUID
    actor_user_id: UUID
    verb: ActivityVerb
    object_kind: str
    object_id: UUID
    payload: dict[str, Any]
    created_at: datetime
    delivered_at: datetime | None = None
    target_kind: str | None = None
    target_id: UUID | None = None


@dataclass(slots=True, frozen=True)
class ActivityPage:
    items: tuple[ActivityFeedItem, ...]
    next_cursor: datetime | None = None


@dataclass(slots=True, frozen=True)
class UserRef:
    """Lightweight (id, residency, pub_id) tuple used by the API layer."""

    id: UUID
    residency_region: str
    pub_id: str


@dataclass(slots=True, frozen=True)
class FollowEdgeList:
    items: tuple[UserRef, ...] = field(default_factory=tuple)
    total: int = 0
