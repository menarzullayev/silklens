"""Real-provider integration tests — WAVE-5 / FAZA 4.

Covers the boundary between mock and real provider wiring:

* Stripe ``verify_webhook`` accepts a signature we synthesise inline with the
  same HMAC scheme Stripe uses (``t=...,v1=hex``).
* Invalid Stripe signatures bubble up as 401.
* With ``SILKLENS_STRIPE_SECRET_KEY`` unset the factory soft-falls-back to
  ``MockPaymentProvider``.
* Anthropic provider soft-falls when ``ANTHROPIC_API_KEY`` is unset.
* Provider resolver still returns a usable chain in mock mode.
* Live Anthropic round-trip is **skipped** unless the env key is present.

None of these tests require live API keys.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import uuid
from typing import Any

import pytest
from httpx import AsyncClient

from src.core.settings import Settings, get_settings
from src.domain.ai.entities import LlmRequest
from src.domain.ai.errors import AiProviderUnavailable
from src.domain.billing.errors import (
    InvalidWebhookSignature,
    ProviderUnavailable,
)
from src.infrastructure.ai.anthropic_provider import AnthropicLlmProvider
from src.infrastructure.ai.mock_providers import MockLlmProvider
from src.infrastructure.billing.factory import (
    build_payment_provider,
    build_stripe_provider_from_settings,
    is_real_stripe_active,
)
from src.infrastructure.billing.mock_provider import MockPaymentProvider
from src.infrastructure.billing.stripe_provider import StripeProvider, _to_minor_units

pytestmark = pytest.mark.unit


# --- Helpers ---------------------------------------------------------------


def _sign_stripe_payload(payload: str, secret: str, *, ts: int | None = None) -> str:
    """Mint a Stripe-style ``Stripe-Signature`` header for offline tests."""
    timestamp = ts if ts is not None else int(time.time())
    signed = f"{timestamp}.{payload}".encode()
    sig = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={sig}"


def _stripe_event_payload(event_id: str | None = None, **overrides: Any) -> dict[str, Any]:
    """Build a Stripe-shaped event body suitable for ``construct_event``."""
    body: dict[str, Any] = {
        "id": event_id or f"evt_{uuid.uuid4().hex}",
        "type": "payment_intent.succeeded",
        "object": "event",
        "data": {
            "object": {
                "id": f"pi_{uuid.uuid4().hex}",
                "amount": 499,
                "amount_received": 499,
                "currency": "usd",
                "metadata": {"idempotency_key": "idem-xyz"},
            }
        },
    }
    body.update(overrides)
    return body


# --- 1. Stripe webhook signature verification ------------------------------


def test_stripe_verify_webhook_accepts_valid_signature() -> None:
    secret = "whsec_test_secret"
    provider = StripeProvider(api_key="sk_test_x", webhook_secret=secret)
    payload = json.dumps(_stripe_event_payload(event_id="evt_valid_sig"))
    header = _sign_stripe_payload(payload, secret)
    event = provider.verify_webhook(payload=payload.encode(), signature=header)
    assert event["id"] == "evt_valid_sig"
    assert event["type"] == "payment_intent.succeeded"


def test_stripe_verify_webhook_rejects_bad_signature() -> None:
    provider = StripeProvider(api_key="sk_test_x", webhook_secret="whsec_test_secret")
    payload = json.dumps(_stripe_event_payload(event_id="evt_bad_sig"))
    bogus_header = "t=0,v1=" + "00" * 32
    with pytest.raises(InvalidWebhookSignature):
        provider.verify_webhook(payload=payload.encode(), signature=bogus_header)


def test_stripe_verify_webhook_raises_when_secret_missing() -> None:
    provider = StripeProvider(api_key="sk_test_x", webhook_secret="")
    with pytest.raises(ProviderUnavailable):
        provider.verify_webhook(payload=b"{}", signature="t=0,v1=00")


# --- 2. Stripe factory fallback when keys missing --------------------------


def test_factory_falls_back_to_mock_when_stripe_keys_missing() -> None:
    settings = Settings(  # type: ignore[call-arg]
        payment_provider="stripe",
        stripe_secret_key="",
        stripe_webhook_secret="",
    )
    provider = build_payment_provider(settings)
    assert isinstance(provider, MockPaymentProvider)
    assert not is_real_stripe_active(settings)


def test_factory_returns_stripe_when_keys_present() -> None:
    settings = Settings(  # type: ignore[call-arg]
        payment_provider="stripe",
        stripe_secret_key="sk_test_factory",
        stripe_webhook_secret="whsec_factory",
    )
    provider = build_payment_provider(settings)
    assert isinstance(provider, StripeProvider)
    assert is_real_stripe_active(settings)
    stripe_prov = build_stripe_provider_from_settings(settings)
    assert isinstance(stripe_prov, StripeProvider)


def test_factory_default_is_mock_provider() -> None:
    settings = Settings()  # type: ignore[call-arg]
    assert settings.payment_provider == "mock"
    assert isinstance(build_payment_provider(settings), MockPaymentProvider)


# --- 3. Stripe currency conversion -----------------------------------------


def test_to_minor_units_two_decimal_currency() -> None:
    from decimal import Decimal

    assert _to_minor_units(Decimal("4.99"), "USD") == 499
    assert _to_minor_units(Decimal("0.30"), "EUR") == 30


def test_to_minor_units_zero_decimal_currency() -> None:
    from decimal import Decimal

    # JPY uses no decimal — ¥500 must travel to Stripe as 500, not 50000.
    assert _to_minor_units(Decimal("500"), "JPY") == 500


# --- 4. Anthropic soft-fail when key missing -------------------------------


@pytest.mark.asyncio
async def test_anthropic_provider_soft_fails_without_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    provider = AnthropicLlmProvider(api_key=None)
    with pytest.raises(AiProviderUnavailable):
        await provider.call(LlmRequest(prompt="hello"))


# --- 5. Mock fallback at resolver layer when Anthropic key missing ---------


@pytest.mark.asyncio
async def test_resolver_yields_mock_when_anthropic_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without ANTHROPIC_API_KEY the resolver in mock mode returns MockLlm."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    class _DummySession:
        async def execute(self, *_a: object, **_k: object) -> object:
            raise AssertionError("mock mode must not hit the DB")

    from src.infrastructure.ai.resolver import ProviderResolver

    resolver = ProviderResolver(_DummySession(), use_mocks=True)  # type: ignore[arg-type]
    chain = await resolver.resolve_llm()
    assert chain and isinstance(chain[0], MockLlmProvider)


# --- 6. Webhook router — Stripe path lit up & end-to-end signature --------


@pytest.mark.asyncio
async def test_router_stripe_signature_path_accepts_signed_payload(
    http: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When SILKLENS_STRIPE_WEBHOOK_SECRET is set, the router verifies
    the Stripe-Signature header and accepts the event."""
    monkeypatch.setenv("SILKLENS_PAYMENT_PROVIDER", "stripe")
    monkeypatch.setenv("SILKLENS_STRIPE_SECRET_KEY", "sk_test_router")
    monkeypatch.setenv("SILKLENS_STRIPE_WEBHOOK_SECRET", "whsec_router")
    get_settings.cache_clear()  # type: ignore[attr-defined]
    try:
        payload = json.dumps(_stripe_event_payload(event_id=f"evt_rt_{uuid.uuid4().hex}"))
        header = _sign_stripe_payload(payload, "whsec_router")
        response = await http.post(
            "/v1/billing/webhooks/stripe",
            content=payload,
            headers={
                "Stripe-Signature": header,
                "Content-Type": "application/json",
            },
        )
        # Whether the DB integration is up or not, signature path must not 401.
        assert response.status_code != 401, response.text
    finally:
        for var in (
            "SILKLENS_PAYMENT_PROVIDER",
            "SILKLENS_STRIPE_SECRET_KEY",
            "SILKLENS_STRIPE_WEBHOOK_SECRET",
        ):
            monkeypatch.delenv(var, raising=False)
        get_settings.cache_clear()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_router_stripe_signature_path_rejects_bad_signature(
    http: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SILKLENS_PAYMENT_PROVIDER", "stripe")
    monkeypatch.setenv("SILKLENS_STRIPE_SECRET_KEY", "sk_test_router")
    monkeypatch.setenv("SILKLENS_STRIPE_WEBHOOK_SECRET", "whsec_router")
    get_settings.cache_clear()  # type: ignore[attr-defined]
    try:
        payload = json.dumps(_stripe_event_payload())
        bad_header = "t=0,v1=" + "ff" * 32
        response = await http.post(
            "/v1/billing/webhooks/stripe",
            content=payload,
            headers={
                "Stripe-Signature": bad_header,
                "Content-Type": "application/json",
            },
        )
        assert response.status_code == 401, response.text
        body = response.json()
        assert body["detail"]["code"] == "billing.webhook_invalid_signature"
    finally:
        for var in (
            "SILKLENS_PAYMENT_PROVIDER",
            "SILKLENS_STRIPE_SECRET_KEY",
            "SILKLENS_STRIPE_WEBHOOK_SECRET",
        ):
            monkeypatch.delenv(var, raising=False)
        get_settings.cache_clear()  # type: ignore[attr-defined]


# --- 7. Live Anthropic — only when ANTHROPIC_API_KEY is set ----------------


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set — skipping live Anthropic round-trip",
)
async def test_anthropic_real_call_returns_text() -> None:  # pragma: no cover
    provider = AnthropicLlmProvider(
        api_key=os.environ["ANTHROPIC_API_KEY"],
        model_id="claude-haiku-4-5-20251001",
    )
    resp = await provider.call(LlmRequest(prompt="Reply with exactly: pong", max_output_tokens=16))
    assert resp.text
    assert resp.input_tokens > 0
