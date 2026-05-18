"""Heritage repository protocol — interface only."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.domain.heritage.entities import (
    HeritageDraft,
    HeritageFilters,
    HeritageObject,
    HeritagePage,
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
