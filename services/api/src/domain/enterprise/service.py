"""Enterprise SLA application service.

Coordinates SLA tier management, subscription tracking, incident lifecycle,
usage snapshot recording, and SLA compliance report generation.

The service depends only on AsyncSession (SQLAlchemy) — no FastAPI coupling.
"""

from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enterprise.entities import (
    BillingPeriod,
    EnterpriseSLAStatus,
    EnterpriseSLATier,
    EnterpriseSubscription,
    EnterpriseUsageSnapshot,
    IncidentSeverity,
    IncidentStatus,
    SLAIncident,
    SubscriptionStatus,
)
from src.domain.enterprise.errors import (
    IncidentAlreadyResolvedError,
    IncidentNotFoundError,
)


def _row_to_tier(row: Any) -> EnterpriseSLATier:
    return EnterpriseSLATier(
        id=row.id,
        slug=row.slug,
        name=row.name or {},
        monthly_price_usd=row.monthly_price_usd,
        uptime_commitment_pct=Decimal(str(row.uptime_commitment_pct)),
        support_response_hours=row.support_response_hours,
        dedicated_csm=row.dedicated_csm,
        custom_domain=row.custom_domain,
        max_seats=row.max_seats,
        api_rate_limit_per_min=row.api_rate_limit_per_min,
        analytics_retention_days=row.analytics_retention_days,
        includes_white_label=row.includes_white_label,
        white_label_subdomains=row.white_label_subdomains,
        created_at=row.created_at,
    )


def _row_to_subscription(row: Any) -> EnterpriseSubscription:
    return EnterpriseSubscription(
        id=row.id,
        enterprise_account_id=row.enterprise_account_id,
        sla_tier_id=row.sla_tier_id,
        status=SubscriptionStatus(row.status),
        billing_period=BillingPeriod(row.billing_period),
        started_at=row.started_at,
        current_period_end=row.current_period_end,
        mrr_usd=Decimal(str(row.mrr_usd)),
        trial_ends_at=row.trial_ends_at,
        contracted_annual_usd=(
            Decimal(str(row.contracted_annual_usd))
            if row.contracted_annual_usd is not None
            else None
        ),
        created_at=row.created_at,
        updated_at=row.updated_at,
        tier_slug=getattr(row, "tier_slug", None),
        tier_name=getattr(row, "tier_name", {}) or {},
        uptime_commitment_pct=(
            Decimal(str(row.uptime_commitment_pct))
            if getattr(row, "uptime_commitment_pct", None) is not None
            else None
        ),
    )


