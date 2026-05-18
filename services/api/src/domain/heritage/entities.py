"""Heritage domain entities — pure Python, framework-free.

Mirrors the schema introduced in migrations 0010 + 0011. The denormalized
fields (name, summary, etc.) come from ``heritage_objects``; the granular
provenance system (``heritage_facts``, ``fact_provenance``) is not exposed
on the read entity until a later FAZA adds the fact-resolver job.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID


class HeritageStatus(StrEnum):
    DRAFT = "draft"
    REVIEW = "review"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class AliasKind(StrEnum):
    HISTORICAL = "historical"
    TRANSLITERATION = "transliteration"
    COLLOQUIAL = "colloquial"
    OFFICIAL = "official"
    MISSPELLING = "misspelling"


@dataclass(slots=True, frozen=True)
class HeritageObject:
    id: UUID
    tenant_id: UUID
    pub_id: str
    kind_slug: str
    name: dict[str, str]
    summary_md: dict[str, str]
    description_md: dict[str, str]
    tags: tuple[str, ...]
    status: HeritageStatus
    confidence_score: int
    revision: int
    created_at: datetime
    updated_at: datetime
    country_code: str | None = None
    admin_path: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    elevation_m: Decimal | None = None
    period_start_year: int | None = None
    period_end_year: int | None = None
    unesco_inscription_year: int | None = None
    hero_media_id: UUID | None = None
    created_by: UUID | None = None
    updated_by: UUID | None = None
    deleted_at: datetime | None = None


@dataclass(slots=True, frozen=True)
class HeritageAlias:
    id: UUID
    heritage_id: UUID
    alias: str
    language_tag: str
    kind: AliasKind
    confidence: int
    script: str | None = None
    source: str | None = None
    created_at: datetime | None = None


@dataclass(slots=True, frozen=True)
class HeritageDraft:
    """Input bundle for creating a new heritage object."""

    tenant_id: UUID
    kind_slug: str
    name: dict[str, str]
    summary_md: dict[str, str] = field(default_factory=dict)
    description_md: dict[str, str] = field(default_factory=dict)
    tags: tuple[str, ...] = field(default_factory=tuple)
    country_code: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    period_start_year: int | None = None
    period_end_year: int | None = None
    unesco_inscription_year: int | None = None
    status: HeritageStatus = HeritageStatus.DRAFT
    aliases: tuple[HeritageAlias, ...] = field(default_factory=tuple)


@dataclass(slots=True, frozen=True)
class HeritagePage:
    """Pageable result envelope."""

    items: tuple[HeritageObject, ...]
    total: int
    limit: int
    offset: int


@dataclass(slots=True, frozen=True)
class HeritageFilters:
    """Query-side filters; None means no constraint."""

    kind_slug: str | None = None
    country_code: str | None = None
    status: HeritageStatus | None = None
    search: str | None = None
    limit: int = 20
    offset: int = 0

    def normalised(self) -> HeritageFilters:
        return HeritageFilters(
            kind_slug=self.kind_slug,
            country_code=self.country_code.upper() if self.country_code else None,
            status=self.status,
            search=self.search.strip() if self.search else None,
            limit=max(1, min(self.limit, 100)),
            offset=max(0, self.offset),
        )


@dataclass(slots=True, frozen=True)
class HeritageEvent:
    """Outbound domain event tied to a heritage mutation."""

    name: str
    aggregate_id: UUID
    payload: dict[str, Any]
