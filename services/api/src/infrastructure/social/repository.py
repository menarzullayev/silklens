"""SQL implementations of the social-domain repositories.

Three repositories share one ``AsyncSession`` so they can write inside a single
transaction (e.g. ``follow()`` + ``record_event()`` + ``fanout_to_followers``).
The router commits at the end of the request.

All FKs to ``users`` are composite ``(id, residency_region)``; activity
partition writes use ``created_at = now()`` so the row routes into the current
month's partition.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.social.entities import (
    ActivityFeedItem,
    ActivityPage,
    ActivityVerb,
    FollowEdgeList,
    FriendInvitation,
    InvitationStatus,
    UserRef,
)
from src.domain.social.errors import InvitationInvalid
from src.infrastructure._events import emit_event_if_registered, jdump


def _to_user_ref(row: Any) -> UserRef:
    m = row._mapping
    return UserRef(
        id=m["id"],
        residency_region=m["residency_region"],
        pub_id=m["pub_id"],
    )


def _to_invitation(row: Any) -> FriendInvitation:
    m = row._mapping
    return FriendInvitation(
        id=m["id"],
        from_user_id=m["from_user_id"],
        from_residency=m["from_residency"],
        token=m["token"],
        status=InvitationStatus(m["status"]),
        created_at=m["created_at"],
        expires_at=m["expires_at"],
        to_user_id=m["to_user_id"],
        to_residency=m["to_residency"],
        to_email=m["to_email"],
        message=m["message"],
        responded_at=m["responded_at"],
    )


# =====================================================================
# FollowRepository
# =====================================================================


class SqlFollowRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lookup_user_by_pub_id(self, pub_id: str) -> UserRef | None:
        row = await self._session.execute(
            text(
                """
                SELECT id, residency_region, pub_id
                FROM users
                WHERE pub_id = :pub_id
                  AND deleted_at IS NULL
                LIMIT 1
                """
            ),
            {"pub_id": pub_id},
        )
        r = row.one_or_none()
        return _to_user_ref(r) if r else None

    async def follow(
        self,
        *,
        follower_id: UUID,
        follower_residency: str,
        followee_id: UUID,
        followee_residency: str,
        tenant_id: UUID,
    ) -> bool:
        inserted = await self._session.execute(
            text(
                """
                INSERT INTO follows (
                    follower_user_id, follower_residency,
                    followee_user_id, followee_residency
                )
                VALUES (
                    :fid, :fres, :tid, :tres
                )
                ON CONFLICT DO NOTHING
                RETURNING follower_user_id
                """
            ),
            {
                "fid": follower_id,
                "fres": follower_residency,
                "tid": followee_id,
                "tres": followee_residency,
            },
        )
        if inserted.one_or_none() is None:
            return False

        await emit_event_if_registered(
            self._session,
            tenant_id=tenant_id,
            event_name="follow.created.v1",
            aggregate_type="user",
            aggregate_id=follower_id,
            payload={
                "follower_user_id": str(follower_id),
                "followee_user_id": str(followee_id),
            },
        )
        return True

    async def unfollow(self, *, follower_id: UUID, followee_id: UUID) -> bool:
        result = await self._session.execute(
            text(
                """
                DELETE FROM follows
                WHERE follower_user_id = :fid AND followee_user_id = :tid
                RETURNING follower_user_id
                """
            ),
            {"fid": follower_id, "tid": followee_id},
        )
        return result.one_or_none() is not None

    async def is_following(self, follower_id: UUID, followee_id: UUID) -> bool:
        row = await self._session.execute(
            text(
                """
                SELECT 1 FROM follows
                WHERE follower_user_id = :fid AND followee_user_id = :tid
                LIMIT 1
                """
            ),
            {"fid": follower_id, "tid": followee_id},
        )
        return row.one_or_none() is not None

    async def followers(self, user_id: UUID, *, limit: int, offset: int) -> FollowEdgeList:
        total = (
            await self._session.execute(
                text("SELECT count(*) FROM follows WHERE followee_user_id = :u"),
                {"u": user_id},
            )
        ).scalar_one()
        result = await self._session.execute(
            text(
                """
                SELECT u.id, u.residency_region, u.pub_id
                FROM follows f
                JOIN users u
                  ON u.id = f.follower_user_id
                 AND u.residency_region = f.follower_residency
                WHERE f.followee_user_id = :u
                ORDER BY f.created_at DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            {"u": user_id, "limit": limit, "offset": offset},
        )
        items = tuple(_to_user_ref(r) for r in result.all())
        return FollowEdgeList(items=items, total=int(total))

    async def following(self, user_id: UUID, *, limit: int, offset: int) -> FollowEdgeList:
        total = (
            await self._session.execute(
                text("SELECT count(*) FROM follows WHERE follower_user_id = :u"),
                {"u": user_id},
            )
        ).scalar_one()
        result = await self._session.execute(
            text(
                """
                SELECT u.id, u.residency_region, u.pub_id
                FROM follows f
                JOIN users u
                  ON u.id = f.followee_user_id
                 AND u.residency_region = f.followee_residency
                WHERE f.follower_user_id = :u
                ORDER BY f.created_at DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            {"u": user_id, "limit": limit, "offset": offset},
        )
        items = tuple(_to_user_ref(r) for r in result.all())
        return FollowEdgeList(items=items, total=int(total))

    async def is_whale(self, user_id: UUID) -> bool:
        row = await self._session.execute(
            text(
                """
                SELECT 1 FROM whale_users
                WHERE user_id = :u AND fanout_mode IN ('pull','hybrid')
                LIMIT 1
                """
            ),
            {"u": user_id},
        )
        return row.one_or_none() is not None


# =====================================================================
# FriendshipRepository
# =====================================================================


class SqlFriendshipRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

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
    ) -> FriendInvitation:
        row = await self._session.execute(
            text(
                """
                INSERT INTO friend_invitations (
                    from_user_id, from_residency,
                    to_user_id, to_residency, to_email,
                    token, message
                )
                VALUES (
                    :fuid, :fres, :tuid, :tres, :temail, :tok, :msg
                )
                RETURNING id, from_user_id, from_residency, to_user_id,
                          to_residency, to_email, token, status, message,
                          expires_at, responded_at, created_at
                """
            ),
            {
                "fuid": from_user_id,
                "fres": from_residency,
                "tuid": to_user_id,
                "tres": to_residency,
                "temail": to_email,
                "tok": token,
                "msg": message,
            },
        )
        invitation = _to_invitation(row.one())

        # Best-effort domain event — silently skipped if not registered.
        await emit_event_if_registered(
            self._session,
            tenant_id=from_user_id,  # we don't have tenant directly; safe default
            event_name="friend.invited.v1",
            aggregate_type="user",
            aggregate_id=from_user_id,
            payload={
                "invitation_id": str(invitation.id),
                "to_user_id": str(to_user_id) if to_user_id else None,
                "to_email": to_email,
            },
        )
        return invitation

    async def get_invitation_by_token(self, token: str) -> FriendInvitation | None:
        row = await self._session.execute(
            text(
                """
                SELECT id, from_user_id, from_residency, to_user_id,
                       to_residency, to_email, token, status, message,
                       expires_at, responded_at, created_at
                FROM friend_invitations
                WHERE token = :tok
                LIMIT 1
                """
            ),
            {"tok": token},
        )
        r = row.one_or_none()
        return _to_invitation(r) if r else None

    async def accept_invitation(self, token: str, *, accepter_id: UUID) -> FriendInvitation:
        existing = await self.get_invitation_by_token(token)
        if existing is None or existing.status != InvitationStatus.PENDING:
            raise InvitationInvalid()

        await self._session.execute(
            text(
                """
                UPDATE friend_invitations
                SET status = 'accepted', responded_at = now()
                WHERE token = :tok
                """
            ),
            {"tok": token},
        )

        # Materialize the friendship row in canonical (a < b) order.
        if existing.to_user_id is not None:
            a_id, a_res, b_id, b_res = _canonical_pair(
                existing.from_user_id,
                existing.from_residency,
                existing.to_user_id,
                existing.to_residency or "global",
            )
            await self._session.execute(
                text(
                    """
                    INSERT INTO friendships (
                        user_a_id, user_a_residency,
                        user_b_id, user_b_residency,
                        status, accepted_at
                    )
                    VALUES (:aid, :ares, :bid, :bres, 'accepted', now())
                    ON CONFLICT (user_a_id, user_b_id) DO UPDATE
                        SET status = 'accepted',
                            accepted_at = now()
                    """
                ),
                {"aid": a_id, "ares": a_res, "bid": b_id, "bres": b_res},
            )
        updated = await self.get_invitation_by_token(token)
        # accepter_id is currently unused; reserved for future audit log.
        _ = accepter_id
        if updated is None:
            raise RuntimeError(f"friend_invitations row vanished after accept token={token!r}")
        return updated

    async def upsert_block(
        self,
        *,
        blocker_id: UUID,
        blocker_residency: str,
        blocked_id: UUID,
        blocked_residency: str,
        reason: str | None = None,
    ) -> bool:
        await self._session.execute(
            text(
                """
                INSERT INTO block_list (
                    blocker_user_id, blocker_residency,
                    blocked_user_id, blocked_residency, reason
                )
                VALUES (:bker, :bker_res, :bked, :bked_res, :reason)
                ON CONFLICT (blocker_user_id, blocked_user_id) DO UPDATE
                    SET reason = COALESCE(EXCLUDED.reason, block_list.reason)
                """
            ),
            {
                "bker": blocker_id,
                "bker_res": blocker_residency,
                "bked": blocked_id,
                "bked_res": blocked_residency,
                "reason": reason,
            },
        )
        return True

    async def remove_block(self, *, blocker_id: UUID, blocked_id: UUID) -> bool:
        row = await self._session.execute(
            text(
                """
                DELETE FROM block_list
                WHERE blocker_user_id = :a AND blocked_user_id = :b
                RETURNING blocker_user_id
                """
            ),
            {"a": blocker_id, "b": blocked_id},
        )
        return row.one_or_none() is not None

    async def is_blocked(self, blocker_id: UUID, blocked_id: UUID) -> bool:
        row = await self._session.execute(
            text(
                """
                SELECT 1 FROM block_list
                WHERE blocker_user_id = :a AND blocked_user_id = :b
                LIMIT 1
                """
            ),
            {"a": blocker_id, "b": blocked_id},
        )
        return row.one_or_none() is not None


def _canonical_pair(a_id: UUID, a_res: str, b_id: UUID, b_res: str) -> tuple[UUID, str, UUID, str]:
    """Friendships are stored with (user_a_id < user_b_id) per migration 0040."""
    if a_id < b_id:
        return a_id, a_res, b_id, b_res
    return b_id, b_res, a_id, a_res


# =====================================================================
# ActivityFeedRepository
# =====================================================================


def _to_feed_item(row: Any) -> ActivityFeedItem:
    m = row._mapping
    return ActivityFeedItem(
        event_id=m["event_id"],
        actor_user_id=m["actor_user_id"],
        verb=ActivityVerb(m["verb"]),
        object_kind=m["object_kind"],
        object_id=m["object_id"],
        payload=dict(m["payload"]) if m["payload"] else {},
        created_at=m["created_at"],
        delivered_at=m["delivered_at"],
        target_kind=m["target_kind"],
        target_id=m["target_id"],
    )


class SqlActivityFeedRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

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
    ) -> UUID:
        row = await self._session.execute(
            text(
                """
                INSERT INTO activity_events (
                    actor_user_id, actor_residency,
                    verb, object_kind, object_id,
                    target_kind, target_id,
                    visibility, payload
                )
                VALUES (
                    :aid, :ares, :verb, :okind, :oid,
                    :tkind, :tid, :vis, CAST(:payload AS jsonb)
                )
                RETURNING id
                """
            ),
            {
                "aid": actor_id,
                "ares": actor_residency,
                "verb": verb.value,
                "okind": object_kind,
                "oid": object_id,
                "tkind": target_kind,
                "tid": target_id,
                "vis": visibility,
                "payload": jdump(payload or {}),
            },
        )
        return UUID(str(row.scalar_one()))

    async def fanout_to_followers(self, *, event_id: UUID) -> int:
        """Push the event into ``activity_fanout`` for every follower of the actor.

        Whale actors (``fanout_mode IN ('pull','hybrid')``) skip the push step
        — their followees will pull on read.
        """
        # First grab actor + verb to know whether to skip
        actor_row = await self._session.execute(
            text(
                """
                SELECT e.actor_user_id, e.verb, e.created_at
                FROM activity_events e
                WHERE e.id = :eid
                LIMIT 1
                """
            ),
            {"eid": event_id},
        )
        actor = actor_row.one_or_none()
        if actor is None:
            return 0
        actor_id = actor._mapping["actor_user_id"]
        verb = actor._mapping["verb"]

        # Skip push fanout for whales (pull-only mode).
        whale = await self._session.execute(
            text(
                """
                SELECT 1 FROM whale_users
                WHERE user_id = :u AND fanout_mode = 'pull'
                LIMIT 1
                """
            ),
            {"u": actor_id},
        )
        if whale.one_or_none() is not None:
            return 0

        _raw = await self._session.execute(
            text(
                """
                INSERT INTO activity_fanout (
                    recipient_user_id, recipient_residency,
                    event_id, event_created_at, actor_user_id, verb
                )
                SELECT
                    f.follower_user_id, f.follower_residency,
                    :eid, :evt_created_at, :actor_id, :verb
                FROM follows f
                WHERE f.followee_user_id = :actor_id
                """
            ),
            {
                "eid": event_id,
                "evt_created_at": actor._mapping["created_at"],
                "actor_id": actor_id,
                "verb": verb,
            },
        )
        return _raw.rowcount or 0  # type: ignore[attr-defined]

    async def feed(
        self,
        *,
        user_id: UUID,
        residency: str,
        limit: int,
        before_ts: datetime | None,
    ) -> ActivityPage:
        params: dict[str, Any] = {
            "u": user_id,
            "ures": residency,
            "limit": limit,
        }
        ts_clause = ""
        if before_ts is not None:
            ts_clause = " AND created_at < :before_ts"
            params["before_ts"] = before_ts

        # Pre-fanned-out items (push side) AND a small pull from whales the user follows.
        result = await self._session.execute(
            text(
                f"""
                WITH pushed AS (
                    SELECT
                        af.event_id,
                        af.actor_user_id,
                        af.verb,
                        af.delivered_at,
                        ae.object_kind,
                        ae.object_id,
                        ae.target_kind,
                        ae.target_id,
                        ae.payload,
                        ae.created_at
                    FROM activity_fanout af
                    JOIN activity_events ae ON ae.id = af.event_id
                    WHERE af.recipient_user_id = :u
                      AND af.recipient_residency = :ures
                      AND NOT EXISTS (
                          SELECT 1 FROM block_list b
                          WHERE b.blocker_user_id = :u
                            AND b.blocked_user_id = af.actor_user_id
                      )
                ),
                pulled AS (
                    SELECT
                        ae.id            AS event_id,
                        ae.actor_user_id,
                        ae.verb,
                        NULL::timestamptz AS delivered_at,
                        ae.object_kind,
                        ae.object_id,
                        ae.target_kind,
                        ae.target_id,
                        ae.payload,
                        ae.created_at
                    FROM activity_events ae
                    JOIN follows f ON f.followee_user_id = ae.actor_user_id
                    JOIN whale_users w ON w.user_id = ae.actor_user_id
                    WHERE f.follower_user_id = :u
                      AND w.fanout_mode IN ('pull','hybrid')
                      AND NOT EXISTS (
                          SELECT 1 FROM block_list b
                          WHERE b.blocker_user_id = :u
                            AND b.blocked_user_id = ae.actor_user_id
                      )
                )
                SELECT * FROM (
                    SELECT * FROM pushed
                    UNION ALL
                    SELECT * FROM pulled
                ) merged
                WHERE TRUE {ts_clause}
                ORDER BY created_at DESC, event_id DESC
                LIMIT :limit
                """  # noqa: S608 — interpolation is literal SQL fragment, not user data
            ),
            params,
        )
        items = tuple(_to_feed_item(r) for r in result.all())
        next_cursor = items[-1].created_at if items and len(items) == limit else None
        return ActivityPage(items=items, next_cursor=next_cursor)
