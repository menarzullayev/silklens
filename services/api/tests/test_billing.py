"""Billing API integration tests.

Covers the MockPaymentProvider flow: list plans (after we seed prices), start a
subscription, hit the idempotent retry, force a failure with a `fail_` token,
cancel + resume the sub, check entitlements, and exercise webhook idempotency.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.integration


DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"


def _email() -> str:
    return f"billing-{uuid.uuid4().hex[:10]}@silklens-test.com"


async def _register(http: AsyncClient) -> dict[str, Any]:
    response = await http.post(
        "/v1/auth/register",
        json={"email": _email(), "password": "BillingTest12345"},
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
async def billing_seed(db_session: AsyncSession) -> dict[str, str]:
    """Idempotent seed of plans, prices, plan_features for test usage.

    Returns a small dict of slugs so tests can refer back to them.
    """
    await db_session.execute(
        text(
            """
            INSERT INTO product_plans (
                tenant_id, product_id, slug, name, billing_period, trial_days, is_default
            )
            SELECT pr.tenant_id, pr.id, 'premium_monthly',
                   '{"en":"Premium monthly"}'::jsonb, 'monthly', 7, true
            FROM products pr WHERE pr.slug = 'silklens_premium_monthly'
            ON CONFLICT (product_id, slug) DO UPDATE
                SET trial_days = EXCLUDED.trial_days, is_default = EXCLUDED.is_default
            """
        )
    )
    await db_session.execute(
        text(
            """
            INSERT INTO product_plans (
                tenant_id, product_id, slug, name, billing_period, trial_days, is_default
            )
            SELECT pr.tenant_id, pr.id, 'premium_yearly_paid',
                   '{"en":"Premium yearly"}'::jsonb, 'yearly', 0, false
            FROM products pr WHERE pr.slug = 'silklens_premium_yearly'
            ON CONFLICT (product_id, slug) DO NOTHING
            """
        )
    )
    await db_session.execute(
        text(
            """
            INSERT INTO prices (plan_id, pricing_zone_id, currency, amount, effective_from)
            SELECT pp.id, pz.id, 'USD', 4.99, now()
            FROM product_plans pp
            CROSS JOIN pricing_zones pz
            WHERE pp.slug = 'premium_monthly' AND pz.slug = 'cis'
            ON CONFLICT (plan_id, pricing_zone_id, currency, effective_from) DO NOTHING
            """
        )
    )
    await db_session.execute(
        text(
            """
            INSERT INTO prices (plan_id, pricing_zone_id, currency, amount, effective_from)
            SELECT pp.id, pz.id, 'USD', 39.99, now()
            FROM product_plans pp
            CROSS JOIN pricing_zones pz
            WHERE pp.slug = 'premium_yearly_paid' AND pz.slug = 'cis'
            ON CONFLICT (plan_id, pricing_zone_id, currency, effective_from) DO NOTHING
            """
        )
    )
    await db_session.execute(
        text(
            """
            INSERT INTO plan_features (plan_id, feature_key, enabled, limit_value)
            SELECT pp.id, 'ai_chat_unlimited', true, NULL
            FROM product_plans pp WHERE pp.slug = 'premium_monthly'
            ON CONFLICT (plan_id, feature_key) DO NOTHING
            """
        )
    )
    await db_session.execute(
        text(
            """
            INSERT INTO plan_features (plan_id, feature_key, enabled, limit_value)
            SELECT pp.id, 'ad_free', true, NULL
            FROM product_plans pp WHERE pp.slug = 'premium_monthly'
            ON CONFLICT (plan_id, feature_key) DO NOTHING
            """
        )
    )
    await db_session.commit()
    return {"trial_plan": "premium_monthly", "paid_plan": "premium_yearly_paid"}


# --- Public list ----------------------------------------------------------


@pytest.mark.asyncio
async def test_list_plans_public_returns_seeded_plans(
    http: AsyncClient, billing_seed: dict[str, str]
) -> None:
    response = await http.get("/v1/billing/plans?pricing_zone=cis")
    assert response.status_code == 200, response.text
    body = response.json()
    slugs = {p["slug"] for p in body["items"]}
    assert "premium_monthly" in slugs
    assert body["pricing_zone"] == "cis"


# --- Trial subscription (idempotent) --------------------------------------


@pytest.mark.asyncio
async def test_start_subscription_creates_trial(
    http: AsyncClient, billing_seed: dict[str, str]
) -> None:
    auth = await _register(http)
    idem = f"key-{uuid.uuid4().hex}"
    response = await http.post(
        "/v1/billing/subscriptions",
        headers={
            "Authorization": f"Bearer {auth['tokens']['access_token']}",
            "Idempotency-Key": idem,
        },
        json={
            "plan_slug": billing_seed["trial_plan"],
            "payment_method_token": "tok_success",
            "pricing_zone_slug": "cis",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["subscription"]["status"] == "trial"
    # trial path doesn't surface a payment_intent
    assert body["payment_intent"] is None


@pytest.mark.asyncio
async def test_start_subscription_paid_path_succeeds(
    http: AsyncClient, billing_seed: dict[str, str]
) -> None:
    auth = await _register(http)
    idem = f"key-{uuid.uuid4().hex}"
    response = await http.post(
        "/v1/billing/subscriptions",
        headers={
            "Authorization": f"Bearer {auth['tokens']['access_token']}",
            "Idempotency-Key": idem,
        },
        json={
            "plan_slug": billing_seed["paid_plan"],
            "payment_method_token": "tok_success",
            "pricing_zone_slug": "cis",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["subscription"]["status"] == "active"
    assert body["payment_intent"] is not None
    assert body["payment_intent"]["status"] == "succeeded"


@pytest.mark.asyncio
async def test_start_subscription_failed_payment_returns_402(
    http: AsyncClient, billing_seed: dict[str, str]
) -> None:
    auth = await _register(http)
    idem = f"key-{uuid.uuid4().hex}"
    response = await http.post(
        "/v1/billing/subscriptions",
        headers={
            "Authorization": f"Bearer {auth['tokens']['access_token']}",
            "Idempotency-Key": idem,
        },
        json={
            "plan_slug": billing_seed["paid_plan"],
            "payment_method_token": "fail_card_declined",
            "pricing_zone_slug": "cis",
        },
    )
    assert response.status_code == 402, response.text
    assert response.json()["detail"]["code"] == "billing.payment_failed"


@pytest.mark.asyncio
async def test_start_subscription_idempotent_retry(
    http: AsyncClient, billing_seed: dict[str, str]
) -> None:
    auth = await _register(http)
    idem = f"key-{uuid.uuid4().hex}"

    first = await http.post(
        "/v1/billing/subscriptions",
        headers={
            "Authorization": f"Bearer {auth['tokens']['access_token']}",
            "Idempotency-Key": idem,
        },
        json={
            "plan_slug": billing_seed["paid_plan"],
            "payment_method_token": "tok_ok",
            "pricing_zone_slug": "cis",
        },
    )
    assert first.status_code == 201, first.text
    sub_id_first = first.json()["subscription"]["id"]

    second = await http.post(
        "/v1/billing/subscriptions",
        headers={
            "Authorization": f"Bearer {auth['tokens']['access_token']}",
            "Idempotency-Key": idem,
        },
        json={
            "plan_slug": billing_seed["paid_plan"],
            "payment_method_token": "tok_ok",
            "pricing_zone_slug": "cis",
        },
    )
    assert second.status_code == 201, second.text
    assert second.json()["subscription"]["id"] == sub_id_first


# --- Cancel + resume ------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_at_period_end_then_resume(
    http: AsyncClient, billing_seed: dict[str, str]
) -> None:
    auth = await _register(http)
    headers = {"Authorization": f"Bearer {auth['tokens']['access_token']}"}
    await http.post(
        "/v1/billing/subscriptions",
        headers={**headers, "Idempotency-Key": f"k-{uuid.uuid4().hex}"},
        json={
            "plan_slug": billing_seed["trial_plan"],
            "payment_method_token": "tok_ok",
        },
    )
    cancel = await http.post(
        "/v1/billing/subscriptions/cancel",
        headers=headers,
        json={"at_period_end": True},
    )
    assert cancel.status_code == 200, cancel.text
    body = cancel.json()
    assert body["cancel_at_period_end"] is True
    assert body["status"] == "trial"

    resume = await http.post("/v1/billing/subscriptions/resume", headers=headers)
    assert resume.status_code == 200, resume.text
    assert resume.json()["cancel_at_period_end"] is False


# --- Entitlements --------------------------------------------------------


@pytest.mark.asyncio
async def test_entitlements_materialised_after_subscribe(
    http: AsyncClient, billing_seed: dict[str, str]
) -> None:
    auth = await _register(http)
    headers = {"Authorization": f"Bearer {auth['tokens']['access_token']}"}
    await http.post(
        "/v1/billing/subscriptions",
        headers={**headers, "Idempotency-Key": f"k-{uuid.uuid4().hex}"},
        json={
            "plan_slug": billing_seed["trial_plan"],
            "payment_method_token": "tok_ok",
        },
    )
    entitlements = await http.get("/v1/billing/me/entitlements", headers=headers)
    assert entitlements.status_code == 200
    body = entitlements.json()
    feature_keys = {e["feature_key"] for e in body["items"]}
    assert "ai_chat_unlimited" in feature_keys
    assert "ad_free" in feature_keys


# --- Webhooks idempotency -------------------------------------------------

# Shared-secret header guards the endpoint until per-provider signature
# verification lands in FAZA 4. Matches SILKLENS_WEBHOOK_SHARED_SECRET default
# in src/core/settings.py.
_WEBHOOK_HEADERS = {"X-Silklens-Webhook-Secret": "dev-only-webhook-shared-secret"}


@pytest.mark.asyncio
async def test_webhook_first_call_records(http: AsyncClient) -> None:
    response = await http.post(
        "/v1/billing/webhooks/stripe",
        json={"id": f"evt_{uuid.uuid4().hex}", "type": "payment_intent.succeeded"},
        headers=_WEBHOOK_HEADERS,
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"received": True, "duplicate": False}


@pytest.mark.asyncio
async def test_webhook_replay_is_idempotent(http: AsyncClient) -> None:
    event_id = f"evt_{uuid.uuid4().hex}"
    payload = {"id": event_id, "type": "payment_intent.succeeded"}
    first = await http.post("/v1/billing/webhooks/stripe", json=payload, headers=_WEBHOOK_HEADERS)
    second = await http.post("/v1/billing/webhooks/stripe", json=payload, headers=_WEBHOOK_HEADERS)
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["duplicate"] is True


@pytest.mark.asyncio
async def test_webhook_unknown_provider_rejected(http: AsyncClient) -> None:
    response = await http.post(
        "/v1/billing/webhooks/madeup",
        json={"id": "evt_x", "type": "foo"},
        headers=_WEBHOOK_HEADERS,
    )
    # Provider allow-list rejects with 404 (unknown provider).
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "billing.webhook_unknown_provider"


@pytest.mark.asyncio
async def test_webhook_rejects_missing_secret(http: AsyncClient) -> None:
    response = await http.post(
        "/v1/billing/webhooks/stripe",
        json={"id": "evt_z", "type": "payment_intent.succeeded"},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "billing.webhook_unauthorized"


# --- Subscription endpoint -------------------------------------------------


@pytest.mark.asyncio
async def test_me_subscription_null_for_new_user(http: AsyncClient) -> None:
    auth = await _register(http)
    response = await http.get(
        "/v1/billing/me/subscription",
        headers={"Authorization": f"Bearer {auth['tokens']['access_token']}"},
    )
    assert response.status_code == 200
    assert response.json() is None


# --- MED-B2: invoice number generated by trigger ---------------------------


@pytest.mark.asyncio
async def test_invoice_number_generated_by_trigger(
    http: AsyncClient, db_session: AsyncSession
) -> None:
    """MED-B2: ``invoices.number`` is generated by ``tg_invoice_number``.

    The repo no longer passes ``number = ''``; the column is omitted and
    the BEFORE INSERT trigger fills it with ``SLN-YYYY-NNNNNNN``. We
    invoke the repository directly so the test focuses on the row shape
    rather than the subscribe orchestration (which doesn't open invoices
    in this FAZA — that happens via the period-renewal worker).
    """
    import re
    from decimal import Decimal

    from src.infrastructure.billing.repository import SqlInvoiceRepository

    auth = await _register(http)
    user_pub_id = auth["user"]["pub_id"]
    user_row = (
        await db_session.execute(
            text("SELECT id, residency_region FROM users WHERE pub_id = :p"),
            {"p": user_pub_id},
        )
    ).one()
    user_id = user_row._mapping["id"]
    residency = user_row._mapping["residency_region"]

    repo = SqlInvoiceRepository(db_session)
    invoice = await repo.create(
        tenant_id=uuid.UUID(DEFAULT_TENANT_ID),
        user_id=user_id,
        residency_region=residency,
        subscription_id=None,
        total=Decimal("12.34"),
        currency="USD",
    )
    # SLN-YYYY-NNNNNNN — seven-digit zero-padded sequence
    assert re.fullmatch(r"SLN-\d{4}-\d{7}", invoice.number), invoice.number


# --- MED-B1: payment.captured.v1 only on first insert ---------------------


@pytest.mark.asyncio
async def test_record_payment_emits_event_only_once(
    http: AsyncClient,
    db_session: AsyncSession,
    billing_seed: dict[str, str],
) -> None:
    """MED-B1: a duplicate ``record_payment`` call must NOT re-emit the event.

    We force the ledger insert twice with the same
    ``(provider, provider_charge_id)`` using the repository directly, after
    the HTTP flow has set up a valid subscription + intent. The first call
    inserts and emits ``payment.captured.v1`` once; the retry sees the
    ``ON CONFLICT DO NOTHING`` short-circuit and skips the emit.
    """
    from decimal import Decimal

    from src.infrastructure.billing.repository import SqlPaymentRepository

    # Walk the happy path so the intent + payment exist.
    auth = await _register(http)
    response = await http.post(
        "/v1/billing/subscriptions",
        headers={
            "Authorization": f"Bearer {auth['tokens']['access_token']}",
            "Idempotency-Key": f"med-b1-{uuid.uuid4().hex}",
        },
        json={
            "plan_slug": billing_seed["paid_plan"],
            "payment_method_token": "tok_double_emit",
            "pricing_zone_slug": "cis",
        },
    )
    assert response.status_code == 201, response.text
    intent_id_str = response.json()["payment_intent"]["id"]

    intent_row = (
        await db_session.execute(
            text(
                """
                SELECT pi.id, p.provider, p.provider_charge_id, p.captured_amount, p.currency
                FROM payment_intents pi
                JOIN payments p ON p.intent_id = pi.id
                WHERE pi.id = CAST(:iid AS uuid)
                """
            ),
            {"iid": intent_id_str},
        )
    ).one_or_none()
    assert intent_row is not None
    m = intent_row._mapping
    intent_id = m["id"]
    charge_id = m["provider_charge_id"]

    # Retry the same payment — should be a NO-OP for both ledger + outbox.
    intent_repo = SqlPaymentRepository(db_session)
    await intent_repo.record_payment(
        intent_id=intent_id,
        provider=m["provider"],
        provider_charge_id=charge_id,
        captured_amount=Decimal(m["captured_amount"]),
        currency=m["currency"],
    )

    emitted = (
        await db_session.execute(
            text(
                """
                SELECT count(*)
                FROM event_outbox
                WHERE event_name = 'payment.captured.v1'
                  AND aggregate_id = :iid
                """
            ),
            {"iid": intent_id},
        )
    ).scalar_one()
    assert int(emitted) == 1
