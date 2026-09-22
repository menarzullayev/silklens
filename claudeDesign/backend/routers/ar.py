"""AR gamification endpoints — challenges, sessions, overlays."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.domain.ar.entities import ArChallengeKind, ArSessionKind
from src.domain.ar.errors import ArError
from src.domain.ar.service import ArService
from src.infrastructure.ar.repository import ArRepository
from src.middleware.auth import CurrentUserDep

router = APIRouter(tags=["ar"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _service(db: AsyncSession) -> ArService:
    return ArService(repository=ArRepository(db))


def _raise(exc: ArError) -> None:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": str(exc)},
    ) from exc


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ArChallengeOut(BaseModel):
    id: UUID
    slug: str
    title: dict[str, Any]
    description_md: dict[str, Any]
    kind: str
    difficulty: str
    reward_xp: int
    time_limit_seconds: int | None
    ar_anchor_lat: float
    ar_anchor_lng: float
    ar_anchor_altitude_m: float | None
    trigger_radius_m: float
    clue_text_md: dict[str, Any]
    hint_available: bool
    is_active: bool
    completion_count: int


class ArChallengeListOut(BaseModel):
    items: list[ArChallengeOut]
    count: int


class SubmitAnswerIn(BaseModel):
    answer: dict[str, Any]
    time_taken_seconds: int
    hint_used: bool = False
    photo_media_id: UUID | None = None


class SubmitAnswerOut(BaseModel):
    score: int
    xp_awarded: int
    badge_unlocked: bool
    completion_id: UUID


class HintOut(BaseModel):
    hint_text_md: dict[str, Any]


class StartSessionIn(BaseModel):
    heritage_pub_id: str | None = None
    kind: ArSessionKind = ArSessionKind.SOLO
    max_participants: int = 1


class ArSessionOut(BaseModel):
    id: UUID
    session_kind: str
    started_at: str
    max_participants: int
    session_code: str | None
    heritage_id: UUID | None


class ArOverlayOut(BaseModel):
    id: UUID
    overlay_kind: str
    position_data: dict[str, Any]
    content_md: dict[str, Any]
    media_asset_id: UUID | None
    display_from_date: str | None
    display_until_date: str | None


class ArOverlayListOut(BaseModel):
    items: list[ArOverlayOut]
    count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _challenge_out(c: Any) -> ArChallengeOut:
    return ArChallengeOut(
        id=c.id,
        slug=c.slug,
        title=c.title,
        description_md=c.description_md,
        kind=c.kind.value,
        difficulty=c.difficulty.value,
        reward_xp=c.reward_xp,
        time_limit_seconds=c.time_limit_seconds,
        ar_anchor_lat=c.ar_anchor_lat,
        ar_anchor_lng=c.ar_anchor_lng,
        ar_anchor_altitude_m=c.ar_anchor_altitude_m,
        trigger_radius_m=c.trigger_radius_m,
        clue_text_md=c.clue_text_md,
        hint_available=c.hint_text_md is not None,
        is_active=c.is_active,
        completion_count=c.completion_count,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/v1/ar/challenges", response_model=ArChallengeListOut)
async def list_ar_challenges(
    db: SessionDep,
    heritage_pub_id: Annotated[str | None, Query()] = None,
    kind: Annotated[ArChallengeKind | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ArChallengeListOut:
    """Public: list active AR challenges, optionally filtered by heritage and/or kind."""
    challenges = await _service(db).list_challenges(
        heritage_pub_id=heritage_pub_id,
        kind=kind,
        limit=limit,
    )
    return ArChallengeListOut(
        items=[_challenge_out(c) for c in challenges],
        count=len(challenges),
    )


@router.get("/v1/ar/challenges/{slug}", response_model=ArChallengeOut)
async def get_ar_challenge(slug: str, db: SessionDep) -> ArChallengeOut:
    """Public: get a single AR challenge by slug."""
    try:
        challenge = await _service(db).get_challenge(slug)
    except ArError as exc:
        _raise(exc)
    return _challenge_out(challenge)


@router.post(
    "/v1/ar/challenges/{slug}/complete",
    response_model=SubmitAnswerOut,
    status_code=status.HTTP_200_OK,
)
async def complete_ar_challenge(
    slug: str,
    body: SubmitAnswerIn,
    db: SessionDep,
    ctx: CurrentUserDep,
) -> SubmitAnswerOut:
    """Auth: submit an answer for an AR challenge. Returns score + XP awarded.

    Returns 409 if the challenge was already completed.
    """
    service = _service(db)
    try:
        challenge = await service.get_challenge(slug)
        completion, _xp_delta, badge_unlocked = await service.submit_completion(
            user_id=ctx.user_id,
            residency=ctx.residency_region.value,
            tenant_id=ctx.tenant_id,
            challenge_id=challenge.id,
            answer=body.answer,
            time_taken_seconds=body.time_taken_seconds,
            hint_used=body.hint_used,
            photo_media_id=body.photo_media_id,
        )
    except ArError as exc:
        _raise(exc)
    await db.commit()
    return SubmitAnswerOut(
        score=completion.score,
        xp_awarded=completion.xp_awarded,
        badge_unlocked=badge_unlocked,
        completion_id=completion.id,
    )


@router.get("/v1/ar/challenges/{slug}/hint", response_model=HintOut)
async def get_ar_challenge_hint(
    slug: str,
    db: SessionDep,
    ctx: CurrentUserDep,  # presence enforces auth requirement; value not read
) -> HintOut:
    """Auth: retrieve hint text for a challenge. Caller opts-in to XP cost."""
    try:
        hint_md = await _service(db).get_hint(slug)
    except ArError as exc:
        _raise(exc)
    return HintOut(hint_text_md=hint_md)


@router.post(
    "/v1/ar/sessions",
    response_model=ArSessionOut,
    status_code=status.HTTP_201_CREATED,
)
async def start_ar_session(
    body: StartSessionIn,
    db: SessionDep,
    ctx: CurrentUserDep,
) -> ArSessionOut:
    """Auth: start a new solo or group AR session."""
    # Resolve heritage_id from pub_id if provided
    heritage_id: UUID | None = None
    if body.heritage_pub_id:
        from sqlalchemy import text as _text

        row = (
            await db.execute(
                _text("SELECT id FROM heritage_objects WHERE pub_id = :p"),
                {"p": body.heritage_pub_id},
            )
        ).scalar_one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail={"code": "heritage.not_found"})
        heritage_id = row

    session = await _service(db).start_session(
        user_id=ctx.user_id,
        residency=ctx.residency_region.value,
        heritage_id=heritage_id,
        kind=body.kind,
        max_participants=body.max_participants,
    )
    await db.commit()
    return ArSessionOut(
        id=session.id,
        session_kind=session.session_kind.value,
        started_at=session.started_at.isoformat(),
        max_participants=session.max_participants,
        session_code=session.session_code,
        heritage_id=session.heritage_id,
    )


@router.post(
    "/v1/ar/sessions/{code}/join",
    response_model=ArSessionOut,
    status_code=status.HTTP_200_OK,
)
async def join_ar_session(
    code: str,
    db: SessionDep,
    ctx: CurrentUserDep,
) -> ArSessionOut:
    """Auth: join an existing group AR session by 6-char session code."""
    try:
        session = await _service(db).join_session(
            user_id=ctx.user_id,
            residency=ctx.residency_region.value,
            session_code=code.upper(),
        )
    except ArError as exc:
        _raise(exc)
    await db.commit()
    return ArSessionOut(
        id=session.id,
        session_kind=session.session_kind.value,
        started_at=session.started_at.isoformat(),
        max_participants=session.max_participants,
        session_code=session.session_code,
        heritage_id=session.heritage_id,
    )


@router.get("/v1/ar/overlays", response_model=ArOverlayListOut)
async def list_ar_overlays(
    db: SessionDep,
    heritage_pub_id: Annotated[str, Query()],
    ref_date: Annotated[date | None, Query(alias="date")] = None,
) -> ArOverlayListOut:
    """Public: list active AR overlays for a heritage site on a given date."""
    overlays = await _service(db).list_overlays(
        heritage_pub_id=heritage_pub_id,
        reference_date=ref_date.isoformat() if ref_date else None,
    )
    return ArOverlayListOut(
        items=[
            ArOverlayOut(
                id=o.id,
                overlay_kind=o.overlay_kind.value,
                position_data=o.position_data,
                content_md=o.content_md,
                media_asset_id=o.media_asset_id,
                display_from_date=o.display_from_date,
                display_until_date=o.display_until_date,
            )
            for o in overlays
        ],
        count=len(overlays),
    )
