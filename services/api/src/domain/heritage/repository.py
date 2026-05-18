"""Heritage repository protocol — interface only."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.domain.heritage.entities import (
    HeritageAlias,
    HeritageAliasDraft,
    HeritageDraft,
    HeritageFilters,
    HeritageObject,
    HeritagePage,
    HeritageRevisionPage,
    HeritageUpdate,
)


class HeritageRepository(Protocol):
    async def get_by_pub_id(self, pub_id: str) -> HeritageObject | None: ...

    async def get_by_id(self, heritage_id: UUID) -> HeritageObject | None: ...

    async def list_page(self, filters: HeritageFilters) -> HeritagePage: ...

    async def pub_id_exists(self, pub_id: str) -> bool: ...

    async def kind_exists(self, kind_slug: str) -> bool: ...

    async def create(
        self,
        *,
        draft: HeritageDraft,
        pub_id: str,
        created_by: UUID,
    ) -> HeritageObject: ...

    async def update(
        self,
        *,
        existing: HeritageObject,
        update: HeritageUpdate,
        updated_by: UUID,
    ) -> HeritageObject: ...

    async def soft_delete(
        self,
        *,
        existing: HeritageObject,
        deleted_by: UUID,
    ) -> HeritageObject: ...

    async def add_alias(
        self,
        *,
        heritage_id: UUID,
        tenant_id: UUID,
        draft: HeritageAliasDraft,
        actor: UUID,
    ) -> HeritageAlias: ...

    async def list_revisions(
        self,
        *,
        heritage_id: UUID,
        limit: int,
        offset: int,
    ) -> HeritageRevisionPage: ...

    async def transition_status(
        self,
        *,
        existing: HeritageObject,
        new_status: str,
        actor: UUID,
    ) -> HeritageObject: ...
