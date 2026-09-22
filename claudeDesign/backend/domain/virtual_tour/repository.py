"""Repository protocol for the virtual-tour bounded context."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.domain.virtual_tour.entities import (
    TourDraft,
    TourPage,
    TourProgress,
    TourUpdate,
    VirtualTour,
    VirtualTourCollection,
)


class VirtualTourRepository(Protocol):
    async def list_tours(
        self,
        *,
        heritage_id: UUID | None,
        collection_slug: str | None,
        kind: str | None,
        limit: int,
        offset: int,
    ) -> TourPage: ...

    async def get_by_slug(self, slug: str) -> VirtualTour | None: ...

    async def create(self, draft: TourDraft) -> VirtualTour: ...

    async def update(self, slug: str, update: TourUpdate) -> VirtualTour | None: ...

    async def set_status(self, slug: str, status: str) -> VirtualTour | None: ...

    async def upsert_progress(
        self,
        user_id: UUID,
        residency_region: str,
        tour_id: UUID,
        last_scene_order: int,
        completed: bool,
    ) -> TourProgress: ...

    async def get_progress(
        self,
        user_id: UUID,
        residency_region: str,
        tour_id: UUID,
    ) -> TourProgress | None: ...

    async def list_collections(self) -> list[VirtualTourCollection]: ...

    async def increment_view_count(self, tour_id: UUID) -> None: ...
