"""Partnership application service.

Orchestrates agreement lifecycle, SLA report generation, uptime status
aggregation, and badge issuance. All heavy SQL lives in the repository;
this layer is pure domain logic + validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.partnership.entities import (
    AgreementStatus,
    BadgeKind,
    PartnerBadge,
    PartnerKind,
    PartnershipAgreement,
    SlaReport,
    UptimeStatus,
    UptimeWindow,
)
from src.domain.partnership.errors import (
    AgreementNotFound,
    BadgeAlreadyIssued,
    InvalidMouUrl,
    TierNotFound,
)


@dataclass
class AgreementDraft:
    partner_name: str
    partner_kind: PartnerKind
    tier_slug: str
    tenant_id: UUID
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    annual_value_usd: Decimal | None = None
    notes_md: str | None = None
    mou_url: str | None = None
    auto_renew: bool = False
    expires_at: datetime | None = None


class PartnershipService:
    """Domain service for partnership management."""

    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    # ------------------------------------------------------------------ #
    #  Public queries                                                      #
    # ------------------------------------------------------------------ #

    async def list_public_partners(self) -> list[PartnershipAgreement]:
        """Return active agreements — public, no auth required."""
        rows = await self._db.execute(
            text(
                """
                SELECT pa.id, pa.tenant_id, pa.partner_name, pa.partner_kind,
                       pa.tier_id, pa.status, pa.signed_at, pa.expires_at,
                       pa.auto_renew, pa.annual_value_usd,
                       pa.contact_name, pa.contact_email, pa.contact_phone,
                       pa.notes_md, pa.mou_url, pa.created_at, pa.updated_at,
                       pt.slug  AS tier_slug,
                       pt.name  AS tier_name,
                       pt.sla_uptime_pct AS tier_sla_uptime_pct
                FROM   partnership_agreements pa
                JOIN   partnership_tiers pt ON pt.id = pa.tier_id
                WHERE  pa.status = 'active'
                ORDER  BY pa.partner_name
                """
            )
        )
        return [self._row_to_agreement(r) for r in rows.mappings()]

    async def current_uptime_status(self) -> UptimeStatus:
        """Aggregate last-30d uptime_windows into a status dict."""
        since = datetime.now(tz=UTC) - timedelta(days=30)
        rows = await self._db.execute(
            text(
                """
                SELECT id, started_at, ended_at, kind, severity,
                       description_md, affected_services, is_resolved,
                       resolution_notes, created_at
                FROM   uptime_windows
                WHERE  started_at >= :since
                ORDER  BY started_at DESC
                """
            ),
            {"since": since},
        )
        windows = [self._row_to_window(r) for r in rows.mappings()]
        return self._compute_uptime_status(windows, since)

    # ------------------------------------------------------------------ #
    #  Admin queries                                                       #
    # ------------------------------------------------------------------ #

    async def list_agreements(
        self,
        status: AgreementStatus | None = None,
        kind: PartnerKind | None = None,
    ) -> list[PartnershipAgreement]:
        """Admin view — filterable by status and/or partner kind."""
        filters: list[str] = []
        params: dict[str, Any] = {}
        if status is not None:
            filters.append("pa.status = :status")
            params["status"] = status.value
        if kind is not None:
            filters.append("pa.partner_kind = :kind")
            params["kind"] = kind.value
        where = ("WHERE " + " AND ".join(filters)) if filters else ""
        rows = await self._db.execute(
            text(
                f"""
                SELECT pa.id, pa.tenant_id, pa.partner_name, pa.partner_kind,
                       pa.tier_id, pa.status, pa.signed_at, pa.expires_at,
                       pa.auto_renew, pa.annual_value_usd,
                       pa.contact_name, pa.contact_email, pa.contact_phone,
                       pa.notes_md, pa.mou_url, pa.created_at, pa.updated_at,
                       pt.slug  AS tier_slug,
                       pt.name  AS tier_name,
                       pt.sla_uptime_pct AS tier_sla_uptime_pct
                FROM   partnership_agreements pa
                JOIN   partnership_tiers pt ON pt.id = pa.tier_id
                {where}
                ORDER  BY pa.created_at DESC
                """  # noqa: S608
            ),
            params,
        )
        return [self._row_to_agreement(r) for r in rows.mappings()]

    async def get_agreement(self, agreement_id: UUID) -> PartnershipAgreement:
        row = await self._db.execute(
            text(
                """
                SELECT pa.id, pa.tenant_id, pa.partner_name, pa.partner_kind,
                       pa.tier_id, pa.status, pa.signed_at, pa.expires_at,
                       pa.auto_renew, pa.annual_value_usd,
                       pa.contact_name, pa.contact_email, pa.contact_phone,
                       pa.notes_md, pa.mou_url, pa.created_at, pa.updated_at,
                       pt.slug  AS tier_slug,
                       pt.name  AS tier_name,
                       pt.sla_uptime_pct AS tier_sla_uptime_pct
                FROM   partnership_agreements pa
                JOIN   partnership_tiers pt ON pt.id = pa.tier_id
                WHERE  pa.id = :aid
                """
            ),
            {"aid": agreement_id},
        )
        mapping = row.mappings().first()
        if mapping is None:
            raise AgreementNotFound(agreement_id)
        return self._row_to_agreement(mapping)

    # ------------------------------------------------------------------ #
    #  Mutations                                                           #
    # ------------------------------------------------------------------ #

    async def create_agreement(self, draft: AgreementDraft, actor: UUID) -> PartnershipAgreement:
        if draft.mou_url and not draft.mou_url.startswith("https://"):
            raise InvalidMouUrl(draft.mou_url)

        tier_row = await self._db.execute(
            text("SELECT id FROM partnership_tiers WHERE slug = :slug"),
            {"slug": draft.tier_slug},
        )
        tier = tier_row.mappings().first()
        if tier is None:
            raise TierNotFound(draft.tier_slug)

        result = await self._db.execute(
            text(
                """
                INSERT INTO partnership_agreements (
                    tenant_id, partner_name, partner_kind, tier_id, status,
                    auto_renew, annual_value_usd, contact_name, contact_email,
                    contact_phone, notes_md, mou_url, expires_at
                ) VALUES (
                    :tenant_id, :partner_name, :partner_kind, :tier_id, 'draft',
                    :auto_renew, :annual_value_usd, :contact_name, :contact_email,
                    :contact_phone, :notes_md, :mou_url, :expires_at
                )
                RETURNING id
                """
            ),
            {
                "tenant_id": draft.tenant_id,
                "partner_name": draft.partner_name,
                "partner_kind": draft.partner_kind.value,
                "tier_id": tier["id"],
                "auto_renew": draft.auto_renew,
                "annual_value_usd": draft.annual_value_usd,
                "contact_name": draft.contact_name,
                "contact_email": draft.contact_email,
                "contact_phone": draft.contact_phone,
                "notes_md": draft.notes_md,
                "mou_url": draft.mou_url,
                "expires_at": draft.expires_at,
            },
        )
        new_id = result.scalar_one()
        await self._db.commit()
        return await self.get_agreement(new_id)

    async def generate_sla_report(
        self,
        agreement_id: UUID,
        period_start: date,
        period_end: date,
    ) -> SlaReport:
        agreement = await self.get_agreement(agreement_id)  # noqa: F841

        # Count incidents during the period
        inc_result = await self._db.execute(
            text(
                """
                SELECT COUNT(*) FILTER (WHERE kind = 'incident')          AS incidents,
                       COUNT(*) FILTER (WHERE kind = 'incident'
                                          AND is_resolved = true)         AS resolved,
                       COALESCE(SUM(EXTRACT(EPOCH FROM (
                           COALESCE(ended_at, now()) - started_at
                       )) / 60.0)
                       FILTER (WHERE kind = 'incident'), 0)               AS total_outage_min
                FROM   uptime_windows
                WHERE  started_at::date BETWEEN :ps AND :pe
                """
            ),
            {"ps": period_start, "pe": period_end},
        )
        row = inc_result.mappings().first()
        incidents_count = int(row["incidents"]) if row else 0
        incidents_resolved = int(row["resolved"]) if row else 0
        outage_min = float(row["total_outage_min"]) if row else 0.0

        total_min = (period_end - period_start).days * 24 * 60
        measured_uptime = Decimal(
            max(0.0, min(100.0, (1.0 - outage_min / max(total_min, 1)) * 100.0))
        ).quantize(Decimal("0.01"))

        result = await self._db.execute(
            text(
                """
                INSERT INTO sla_reports (
                    agreement_id, period_start, period_end,
                    measured_uptime_pct, incidents_count,
                    incidents_resolved_in_sla, api_calls_total,
                    data_exports_count, generated_at
                ) VALUES (
                    :aid, :ps, :pe, :uptime, :inc, :resolved, 0, 0, now()
                )
                RETURNING id, generated_at, created_at
                """
            ),
            {
                "aid": agreement_id,
                "ps": period_start,
                "pe": period_end,
                "uptime": float(measured_uptime),
                "inc": incidents_count,
                "resolved": incidents_resolved,
            },
        )
        row2 = result.mappings().first()
        if row2 is None:
            raise RuntimeError("SlaReport INSERT returned no row")
        await self._db.commit()

        return SlaReport(
            id=row2["id"],
            agreement_id=agreement_id,
            period_start=period_start,
            period_end=period_end,
            measured_uptime_pct=measured_uptime,
            incidents_count=incidents_count,
            incidents_resolved_in_sla=incidents_resolved,
            api_calls_total=0,
            data_exports_count=0,
            generated_at=row2["generated_at"],
            created_at=row2["created_at"],
            report_url=None,
        )

    async def issue_badge(
        self,
        agreement_id: UUID,
        badge_kind: BadgeKind,
        actor: UUID,
    ) -> PartnerBadge:
        # Verify agreement exists
        await self.get_agreement(agreement_id)

        # Check for existing active badge of same kind
        existing = await self._db.execute(
            text(
                """
                SELECT id FROM partner_badges
                WHERE agreement_id = :aid AND badge_kind = :bk AND is_active = true
                """
            ),
            {"aid": agreement_id, "bk": badge_kind.value},
        )
        if existing.first() is not None:
            raise BadgeAlreadyIssued(agreement_id, badge_kind.value)

        result = await self._db.execute(
            text(
                """
                INSERT INTO partner_badges (agreement_id, badge_kind, display_on_heritage)
                VALUES (:aid, :bk, '[]'::jsonb)
                RETURNING id, issued_at, expires_at
                """
            ),
            {"aid": agreement_id, "bk": badge_kind.value},
        )
        row = result.mappings().first()
        if row is None:
            raise RuntimeError("PartnerBadge INSERT returned no row")
        await self._db.commit()

        return PartnerBadge(
            id=row["id"],
            agreement_id=agreement_id,
            badge_kind=badge_kind,
            issued_at=row["issued_at"],
            is_active=True,
            display_on_heritage=[],
            expires_at=row["expires_at"],
        )

    # ------------------------------------------------------------------ #
    #  Private helpers                                                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _row_to_agreement(r: Any) -> PartnershipAgreement:
        tier_name = r["tier_name"]
        if isinstance(tier_name, str):
            import json

            tier_name = json.loads(tier_name)
        return PartnershipAgreement(
            id=r["id"],
            tenant_id=r["tenant_id"],
            partner_name=r["partner_name"],
            partner_kind=PartnerKind(r["partner_kind"]),
            tier_id=r["tier_id"],
            status=AgreementStatus(r["status"]),
            signed_at=r["signed_at"],
            expires_at=r["expires_at"],
            auto_renew=bool(r["auto_renew"]),
            annual_value_usd=Decimal(str(r["annual_value_usd"])) if r["annual_value_usd"] else None,
            contact_name=r["contact_name"],
            contact_email=r["contact_email"],
            contact_phone=r["contact_phone"],
            notes_md=r["notes_md"],
            mou_url=r["mou_url"],
            created_at=r["created_at"],
            updated_at=r["updated_at"],
            tier_slug=r["tier_slug"],
            tier_name=tier_name,
            tier_sla_uptime_pct=Decimal(str(r["tier_sla_uptime_pct"]))
            if r.get("tier_sla_uptime_pct")
            else None,
        )

    @staticmethod
    def _row_to_window(r: Any) -> UptimeWindow:
        return UptimeWindow(
            id=r["id"],
            started_at=r["started_at"],
            ended_at=r["ended_at"],
            kind=r["kind"],
            severity=r["severity"],
            description_md=r["description_md"],
            affected_services=list(r["affected_services"]) if r["affected_services"] else ["api"],
            is_resolved=bool(r["is_resolved"]),
            resolution_notes=r["resolution_notes"],
            created_at=r["created_at"],
        )

    @staticmethod
    def _compute_uptime_status(
        windows: list[UptimeWindow],
        since: datetime,
    ) -> UptimeStatus:
        now = datetime.now(tz=UTC)
        total_min = (now - since).total_seconds() / 60.0
        outage_min = sum(
            ((w.ended_at or now) - w.started_at).total_seconds() / 60.0
            for w in windows
            if w.kind == "incident"
        )
        uptime_pct = Decimal(
            max(0.0, min(100.0, (1.0 - outage_min / max(total_min, 1)) * 100.0))
        ).quantize(Decimal("0.01"))

        open_incidents = [w for w in windows if w.kind == "incident" and not w.is_resolved]
        last_incident = next((w.started_at for w in windows if w.kind == "incident"), None)

        if open_incidents:
            worst = max(
                open_incidents, key=lambda w: ["info", "degraded", "outage"].index(w.severity)
            )
            service_status = worst.severity if worst.severity != "info" else "degraded"
        else:
            service_status = "operational"

        return UptimeStatus(
            uptime_pct=uptime_pct,
            total_windows=len(windows),
            open_incidents=len(open_incidents),
            last_incident_at=last_incident,
            service_status=service_status,
            computed_at=now,
            recent_windows=[
                {
                    "id": str(w.id),
                    "started_at": w.started_at.isoformat(),
                    "ended_at": w.ended_at.isoformat() if w.ended_at else None,
                    "kind": w.kind,
                    "severity": w.severity,
                    "is_resolved": w.is_resolved,
                    "affected_services": w.affected_services,
                }
                for w in windows[:10]
            ],
        )
