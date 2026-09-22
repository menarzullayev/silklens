"""Reseller repository protocol — interface only."""

from __future__ import annotations

from decimal import Decimal
from typing import Protocol
from uuid import UUID

from src.domain.reseller.entities import (
    ApplicationStatus,
    PlanKind,
    ResellerApplication,
    ResellerApplicationDraft,
    TenantChain,
    TenantRevenueShare,
)


class ResellerRepository(Protocol):
    # --- applications --------------------------------------------------------

    async def insert_application(
        self,
        *,
        draft: ResellerApplicationDraft,
    ) -> ResellerApplication: ...

    async def get_application(self, application_id: UUID) -> ResellerApplication | None: ...

    async def has_open_duplicate(
        self,
        *,
        applicant_email: str,
        company_name: str,
    ) -> bool: ...

    async def list_applications(
        self,
        *,
        status_filter: ApplicationStatus | None,
        limit: int,
        offset: int,
    ) -> tuple[tuple[ResellerApplication, ...], int]: ...

    async def transition_application(
        self,
        *,
        application_id: UUID,
        new_status: ApplicationStatus,
        reviewed_by: UUID,
        notes: str | None,
        tenant_id_assigned: UUID | None = None,
    ) -> ResellerApplication: ...

    # --- child tenant provisioning ------------------------------------------

    async def provision_child_tenant(
        self,
        *,
        parent_tenant_id: UUID,
        application: ResellerApplication,
        plan_kind: PlanKind,
        actor: UUID,
    ) -> UUID: ...

    # --- revenue share ------------------------------------------------------

    async def insert_revenue_share(
        self,
        *,
        parent_tenant_id: UUID,
        child_tenant_id: UUID,
        percentage: Decimal,
        notes: str | None,
    ) -> TenantRevenueShare: ...

    async def list_revenue_shares_for_child(
        self,
        *,
        child_tenant_id: UUID,
    ) -> tuple[TenantRevenueShare, ...]: ...

    async def close_open_revenue_share(
        self,
        *,
        parent_tenant_id: UUID,
        child_tenant_id: UUID,
    ) -> None: ...

    async def active_share_total_for_child(
        self,
        *,
        child_tenant_id: UUID,
        exclude_parent_id: UUID | None,
    ) -> Decimal: ...

    # --- tenant lookups -----------------------------------------------------

    async def get_tenant_id_by_slug(self, slug: str) -> UUID | None: ...

    async def get_tenant_chain(self, tenant_id: UUID) -> TenantChain | None: ...

    # --- event emission -----------------------------------------------------

    async def emit_event(
        self,
        *,
        tenant_id: UUID,
        event_name: str,
        aggregate_kind: str,
        aggregate_id: UUID,
        payload: dict[str, object],
    ) -> None: ...

    async def commit(self) -> None: ...
