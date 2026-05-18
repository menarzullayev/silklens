"""Review, reaction, comment, and report endpoints."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.domain.reviews.entities import (
    CommentParentKind,
    ReactionTargetKind,
    ReportReason,
    ReportTargetKind,
    Review,
    ReviewSort,
)
from src.domain.reviews.errors import ReviewError
from src.domain.reviews.service import ReviewService
from src.infrastructure.reviews.repository import SqlReviewRepository
from src.middleware.auth import CurrentUserDep

router = APIRouter(tags=["reviews"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _service(db: AsyncSession) -> ReviewService:
    return ReviewService(repository=SqlReviewRepository(db))


def _raise(exc: ReviewError) -> None:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": str(exc)},
    ) from exc


# --- Schemas ---------------------------------------------------------------


class ReviewRatingIn(BaseModel):
    dimension_slug: str = Field(min_length=2, max_length=64)
    value: int = Field(ge=0, le=10)


class ReviewCreate(BaseModel):
    body_md: str = Field(min_length=10, max_length=10000)
    language_tag: str = Field(default="en", min_length=2, max_length=16)
    title: str | None = Field(default=None, max_length=200)
    visited_at: date | None = None
    ratings: list[ReviewRatingIn] = Field(default_factory=list, max_length=12)


class ReviewOut(BaseModel):
    id: UUID
    heritage_id: UUID
    user_id: UUID
    language_tag: str
    title: str | None
    body_md: str
    is_published: bool
    helpful_count: int
    unhelpful_count: int
    average_rating: Decimal | None
    visited_at: date | None
    created_at: datetime


class ReviewPageOut(BaseModel):
    items: list[ReviewOut]
    total: int
    limit: int
    offset: int


class HelpfulRequest(BaseModel):
    vote: int = Field(description="+1 helpful, -1 unhelpful")


class ReactionRequest(BaseModel):
    reaction_slug: str = Field(min_length=2, max_length=64)


class ReactionOut(BaseModel):
    id: UUID
    target_kind: str
    target_id: UUID
    reaction_type_slug: str
    created_at: datetime


class CommentCreate(BaseModel):
    parent_kind: CommentParentKind
    parent_id: UUID
    body_md: str = Field(min_length=1, max_length=5000)
    language_tag: str = Field(default="en", min_length=2, max_length=16)


class CommentOut(BaseModel):
    id: UUID
    parent_kind: str
    parent_id: UUID
    body_md: str
    depth: int
    path: str
    reply_count: int
    created_at: datetime


class ReportRequest(BaseModel):
    target_kind: ReportTargetKind
    target_id: UUID
    reason_slug: ReportReason
    details: str | None = Field(default=None, max_length=2000)


class ReportOut(BaseModel):
    report_id: UUID


def _to_out(review: Review) -> ReviewOut:
    return ReviewOut(
        id=review.id,
        heritage_id=review.heritage_id,
        user_id=review.user_id,
        language_tag=review.language_tag,
        title=review.title,
        body_md=review.body_md,
        is_published=review.is_published,
        helpful_count=review.helpful_count,
        unhelpful_count=review.unhelpful_count,
        average_rating=review.average_rating,
        visited_at=review.visited_at,
        created_at=review.created_at,
    )


# --- Heritage-scoped review endpoints --------------------------------------


@router.post(
    "/v1/heritage/{pub_id}/reviews",
    response_model=ReviewOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_review(
    pub_id: str, payload: ReviewCreate, db: SessionDep, ctx: CurrentUserDep
) -> ReviewOut:
    try:
        review = await _service(db).create_review(
            heritage_pub_id=pub_id,
            tenant_id=ctx.tenant_id,
            user_id=ctx.user_id,
            residency=ctx.residency_region.value,
            trust_tier=ctx.trust_tier.value,
            body_md=payload.body_md,
            language_tag=payload.language_tag,
            title=payload.title,
            visited_at=payload.visited_at,
            ratings=[r.model_dump() for r in payload.ratings],
        )
        await db.commit()
    except ReviewError as exc:
        await db.rollback()
        _raise(exc)
    return _to_out(review)


@router.get("/v1/heritage/{pub_id}/reviews", response_model=ReviewPageOut)
async def list_reviews_for_heritage(
    pub_id: str,
    db: SessionDep,
    sort: Annotated[ReviewSort, Query()] = ReviewSort.RECENT,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ReviewPageOut:
    try:
        page = await _service(db).list_for_heritage(
            heritage_pub_id=pub_id, sort=sort, limit=limit, offset=offset
        )
    except ReviewError as exc:
        _raise(exc)
    return ReviewPageOut(
        items=[_to_out(r) for r in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


# --- Review-scoped operations ---------------------------------------------


@router.patch("/v1/reviews/{review_id}/helpful", response_model=ReviewOut)
async def vote_helpful(
    review_id: UUID, payload: HelpfulRequest, db: SessionDep, ctx: CurrentUserDep
) -> ReviewOut:
    try:
        review = await _service(db).vote_helpful(
            review_id=review_id,
            voter_id=ctx.user_id,
            voter_residency=ctx.residency_region.value,
            vote=payload.vote,
        )
        await db.commit()
    except ReviewError as exc:
        await db.rollback()
        _raise(exc)
    return _to_out(review)


@router.post(
    "/v1/reviews/{review_id}/reactions",
    response_model=ReactionOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_review_reaction(
    review_id: UUID, payload: ReactionRequest, db: SessionDep, ctx: CurrentUserDep
) -> ReactionOut:
    try:
        reaction = await _service(db).add_reaction(
            reactor_id=ctx.user_id,
            reactor_residency=ctx.residency_region.value,
            target_kind=ReactionTargetKind.REVIEW,
            target_id=review_id,
            reaction_slug=payload.reaction_slug,
        )
        await db.commit()
    except ReviewError as exc:
        await db.rollback()
        _raise(exc)
    return ReactionOut(
        id=reaction.id,
        target_kind=reaction.target_kind.value,
        target_id=reaction.target_id,
        reaction_type_slug=reaction.reaction_type_slug,
        created_at=reaction.created_at,
    )


@router.delete("/v1/reviews/{review_id}/reactions/{reaction_slug}")
async def remove_review_reaction(
    review_id: UUID, reaction_slug: str, db: SessionDep, ctx: CurrentUserDep
) -> dict:
    removed = await _service(db).remove_reaction(
        reactor_id=ctx.user_id,
        target_kind=ReactionTargetKind.REVIEW,
        target_id=review_id,
        reaction_slug=reaction_slug,
    )
    await db.commit()
    return {"status": "ok", "removed": removed}


# --- Comments --------------------------------------------------------------


@router.post("/v1/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
async def create_comment(payload: CommentCreate, db: SessionDep, ctx: CurrentUserDep) -> CommentOut:
    try:
        comment = await _service(db).add_comment(
            tenant_id=ctx.tenant_id,
            author_id=ctx.user_id,
            author_residency=ctx.residency_region.value,
            parent_kind=payload.parent_kind,
            parent_id=payload.parent_id,
            body_md=payload.body_md,
            language_tag=payload.language_tag,
        )
        await db.commit()
    except ReviewError as exc:
        await db.rollback()
        _raise(exc)
    return CommentOut(
        id=comment.id,
        parent_kind=comment.parent_kind.value,
        parent_id=comment.parent_id,
        body_md=comment.body_md,
        depth=comment.depth,
        path=comment.path,
        reply_count=comment.reply_count,
        created_at=comment.created_at,
    )


# --- Reports ---------------------------------------------------------------


@router.post("/v1/reports", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
async def create_report(payload: ReportRequest, db: SessionDep, ctx: CurrentUserDep) -> ReportOut:
    report_id = await _service(db).report(
        reporter_id=ctx.user_id,
        reporter_residency=ctx.residency_region.value,
        target_kind=payload.target_kind,
        target_id=payload.target_id,
        reason=payload.reason_slug,
        details=payload.details,
    )
    await db.commit()
    return ReportOut(report_id=report_id)
