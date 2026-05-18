"""Heritage application service.

Coordinates the repository, generates pub_ids, enforces validation rules that
the schema can't (e.g. the kind_slug must be a registered controlled-vocabulary
term, not an arbitrary string).
"""

from __future__ import annotations

import secrets
from uuid import UUID

from src.domain.heritage.entities import (
    HeritageDraft,
    HeritageFilters,
    HeritageObject,
    HeritagePage,
)
from src.domain.heritage.errors import (
    DuplicatePubId,
    HeritageNotFound,
    HeritageValidationError,
    InvalidHeritageKind,
)
from src.domain.heritage.repository import HeritageRepository


def _generate_pub_id() -> str:
    """URL-safe 10-char id (matches heritage_objects.pub_id ^[a-zA-Z0-9_-]{6,32}$)."""
    raw = secrets.token_urlsafe(8)
    return raw[:10]


def _validate_draft(draft: HeritageDraft) -> None:
    if not draft.name:
        raise HeritageValidationError("name", "at least one language entry required")
    if "en" not in draft.name and "uz" not in draft.name:
        # We always require English OR Uzbek as a baseline so other-language
        # consumers have a fallback to translate from.
        raise HeritageValidationError("name", "must include either 'en' or 'uz'")
    if draft.latitude is not None and (draft.latitude < -90 or draft.latitude > 90):
        raise HeritageValidationError("latitude", "must be between -90 and 90")
    if draft.longitude is not None and (draft.longitude < -180 or draft.longitude > 180):
        raise HeritageValidationError("longitude", "must be between -180 and 180")
    if (
        draft.period_end_year is not None
        and draft.period_start_year is not None
        and draft.period_end_year < draft.period_start_year
    ):
        raise HeritageValidationError("period_end_year", "must be ≥ period_start_year")


class HeritageService:
    def __init__(self, *, repository: HeritageRepository) -> None:
        self._repo = repository

    async def list(self, filters: HeritageFilters) -> HeritagePage:
        return await self._repo.list_page(filters.normalised())

    async def get(self, pub_id: str) -> HeritageObject:
        item = await self._repo.get_by_pub_id(pub_id)
        if item is None or item.deleted_at is not None:
            raise HeritageNotFound(pub_id)
        return item

    async def create(self, draft: HeritageDraft, *, created_by: UUID) -> HeritageObject:
        _validate_draft(draft)
        if not await self._repo.kind_exists(draft.kind_slug):
            raise InvalidHeritageKind(draft.kind_slug)

        # Retry up to 5 times on pub_id collisions (extremely unlikely with 10
        # base62 chars, but cheap to handle).
        for _ in range(5):
            candidate = _generate_pub_id()
            if not await self._repo.pub_id_exists(candidate):
                return await self._repo.create(draft=draft, pub_id=candidate, created_by=created_by)
        raise DuplicatePubId("could not allocate a unique pub_id")
