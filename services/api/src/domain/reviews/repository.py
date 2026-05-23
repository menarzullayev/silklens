"""Review/UGC repository protocols."""

from __future__ import annotations

from typing import Any, Protocol
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
    ReviewSort,
    UgcStatus,
    UgcSubmission,
)


class ReviewRepository(Protocol):
    async def heritage_pub_id_to_id(self, pub_id: str) -> UUID | None: ...

    async def get_by_id(self, review_id: UUID) -> Review | None: ...

    async def list_for_heritage(
        self,
        *,
        heritage_id: UUID,
        sort: ReviewSort,
        limit: int,
        offset: int,
    ) -> ReviewPage: ...

    async def create_review(self, *, draft: ReviewDraft, auto_publish: bool) -> Review: ...

    async def upsert_helpful_vote(
        self, *, review_id: UUID, voter_id: UUID, voter_residency: str, vote: int
    ) -> Review: ...

    async def add_reaction(
        self,
        *,
        reactor_id: UUID,
        reactor_residency: str,
        target_kind: ReactionTargetKind,
        target_id: UUID,
        reaction_slug: str,
    ) -> Reaction: ...

    async def remove_reaction(
        self,
        *,
        reactor_id: UUID,
        target_kind: ReactionTargetKind,
        target_id: UUID,
        reaction_slug: str,
    ) -> bool: ...

    async def reaction_type_exists(self, slug: str) -> bool: ...

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
    ) -> Comment: ...

    async def submit_ugc(
        self,
        *,
        tenant_id: UUID,
        kind: str,
        target_id: UUID,
        author_id: UUID,
        author_residency: str,
        payload: dict[str, Any],
        status: UgcStatus,
        trust_tier: str,
    ) -> UgcSubmission: ...

    async def create_report(
        self,
        *,
        reporter_id: UUID,
        reporter_residency: str,
        target_kind: ReportTargetKind,
        target_id: UUID,
        reason: ReportReason,
        details: str | None,
    ) -> UUID: ...
