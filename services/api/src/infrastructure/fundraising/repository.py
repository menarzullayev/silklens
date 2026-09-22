"""SQLAlchemy-backed implementation of ``FundraisingRepository``.

Hand-written SQL — migration 0092 owns the canonical schema.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.fundraising.entities import (
    AccessLevel,
    Commitment,
    CommitmentStatus,
    DataRoomAccessGrant,
    DataRoomDocument,
    DocumentCategory,
    FundraisingRound,
    InvestorKind,
    InvestorProfile,
    InvestorProfileDraft,
    InvestorStatus,
    KpiSnapshot,
    KpiSnapshotStats,
    RoundDraft,
    RoundKind,
    RoundStatus,
)
from src.domain.fundraising.errors import DuplicateCommitment


def _row_to_investor(row: object) -> InvestorProfile:
    m = row._mapping  # type: ignore[attr-defined]
    return InvestorProfile(
        id=m["id"],
        tenant_id=m["tenant_id"],
        name=m["name"],
        firm_name=m["firm_name"],
        kind=InvestorKind(m["kind"]),
        region=m["region"],
        status=InvestorStatus(m["status"]),
        thesis_md=m.get("thesis_md"),
        min_check_size_usd=m.get("min_check_size_usd"),
        max_check_size_usd=m.get("max_check_size_usd"),
        contacted_at=m.get("contacted_at"),
        nda_signed_at=m.get("nda_signed_at"),
        created_at=m["created_at"],
        updated_at=m["updated_at"],
    )


def _row_to_round(row: object) -> FundraisingRound:
    m = row._mapping  # type: ignore[attr-defined]
    return FundraisingRound(
        id=m["id"],
        tenant_id=m["tenant_id"],
        round_name=m["round_name"],
        target_raise_usd=Decimal(str(m["target_raise_usd"])),
        round_kind=RoundKind(m["round_kind"]),
        status=RoundStatus(m["status"]),
        raised_usd=Decimal(str(m["raised_usd"])),
        valuation_cap_usd=Decimal(str(m["valuation_cap_usd"]))
        if m.get("valuation_cap_usd")
        else None,
        discount_pct=Decimal(str(m["discount_pct"])) if m.get("discount_pct") else None,
        opened_at=m.get("opened_at"),
        closed_at=m.get("closed_at"),
        created_at=m["created_at"],
    )


def _row_to_commitment(row: object) -> Commitment:
    m = row._mapping  # type: ignore[attr-defined]
    return Commitment(
        id=m["id"],
        investor_id=m["investor_id"],
        round_id=m["round_id"],
        committed_usd=Decimal(str(m["committed_usd"])),
        actual_usd=Decimal(str(m["actual_usd"])) if m.get("actual_usd") else None,
        status=CommitmentStatus(m["status"]),
        signed_at=m.get("signed_at"),
        wired_at=m.get("wired_at"),
        created_at=m["created_at"],
    )


def _row_to_document(row: object) -> DataRoomDocument:
    m = row._mapping  # type: ignore[attr-defined]
    return DataRoomDocument(
        id=m["id"],
        tenant_id=m["tenant_id"],
        name=m["name"],
        description_md=m.get("description_md"),
        category=DocumentCategory(m["category"]),
        version=m["version"],
        doc_url=m["doc_url"],
        access_level=AccessLevel(m["access_level"]),
        is_current=bool(m["is_current"]),
        uploaded_at=m["uploaded_at"],
        expires_at=m.get("expires_at"),
    )


def _row_to_grant(row: object) -> DataRoomAccessGrant:
    m = row._mapping  # type: ignore[attr-defined]
    return DataRoomAccessGrant(
        investor_id=m["investor_id"],
        document_id=m["document_id"],
        granted_by=m["granted_by"],
        granted_at=m["granted_at"],
        expires_at=m.get("expires_at"),
        revoked_at=m.get("revoked_at"),
        accessed_at=m.get("accessed_at"),
    )


def _row_to_kpi(row: object) -> KpiSnapshot:
    m = row._mapping  # type: ignore[attr-defined]
    return KpiSnapshot(
        id=m["id"],
        tenant_id=m["tenant_id"],
        snapshot_date=m["snapshot_date"],
        mau=int(m["mau"]),
        dau=int(m["dau"]),
        paying_users=int(m["paying_users"]),
        mrr_usd=Decimal(str(m["mrr_usd"])),
        arr_usd=Decimal(str(m["arr_usd"])),
        heritage_count=int(m["heritage_count"]),
        countries_count=int(m["countries_count"]),
        nps_score=Decimal(str(m["nps_score"])) if m.get("nps_score") is not None else None,
        churn_rate_pct=Decimal(str(m["churn_rate_pct"]))
        if m.get("churn_rate_pct") is not None
        else None,
        ltv_usd=Decimal(str(m["ltv_usd"])) if m.get("ltv_usd") is not None else None,
        cac_usd=Decimal(str(m["cac_usd"])) if m.get("cac_usd") is not None else None,
        created_at=m["created_at"],
    )


class SqlFundraisingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    # -----------------------------------------------------------------------
    # Investors
    # -----------------------------------------------------------------------

    async def list_investors(
        self, tenant_id: UUID, status: InvestorStatus | None = None
    ) -> list[InvestorProfile]:
        sql = "SELECT * FROM investor_profiles WHERE tenant_id = :tid"
        params: dict[str, Any] = {"tid": str(tenant_id)}
        if status is not None:
            sql += " AND status = :status"
            params["status"] = status.value
        sql += " ORDER BY created_at DESC"
        result = await self._s.execute(text(sql), params)
        return [_row_to_investor(r) for r in result.fetchall()]

    async def get_investor(self, investor_id: UUID) -> InvestorProfile | None:
        result = await self._s.execute(
            text("SELECT * FROM investor_profiles WHERE id = :id"),
            {"id": str(investor_id)},
        )
        row = result.fetchone()
        return _row_to_investor(row) if row else None

    async def create_investor(
        self, tenant_id: UUID, draft: InvestorProfileDraft
    ) -> InvestorProfile:
        result = await self._s.execute(
            text(
                """
                INSERT INTO investor_profiles (
                    tenant_id, name, firm_name, kind, region,
                    thesis_md, min_check_size_usd, max_check_size_usd
                ) VALUES (
                    :tenant_id, :name, :firm_name, :kind, :region,
                    :thesis_md, :min_check, :max_check
                )
                RETURNING *
                """
            ),
            {
                "tenant_id": str(tenant_id),
                "name": draft.name,
                "firm_name": draft.firm_name,
                "kind": draft.kind.value,
                "region": draft.region,
                "thesis_md": draft.thesis_md,
                "min_check": str(draft.min_check_size_usd) if draft.min_check_size_usd else None,
                "max_check": str(draft.max_check_size_usd) if draft.max_check_size_usd else None,
            },
        )
        return _row_to_investor(result.fetchone())

    async def update_investor_status(
        self, investor_id: UUID, status: InvestorStatus
    ) -> InvestorProfile:
        extra: dict[str, Any] = {}
        if status == InvestorStatus.CONTACTED:
            extra["contacted_at"] = "now()"
        if status == InvestorStatus.NDA_SIGNED:
            extra["nda_signed_at"] = "now()"

        set_clause = "status = :status, updated_at = now()"
        params: dict[str, Any] = {"status": status.value, "id": str(investor_id)}

        if "contacted_at" in extra:
            set_clause += ", contacted_at = now()"
        if "nda_signed_at" in extra:
            set_clause += ", nda_signed_at = now()"

        result = await self._s.execute(
            text(f"UPDATE investor_profiles SET {set_clause} WHERE id = :id RETURNING *"),  # noqa: S608
            params,
        )
        return _row_to_investor(result.fetchone())

    # -----------------------------------------------------------------------
    # Rounds
    # -----------------------------------------------------------------------

    async def list_rounds(self, tenant_id: UUID) -> list[FundraisingRound]:
        result = await self._s.execute(
            text(
                "SELECT * FROM fundraising_rounds WHERE tenant_id = :tid ORDER BY created_at DESC"
            ),
            {"tid": str(tenant_id)},
        )
        return [_row_to_round(r) for r in result.fetchall()]

    async def create_round(self, tenant_id: UUID, draft: RoundDraft) -> FundraisingRound:
        result = await self._s.execute(
            text(
                """
                INSERT INTO fundraising_rounds (
                    tenant_id, round_name, target_raise_usd, valuation_cap_usd,
                    discount_pct, round_kind
                ) VALUES (
                    :tenant_id, :round_name, :target_raise_usd, :valuation_cap_usd,
                    :discount_pct, :round_kind
                )
                RETURNING *
                """
            ),
            {
                "tenant_id": str(tenant_id),
                "round_name": draft.round_name,
                "target_raise_usd": str(draft.target_raise_usd),
                "valuation_cap_usd": str(draft.valuation_cap_usd)
                if draft.valuation_cap_usd
                else None,
                "discount_pct": str(draft.discount_pct) if draft.discount_pct else None,
                "round_kind": draft.round_kind.value,
            },
        )
        return _row_to_round(result.fetchone())

    # -----------------------------------------------------------------------
    # Commitments
    # -----------------------------------------------------------------------

    async def create_commitment(
        self,
        investor_id: UUID,
        round_id: UUID,
        committed_usd: Decimal,
    ) -> Commitment:
        try:
            result = await self._s.execute(
                text(
                    """
                    INSERT INTO investor_commitments (investor_id, round_id, committed_usd)
                    VALUES (:investor_id, :round_id, :committed_usd)
                    RETURNING *
                    """
                ),
                {
                    "investor_id": str(investor_id),
                    "round_id": str(round_id),
                    "committed_usd": str(committed_usd),
                },
            )
        except IntegrityError as exc:
            if "uq_commitment_investor_round" in str(exc.orig):
                raise DuplicateCommitment(investor_id, round_id) from exc
            raise
        return _row_to_commitment(result.fetchone())

    # -----------------------------------------------------------------------
    # Data room
    # -----------------------------------------------------------------------

    async def list_documents(
        self, tenant_id: UUID, access_level: AccessLevel | None = None
    ) -> list[DataRoomDocument]:
        sql = "SELECT * FROM data_room_documents WHERE tenant_id = :tid AND is_current = true"
        params: dict[str, Any] = {"tid": str(tenant_id)}
        if access_level is not None:
            sql += " AND access_level = :access_level"
            params["access_level"] = access_level.value
        sql += " ORDER BY uploaded_at DESC"
        result = await self._s.execute(text(sql), params)
        return [_row_to_document(r) for r in result.fetchall()]

    async def get_document(self, document_id: UUID) -> DataRoomDocument | None:
        result = await self._s.execute(
            text("SELECT * FROM data_room_documents WHERE id = :id"),
            {"id": str(document_id)},
        )
        row = result.fetchone()
        return _row_to_document(row) if row else None

    async def grant_access(
        self,
        investor_id: UUID,
        document_id: UUID,
        granted_by: UUID,
        expires_at: object | None,
    ) -> DataRoomAccessGrant:
        result = await self._s.execute(
            text(
                """
                INSERT INTO data_room_access_grants (investor_id, document_id, granted_by, expires_at)
                VALUES (:investor_id, :document_id, :granted_by, :expires_at)
                ON CONFLICT (investor_id, document_id) DO UPDATE
                  SET granted_by = EXCLUDED.granted_by,
                      granted_at = now(),
                      expires_at = EXCLUDED.expires_at,
                      revoked_at = NULL
                RETURNING *
                """  # noqa: E501
            ),
            {
                "investor_id": str(investor_id),
                "document_id": str(document_id),
                "granted_by": str(granted_by),
                "expires_at": expires_at,
            },
        )
        return _row_to_grant(result.fetchone())

    # -----------------------------------------------------------------------
    # KPI
    # -----------------------------------------------------------------------

    async def latest_kpi(self, tenant_id: UUID) -> KpiSnapshot | None:
        result = await self._s.execute(
            text(
                "SELECT * FROM kpi_snapshots WHERE tenant_id = :tid "
                "ORDER BY snapshot_date DESC LIMIT 1"
            ),
            {"tid": str(tenant_id)},
        )
        row = result.fetchone()
        return _row_to_kpi(row) if row else None

    async def list_kpi(self, tenant_id: UUID, limit: int = 12) -> list[KpiSnapshot]:
        result = await self._s.execute(
            text(
                "SELECT * FROM kpi_snapshots WHERE tenant_id = :tid "
                "ORDER BY snapshot_date DESC LIMIT :lim"
            ),
            {"tid": str(tenant_id), "lim": limit},
        )
        return [_row_to_kpi(r) for r in result.fetchall()]

    async def upsert_kpi(self, tenant_id: UUID, stats: KpiSnapshotStats) -> KpiSnapshot:
        result = await self._s.execute(
            text(
                """
                INSERT INTO kpi_snapshots (
                    tenant_id, snapshot_date, mau, dau, paying_users,
                    mrr_usd, arr_usd, heritage_count, countries_count,
                    nps_score, churn_rate_pct, ltv_usd, cac_usd
                ) VALUES (
                    :tenant_id, :snapshot_date, :mau, :dau, :paying_users,
                    :mrr_usd, :arr_usd, :heritage_count, :countries_count,
                    :nps_score, :churn_rate_pct, :ltv_usd, :cac_usd
                )
                ON CONFLICT (snapshot_date) DO UPDATE SET
                    mau = EXCLUDED.mau,
                    dau = EXCLUDED.dau,
                    paying_users = EXCLUDED.paying_users,
                    mrr_usd = EXCLUDED.mrr_usd,
                    arr_usd = EXCLUDED.arr_usd,
                    heritage_count = EXCLUDED.heritage_count,
                    countries_count = EXCLUDED.countries_count,
                    nps_score = EXCLUDED.nps_score,
                    churn_rate_pct = EXCLUDED.churn_rate_pct,
                    ltv_usd = EXCLUDED.ltv_usd,
                    cac_usd = EXCLUDED.cac_usd
                RETURNING *
                """
            ),
            {
                "tenant_id": str(tenant_id),
                "snapshot_date": str(stats.snapshot_date),
                "mau": stats.mau,
                "dau": stats.dau,
                "paying_users": stats.paying_users,
                "mrr_usd": str(stats.mrr_usd),
                "arr_usd": str(stats.arr_usd),
                "heritage_count": stats.heritage_count,
                "countries_count": stats.countries_count,
                "nps_score": str(stats.nps_score) if stats.nps_score is not None else None,
                "churn_rate_pct": str(stats.churn_rate_pct) if stats.churn_rate_pct else None,
                "ltv_usd": str(stats.ltv_usd) if stats.ltv_usd else None,
                "cac_usd": str(stats.cac_usd) if stats.cac_usd else None,
            },
        )
        return _row_to_kpi(result.fetchone())
