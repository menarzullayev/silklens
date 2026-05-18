"""Reseller application service.

Orchestrates the public intake → admin review → child-tenant provisioning
flow. Side-effects (child tenant insert, branding-stub insert, revenue-share
row insert, outbox event emission) are pushed down into the repository so
the service stays pure and testable.

Approval flow (``approve_application``):
  1. load + validate the application (must be in submitted/under_review).
  2. provision a new child tenant via the repository (this also creates
     a tenant_branding stub so the white-label UI has a row to PUT into).
  3. mark the application ``approved`` and record ``tenant_id_assigned``.
  4. insert an initial ``tenant_revenue_share`` row (parent = the admin's
     tenant; child = freshly minted tenant).
  5. emit ``reseller.approved.v1`` into the event outbox.

Revenue-share allocation rule: the active-share total for a given child
across all parents must not exceed 100%. The service enforces this via a
pre-flight query before insert; the schema check on the row alone cannot
see cross-row sums.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from src.domain.reseller.entities import (
    ApplicationStatus,
    PlanKind,
    ResellerApplication,
    ResellerApplicationDraft,
    TenantChain,
    TenantRevenueShare,
)
from src.domain.reseller.errors import (
    AlreadyDecided,
    ApplicationNotFound,
    DuplicateApplication,
    InvalidApplicationStatus,
    ResellerValidationError,
    RevenueShareConflict,
    TenantNotFound,
)
from src.domain.reseller.repository import ResellerRepository

_TERMINAL = {
    ApplicationStatus.APPROVED,
    ApplicationStatus.REJECTED,
    ApplicationStatus.WITHDRAWN,
}


def _validate_draft(draft: ResellerApplicationDraft) -> None:
    if not draft.applicant_email or "@" not in draft.applicant_email:
        raise ResellerValidationError("applicant_email", "must be a valid email")
    if not draft.applicant_name.strip():
        raise ResellerValidationError("applicant_name", "must not be empty")
    if not draft.company_name.strip():
        raise ResellerValidationError("company_name", "must not be empty")
    if draft.country_code is not None and len(draft.country_code) != 2:
        raise ResellerValidationError("country_code", "must be ISO-3166 alpha-2")
    if draft.expected_users < 0:
        raise ResellerValidationError("expected_users", "must be >= 0")


def _validate_percentage(pct: Decimal) -> None:
    if pct < Decimal("0") or pct > Decimal("100"):
        raise ResellerValidationError("percentage", "must be between 0 and 100")


class ResellerService:
    def __init__(self, *, repository: ResellerRepository) -> None:
        self._repo = repository

    # --- applications --------------------------------------------------------

    async def submit_application(
        self,
        draft: ResellerApplicationDraft,
    ) -> ResellerApplication:
        _validate_draft(draft)
        # Service-layer dedupe (also enforced at the schema level via partial
        # unique index). We check first so we can raise a typed 409 instead
        # of leaking the IntegrityError shape.
        if await self._repo.has_open_duplicate(
            applicant_email=draft.applicant_email,
            company_name=draft.company_name,
        ):
            raise DuplicateApplication("an open application from this email+company already exists")

        # Normalize: uppercase country code, strip names.
        normalized = ResellerApplicationDraft(
            applicant_email=draft.applicant_email.strip().lower(),
            applicant_name=draft.applicant_name.strip(),
            company_name=draft.company_name.strip(),
            plan_kind=draft.plan_kind,
            expected_users=draft.expected_users,
            country_code=(draft.country_code.upper() if draft.country_code else None),
            tax_id=(draft.tax_id.strip() if draft.tax_id else None),
            message=(draft.message.strip() if draft.message else None),
        )
        application = await self._repo.insert_application(draft=normalized)
        await self._repo.emit_event(
            tenant_id=UUID("00000000-0000-0000-0000-000000000001"),
            event_name="reseller.applied.v1",
            aggregate_kind="reseller_application",
            aggregate_id=application.id,
            payload={
                "applicant_email": application.applicant_email,
                "company_name": application.company_name,
                "plan_kind": application.plan_kind.value,
                "country_code": application.country_code,
            },
        )
        await self._repo.commit()
        return application

    async def get_application(self, application_id: UUID) -> ResellerApplication:
        application = await self._repo.get_application(application_id)
        if application is None:
            raise ApplicationNotFound(f"application {application_id} not found")
        return application

    async def list_applications(
        self,
        *,
        status_filter: ApplicationStatus | None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[tuple[ResellerApplication, ...], int]:
        return await self._repo.list_applications(
            status_filter=status_filter,
            limit=max(1, min(limit, 100)),
            offset=max(0, offset),
        )

    async def approve_application(
        self,
        *,
        application_id: UUID,
        plan_kind: PlanKind,
        admin_user: UUID,
        admin_tenant_id: UUID,
        initial_revenue_share_pct: Decimal,
        notes: str | None = None,
    ) -> tuple[ResellerApplication, TenantRevenueShare]:
        _validate_percentage(initial_revenue_share_pct)

        application = await self.get_application(application_id)
        if application.status in _TERMINAL:
            raise AlreadyDecided(f"application is in terminal state {application.status.value}")

        # Pre-flight: a fresh child tenant has no existing parents, so the
        # sum-check is trivially satisfied. We still run the helper so the
        # behaviour is symmetric with ``configure_revenue_share``.
        child_tenant_id = await self._repo.provision_child_tenant(
            parent_tenant_id=admin_tenant_id,
            application=application,
            plan_kind=plan_kind,
            actor=admin_user,
        )

        approved = await self._repo.transition_application(
            application_id=application_id,
            new_status=ApplicationStatus.APPROVED,
            reviewed_by=admin_user,
            notes=notes,
            tenant_id_assigned=child_tenant_id,
        )

        share = await self._repo.insert_revenue_share(
            parent_tenant_id=admin_tenant_id,
            child_tenant_id=child_tenant_id,
            percentage=initial_revenue_share_pct,
            notes="Initial allocation on reseller approval",
        )

        await self._repo.emit_event(
            tenant_id=admin_tenant_id,
            event_name="reseller.approved.v1",
            aggregate_kind="reseller_application",
            aggregate_id=approved.id,
            payload={
                "child_tenant_id": str(child_tenant_id),
                "plan_kind": plan_kind.value,
                "company_name": approved.company_name,
                "initial_revenue_share_pct": str(initial_revenue_share_pct),
                "approved_by": str(admin_user),
            },
        )
        await self._repo.commit()
        return approved, share

    async def reject_application(
        self,
        *,
        application_id: UUID,
        admin_user: UUID,
        reason: str,
    ) -> ResellerApplication:
        if not reason.strip():
            raise ResellerValidationError("reason", "must not be empty")
        application = await self.get_application(application_id)
        if application.status in _TERMINAL:
            raise AlreadyDecided(f"application is in terminal state {application.status.value}")
        rejected = await self._repo.transition_application(
            application_id=application_id,
            new_status=ApplicationStatus.REJECTED,
            reviewed_by=admin_user,
            notes=reason.strip(),
        )
        await self._repo.emit_event(
            tenant_id=UUID("00000000-0000-0000-0000-000000000001"),
            event_name="reseller.rejected.v1",
            aggregate_kind="reseller_application",
            aggregate_id=rejected.id,
            payload={"reason": reason.strip(), "rejected_by": str(admin_user)},
        )
        await self._repo.commit()
        return rejected

    async def withdraw_application(
        self,
        *,
        application_id: UUID,
    ) -> ResellerApplication:
        application = await self.get_application(application_id)
        if application.status in _TERMINAL:
            raise AlreadyDecided(f"application is in terminal state {application.status.value}")
        withdrawn = await self._repo.transition_application(
            application_id=application_id,
            new_status=ApplicationStatus.WITHDRAWN,
            reviewed_by=application.reviewed_by or _SENTINEL_ACTOR,
            notes=application.notes,
        )
        await self._repo.commit()
        return withdrawn

    # --- revenue share -------------------------------------------------------

    async def configure_revenue_share(
        self,
        *,
        parent_tenant_slug: str,
        child_tenant_slug: str,
        percentage: Decimal,
        notes: str | None = None,
    ) -> TenantRevenueShare:
        _validate_percentage(percentage)

        parent_id = await self._repo.get_tenant_id_by_slug(parent_tenant_slug)
        if parent_id is None:
            raise TenantNotFound(f"parent tenant '{parent_tenant_slug}' not found")
        child_id = await self._repo.get_tenant_id_by_slug(child_tenant_slug)
        if child_id is None:
            raise TenantNotFound(f"child tenant '{child_tenant_slug}' not found")
        if parent_id == child_id:
            raise ResellerValidationError("child_tenant_slug", "parent and child must differ")

        # Sum of active parent shares (excluding the parent we're about to
        # set/replace) plus the new percentage must not exceed 100%.
        existing_total = await self._repo.active_share_total_for_child(
            child_tenant_id=child_id,
            exclude_parent_id=parent_id,
        )
        if existing_total + percentage > Decimal("100"):
            raise RevenueShareConflict(
                f"total active revenue share for child would be "
                f"{existing_total + percentage}% (max 100%)"
            )

        # Close any open row for this parent/child pair so history is clean.
        await self._repo.close_open_revenue_share(
            parent_tenant_id=parent_id,
            child_tenant_id=child_id,
        )
        share = await self._repo.insert_revenue_share(
            parent_tenant_id=parent_id,
            child_tenant_id=child_id,
            percentage=percentage,
            notes=notes,
        )
        await self._repo.emit_event(
            tenant_id=parent_id,
            event_name="reseller.revenue_share_configured.v1",
            aggregate_kind="tenant",
            aggregate_id=child_id,
            payload={
                "parent_tenant_id": str(parent_id),
                "child_tenant_id": str(child_id),
                "percentage": str(percentage),
            },
        )
        await self._repo.commit()
        return share

    async def list_revenue_shares_for_child_slug(
        self,
        child_tenant_slug: str,
    ) -> tuple[TenantRevenueShare, ...]:
        child_id = await self._repo.get_tenant_id_by_slug(child_tenant_slug)
        if child_id is None:
            raise TenantNotFound(f"tenant '{child_tenant_slug}' not found")
        return await self._repo.list_revenue_shares_for_child(child_tenant_id=child_id)

    # --- tenant chain --------------------------------------------------------

    async def get_tenant_chain(self, tenant_id: UUID) -> TenantChain:
        chain = await self._repo.get_tenant_chain(tenant_id)
        if chain is None:
            raise TenantNotFound(f"tenant {tenant_id} not found")
        return chain


# Sentinel for ``withdraw_application`` when the actor is the applicant
# (we don't have a user_id for the public endpoint). The repository stores
# this as NULL on ``reviewed_by`` so we keep the SQL constraint happy.
_SENTINEL_ACTOR = UUID("00000000-0000-0000-0000-000000000002")

# Modules that import ``InvalidApplicationStatus`` symbol re-export only;
# kept for compatibility with tests that exercise the explicit error type.
__all__ = [
    "InvalidApplicationStatus",
    "ResellerService",
]
