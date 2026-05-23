"""Smart Expense Tracker endpoints. SILK-0072.

Endpoints:
  POST   /v1/me/budget            — create a travel budget
  GET    /v1/me/budget            — list the caller's active budgets
  POST   /v1/me/expenses          — add an expense entry to a budget
  GET    /v1/me/expenses/summary  — spending totals grouped by category

All routes require a valid bearer token (``CurrentUserDep``).  The
``user_id`` from the JWT claim guards every query so users can never read
or write another user's budget rows.  ``residency_region`` is stored on
``travel_budgets`` for future partitioning but is not included in the
current WHERE clauses against ``budget_entries`` (child table, joined via
FK).
"""

from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.middleware.auth import CurrentUserDep
from src.middleware.ratelimit import rate_limit

router = APIRouter(prefix="/v1/me", tags=["expenses"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------

_CATEGORY_VALUES = (
    "food",
    "transport",
    "entrance",
    "souvenir",
    "accommodation",
    "activity",
    "other",
)


class BudgetCreate(BaseModel):
    title: str | None = Field(None, max_length=200)
    total_budget_usd: float = Field(..., gt=0, le=100_000)
    currency: str = Field("USD", min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    start_date: date | None = None
    end_date: date | None = None


class BudgetOut(BaseModel):
    id: UUID
    title: str | None
    total_budget_usd: float
    currency: str
    start_date: date | None
    end_date: date | None
    is_active: bool
    created_at: str


class ExpenseCreate(BaseModel):
    category: str = Field(
        "other",
        max_length=30,
        description="food|transport|entrance|souvenir|accommodation|activity|other",
    )
    amount_usd: float = Field(..., gt=0, le=10_000)
    description: str | None = Field(None, max_length=200)
    entry_date: date | None = None


class ExpenseOut(BaseModel):
    id: UUID
    budget_id: UUID
    category: str
    amount_usd: float
    description: str | None
    entry_date: date
    created_at: str


class CategorySummary(BaseModel):
    category: str
    count: int
    total_usd: float
    last_entry: date | None


class BudgetRef(BaseModel):
    limit_usd: float
    currency: str


class SummaryOut(BaseModel):
    total_spent_usd: float
    by_category: list[CategorySummary]
    budget: BudgetRef | None
    remaining_usd: float | None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post(
    "/budget",
    response_model=BudgetOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(rate_limit("10/minute", per="user", scope="expenses:create_budget")),
    ],
)
async def create_budget(
    body: BudgetCreate,
    ctx: CurrentUserDep,
    db: SessionDep,
) -> BudgetOut:
    """Create a new travel budget for the authenticated user.

    The ``residency_region`` from the caller's JWT is stored on the row
    so the table can be partitioned in a future migration without a
    back-fill.
    """
    if body.end_date and body.start_date and body.end_date < body.start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "expenses.invalid_dates", "message": "end_date must be >= start_date"},
        )

    row = (
        (
            await db.execute(
                text(
                    """
                INSERT INTO travel_budgets
                    (user_id, residency_region, title, total_budget_usd,
                     currency, start_date, end_date)
                VALUES
                    (:uid, :region, :title, :budget, :currency, :start, :end)
                RETURNING
                    id, title, total_budget_usd, currency,
                    start_date, end_date, is_active, created_at
                """
                ),
                {
                    "uid": ctx.user_id,
                    "region": ctx.residency_region.value,
                    "title": body.title,
                    "budget": body.total_budget_usd,
                    "currency": body.currency.upper(),
                    "start": body.start_date,
                    "end": body.end_date,
                },
            )
        )
        .mappings()
        .fetchone()
    )
    await db.commit()

    if row is None:
        raise HTTPException(
            status_code=500,
            detail={"code": "expenses.insert_failed", "message": "budget insert returned no row"},
        )
    return BudgetOut(
        id=row["id"],
        title=row["title"],
        total_budget_usd=float(row["total_budget_usd"]),
        currency=row["currency"],
        start_date=row["start_date"],
        end_date=row["end_date"],
        is_active=row["is_active"],
        created_at=row["created_at"].isoformat(),
    )


@router.get(
    "/budget",
    response_model=list[BudgetOut],
)
async def list_budgets(
    ctx: CurrentUserDep,
    db: SessionDep,
    include_inactive: bool = Query(False, description="Include archived budgets"),
) -> list[BudgetOut]:
    """List the authenticated user's travel budgets.

    Returns the 20 most recently created budgets; active only by default.
    """
    rows = (
        (
            await db.execute(
                text(
                    """
                SELECT id, title, total_budget_usd, currency,
                       start_date, end_date, is_active, created_at
                FROM travel_budgets
                WHERE user_id = :uid
                  AND (:include_inactive OR is_active = true)
                ORDER BY created_at DESC
                LIMIT 20
                """
                ),
                {"uid": ctx.user_id, "include_inactive": include_inactive},
            )
        )
        .mappings()
        .fetchall()
    )

    return [
        BudgetOut(
            id=r["id"],
            title=r["title"],
            total_budget_usd=float(r["total_budget_usd"]),
            currency=r["currency"],
            start_date=r["start_date"],
            end_date=r["end_date"],
            is_active=r["is_active"],
            created_at=r["created_at"].isoformat(),
        )
        for r in rows
    ]


