"""Heritage application service.

Coordinates the repository, generates pub_ids, enforces validation rules that
the schema can't (e.g. the kind_slug must be a registered controlled-vocabulary
term, not an arbitrary string).
"""

from __future__ import annotations

import secrets
from uuid import UUID

from src.domain.heritage.entities import (
    HeritageAlias,
    HeritageAliasDraft,
    HeritageDraft,
    HeritageFilters,
    HeritageObject,
    HeritagePage,
    HeritageRevisionPage,
    HeritageStatus,
    HeritageUpdate,
    StatusTransitionAction,
)
from src.domain.heritage.errors import (
    DuplicatePubId,
    HeritageAlreadyDeleted,
    HeritageNotFound,
    HeritageValidationError,
    InvalidHeritageKind,
    InvalidStatusTransition,
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


def _validate_update(update: HeritageUpdate) -> None:
    if (
        update.has("latitude")
        and update.latitude is not None
        and (update.latitude < -90 or update.latitude > 90)
    ):
        raise HeritageValidationError("latitude", "must be between -90 and 90")
    if (
        update.has("longitude")
        and update.longitude is not None
        and (update.longitude < -180 or update.longitude > 180)
    ):
        raise HeritageValidationError("longitude", "must be between -180 and 180")
    if (
        update.has("period_start_year")
        and update.has("period_end_year")
        and update.period_start_year is not None
        and update.period_end_year is not None
        and update.period_end_year < update.period_start_year
    ):
        raise HeritageValidationError("period_end_year", "must be ≥ period_start_year")


# State machine for moderation. Keys are (current_status, action) → next_status.
# Permission-side checks (heritage:update / heritage:moderate / heritage:delete)
# live in the router layer; here we only enforce structural validity.
_TRANSITIONS: dict[tuple[HeritageStatus, StatusTransitionAction], HeritageStatus] = {
    (HeritageStatus.DRAFT, StatusTransitionAction.SUBMIT_REVIEW): HeritageStatus.REVIEW,
    (HeritageStatus.REVIEW, StatusTransitionAction.APPROVE): HeritageStatus.PUBLISHED,
    (HeritageStatus.REVIEW, StatusTransitionAction.REJECT): HeritageStatus.DRAFT,
    (HeritageStatus.DRAFT, StatusTransitionAction.ARCHIVE): HeritageStatus.ARCHIVED,
    (HeritageStatus.REVIEW, StatusTransitionAction.ARCHIVE): HeritageStatus.ARCHIVED,
    (HeritageStatus.PUBLISHED, StatusTransitionAction.ARCHIVE): HeritageStatus.ARCHIVED,
}


def required_permission(action: StatusTransitionAction) -> str:
    """Permission required for each moderation action."""
    if action is StatusTransitionAction.SUBMIT_REVIEW:
        return "heritage:update"
    if action in (StatusTransitionAction.APPROVE, StatusTransitionAction.REJECT):
        return "heritage:moderate"
    return "heritage:delete"  # ARCHIVE


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

    async def update(
        self,
        *,
        pub_id: str,
        update: HeritageUpdate,
        updated_by: UUID,
    ) -> HeritageObject:
        existing = await self.get(pub_id)
        _validate_update(update)
        if update.has("name") and update.name is not None:
            merged = {**existing.name, **update.name}
            if not merged:
                raise HeritageValidationError("name", "at least one language entry required")
            if "en" not in merged and "uz" not in merged:
                raise HeritageValidationError("name", "must include either 'en' or 'uz'")
        return await self._repo.update(existing=existing, update=update, updated_by=updated_by)

    async def soft_delete(self, *, pub_id: str, deleted_by: UUID) -> HeritageObject:
        existing = await self._repo.get_by_pub_id(pub_id)
        if existing is None:
            raise HeritageNotFound(pub_id)
        if existing.deleted_at is not None:
            raise HeritageAlreadyDeleted(pub_id)
        return await self._repo.soft_delete(existing=existing, deleted_by=deleted_by)

    async def add_alias(
        self,
        *,
        pub_id: str,
        draft: HeritageAliasDraft,
        actor: UUID,
    ) -> HeritageAlias:
        existing = await self.get(pub_id)
        if not draft.alias.strip():
            raise HeritageValidationError("alias", "must not be empty")
        return await self._repo.add_alias(
            heritage_id=existing.id,
            tenant_id=existing.tenant_id,
            draft=draft,
            actor=actor,
        )

    async def list_revisions(
        self,
        *,
        pub_id: str,
        limit: int,
        offset: int,
    ) -> HeritageRevisionPage:
        existing = await self._repo.get_by_pub_id(pub_id)
        if existing is None:
            raise HeritageNotFound(pub_id)
        return await self._repo.list_revisions(
            heritage_id=existing.id,
            limit=max(1, min(limit, 100)),
            offset=max(0, offset),
        )

    async def transition_status(
        self,
        *,
        pub_id: str,
        action: StatusTransitionAction,
        actor: UUID,
    ) -> HeritageObject:
        existing = await self.get(pub_id)
        key = (existing.status, action)
        if key not in _TRANSITIONS:
            raise InvalidStatusTransition(existing.status.value, action.value)
        new_status = _TRANSITIONS[key]
        return await self._repo.transition_status(
            existing=existing,
            new_status=new_status.value,
            actor=actor,
        )
