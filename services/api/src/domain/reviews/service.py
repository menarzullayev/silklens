"""Reviews / reactions / comments / reports application service."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from src.domain.reviews.entities import (
    Comment,
    CommentParentKind,
    Reaction,
    ReactionTargetKind,
    ReportReason,
    ReportTargetKind,
    Review,
    ReviewDraft,
    ReviewPage,
    ReviewRating,
    ReviewSort,
    UgcStatus,
)
from src.domain.reviews.errors import (
    HeritageNotFoundForReview,
    InvalidRating,
    InvalidVote,
    ReviewNotFound,
    UnknownReactionType,
)
from src.domain.reviews.repository import ReviewRepository

# Trust tiers that get straight-to-published reviews (no human queue).
_AUTO_PUBLISH_TIERS = {"trusted", "contributor", "staff", "admin"}


class ReviewService:
    def __init__(self, *, repository: ReviewRepository) -> None:
        self._repo = repository

    async def create_review(
        self,
        *,
        heritage_pub_id: str,
        tenant_id: UUID,
        user_id: UUID,
        residency: str,
        trust_tier: str,
        body_md: str,
        language_tag: str,
        title: str | None,
        visited_at: date | None,
        ratings: list[dict[str, Any]],
    ) -> Review:
        heritage_id = await self._repo.heritage_pub_id_to_id(heritage_pub_id)
        if heritage_id is None:
            raise HeritageNotFoundForReview()
        validated = self._validate_ratings(ratings)

        auto_publish = trust_tier in _AUTO_PUBLISH_TIERS
        draft = ReviewDraft(
            tenant_id=tenant_id,
            heritage_id=heritage_id,
            user_id=user_id,
            residency_region=residency,
            language_tag=language_tag,
            body_md=body_md,
            title=title,
            visited_at=visited_at,
            ratings=validated,
        )
        review = await self._repo.create_review(draft=draft, auto_publish=auto_publish)

        # Always also write a UGC submission row so the moderation pipeline has
        # a single queue to drain.
        await self._repo.submit_ugc(
            tenant_id=tenant_id,
            kind="review",
            target_id=review.id,
            author_id=user_id,
            author_residency=residency,
            payload={"language_tag": language_tag, "auto_publish": auto_publish},
            status=UgcStatus.AUTO_APPROVED if auto_publish else UgcStatus.PENDING,
            trust_tier=trust_tier,
        )
        return review

    @staticmethod
    def _validate_ratings(raw: list[dict[str, Any]]) -> tuple[ReviewRating, ...]:
        out: list[ReviewRating] = []
        for entry in raw:
            try:
                slug = str(entry["dimension_slug"])
                value = int(entry["value"])
            except (KeyError, TypeError, ValueError) as exc:
                raise InvalidRating("dimension_slug and integer value are required") from exc
            if not (0 <= value <= 10):
                raise InvalidRating(f"value {value} out of allowed 0..10 range")
            out.append(ReviewRating(dimension_slug=slug, value=value))
        return tuple(out)

    async def vote_helpful(
        self,
        *,
        review_id: UUID,
        voter_id: UUID,
        voter_residency: str,
        vote: int,
    ) -> Review:
        if vote not in (-1, 1):
            raise InvalidVote("vote must be -1 or +1")
        review = await self._repo.get_by_id(review_id)
        if review is None:
            raise ReviewNotFound()
        return await self._repo.upsert_helpful_vote(
            review_id=review_id,
            voter_id=voter_id,
            voter_residency=voter_residency,
            vote=vote,
        )

    async def add_reaction(
        self,
        *,
        reactor_id: UUID,
        reactor_residency: str,
        target_kind: ReactionTargetKind,
        target_id: UUID,
        reaction_slug: str,
    ) -> Reaction:
        if not await self._repo.reaction_type_exists(reaction_slug):
            raise UnknownReactionType()
        return await self._repo.add_reaction(
            reactor_id=reactor_id,
            reactor_residency=reactor_residency,
            target_kind=target_kind,
            target_id=target_id,
            reaction_slug=reaction_slug,
        )

    async def remove_reaction(
        self,
        *,
        reactor_id: UUID,
        target_kind: ReactionTargetKind,
        target_id: UUID,
        reaction_slug: str,
    ) -> bool:
        return await self._repo.remove_reaction(
            reactor_id=reactor_id,
            target_kind=target_kind,
            target_id=target_id,
            reaction_slug=reaction_slug,
        )

    async def add_comment(
        self,
        *,
        tenant_id: UUID,
        author_id: UUID,
        author_residency: str,
        parent_kind: CommentParentKind,
        parent_id: UUID,
        body_md: str,
        language_tag: str,
    ) -> Comment:
        return await self._repo.add_comment(
            tenant_id=tenant_id,
            author_id=author_id,
            author_residency=author_residency,
            parent_kind=parent_kind,
            parent_id=parent_id,
            body_md=body_md,
            language_tag=language_tag,
        )

    async def report(
        self,
        *,
        reporter_id: UUID,
        reporter_residency: str,
        target_kind: ReportTargetKind,
        target_id: UUID,
        reason: ReportReason,
        details: str | None,
    ) -> UUID:
        return await self._repo.create_report(
            reporter_id=reporter_id,
            reporter_residency=reporter_residency,
            target_kind=target_kind,
            target_id=target_id,
            reason=reason,
            details=details,
        )

    async def list_for_heritage(
        self,
        *,
        heritage_pub_id: str,
        sort: ReviewSort,
        limit: int,
        offset: int,
    ) -> ReviewPage:
        heritage_id = await self._repo.heritage_pub_id_to_id(heritage_pub_id)
        if heritage_id is None:
            raise HeritageNotFoundForReview()
        return await self._repo.list_for_heritage(
            heritage_id=heritage_id, sort=sort, limit=limit, offset=offset
        )