@router.post(
    "/expenses",
    response_model=ExpenseOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(rate_limit("30/minute", per="user", scope="expenses:add_entry")),
    ],
)
async def add_expense(
    body: ExpenseCreate,
    ctx: CurrentUserDep,
    db: SessionDep,
    budget_id: UUID | None = Query(None, description="Budget to attach the entry to"),  # noqa: B008
) -> ExpenseOut:
    """Add an expense entry.

    If ``budget_id`` is omitted the most recently created active budget for
    the caller is used.  Ownership of the budget is verified against
    ``user_id = ctx.user_id`` so a caller cannot inject entries into another
    user's budget even if they know the UUID.
    """
    if body.category not in _CATEGORY_VALUES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "expenses.invalid_category",
                "message": f"category must be one of: {', '.join(_CATEGORY_VALUES)}",
            },
        )

    resolved_budget_id: UUID
    if budget_id is not None:
        # Verify ownership
        owned = (
            await db.execute(
                text(
                    """
                    SELECT id FROM travel_budgets
                    WHERE id = :bid AND user_id = :uid
                    """
                ),
                {"bid": budget_id, "uid": ctx.user_id},
            )
        ).fetchone()
        if owned is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "expenses.budget_not_found", "message": "budget not found"},
            )
        resolved_budget_id = budget_id
    else:
        latest = (
            await db.execute(
                text(
                    """
                    SELECT id FROM travel_budgets
                    WHERE user_id = :uid AND is_active = true
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                ),
                {"uid": ctx.user_id},
            )
        ).fetchone()
        if latest is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "expenses.no_active_budget",
                    "message": "no active budget found — create one first",
                },
            )
        resolved_budget_id = latest[0]

    row = (
        (
            await db.execute(
                text(
                    """
                INSERT INTO budget_entries
                    (budget_id, category, amount_usd, description, entry_date)
                VALUES
                    (:bid, :category, :amount, :desc,
                     COALESCE(cast(:entry_date AS date), CURRENT_DATE))
                RETURNING
                    id, budget_id, category, amount_usd,
                    description, entry_date, created_at
                """
                ),
                {
                    "bid": resolved_budget_id,
                    "category": body.category,
                    "amount": body.amount_usd,
                    "desc": body.description,
                    "entry_date": body.entry_date,
                },
            )
        )
        .mappings()
        .fetchone()
    )
    await db.commit()

    if row is None:
        raise HTTPException(
            status_code=500,
            detail={"code": "expenses.insert_failed", "message": "expense insert returned no row"},
        )
    return ExpenseOut(
        id=row["id"],
        budget_id=row["budget_id"],
        category=row["category"],
        amount_usd=float(row["amount_usd"]),
        description=row["description"],
        entry_date=row["entry_date"],
        created_at=row["created_at"].isoformat(),
    )


@router.get(
    "/expenses/summary",
    response_model=SummaryOut,
)
async def expense_summary(
    ctx: CurrentUserDep,
    db: SessionDep,
    budget_id: UUID | None = Query(None, description="Scope to a specific budget"),  # noqa: B008
) -> SummaryOut:
    """Return spending totals grouped by category.

    When ``budget_id`` is supplied the totals are scoped to that budget and
    the response includes the budget's limit + remaining balance.  Without it
    the summary aggregates across all of the caller's budgets.

    Ownership is always enforced via ``travel_budgets.user_id = :uid`` in the
    JOIN so callers cannot read another user's entries.
    """
    rows = (
        (
            await db.execute(
                text(
                    """
                SELECT
                    be.category,
                    COUNT(*)::int            AS count,
                    SUM(be.amount_usd)       AS total_usd,
                    MAX(be.entry_date)       AS last_entry
                FROM budget_entries be
                JOIN travel_budgets tb ON tb.id = be.budget_id
                WHERE tb.user_id = :uid
                  AND (cast(:bid AS uuid) IS NULL OR be.budget_id = cast(:bid AS uuid))
                GROUP BY be.category
                ORDER BY total_usd DESC
                """
                ),
                {"uid": ctx.user_id, "bid": str(budget_id) if budget_id is not None else None},
            )
        )
        .mappings()
        .fetchall()
    )

    by_category = [
        CategorySummary(
            category=r["category"],
            count=r["count"],
            total_usd=round(float(r["total_usd"]), 2),
            last_entry=r["last_entry"],
        )
        for r in rows
    ]
    total = sum(c.total_usd for c in by_category)

    budget_ref: BudgetRef | None = None
    remaining: float | None = None
    if budget_id is not None:
        brow = (
            (
                await db.execute(
                    text(
                        """
                    SELECT total_budget_usd, currency
                    FROM travel_budgets
                    WHERE id = :bid AND user_id = :uid
                    """
                    ),
                    {"bid": budget_id, "uid": ctx.user_id},
                )
            )
            .mappings()
            .fetchone()
        )
        if brow is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "expenses.budget_not_found", "message": "budget not found"},
            )
        budget_ref = BudgetRef(
            limit_usd=float(brow["total_budget_usd"]),
            currency=brow["currency"],
        )
        remaining = round(budget_ref.limit_usd - total, 2)

    return SummaryOut(
        total_spent_usd=round(total, 2),
        by_category=by_category,
        budget=budget_ref,
        remaining_usd=remaining,
    )
