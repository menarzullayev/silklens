"""Virtual-tour domain entities — pure Python, framework-free.

Mirrors the schema introduced in migration 0087_virtual_tours.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class TourKind(StrEnum):
    MUSEUM_WALKTHROUGH = "museum_walkthrough"
    SITE_FLYTHROUGH = "site_flythrough"
    ROOM_EXPLORATION = "room_exploration"
    TIMELINE_3D = "timeline_3d"


class TourStatus(StrEnum):
    DRAFT = "draft"
    PROCESSING = "processing"
    PUBLISHED = "published"
    ARCHIVED = "archived"


@dataclass(slots=True, frozen=True)
class TourScene:
    id: UUID
    tour_id: UUID
    scene_order: int
    title: dict[str, str]
    description_md: dict[str, str]
    hotspot_data: list[dict[str, Any]]
    panorama_media_id: UUID | None = None
    model_3d_asset_id: UUID | None = None
    audio_guide_media_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(slots=True, frozen=True)
class VirtualTour:
    id: UUID
    tenant_id: UUID
    slug: str
    title: dict[str, str]
    description_md: dict[str, str]
    kind: TourKind
    status: TourStatus
    view_count: int
    created_at: datetime
    updated_at: datetime
    scenes: tuple[TourScene, ...] = field(default_factory=tuple)
    heritage_id: UUID | None = None
    thumbnail_media_id: UUID | None = None
    tour_duration_seconds: int | None = None
    viewer_url: str | None = None
    embed_code: str | None = None
    deleted_at: datetime | None = None


@dataclass(slots=True, frozen=True)
class TourProgress:
    user_id: UUID
    residency_region: str
    tour_id: UUID
    last_scene_order: int
    completed: bool
    started_at: datetime
    updated_at: datetime


@dataclass(slots=True, frozen=True)
class VirtualTourCollection:
    id: UUID
    tenant_id: UUID
    slug: str
    title: dict[str, str]
    description_md: dict[str, str]
    is_featured: bool
    sort_order: int
    created_at: datetime


@dataclass(slots=True, frozen=True)
class TourDraft:
    """Input bundle for creating a new tour."""

    tenant_id: UUID
    slug: str
    title: dict[str, str]
    kind: TourKind
    description_md: dict[str, str] = field(default_factory=dict)
    heritage_id: UUID | None = None
    thumbnail_media_id: UUID | None = None
    tour_duration_seconds: int | None = None
    viewer_url: str | None = None
    embed_code: str | None = None
    status: TourStatus = TourStatus.DRAFT


@dataclass(slots=True, frozen=True)
class TourUpdate:
    """Partial-update bundle for PATCH."""

    title: dict[str, str] | None = None
    description_md: dict[str, str] | None = None
    kind: TourKind | None = None
    tour_duration_seconds: int | None = None
    viewer_url: str | None = None
    embed_code: str | None = None
    thumbnail_media_id: UUID | None = None
    set_fields: frozenset[str] = field(default_factory=frozenset)

    def has(self, name: str) -> bool:
        return name in self.set_fields


@dataclass(slots=True, frozen=True)
class TourPage:
    items: tuple[VirtualTour, ...]
    total: int
    limit: int
    offset: int
