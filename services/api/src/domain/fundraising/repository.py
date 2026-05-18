"""Fundraising repository protocol — pure interface, no I/O."""

from __future__ import annotations

from decimal import Decimal
from typing import Protocol
from uuid import UUID

from src.domain.fundraising.entities import (
    AccessLevel,
    Commitment,
    DataRoomAccessGrant,
    DataRoomDocument,
    FundraisingRound,
    InvestorProfile,
    InvestorProfileDraft,
    InvestorStatus,
    KpiSnapshot,
    KpiSnapshotStats,
    RoundDraft,
)


class FundraisingRepository(Protocol):
    # --- Investors ---
    async def list_investors(
        self, tenant_id: UUID, status: InvestorStatus | None = None
    ) -> list[InvestorProfile]: ...

    async def get_investor(self, investor_id: UUID) -> InvestorProfile | None: ...

    async def create_investor(
        self, tenant_id: UUID, draft: InvestorProfileDraft
    ) -> InvestorProfile: ...

    async def update_investor_status(
        self, investor_id: UUID, status: InvestorStatus
    ) -> InvestorProfile: ...

    # --- Rounds ---
    async def list_rounds(self, tenant_id: UUID) -> list[FundraisingRound]: ...

    async def create_round(self, tenant_id: UUID, draft: RoundDraft) -> FundraisingRound: ...

    # --- Commitments ---
    async def create_commitment(
        self,
        investor_id: UUID,
        round_id: UUID,
        committed_usd: Decimal,
    ) -> Commitment: ...

    # --- Data room ---
    async def list_documents(
        self, tenant_id: UUID, access_level: AccessLevel | None = None
    ) -> list[DataRoomDocument]: ...

    async def get_document(self, document_id: UUID) -> DataRoomDocument | None: ...

    async def grant_access(
        self,
        investor_id: UUID,
        document_id: UUID,
        granted_by: UUID,
        expires_at: object | None,
    ) -> DataRoomAccessGrant: ...

    # --- KPI ---
    async def latest_kpi(self, tenant_id: UUID) -> KpiSnapshot | None: ...

    async def list_kpi(self, tenant_id: UUID, limit: int = 12) -> list[KpiSnapshot]: ...

    async def upsert_kpi(self, tenant_id: UUID, stats: KpiSnapshotStats) -> KpiSnapshot: ...
