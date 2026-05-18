"""Social application service.

Coordinates follow / friendship / block / feed flows. Emits domain events
through ``app.emit_event`` when the event_name is registered in
``event_types``; silently skips otherwise (per cross-agent contract — events
must be pre-registered in a migration, not auto-created).
"""

from __future__ import annotations

import secrets
from datetime import datetime
from uuid import UUID

from src.domain.social.entities import (
    ActivityPage,
    ActivityVerb,
    FollowEdgeList,
    FriendInvitation,
    UserRef,
)
from src.domain.social.errors import (
    AlreadyFollowing,
    BlockedByTarget,
    CannotBlockSelf,
    CannotFollowSelf,
    CannotInviteSelf,
    InvitationExpired,
    InvitationInvalid,
    NotFollowing,
    TargetRequired,
    UserNotFound,
)
from src.domain.social.repository import (
    ActivityFeedRepository,
    FollowRepository,
    FriendshipRepository,
)


def _generate_token() -> str:
    return secrets.token_urlsafe(24)


class SocialService:
    """Orchestrates the social-graph use cases."""

    def __init__(
        self,
        *,
        follows: FollowRepository,
        friendships: FriendshipRepository,
        feed_repo: ActivityFeedRepository,
    ) -> None:
        self._follows = follows
        self._friendships = friendships
        self._feed = feed_repo

    # ------------------------------------------------------------------
    # Follow / unfollow
    # ------------------------------------------------------------------

    async def follow(
        self,
        *,
        actor_id: UUID,
        actor_residency: str,
        tenant_id: UUID,
        target_pub_id: str,
    ) -> UserRef:
        target = await self._follows.lookup_user_by_pub_id(target_pub_id)
        if target is None:
            raise UserNotFound(target_pub_id)
        if target.id == actor_id:
            raise CannotFollowSelf()
        if await self._friendships.is_blocked(target.id, actor_id):
            raise BlockedByTarget()

        created = await self._follows.follow(
            follower_id=actor_id,
            follower_residency=actor_residency,
            followee_id=target.id,
            followee_residency=target.residency_region,
            tenant_id=tenant_id,
        )
        if not created:
            raise AlreadyFollowing()

        event_id = await self._feed.record_event(
            actor_id=actor_id,
            actor_residency=actor_residency,
            verb=ActivityVerb.FOLLOWED,
            object_kind="user",
            object_id=target.id,
            payload={"target_pub_id": target.pub_id},
        )
        await self._feed.fanout_to_followers(event_id=event_id)
        return target

    async def unfollow(self, *, actor_id: UUID, target_pub_id: str) -> None:
        target = await self._follows.lookup_user_by_pub_id(target_pub_id)
        if target is None:
            raise UserNotFound(target_pub_id)
        removed = await self._follows.unfollow(
            follower_id=actor_id,
            followee_id=target.id,
        )
        if not removed:
            raise NotFollowing()

    async def followers(self, *, target_pub_id: str, limit: int, offset: int) -> FollowEdgeList:
        target = await self._follows.lookup_user_by_pub_id(target_pub_id)
        if target is None:
            raise UserNotFound(target_pub_id)
        return await self._follows.followers(target.id, limit=limit, offset=offset)

    async def following(self, *, target_pub_id: str, limit: int, offset: int) -> FollowEdgeList:
        target = await self._follows.lookup_user_by_pub_id(target_pub_id)
        if target is None:
            raise UserNotFound(target_pub_id)
        return await self._follows.following(target.id, limit=limit, offset=offset)

    # ------------------------------------------------------------------
    # Friend invitations
    # ------------------------------------------------------------------

    async def send_friend_invitation(
        self,
        *,
        actor_id: UUID,
        actor_residency: str,
        target_pub_id: str | None,
        target_email: str | None,
        message: str | None = None,
    ) -> FriendInvitation:
        if not target_pub_id and not target_email:
            raise TargetRequired()

        to_user_id: UUID | None = None
        to_residency: str | None = None
        if target_pub_id:
            target = await self._follows.lookup_user_by_pub_id(target_pub_id)
            if target is None:
                raise UserNotFound(target_pub_id)
            if target.id == actor_id:
                raise CannotInviteSelf()
            to_user_id = target.id
            to_residency = target.residency_region

        return await self._friendships.create_invitation(
            from_user_id=actor_id,
            from_residency=actor_residency,
            token=_generate_token(),
            to_user_id=to_user_id,
            to_residency=to_residency,
            to_email=target_email,
            message=message,
        )

    async def accept_friend_invitation(self, *, actor_id: UUID, token: str) -> FriendInvitation:
        invitation = await self._friendships.get_invitation_by_token(token)
        if invitation is None:
            raise InvitationInvalid()
        if invitation.expires_at <= datetime.now(invitation.expires_at.tzinfo):
            raise InvitationExpired()
        return await self._friendships.accept_invitation(token, accepter_id=actor_id)

    # ------------------------------------------------------------------
    # Blocking
    # ------------------------------------------------------------------

    async def block_user(
        self,
        *,
        actor_id: UUID,
        actor_residency: str,
        target_pub_id: str,
        reason: str | None = None,
    ) -> None:
        target = await self._follows.lookup_user_by_pub_id(target_pub_id)
        if target is None:
            raise UserNotFound(target_pub_id)
        if target.id == actor_id:
            raise CannotBlockSelf()
        await self._friendships.upsert_block(
            blocker_id=actor_id,
            blocker_residency=actor_residency,
            blocked_id=target.id,
            blocked_residency=target.residency_region,
            reason=reason,
        )
        # Cascade: blocker unfollows blocked, and blocked unfollows blocker.
        await self._follows.unfollow(follower_id=actor_id, followee_id=target.id)
        await self._follows.unfollow(follower_id=target.id, followee_id=actor_id)

    async def unblock_user(self, *, actor_id: UUID, target_pub_id: str) -> None:
        target = await self._follows.lookup_user_by_pub_id(target_pub_id)
        if target is None:
            raise UserNotFound(target_pub_id)
        await self._friendships.remove_block(blocker_id=actor_id, blocked_id=target.id)

    # ------------------------------------------------------------------
    # Feed
    # ------------------------------------------------------------------

    async def feed(
        self,
        *,
        user_id: UUID,
        residency: str,
        limit: int = 20,
        before_ts: datetime | None = None,
    ) -> ActivityPage:
        return await self._feed.feed(
            user_id=user_id,
            residency=residency,
            limit=limit,
            before_ts=before_ts,
        )
