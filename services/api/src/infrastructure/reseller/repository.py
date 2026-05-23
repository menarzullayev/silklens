"""SQLAlchemy-backed implementation of ``ResellerRepository``.

Hand-written SQL — migration 0083 owns the canonical schema; ORM models on
top would duplicate truth.

Child-tenant provisioning runs as part of ``provision_child_tenant``:

  1. INSERT a fresh row into ``tenants`` with a deterministic slug derived
     from the application's company name (lower-snake + 6-char suffix to
     avoid collisions).
  2. INSERT a stub row into ``tenant_branding`` so the white-label admin UI
     has a row to PATCH against from the first PUT.

All writes within a single service method share the AsyncSession; the
service calls ``commit()`` once at the end so the outbox + the schema rows
land atomically.
"""

from __future__ import annotations

import json
import re
import secrets
from decimal import Decimal
from typing import Final
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.reseller.entities import (
    ApplicationStatus,
    PlanKind,
    ResellerApplication,
    ResellerApplicationDraft,
    TenantChain,
    TenantRevenueShare,
)
from src.domain.reseller.errors import (
    ApplicationNotFound,
    DuplicateApplication,
)

_SLUG_NORMALIZE: Final = re.compile(r"[^a-z0-9]+")


def _slugify(company: str) -> str:
    """Derive a tenant slug from a company name. Always returns ASCII +
    appends a short random suffix to avoid collisions in the unique slug
    space. The migration constraint is ``^[a-z0-9]([a-z0-9-]*[a-z0-9])?$``
    so we collapse runs of non-alphanumerics into a single hyphen.
    """
    base = _SLUG_NORMALIZE.sub("-", company.strip().lower()).strip("-")
    if not base:
        base = "reseller"
    # 6 chars of urlsafe random + lowercase
    suffix = secrets.token_hex(3)
    return f"{base[:40]}-{suffix}".strip("-")


def _json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)


def _row_to_application(row: object) -> ResellerApplication:
    m = row._mapping  # type: ignore[attr-defined]
    return ResellerApplication(
        id=m["id"],
        applicant_email=m["applicant_email"],
        applicant_name=m["applicant_name"],
        company_name=m["company_name"],
        plan_kind=PlanKind(m["plan_kind"]),
        status=ApplicationStatus(m["status"]),
        expected_users=int(m["expected_users"]),
        submitted_at=m["submitted_at"],
        created_at=m["created_at"],
        updated_at=m["updated_at"],
        country_code=m["country_code"],
        tax_id=m["tax_id"],
        message=m["message"],
        notes=m["notes"],
        reviewed_at=m["reviewed_at"],
        reviewed_by=m["reviewed_by"],
        tenant_id_assigned=m["tenant_id_assigned"],
    )


def _row_to_revenue_share(row: object) -> TenantRevenueShare:
    m = row._mapping  # type: ignore[attr-defined]
    return TenantRevenueShare(
        parent_tenant_id=m["parent_tenant_id"],
        child_tenant_id=m["child_tenant_id"],
        percentage=Decimal(m["percentage"]),
        effective_from=m["effective_from"],
        effective_until=m["effective_until"],
        notes=m["notes"],
        created_at=m["created_at"],
        updated_at=m["updated_at"],
    )


_APP_COLS: Final = (
    "id, applicant_email, applicant_name, company_name, country_code, tax_id, "
    "plan_kind, expected_users, message, status, submitted_at, reviewed_at, "
    "reviewed_by, notes, tenant_id_assigned, created_at, updated_at"
)


class SqlResellerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # --- applications --------------------------------------------------------

    async def insert_application(
        self,
        *,
        draft: ResellerApplicationDraft,
    ) -> ResellerApplication:
        try:
            result = await self._session.execute(
                text(
                    f"""
                    INSERT INTO reseller_application (
                        applicant_email, applicant_name, company_name, country_code,
                        tax_id, plan_kind, expected_users, message
                    )
                    VALUES (
                        :email, :name, :company, :country, :tax, :plan,
                        :expected, :message
                    )
                    RETURNING {_APP_COLS}
                    """  # noqa: S608
                ),
                {
                    "email": draft.applicant_email,
                    "name": draft.applicant_name,
                    "company": draft.company_name,
                    "country": draft.country_code,
                    "tax": draft.tax_id,
                    "plan": draft.plan_kind.value,
                    "expected": draft.expected_users,
                    "message": draft.message,
                },
            )
        except IntegrityError as exc:
            await self._session.rollback()
            raise DuplicateApplication(
                "open application with this email+company already exists"
            ) from exc
        return _row_to_application(result.one())

    async def get_application(self, application_id: UUID) -> ResellerApplication | None:
        row = (
            await self._session.execute(
                text(
                    f"SELECT {_APP_COLS} FROM reseller_application WHERE id = :id"  # noqa: S608
                ),
                {"id": application_id},
            )
        ).one_or_none()
        return _row_to_application(row) if row else None

    async def has_open_duplicate(
        self,
        *,
        applicant_email: str,
        company_name: str,
    ) -> bool:
        row = await self._session.execute(
            text(
                """
                SELECT 1 FROM reseller_application
                WHERE lower(applicant_email) = lower(:email)
                  AND lower(company_name) = lower(:company)
                  AND status IN ('submitted','under_review')
                LIMIT 1
                """
            ),
            {"email": applicant_email, "company": company_name},
        )
        return row.one_or_none() is not None

    async def list_applications(
        self,
        *,
        status_filter: ApplicationStatus | None,
        limit: int,
        offset: int,
    ) -> tuple[tuple[ResellerApplication, ...], int]:
        params: dict[str, object] = {"limit": limit, "offset": offset}
        where = ""
        count_params: dict[str, object] = {}
        if status_filter is not None:
            where = "WHERE status = :status"
            params["status"] = status_filter.value
            count_params["status"] = status_filter.value
        total = (
            await self._session.execute(
                text(f"SELECT count(*) FROM reseller_application {where}"),  # noqa: S608
                count_params,
            )
        ).scalar_one()
        result = await self._session.execute(
            text(
                f"""
                SELECT {_APP_COLS}
                FROM reseller_application
                {where}
                ORDER BY submitted_at DESC, id DESC
                LIMIT :limit OFFSET :offset
                """  # noqa: S608
            ),
            params,
        )
        items = tuple(_row_to_application(r) for r in result.all())
        return items, int(total)

    async def transition_application(
        self,
        *,
        application_id: UUID,
        new_status: ApplicationStatus,
        reviewed_by: UUID,
        notes: str | None,
        tenant_id_assigned: UUID | None = None,
    ) -> ResellerApplication:
        result = await self._session.execute(
            text(
                f"""
                UPDATE reseller_application
                SET status = :status,
                    reviewed_at = now(),
                    reviewed_by = :reviewer,
                    notes = COALESCE(:notes, notes),
                    tenant_id_assigned = COALESCE(:tid, tenant_id_assigned)
                WHERE id = :id
                RETURNING {_APP_COLS}
                """  # noqa: S608
            ),
            {
                "status": new_status.value,
                "reviewer": reviewed_by,
                "notes": notes,
                "tid": tenant_id_assigned,
                "id": application_id,
            },
        )
        row = result.one_or_none()
        if row is None:
            raise ApplicationNotFound(f"application {application_id} not found")
        return _row_to_application(row)

    # --- child tenant provisioning ------------------------------------------

    async def provision_child_tenant(
        self,
        *,
        parent_tenant_id: UUID,
        application: ResellerApplication,
        plan_kind: PlanKind,
        actor: UUID,
    ) -> UUID:
        # Retry on slug collision (cheap; secrets.token_hex(3) is 16M space).
        last_exc: IntegrityError | None = None
        for _ in range(5):
            slug = _slugify(application.company_name)
            try:
                row = await self._session.execute(
                    text(
                        """
                        INSERT INTO tenants (
                            slug, display_name, status, plan_tier,
                            parent_tenant_id, owner_user_id, metadata
                        )
                        VALUES (
                            :slug,
                            CAST(:display AS jsonb),
                            'active',
                            :plan_tier,
                            :parent,
                            NULL,
                            CAST(:metadata AS jsonb)
                        )
                        RETURNING id
                        """
                    ),
                    {
                        "slug": slug,
                        "display": _json({"en": application.company_name}),
                        "plan_tier": _plan_tier_for(plan_kind),
                        "parent": parent_tenant_id,
                        "metadata": _json(
                            {
                                "provisioned_from_application": str(application.id),
                                "plan_kind": plan_kind.value,
                                "provisioned_by": str(actor),
                            }
                        ),
                    },
                )
                child_tenant_id: UUID = row.scalar_one()
                break
            except IntegrityError as exc:  # likely slug collision
                last_exc = exc
                await self._session.rollback()
        else:
            # The ``for`` loop only exhausts the retry budget when every
            # attempt raised ``IntegrityError`` -- so ``last_exc`` is
            # guaranteed to be set. Defensive check to satisfy ``-O``.
            if last_exc is None:
                raise RuntimeError("reseller create: retry budget exhausted without exception")
            raise last_exc

        # Branding stub so the white-label admin UI has a row to PUT into.
        await self._session.execute(
            text(
                """
                INSERT INTO tenant_branding (
                    tenant_id, app_name, theme_mode_default
                )
                VALUES (
                    :tid,
                    CAST(:app_name AS jsonb),
                    'system'
                )
                ON CONFLICT (tenant_id) DO NOTHING
                """
            ),
            {
                "tid": child_tenant_id,
                "app_name": _json({"en": application.company_name}),
            },
        )
        return child_tenant_id

    # --- revenue share ------------------------------------------------------

    async def insert_revenue_share(
        self,
        *,
        parent_tenant_id: UUID,
        child_tenant_id: UUID,
        percentage: Decimal,
        notes: str | None,
    ) -> TenantRevenueShare:
        result = await self._session.execute(
            text(
                """
                INSERT INTO tenant_revenue_share (
                    parent_tenant_id, child_tenant_id, percentage, notes
                )
                VALUES (:parent, :child, :pct, :notes)
                RETURNING parent_tenant_id, child_tenant_id, percentage,
                          effective_from, effective_until, notes,
                          created_at, updated_at
                """
            ),
            {
                "parent": parent_tenant_id,
                "child": child_tenant_id,
                "pct": percentage,
                "notes": notes,
            },
        )
        return _row_to_revenue_share(result.one())

    async def list_revenue_shares_for_child(
        self,
        *,
        child_tenant_id: UUID,
    ) -> tuple[TenantRevenueShare, ...]:
        result = await self._session.execute(
            text(
                """
                SELECT parent_tenant_id, child_tenant_id, percentage,
                       effective_from, effective_until, notes,
                       created_at, updated_at
                FROM tenant_revenue_share
                WHERE child_tenant_id = :child
                ORDER BY effective_from DESC
                """
            ),
            {"child": child_tenant_id},
        )
        return tuple(_row_to_revenue_share(r) for r in result.all())

    async def close_open_revenue_share(
        self,
        *,
        parent_tenant_id: UUID,
        child_tenant_id: UUID,
    ) -> None:
        await self._session.execute(
            text(
                """
                UPDATE tenant_revenue_share
                SET effective_until = now()
                WHERE parent_tenant_id = :parent
                  AND child_tenant_id = :child
                  AND effective_until IS NULL
                """
            ),
            {"parent": parent_tenant_id, "child": child_tenant_id},
        )

    async def active_share_total_for_child(
        self,
        *,
        child_tenant_id: UUID,
        exclude_parent_id: UUID | None,
    ) -> Decimal:
        # The ``:exclude`` bind appears twice — once in the NULL check, once
        # in the inequality. asyncpg's parameter binder rejects repeating a
        # named bind across positional placeholders, so we expand the SQL to
        # two distinct binds (``:exclude_a`` and ``:exclude_b``).
        result = await self._session.execute(
            text(
                """
                SELECT COALESCE(SUM(percentage), 0)
                FROM tenant_revenue_share
                WHERE child_tenant_id = :child
                  AND effective_until IS NULL
                  AND (CAST(:exclude_a AS uuid) IS NULL
                       OR parent_tenant_id <> CAST(:exclude_b AS uuid))
                """
            ),
            {
                "child": child_tenant_id,
                "exclude_a": exclude_parent_id,
                "exclude_b": exclude_parent_id,
            },
        )
        return Decimal(result.scalar_one())

    # --- tenant lookups -----------------------------------------------------

    async def get_tenant_id_by_slug(self, slug: str) -> UUID | None:
        row = (
            await self._session.execute(
                text(
                    """
                    SELECT id FROM tenants
                    WHERE slug = :slug AND deleted_at IS NULL
                    """
                ),
                {"slug": slug},
            )
        ).one_or_none()
        return row[0] if row else None

    async def get_tenant_chain(self, tenant_id: UUID) -> TenantChain | None:
        # Recursive CTE walking up parent_tenant_id. Cap at 10 levels so a
        # cycle (which the schema doesn't prevent) can't kill the query.
        result = await self._session.execute(
            text(
                """
                WITH RECURSIVE chain AS (
                    SELECT id, slug::text AS slug, display_name, status,
                           plan_tier, parent_tenant_id, 0 AS depth
                    FROM tenants WHERE id = :tid AND deleted_at IS NULL
                  UNION ALL
                    SELECT t.id, t.slug::text, t.display_name, t.status,
                           t.plan_tier, t.parent_tenant_id, c.depth + 1
                    FROM tenants t
                    JOIN chain c ON t.id = c.parent_tenant_id
                    WHERE t.deleted_at IS NULL AND c.depth < 10
                )
                SELECT * FROM chain ORDER BY depth ASC
                """
            ),
            {"tid": tenant_id},
        )
        rows = result.all()
        if not rows:
            return None
        head = rows[0]._mapping
        # The caller's own tenant is the depth=0 row; remaining rows are
        # ancestors. Reverse so parent_chain is root-first → caller-last.
        ancestors = tuple(r._mapping["id"] for r in rows[1:])
        return TenantChain(
            tenant_id=head["id"],
            slug=head["slug"],
            display_name=dict(head["display_name"]) if head["display_name"] else {},
            plan_tier=head["plan_tier"],
            status=head["status"],
            parent_chain=tuple(reversed(ancestors)),
        )

    # --- event emission -----------------------------------------------------

    async def emit_event(
        self,
        *,
        tenant_id: UUID,
        event_name: str,
        aggregate_kind: str,
        aggregate_id: UUID,
        payload: dict[str, object],
    ) -> None:
        await self._session.execute(
            text(
                """
                SELECT app.emit_event(
                    :tenant, :event_name, :kind, :aggregate,
                    CAST(:payload AS jsonb)
                )
                """
            ),
            {
                "tenant": tenant_id,
                "event_name": event_name,
                "kind": aggregate_kind,
                "aggregate": aggregate_id,
                "payload": _json(payload),
            },
        )

    async def commit(self) -> None:
        await self._session.commit()


def _plan_tier_for(plan_kind: PlanKind) -> str:
    """Map an application plan_kind to a tenants.plan_tier string.

    Government + national-platform style deals get ``enterprise``; the rest
    start at ``business`` so they pick up branding + custom-domain features
    without enterprise API limits.
    """
    if plan_kind is PlanKind.GOVERNMENT:
        return "enterprise"
    if plan_kind in (PlanKind.CORPORATE, PlanKind.TOURISM_AGENCY):
        return "business"
    return "academic"
