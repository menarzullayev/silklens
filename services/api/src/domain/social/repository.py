"""Social-domain repository protocols — pure interfaces."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from src.domain.social.entities import (
    ActivityPage,
    ActivityVerb,
    FollowEdgeList,
    FriendInvitation,
    UserRef,
)


class FollowRepository(Protocol):
    async def lookup_user_by_pub_id(self, pub_id: str) -> UserRef | None: ...

    async def follow(
        self,
        *,
        follower_id: UUID,
        follower_residency: str,
        followee_id: UUID,
        followee_residency: str,
        tenant_id: UUID,
    ) -> bool:
        """Insert a follow row.

        Returns ``True`` when newly created, ``False`` if it already existed.
        """

    async def unfollow(
        self,
        *,
        follower_id: UUID,
        followee_id: UUID,
    ) -> bool:
        """Delete the follow edge. Returns ``True`` if a row was removed."""

    async def is_following(self, follower_id: UUID, followee_id: UUID) -> bool: ...

    async def followers(self, user_id: UUID, *, limit: int, offset: int) -> FollowEdgeList: ...

    async def following(self, user_id: UUID, *, limit: int, offset: int) -> FollowEdgeList: ...

    async def is_whale(self, user_id: UUID) -> bool: ...


class FriendshipRepository(Protocol):
    async def create_invitation(
        self,
        *,
        from_user_id: UUID,
        from_residency: str,
        token: str,
        to_user_id: UUID | None,
        to_residency: str | None,
        to_email: str | None,
        message: str | None,
    ) -> FriendInvitation: ...

    async def get_invitation_by_token(self, token: str) -> FriendInvitation | None: ...

    async def accept_invitation(self, token: str, *, accepter_id: UUID) -> FriendInvitation: ...

    async def upsert_block(
        self,
        *,
        blocker_id: UUID,
        blocker_residency: str,
        blocked_id: UUID,
        blocked_residency: str,
        reason: str | None = None,
    ) -> bool: ...

    async def remove_block(self, *, blocker_id: UUID, blocked_id: UUID) -> bool: ...

    async def is_blocked(self, blocker_id: UUID, blocked_id: UUID) -> bool: ...


class ActivityFeedRepository(Protocol):
    async def record_event(
        self,
        *,
        actor_id: UUID,
        actor_residency: str,
        verb: ActivityVerb,
        object_kind: str,
        object_id: UUID,
        target_kind: str | None = None,
        target_id: UUID | None = None,
        visibility: str = "public",
        payload: dict[str, Any] | None = None,
    ) -> UUID: ...

    async def fanout_to_followers(self, *, event_id: UUID) -> int:
        """Push event to every follower of the actor (skipping whales)."""

    async def feed(
        self,
        *,
        user_id: UUID,
        residency: str,
        limit: int,
        before_ts: datetime | None,
    ) -> ActivityPage: ...
