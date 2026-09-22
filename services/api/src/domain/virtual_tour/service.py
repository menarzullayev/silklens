"""Virtual-tour application service.

Coordinates the repository, enforces state transitions and validation.
"""

from __future__ import annotations

import contextlib
from uuid import UUID

from src.domain.virtual_tour.entities import (
    TourDraft,
    TourPage,
    TourProgress,
    TourStatus,
    TourUpdate,
    VirtualTour,
    VirtualTourCollection,
)
from src.domain.virtual_tour.errors import (
    DuplicateTourSlug,
    InvalidTourTransition,
    TourNotFound,
    TourNotPublished,
    TourValidationError,
)
from src.domain.virtual_tour.repository import VirtualTourRepository

# Valid state machine transitions: current → allowed next statuses
_ALLOWED_PUBLISH_TRANSITIONS: dict[TourStatus, set[TourStatus]] = {
    TourStatus.DRAFT: {TourStatus.PROCESSING, TourStatus.PUBLISHED},
    TourStatus.PROCESSING: {TourStatus.PUBLISHED, TourStatus.DRAFT},
    TourStatus.PUBLISHED: {TourStatus.ARCHIVED},
    TourStatus.ARCHIVED: set(),
}

_MSG_SLUG_CHARS = "must only contain letters, numbers, hyphens, underscores"


def _validate_draft(draft: TourDraft) -> None:
    if not draft.title:
        raise TourValidationError("title", "at least one language entry required")
    if "en" not in draft.title and "uz" not in draft.title:
        raise TourValidationError("title", "must include either 'en' or 'uz'")
    if not draft.slug or len(draft.slug) < 3:
        raise TourValidationError("slug", "must be at least 3 characters")
    if not draft.slug.replace("-", "").replace("_", "").isalnum():
        raise TourValidationError("slug", _MSG_SLUG_CHARS)


class VirtualTourService:
    def __init__(self, repository: VirtualTourRepository) -> None:
        self._repo = repository

    async def list_tours(
        self,
        heritage_pub_id: str | None = None,  # resolved to UUID by router before calling
        collection_slug: str | None = None,
        kind: str | None = None,
        limit: int = 20,
        offset: int = 0,
        heritage_id: UUID | None = None,
    ) -> TourPage:
        # heritage_id may be pre-resolved by the router layer
        return await self._repo.list_tours(
            heritage_id=heritage_id,
            collection_slug=collection_slug,
            kind=kind,
            limit=max(1, min(limit, 100)),
            offset=max(0, offset),
        )

    async def get_tour(self, slug: str) -> VirtualTour:
        tour = await self._repo.get_by_slug(slug)
        if tour is None or tour.deleted_at is not None:
            raise TourNotFound(slug)
        # Count the view (best-effort; never break the response on failure)
        with contextlib.suppress(Exception):
            await self._repo.increment_view_count(tour.id)
        return tour

    async def create_tour(self, draft: TourDraft, actor_user_id: UUID) -> VirtualTour:
        _validate_draft(draft)
        try:
            return await self._repo.create(draft)
        except Exception as exc:
            msg = str(exc)
            if "unique" in msg.lower() and "slug" in msg.lower():
                raise DuplicateTourSlug(draft.slug) from exc
            raise

    async def update_tour(self, slug: str, update: TourUpdate, actor_user_id: UUID) -> VirtualTour:
        tour = await self._repo.get_by_slug(slug)
        if tour is None or tour.deleted_at is not None:
            raise TourNotFound(slug)
        updated = await self._repo.update(slug, update)
        if updated is None:
            raise TourNotFound(slug)
        return updated

    async def publish_tour(self, slug: str, actor_user_id: UUID) -> VirtualTour:
        tour = await self._repo.get_by_slug(slug)
        if tour is None or tour.deleted_at is not None:
            raise TourNotFound(slug)
        allowed = _ALLOWED_PUBLISH_TRANSITIONS.get(tour.status, set())
        if TourStatus.PUBLISHED not in allowed:
            raise InvalidTourTransition(tour.status, TourStatus.PUBLISHED)
        published = await self._repo.set_status(slug, TourStatus.PUBLISHED)
        if published is None:
            raise TourNotFound(slug)
        return published

    async def record_progress(
        self,
        user_id: UUID,
        residency_region: str,
        tour_id: UUID,
        scene_order: int,
        completed: bool,
    ) -> TourProgress:
        return await self._repo.upsert_progress(
            user_id=user_id,
            residency_region=residency_region,
            tour_id=tour_id,
            last_scene_order=scene_order,
            completed=completed,
        )

    async def get_progress(
        self,
        user_id: UUID,
        residency_region: str,
        tour_id: UUID,
    ) -> TourProgress | None:
        return await self._repo.get_progress(user_id, residency_region, tour_id)

    async def list_collections(self) -> list[VirtualTourCollection]:
        return await self._repo.list_collections()

    async def get_embed(self, slug: str) -> str | None:
        tour = await self._repo.get_by_slug(slug)
        if tour is None or tour.deleted_at is not None:
            raise TourNotFound(slug)
        if tour.status != TourStatus.PUBLISHED:
            raise TourNotPublished(slug)
        return tour.embed_code
