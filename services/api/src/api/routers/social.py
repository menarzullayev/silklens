"""Social graph endpoints — follows, friends, blocks, activity feed.

Follows are residency-aware: every write carries the actor's residency so the
composite FK to ``users`` resolves correctly. Public read endpoints (followers,
following) don't require auth.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.domain.social.errors import SocialError
from src.domain.social.service import SocialService
from src.infrastructure.social.repository import (
    SqlActivityFeedRepository,
    SqlFollowRepository,
    SqlFriendshipRepository,
)
from src.middleware.auth import CurrentUserDep

router = APIRouter(prefix="/v1/social", tags=["social"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _service(db: AsyncSession) -> SocialService:
    return SocialService(
        follows=SqlFollowRepository(db),
        friendships=SqlFriendshipRepository(db),
        feed_repo=SqlActivityFeedRepository(db),
    )


def _raise(exc: SocialError) -> None:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": str(exc)},
    ) from exc


# --- Schemas ---------------------------------------------------------------


class UserRefOut(BaseModel):
    pub_id: str
    residency_region: str


class FollowEdgeListOut(BaseModel):
    items: list[UserRefOut]
    total: int


class FriendInviteRequest(BaseModel):
    target_pub_id: str | None = Field(default=None, min_length=4, max_length=64)
    target_email: EmailStr | None = None
    message: str | None = Field(default=None, max_length=512)


class FriendInviteOut(BaseModel):
    """Response shape for the friend-invite POST + accept routes.

    SEC-021: the raw ``token`` is only meaningful to the inviter (who needs
    to share it out-of-band) and the invited party (who needs it to accept).
    Once the row has been read back from any other path, we mask the field
    so it doesn't leak via screenshot / log / response replay. The
    ``token = "***"`` sentinel is also what the admin panel's mask-aware
    components render. Admin callers can re-fetch the underlying row via the
    admin endpoint if they need the raw value.
    """

    id: UUID
    token: str
    status: str
    expires_at: datetime

    @classmethod
    def fresh(cls, *, id: UUID, token: str, status: str, expires_at: datetime) -> FriendInviteOut:
        """Builder used at *creation* time; returns the raw token verbatim."""
        return cls(id=id, token=token, status=status, expires_at=expires_at)

    @classmethod
    def masked(cls, *, id: UUID, status: str, expires_at: datetime) -> FriendInviteOut:
        """Builder used for subsequent reads; the token field is redacted."""
        return cls(id=id, token="***", status=status, expires_at=expires_at)  # noqa: S106 — explicit mask sentinel, not a credential


class FriendAcceptRequest(BaseModel):
    token: str = Field(min_length=16, max_length=128)


class BlockRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=512)


class ActivityItemOut(BaseModel):
    event_id: UUID
    actor_user_id: UUID
    verb: str
    object_kind: str
    object_id: UUID
    payload: dict[str, Any]
    created_at: datetime
    delivered_at: datetime | None
    target_kind: str | None
    target_id: UUID | None


class FeedOut(BaseModel):
    items: list[ActivityItemOut]
    next_cursor: datetime | None


# --- Follow / unfollow -----------------------------------------------------


@router.post("/follow/{pub_id}", status_code=status.HTTP_201_CREATED)
async def follow(
    pub_id: str,
    db: SessionDep,
    ctx: CurrentUserDep,
) -> dict[str, Any]:
    try:
        target = await _service(db).follow(
            actor_id=ctx.user_id,
            actor_residency=ctx.residency_region.value,
            tenant_id=ctx.tenant_id,
            target_pub_id=pub_id,
        )
        await db.commit()
    except SocialError as exc:
        await db.rollback()
        _raise(exc)
    return {"status": "ok", "target_pub_id": target.pub_id}


@router.delete("/follow/{pub_id}", status_code=status.HTTP_200_OK)
async def unfollow(pub_id: str, db: SessionDep, ctx: CurrentUserDep) -> dict[str, Any]:
    try:
        await _service(db).unfollow(actor_id=ctx.user_id, target_pub_id=pub_id)
        await db.commit()
    except SocialError as exc:
        await db.rollback()
        _raise(exc)
    return {"status": "ok"}


@router.get("/followers/{pub_id}", response_model=FollowEdgeListOut)
async def followers(
    pub_id: str,
    db: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> FollowEdgeListOut:
    try:
        page = await _service(db).followers(target_pub_id=pub_id, limit=limit, offset=offset)
    except SocialError as exc:
        _raise(exc)
    return FollowEdgeListOut(
        items=[
            UserRefOut(pub_id=u.pub_id, residency_region=u.residency_region) for u in page.items
        ],
        total=page.total,
    )


@router.get("/following/{pub_id}", response_model=FollowEdgeListOut)
async def following(
    pub_id: str,
    db: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> FollowEdgeListOut:
    try:
        page = await _service(db).following(target_pub_id=pub_id, limit=limit, offset=offset)
    except SocialError as exc:
        _raise(exc)
    return FollowEdgeListOut(
        items=[
            UserRefOut(pub_id=u.pub_id, residency_region=u.residency_region) for u in page.items
        ],
        total=page.total,
    )


# --- Friend invitations ----------------------------------------------------


@router.post("/friends/invite", response_model=FriendInviteOut)
async def send_friend_invitation(
    payload: FriendInviteRequest, db: SessionDep, ctx: CurrentUserDep
) -> FriendInviteOut:
    try:
        invitation = await _service(db).send_friend_invitation(
            actor_id=ctx.user_id,
            actor_residency=ctx.residency_region.value,
            target_pub_id=payload.target_pub_id,
            target_email=str(payload.target_email) if payload.target_email else None,
            message=payload.message,
        )
        await db.commit()
    except SocialError as exc:
        await db.rollback()
        _raise(exc)
    # POST is the *only* creation point — the inviter gets the raw token so
    # they can paste it into a message/share link out-of-band.
    return FriendInviteOut.fresh(
        id=invitation.id,
        token=invitation.token,
        status=invitation.status.value,
        expires_at=invitation.expires_at,
    )


@router.post("/friends/accept", response_model=FriendInviteOut)
async def accept_friend_invitation(
    payload: FriendAcceptRequest, db: SessionDep, ctx: CurrentUserDep
) -> FriendInviteOut:
    try:
        invitation = await _service(db).accept_friend_invitation(
            actor_id=ctx.user_id, token=payload.token
        )
        await db.commit()
    except SocialError as exc:
        await db.rollback()
        _raise(exc)
    # SEC-021: this is a "subsequent read" of the invitation row — the caller
    # already had the token (they POSTed it). Mask before returning so the
    # value can't leak via a response log or shared screenshot.
    return FriendInviteOut.masked(
        id=invitation.id,
        status=invitation.status.value,
        expires_at=invitation.expires_at,
    )


# --- Block / unblock -------------------------------------------------------


@router.post("/block/{pub_id}", status_code=status.HTTP_201_CREATED)
async def block(
    pub_id: str,
    db: SessionDep,
    ctx: CurrentUserDep,
    payload: BlockRequest | None = None,
) -> dict[str, Any]:
    try:
        await _service(db).block_user(
            actor_id=ctx.user_id,
            actor_residency=ctx.residency_region.value,
            target_pub_id=pub_id,
            reason=payload.reason if payload else None,
        )
        await db.commit()
    except SocialError as exc:
        await db.rollback()
        _raise(exc)
    return {"status": "ok"}


@router.delete("/block/{pub_id}")
async def unblock(pub_id: str, db: SessionDep, ctx: CurrentUserDep) -> dict[str, Any]:
    try:
        await _service(db).unblock_user(actor_id=ctx.user_id, target_pub_id=pub_id)
        await db.commit()
    except SocialError as exc:
        await db.rollback()
        _raise(exc)
    return {"status": "ok"}


# --- Feed ------------------------------------------------------------------


@router.get("/feed", response_model=FeedOut)
async def feed(
    db: SessionDep,
    ctx: CurrentUserDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    before: Annotated[datetime | None, Query()] = None,
) -> FeedOut:
    page = await _service(db).feed(
        user_id=ctx.user_id,
        residency=ctx.residency_region.value,
        limit=limit,
        before_ts=before,
    )
    return FeedOut(
        items=[
            ActivityItemOut(
                event_id=i.event_id,
                actor_user_id=i.actor_user_id,
                verb=i.verb.value,
                object_kind=i.object_kind,
                object_id=i.object_id,
                payload=i.payload,
                created_at=i.created_at,
                delivered_at=i.delivered_at,
                target_kind=i.target_kind,
                target_id=i.target_id,
            )
            for i in page.items
        ],
        next_cursor=page.next_cursor,
    )


# --- Traveler discovery (SILK-0077) ----------------------------------------


@router.get("/travelers/nearby")
async def nearby_travelers(
    ctx: CurrentUserDep,
    db: SessionDep,
    heritage_pub_id: Annotated[UUID, Query(...)],
    limit: Annotated[int, Query(ge=1, le=20)] = 10,
) -> dict[str, Any]:
    """Find other discoverable travelers near a heritage site.

    Only returns users who have opted in (is_discoverable=true) and
    checked in within the last 2 hours. Mutual blocks are respected.

    Note: heritage_check_ins table is created in migration 0099.
    """
    from sqlalchemy import text

    rows = await db.execute(
        text("""
            SELECT DISTINCT u.pub_id, up.display_name, up.avatar_url,
                   up.travel_style, up.interests
            FROM heritage_check_ins hci
            JOIN users u ON u.id = hci.user_id
            JOIN user_profiles up ON up.user_id = u.id
            WHERE hci.heritage_pub_id = :pub_id
              AND hci.checked_in_at > now() - interval '2 hours'
              AND hci.user_id != :uid
              AND up.is_discoverable = true
              AND NOT EXISTS (
                  SELECT 1 FROM block_list bl
                  WHERE (bl.blocker_id = :uid AND bl.blocked_id = hci.user_id)
                     OR (bl.blocker_id = hci.user_id AND bl.blocked_id = :uid)
              )
            ORDER BY hci.checked_in_at DESC
            LIMIT :limit
        """),
        {"pub_id": str(heritage_pub_id), "uid": ctx.user_id, "limit": limit},
    )
    return {
        "travelers": [dict(r) for r in rows.mappings().fetchall()],
        "heritage_pub_id": str(heritage_pub_id),
    }
