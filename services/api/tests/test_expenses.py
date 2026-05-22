"""Smart Expense Tracker integration tests. SILK-0072.

Covers:
  - Happy path: create budget (201)
  - Happy path: list budgets (200)
  - Happy path: add expense (201)
  - Happy path: expense summary (200)
  - Auth required — 401 without bearer on every mutating endpoint
  - Validation — 422 on bad payload (negative amount, over-length title)
  - Invalid category — 422 from domain check
  - No active budget — 404 when adding expense with no budgets
  - Budget not found — 404 when budget_id belongs to another user
  - Date validation — 422 when end_date < start_date
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


def _email() -> str:
    return f"expenses-{uuid.uuid4().hex[:10]}@silklens-test.com"


_PASSWORD = "ExpenseTrackerPass12345!"


async def _register(http: AsyncClient, email: str | None = None) -> dict[str, Any]:
    resp = await http.post(
        "/v1/auth/register",
        json={"email": email or _email(), "password": _PASSWORD},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _bearer(auth: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {auth['tokens']['access_token']}"}


# ---------------------------------------------------------------------------
# Budget creation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_budget_happy_path(http: AsyncClient) -> None:
    auth = await _register(http)
    resp = await http.post(
        "/v1/me/budget",
        json={
            "title": "Silk Road Trip 2026",
            "total_budget_usd": 1500.00,
            "currency": "USD",
            "start_date": "2026-06-01",
            "end_date": "2026-06-30",
        },
        headers=_bearer(auth),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["title"] == "Silk Road Trip 2026"
    assert body["total_budget_usd"] == 1500.0
    assert body["currency"] == "USD"
    assert body["is_active"] is True
    assert "id" in body
    assert "created_at" in body


@pytest.mark.asyncio
async def test_create_budget_requires_auth(http: AsyncClient) -> None:
    resp = await http.post(
        "/v1/me/budget",
        json={"total_budget_usd": 500.0},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_budget_validation_negative_amount(http: AsyncClient) -> None:
    auth = await _register(http)
    resp = await http.post(
        "/v1/me/budget",
        json={"total_budget_usd": -50.0},
        headers=_bearer(auth),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_budget_validation_title_too_long(http: AsyncClient) -> None:
    auth = await _register(http)
    resp = await http.post(
        "/v1/me/budget",
        json={"title": "x" * 201, "total_budget_usd": 100.0},
        headers=_bearer(auth),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_budget_end_before_start(http: AsyncClient) -> None:
    auth = await _register(http)
    resp = await http.post(
        "/v1/me/budget",
        json={
            "total_budget_usd": 200.0,
            "start_date": "2026-07-01",
            "end_date": "2026-06-01",
        },
        headers=_bearer(auth),
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "expenses.invalid_dates"


# ---------------------------------------------------------------------------
# Budget listing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_budgets_happy_path(http: AsyncClient) -> None:
    auth = await _register(http)
    for i in range(3):
        await http.post(
            "/v1/me/budget",
            json={"title": f"Budget {i}", "total_budget_usd": 100.0 * (i + 1)},
            headers=_bearer(auth),
        )

    resp = await http.get("/v1/me/budget", headers=_bearer(auth))
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 3
    # Ordered newest first
    assert items[0]["title"] == "Budget 2"


@pytest.mark.asyncio
async def test_list_budgets_requires_auth(http: AsyncClient) -> None:
    resp = await http.get("/v1/me/budget")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_budgets_isolation(http: AsyncClient) -> None:
    """User A's budgets must not appear in User B's listing."""
    auth_a = await _register(http)
    auth_b = await _register(http)

    await http.post(
        "/v1/me/budget",
        json={"title": "UserA Budget", "total_budget_usd": 999.0},
        headers=_bearer(auth_a),
    )

    resp = await http.get("/v1/me/budget", headers=_bearer(auth_b))
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# Expense entry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_expense_happy_path(http: AsyncClient) -> None:
    auth = await _register(http)
    bud = await http.post(
        "/v1/me/budget",
        json={"title": "Food only", "total_budget_usd": 300.0},
        headers=_bearer(auth),
    )
    budget_id = bud.json()["id"]

    resp = await http.post(
        "/v1/me/expenses",
        json={"category": "food", "amount_usd": 12.50, "description": "Plov at bazaar"},
        params={"budget_id": budget_id},
        headers=_bearer(auth),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["category"] == "food"
    assert body["amount_usd"] == 12.50
    assert body["budget_id"] == budget_id


@pytest.mark.asyncio
async def test_add_expense_auto_selects_latest_budget(http: AsyncClient) -> None:
    auth = await _register(http)
    await http.post(
        "/v1/me/budget",
        json={"title": "Auto budget", "total_budget_usd": 500.0},
        headers=_bearer(auth),
    )

    resp = await http.post(
        "/v1/me/expenses",
        json={"category": "transport", "amount_usd": 5.0},
        headers=_bearer(auth),
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["category"] == "transport"


@pytest.mark.asyncio
async def test_add_expense_requires_auth(http: AsyncClient) -> None:
    resp = await http.post(
        "/v1/me/expenses",
        json={"category": "food", "amount_usd": 10.0},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_add_expense_no_budget_404(http: AsyncClient) -> None:
    auth = await _register(http)
    resp = await http.post(
        "/v1/me/expenses",
        json={"category": "food", "amount_usd": 10.0},
        headers=_bearer(auth),
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "expenses.no_active_budget"


@pytest.mark.asyncio
async def test_add_expense_invalid_category(http: AsyncClient) -> None:
    auth = await _register(http)
    await http.post(
        "/v1/me/budget",
        json={"total_budget_usd": 100.0},
        headers=_bearer(auth),
    )
    resp = await http.post(
        "/v1/me/expenses",
        json={"category": "yolo", "amount_usd": 5.0},
        headers=_bearer(auth),
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "expenses.invalid_category"


@pytest.mark.asyncio
async def test_add_expense_wrong_budget_id_404(http: AsyncClient) -> None:
    """Attempt to attach an entry to another user's budget returns 404."""
    auth_a = await _register(http)
    auth_b = await _register(http)

    bud = await http.post(
        "/v1/me/budget",
        json={"title": "UserA private budget", "total_budget_usd": 200.0},
        headers=_bearer(auth_a),
    )
    budget_id = bud.json()["id"]

    resp = await http.post(
        "/v1/me/expenses",
        json={"category": "food", "amount_usd": 5.0},
        params={"budget_id": budget_id},
        headers=_bearer(auth_b),
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "expenses.budget_not_found"


@pytest.mark.asyncio
async def test_add_expense_validation_amount_zero(http: AsyncClient) -> None:
    auth = await _register(http)
    resp = await http.post(
        "/v1/me/expenses",
        json={"category": "food", "amount_usd": 0},
        headers=_bearer(auth),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_add_expense_validation_description_too_long(http: AsyncClient) -> None:
    auth = await _register(http)
    resp = await http.post(
        "/v1/me/expenses",
        json={"category": "food", "amount_usd": 5.0, "description": "x" * 201},
        headers=_bearer(auth),
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_expense_summary_happy_path(http: AsyncClient) -> None:
    auth = await _register(http)
    bud = await http.post(
        "/v1/me/budget",
        json={"title": "Summary test", "total_budget_usd": 1000.0},
        headers=_bearer(auth),
    )
    budget_id = bud.json()["id"]
    headers = _bearer(auth)
    params = {"budget_id": budget_id}

    for category, amount in [("food", 20.0), ("food", 30.0), ("transport", 15.0)]:
        await http.post(
            "/v1/me/expenses",
            json={"category": category, "amount_usd": amount},
            params=params,
            headers=headers,
        )

    resp = await http.get("/v1/me/expenses/summary", params=params, headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total_spent_usd"] == 65.0
    assert body["budget"]["limit_usd"] == 1000.0
    assert body["remaining_usd"] == 935.0

    cats = {c["category"]: c for c in body["by_category"]}
    assert cats["food"]["count"] == 2
    assert cats["food"]["total_usd"] == 50.0
    assert cats["transport"]["total_usd"] == 15.0


@pytest.mark.asyncio
async def test_expense_summary_requires_auth(http: AsyncClient) -> None:
    resp = await http.get("/v1/me/expenses/summary")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_expense_summary_budget_not_found(http: AsyncClient) -> None:
    auth = await _register(http)
    fake_id = str(uuid.uuid4())
    resp = await http.get(
        "/v1/me/expenses/summary",
        params={"budget_id": fake_id},
        headers=_bearer(auth),
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "expenses.budget_not_found"


@pytest.mark.asyncio
async def test_expense_summary_empty(http: AsyncClient) -> None:
    """Summary with no entries returns zeroed totals."""
    auth = await _register(http)
    resp = await http.get("/v1/me/expenses/summary", headers=_bearer(auth))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_spent_usd"] == 0.0
    assert body["by_category"] == []
    assert body["budget"] is None
    assert body["remaining_usd"] is None