def _row_to_incident(row: Any) -> SLAIncident:
    return SLAIncident(
        id=row.id,
        enterprise_account_id=row.enterprise_account_id,
        title=row.title,
        severity=IncidentSeverity(row.severity),
        affected_services=list(row.affected_services or []),
        status=IncidentStatus(row.status),
        started_at=row.started_at,
        resolved_at=row.resolved_at,
        root_cause=row.root_cause,
        remediation_md=row.remediation_md,
        post_mortem_url=row.post_mortem_url,
        public_visible=row.public_visible,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _row_to_snapshot(row: Any) -> EnterpriseUsageSnapshot:
    return EnterpriseUsageSnapshot(
        id=row.id,
        enterprise_account_id=row.enterprise_account_id,
        snapshot_date=row.snapshot_date,
        api_calls=row.api_calls,
        successful_calls=row.successful_calls,
        error_calls=row.error_calls,
        avg_latency_ms=Decimal(str(row.avg_latency_ms)),
        p95_latency_ms=Decimal(str(row.p95_latency_ms)),
        data_exported_mb=Decimal(str(row.data_exported_mb)),
        active_seats=row.active_seats,
        created_at=row.created_at,
    )


class EnterpriseService:
    """SLA management service — stateless, session-scoped."""

    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    # ------------------------------------------------------------------
    # PUBLIC — tier catalogue
    # ------------------------------------------------------------------

    async def list_tiers(self) -> list[EnterpriseSLATier]:
        """Return all SLA tiers ordered by uptime commitment ascending."""
        result = await self._db.execute(
            text(
                """
                SELECT id, slug, name, monthly_price_usd, uptime_commitment_pct,
                       support_response_hours, dedicated_csm, custom_domain,
                       max_seats, api_rate_limit_per_min, analytics_retention_days,
                       includes_white_label, white_label_subdomains, created_at
                FROM enterprise_sla_tiers
                ORDER BY uptime_commitment_pct ASC
                """
            )
        )
        return [_row_to_tier(r) for r in result.fetchall()]

    # ------------------------------------------------------------------
    # ACCOUNT OWNER — subscription + status
    # ------------------------------------------------------------------

    async def my_subscription(self, account_id: UUID) -> EnterpriseSubscription | None:
        """Return the most recent active/trial subscription for an account."""
        result = await self._db.execute(
            text(
                """
                SELECT
                    s.id, s.enterprise_account_id, s.sla_tier_id, s.status,
                    s.billing_period, s.started_at, s.current_period_end,
                    s.trial_ends_at, s.mrr_usd, s.contracted_annual_usd,
                    s.created_at, s.updated_at,
                    t.slug AS tier_slug, t.name AS tier_name,
                    t.uptime_commitment_pct
                FROM enterprise_subscriptions s
                JOIN enterprise_sla_tiers t ON t.id = s.sla_tier_id
                WHERE s.enterprise_account_id = :account_id
                  AND s.status IN ('trial','active','past_due')
                ORDER BY s.created_at DESC
                LIMIT 1
                """
            ),
            {"account_id": account_id},
        )
        row = result.fetchone()
        return _row_to_subscription(row) if row else None

    async def current_status(self, account_id: UUID) -> EnterpriseSLAStatus:
        """Compute current SLA status for an account."""
        sub = await self.my_subscription(account_id)
        committed_pct = (
            sub.uptime_commitment_pct if sub and sub.uptime_commitment_pct else Decimal("99.0")
        )

        # Open incidents for this account (account-specific OR platform-wide)
        result = await self._db.execute(
            text(
                """
                SELECT id, enterprise_account_id, title, severity, affected_services,
                       status, started_at, resolved_at, root_cause, remediation_md,
                       post_mortem_url, public_visible, created_at, updated_at
                FROM sla_incident_reports
                WHERE status != 'resolved'
                  AND (enterprise_account_id = :account_id OR enterprise_account_id IS NULL)
                ORDER BY started_at DESC
                """
            ),
            {"account_id": account_id},
        )
        open_incidents = [_row_to_incident(r) for r in result.fetchall()]

        # Usage this month
        today = date.today()
        month_start = today.replace(day=1)
        usage_result = await self._db.execute(
            text(
                """
                SELECT
                    COALESCE(SUM(api_calls), 0)        AS total_calls,
                    COALESCE(MAX(active_seats), 0)     AS active_seats,
                    COUNT(*)                            AS days_recorded,
                    COUNT(*) FILTER (
                        WHERE successful_calls::float / NULLIF(api_calls, 0) < 1.0
                    ) AS degraded_days
                FROM enterprise_usage_snapshots
                WHERE enterprise_account_id = :account_id
                  AND snapshot_date >= :month_start
                  AND snapshot_date <= :today
                """
            ),
            {"account_id": account_id, "month_start": month_start, "today": today},
        )
        usage = usage_result.fetchone()

        days_recorded = int(usage.days_recorded) if usage else 0

        # Uptime = proportion of recorded days with no errors
        # When no snapshots exist → assume 100%
        if days_recorded == 0:
            uptime_pct = Decimal("100.00")
        else:
            degraded = int(usage.degraded_days) if usage else 0
            good_days = days_recorded - degraded
            uptime_pct = Decimal(str(round(100 * good_days / days_recorded, 2)))

        sla_met = uptime_pct >= committed_pct
        total_calls = int(usage.total_calls) if usage else 0
        active_seats = int(usage.active_seats) if usage else 0

        return EnterpriseSLAStatus(
            uptime_pct=uptime_pct,
            committed_pct=committed_pct,
            open_incidents=open_incidents,
            total_api_calls_this_period=total_calls,
            active_seats=active_seats,
            sla_met=sla_met,
        )

    # ------------------------------------------------------------------
    # PUBLIC — incidents
    # ------------------------------------------------------------------

    async def list_incidents(
        self,
        public_only: bool = True,
        account_id: UUID | None = None,
        limit: int = 50,
    ) -> list[SLAIncident]:
        """List incidents. public_only=True returns only public_visible=true rows."""
        conditions = []
        params: dict[str, Any] = {"limit": limit}

        if public_only:
            conditions.append("public_visible = true")
        if account_id is not None:
            conditions.append(
                "(enterprise_account_id = :account_id OR enterprise_account_id IS NULL)"
            )
            params["account_id"] = account_id

        base_sql = (
            "SELECT id, enterprise_account_id, title, severity, affected_services,"
            " status, started_at, resolved_at, root_cause, remediation_md,"
            " post_mortem_url, public_visible, created_at, updated_at"
            " FROM sla_incident_reports"
        )
        # conditions contains only fixed string literals — no user-controlled input.
        where_clause = (" WHERE " + " AND ".join(conditions)) if conditions else ""
        order_clause = " ORDER BY started_at DESC LIMIT :limit"
        result = await self._db.execute(text(base_sql + where_clause + order_clause), params)
        return [_row_to_incident(r) for r in result.fetchall()]

    # ------------------------------------------------------------------
    # ADMIN — incident lifecycle
    # ------------------------------------------------------------------

    async def create_incident(
        self,
        title: str,
        severity: str,
        services: list[str],
        _actor: str,
        account_id: UUID | None = None,
        public_visible: bool = False,
    ) -> SLAIncident:
        """Create a new incident report (admin only)."""
        result = await self._db.execute(
            text(
                """
                INSERT INTO sla_incident_reports (
                    enterprise_account_id, title, severity, affected_services,
                    status, public_visible
                ) VALUES (
                    :account_id, :title, :severity, :services,
                    'investigating', :public_visible
                )
                RETURNING id, enterprise_account_id, title, severity, affected_services,
                          status, started_at, resolved_at, root_cause, remediation_md,
                          post_mortem_url, public_visible, created_at, updated_at
                """
            ),
            {
                "account_id": account_id,
                "title": title,
                "severity": severity,
                "services": services,
                "public_visible": public_visible,
            },
        )
        row = result.fetchone()
        await self._db.commit()
        return _row_to_incident(row)

    async def resolve_incident(
        self,
        incident_id: UUID,
        root_cause: str,
        _actor: str,
        remediation_md: str | None = None,
        post_mortem_url: str | None = None,
    ) -> SLAIncident:
        """Mark incident as resolved and record root cause (admin only)."""
        # Fetch first
        fetch = await self._db.execute(
            text(
                """
                SELECT id, status FROM sla_incident_reports WHERE id = :id
                """
            ),
            {"id": incident_id},
        )
        existing = fetch.fetchone()
        if not existing:
            raise IncidentNotFoundError(incident_id)
        if existing.status == "resolved":
            raise IncidentAlreadyResolvedError(incident_id)

        result = await self._db.execute(
            text(
                """
                UPDATE sla_incident_reports
                SET status = 'resolved',
                    resolved_at = now(),
                    root_cause = :root_cause,
                    remediation_md = :remediation_md,
                    post_mortem_url = :post_mortem_url
                WHERE id = :id
                RETURNING id, enterprise_account_id, title, severity, affected_services,
                          status, started_at, resolved_at, root_cause, remediation_md,
                          post_mortem_url, public_visible, created_at, updated_at
                """
            ),
            {
                "id": incident_id,
                "root_cause": root_cause,
                "remediation_md": remediation_md,
                "post_mortem_url": post_mortem_url,
            },
        )
        row = result.fetchone()
        await self._db.commit()
        return _row_to_incident(row)

    # ------------------------------------------------------------------
    # INTERNAL / CELERY — usage snapshot
    # ------------------------------------------------------------------

    async def record_usage_snapshot(
        self, account_id: UUID, stats: dict[str, Any]
    ) -> EnterpriseUsageSnapshot:
        """Upsert a daily usage snapshot (idempotent on account+date)."""
        snap_date = stats.get("snapshot_date", date.today())
        result = await self._db.execute(
            text(
                """
                INSERT INTO enterprise_usage_snapshots (
                    enterprise_account_id, snapshot_date,
                    api_calls, successful_calls, error_calls,
                    avg_latency_ms, p95_latency_ms, data_exported_mb, active_seats
                ) VALUES (
                    :account_id, :snapshot_date,
                    :api_calls, :successful_calls, :error_calls,
                    :avg_latency_ms, :p95_latency_ms, :data_exported_mb, :active_seats
                )
                ON CONFLICT (enterprise_account_id, snapshot_date) DO UPDATE SET
                    api_calls           = EXCLUDED.api_calls,
                    successful_calls    = EXCLUDED.successful_calls,
                    error_calls         = EXCLUDED.error_calls,
                    avg_latency_ms      = EXCLUDED.avg_latency_ms,
                    p95_latency_ms      = EXCLUDED.p95_latency_ms,
                    data_exported_mb    = EXCLUDED.data_exported_mb,
                    active_seats        = EXCLUDED.active_seats
                RETURNING id, enterprise_account_id, snapshot_date,
                          api_calls, successful_calls, error_calls,
                          avg_latency_ms, p95_latency_ms, data_exported_mb,
                          active_seats, created_at
                """
            ),
            {
                "account_id": account_id,
                "snapshot_date": snap_date,
                "api_calls": stats.get("api_calls", 0),
                "successful_calls": stats.get("successful_calls", 0),
                "error_calls": stats.get("error_calls", 0),
                "avg_latency_ms": stats.get("avg_latency_ms", Decimal("0")),
                "p95_latency_ms": stats.get("p95_latency_ms", Decimal("0")),
                "data_exported_mb": stats.get("data_exported_mb", Decimal("0")),
                "active_seats": stats.get("active_seats", 0),
            },
        )
        row = result.fetchone()
        await self._db.commit()
        return _row_to_snapshot(row)

    # ------------------------------------------------------------------
    # ACCOUNT OWNER — SLA compliance report
    # ------------------------------------------------------------------

    async def generate_sla_compliance_report(self, account_id: UUID, month: str) -> dict[str, Any]:
        """Compute monthly SLA compliance report.

        Args:
            account_id: enterprise account UUID.
            month: 'YYYY-MM' string.

        Returns a dict with uptime_pct, committed_pct, sla_met, credit_owed_usd,
        total_api_calls, snapshots summary per day.
        """
        year, month_num = int(month.split("-")[0]), int(month.split("-")[1])
        month_start = date(year, month_num, 1)
        days_in_month = calendar.monthrange(year, month_num)[1]
        month_end = date(year, month_num, days_in_month)

        # Fetch subscription to get commitment
        sub = await self.my_subscription(account_id)
        committed_pct = (
            sub.uptime_commitment_pct if sub and sub.uptime_commitment_pct else Decimal("99.0")
        )
        monthly_price = sub.mrr_usd if sub else Decimal("0")

        # Fetch snapshots for the month
        result = await self._db.execute(
            text(
                """
                SELECT snapshot_date, api_calls, successful_calls, error_calls,
                       avg_latency_ms, p95_latency_ms, active_seats
                FROM enterprise_usage_snapshots
                WHERE enterprise_account_id = :account_id
                  AND snapshot_date >= :month_start
                  AND snapshot_date <= :month_end
                ORDER BY snapshot_date ASC
                """
            ),
            {
                "account_id": account_id,
                "month_start": month_start,
                "month_end": month_end,
            },
        )
        rows = result.fetchall()

        # Compute uptime from snapshots
        if not rows:
            uptime_pct = Decimal("100.00")
            total_calls = 0
        else:
            good_days = sum(
                1
                for r in rows
                if r.api_calls == 0
                or (r.successful_calls / r.api_calls) >= float(committed_pct) / 100
            )
            uptime_pct = Decimal(str(round(100 * good_days / len(rows), 2)))
            total_calls = sum(r.api_calls for r in rows)

        sla_met = uptime_pct >= committed_pct

        # Credit calculation per industry standard:
        # If uptime < commitment, credit = (committed - actual) * 10 * monthly_price / 100
        credit_owed = Decimal("0")
        if not sla_met and monthly_price > 0:
            shortfall = committed_pct - uptime_pct
            credit_owed = (shortfall * 10 * monthly_price / 100).quantize(Decimal("0.01"))

        return {
            "account_id": str(account_id),
            "month": month,
            "uptime_pct": float(uptime_pct),
            "committed_pct": float(committed_pct),
            "sla_met": sla_met,
            "total_api_calls": total_calls,
            "days_with_data": len(rows),
            "days_in_month": days_in_month,
            "credit_owed_usd": float(credit_owed),
            "monthly_price_usd": float(monthly_price),
            "snapshots": [
                {
                    "date": str(r.snapshot_date),
                    "api_calls": r.api_calls,
                    "successful_calls": r.successful_calls,
                    "error_calls": r.error_calls,
                    "avg_latency_ms": float(r.avg_latency_ms),
                    "p95_latency_ms": float(r.p95_latency_ms),
                }
                for r in rows
            ],
        }
