"""Fundraising service — orchestration layer for investor-relations logic.

All methods are async and accept a repository injected at the call site so
the service remains testable with in-memory fakes.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
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
from src.domain.fundraising.errors import (
    DocumentNotFound,
    InvestorNotFound,
    RoundNotFound,
)
from src.domain.fundraising.repository import FundraisingRepository


class FundraisingService:
    """High-level fundraising operations."""

    def __init__(self, repo: FundraisingRepository, tenant_id: UUID) -> None:
        self._repo = repo
        self._tenant_id = tenant_id

    # -----------------------------------------------------------------------
    # Traction / public dashboard
    # -----------------------------------------------------------------------

    async def get_traction_summary(self) -> dict:
        """Return curated traction metrics for the public investor page.

        Reads the two most recent KPI snapshots and computes a simple
        month-over-month growth estimate for MAU (presented as an annualised
        percentage for investor storytelling purposes).
        """
        snapshots = await self._repo.list_kpi(self._tenant_id, limit=2)
        if not snapshots:
            return {
                "mau": 0,
                "dau": 0,
                "paying_users": 0,
                "mrr_usd": "0.00",
                "arr_usd": "0.00",
                "heritage_count": 0,
                "countries_count": 0,
                "nps_score": None,
                "mom_mau_growth_pct": None,
                "yoy_growth_est_pct": None,
                "snapshot_date": None,
            }

        latest = snapshots[0]
        prev = snapshots[1] if len(snapshots) > 1 else None

        mom_growth: float | None = None
        yoy_est: float | None = None
        if prev and prev.mau and prev.mau > 0:
            mom_growth = round((latest.mau - prev.mau) / prev.mau * 100, 1)
            # Annualise MoM as a rough YoY estimate (compounding)
            yoy_est = round(((1 + mom_growth / 100) ** 12 - 1) * 100, 1)

        return {
            "mau": latest.mau,
            "dau": latest.dau,
            "paying_users": latest.paying_users,
            "mrr_usd": str(latest.mrr_usd),
            "arr_usd": str(latest.arr_usd),
            "heritage_count": latest.heritage_count,
            "countries_count": latest.countries_count,
            "nps_score": float(latest.nps_score) if latest.nps_score is not None else None,
            "mom_mau_growth_pct": mom_growth,
            "yoy_growth_est_pct": yoy_est,
            "snapshot_date": str(latest.snapshot_date),
        }

    # -----------------------------------------------------------------------
    # Investor management (admin)
    # -----------------------------------------------------------------------

    async def list_investors(self, status: InvestorStatus | None = None) -> list[InvestorProfile]:
        return await self._repo.list_investors(self._tenant_id, status=status)

    async def create_investor(
        self,
        name: str,
        firm_name: str,
        kind: str,
        actor: UUID,
        *,
        region: str = "global",
        thesis_md: str | None = None,
        min_check_size_usd: Decimal | None = None,
        max_check_size_usd: Decimal | None = None,
    ) -> InvestorProfile:
        from src.domain.fundraising.entities import InvestorKind

        draft = InvestorProfileDraft(
            name=name,
            firm_name=firm_name,
            kind=InvestorKind(kind),
            region=region,
            thesis_md=thesis_md,
            min_check_size_usd=min_check_size_usd,
            max_check_size_usd=max_check_size_usd,
        )
        return await self._repo.create_investor(self._tenant_id, draft)

    async def update_investor_status(
        self,
        investor_id: UUID,
        status: str,
        actor: UUID,
    ) -> InvestorProfile:
        investor = await self._repo.get_investor(investor_id)
        if investor is None:
            raise InvestorNotFound(investor_id)
        return await self._repo.update_investor_status(investor_id, InvestorStatus(status))

    # -----------------------------------------------------------------------
    # Fundraising rounds (admin)
    # -----------------------------------------------------------------------

    async def list_rounds(self) -> list[FundraisingRound]:
        return await self._repo.list_rounds(self._tenant_id)

    async def create_round(
        self,
        round_name: str,
        target_raise_usd: Decimal,
        round_kind: str = "safe",
        valuation_cap_usd: Decimal | None = None,
        discount_pct: Decimal | None = None,
    ) -> FundraisingRound:
        from src.domain.fundraising.entities import RoundKind

        draft = RoundDraft(
            round_name=round_name,
            target_raise_usd=target_raise_usd,
            round_kind=RoundKind(round_kind),
            valuation_cap_usd=valuation_cap_usd,
            discount_pct=discount_pct,
        )
        return await self._repo.create_round(self._tenant_id, draft)

    # -----------------------------------------------------------------------
    # Commitments
    # -----------------------------------------------------------------------

    async def create_commitment(
        self,
        investor_id: UUID,
        round_id: UUID,
        committed_usd: Decimal,
    ) -> Commitment:
        investor = await self._repo.get_investor(investor_id)
        if investor is None:
            raise InvestorNotFound(investor_id)
        rounds = await self._repo.list_rounds(self._tenant_id)
        round_ids = {r.id for r in rounds}
        if round_id not in round_ids:
            raise RoundNotFound(round_id)
        return await self._repo.create_commitment(investor_id, round_id, committed_usd)

    # -----------------------------------------------------------------------
    # Data room
    # -----------------------------------------------------------------------

    async def list_documents(self, access_level: str = "public_teaser") -> list[DataRoomDocument]:
        return await self._repo.list_documents(
            self._tenant_id, access_level=AccessLevel(access_level)
        )

    async def grant_access(
        self,
        investor_id: UUID,
        document_id: UUID,
        actor: UUID,
        days: int | None = None,
    ) -> DataRoomAccessGrant:
        investor = await self._repo.get_investor(investor_id)
        if investor is None:
            raise InvestorNotFound(investor_id)
        doc = await self._repo.get_document(document_id)
        if doc is None:
            raise DocumentNotFound(document_id)

        expires_at = datetime.now(tz=UTC) + timedelta(days=days) if days is not None else None
        return await self._repo.grant_access(investor_id, document_id, actor, expires_at)

    # -----------------------------------------------------------------------
    # KPI snapshots (internal / Celery)
    # -----------------------------------------------------------------------

    async def record_kpi_snapshot(self, stats: KpiSnapshotStats) -> KpiSnapshot:
        return await self._repo.upsert_kpi(self._tenant_id, stats)
