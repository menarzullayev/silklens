"""Multi-currency payment provider tests — WAVE-6 / FAZA 5.

Covers:

* Payme adapter: Basic-auth header round-trip + rejection paths.
* Click adapter: MD5 sign-string verification (positive + tampered-negative).
* PayPal adapter: soft-fall to mock when client_id / client_secret unset.
* Factory: per-currency routing (UZS → Payme, USD → Stripe, fall back to mock).
* Protocol structural conformance for all three new providers.

No test requires live keys.
"""

from __future__ import annotations

import base64
from decimal import Decimal

import pytest

from src.core.settings import Settings
from src.domain.billing.errors import (
    InvalidWebhookSignature,
    ProviderUnavailable,
)
from src.domain.billing.service import PaymentProvider
from src.infrastructure.billing.click_provider import (
    CLICK_ACTION_TO_EVENT,
    ClickPaymentProvider,
    click_hmac_sha1,
    click_sign_string,
)
from src.infrastructure.billing.factory import (
    DEFAULT_PROVIDER_BY_CURRENCY,
    build_payment_provider_for_currency,
)
from src.infrastructure.billing.mock_provider import MockPaymentProvider
from src.infrastructure.billing.payme_provider import (
    PAYME_METHOD_TO_EVENT,
    PaymePaymentProvider,
    tiyin_to_uzs,
    uzs_to_tiyin,
)
from src.infrastructure.billing.paypal_provider import PayPalPaymentProvider
from src.infrastructure.billing.stripe_provider import StripeProvider

pytestmark = pytest.mark.unit


# --- Helpers ---------------------------------------------------------------


def _basic_auth(login: str, password: str) -> str:
    blob = base64.b64encode(f"{login}:{password}".encode()).decode()
    return f"Basic {blob}"


# --- 1. Payme provider -----------------------------------------------------


def test_payme_provider_verifies_basic_auth_header() -> None:
    """Properly-encoded Basic header is accepted; JSON-RPC method maps to event."""
    provider = PaymePaymentProvider(merchant_id="merch_xyz", secret_key="topsecret")
    headers = {"Authorization": _basic_auth("Paycom", "topsecret")}
    body = {
        "jsonrpc": "2.0",
        "id": 12345,
        "method": "CreateTransaction",
        "params": {"id": "txn_abc", "amount": 50000},
    }
    event = provider.verify_webhook(headers=headers, body=body)
    assert event.method == "CreateTransaction"
    assert event.event_type == PAYME_METHOD_TO_EVENT["CreateTransaction"]
    assert event.provider_event_id == "txn_abc"


def test_payme_provider_rejects_stripped_authorization_header() -> None:
    provider = PaymePaymentProvider(merchant_id="merch_xyz", secret_key="topsecret")
    body = {"method": "CheckPerformTransaction", "params": {}, "id": 1}
    with pytest.raises(InvalidWebhookSignature):
        provider.verify_webhook(headers={}, body=body)


def test_payme_provider_rejects_wrong_secret() -> None:
    provider = PaymePaymentProvider(merchant_id="merch_xyz", secret_key="topsecret")
    headers = {"Authorization": _basic_auth("Paycom", "wrong-secret")}
    with pytest.raises(InvalidWebhookSignature):
        provider.verify_webhook(
            headers=headers,
            body={"method": "CheckPerformTransaction", "params": {}, "id": 1},
        )


def test_payme_provider_soft_fails_without_keys() -> None:
    provider = PaymePaymentProvider(merchant_id="", secret_key="")
    import asyncio

    with pytest.raises(ProviderUnavailable):
        asyncio.run(
            provider.create_payment_intent(
                amount=Decimal("100.00"),
                currency="UZS",
                customer_ref="u_1",
                idempotency_key="idem-1",
            )
        )


def test_payme_tiyin_roundtrip() -> None:
    assert uzs_to_tiyin(Decimal("123.45")) == 12345
    assert tiyin_to_uzs(12345) == Decimal("123.45")


# --- 2. Click provider -----------------------------------------------------


def test_click_provider_accepts_valid_sign_string() -> None:
    provider = ClickPaymentProvider(
        service_id="svc_42",
        merchant_id="merch_99",
        secret_key="shh_click_secret",
    )
    sign_time = "2026-05-18 12:00:00"
    sign = click_sign_string(
        click_trans_id="click_tx_1",
        service_id="svc_42",
        secret_key="shh_click_secret",
        merchant_trans_id="idem-2",
        amount="50000",
        action="1",
        sign_time=sign_time,
    )
    form = {
        "click_trans_id": "click_tx_1",
        "service_id": "svc_42",
        "merchant_trans_id": "idem-2",
        "amount": "50000",
        "action": "1",
        "sign_time": sign_time,
        "sign_string": sign,
    }
    event = provider.verify_webhook(form)
    assert event.action == "1"
    assert event.event_type == CLICK_ACTION_TO_EVENT["1"]
    assert event.amount == Decimal("50000")
    assert event.click_trans_id == "click_tx_1"


def test_click_provider_rejects_tampered_sign_string() -> None:
    provider = ClickPaymentProvider(
        service_id="svc_42", merchant_id="merch_99", secret_key="shh_click_secret"
    )
    sign_time = "2026-05-18 12:00:00"
    good_sign = click_sign_string(
        click_trans_id="click_tx_2",
        service_id="svc_42",
        secret_key="shh_click_secret",
        merchant_trans_id="idem-3",
        amount="50000",
        action="1",
        sign_time=sign_time,
    )
    # Attacker swaps amount but keeps the original signature.
    form = {
        "click_trans_id": "click_tx_2",
        "service_id": "svc_42",
        "merchant_trans_id": "idem-3",
        "amount": "5000000",  # tampered
        "action": "1",
        "sign_time": sign_time,
        "sign_string": good_sign,
    }
    with pytest.raises(InvalidWebhookSignature):
        provider.verify_webhook(form)


def test_click_hmac_sha1_helper_round_trip() -> None:
    sig = click_hmac_sha1(
        click_trans_id="click_tx_3",
        service_id="svc_42",
        click_paydoc_id="doc_1",
        amount="1000",
        action="0",
        sign_time="2026-05-18 13:00:00",
        merchant_user_id="user_77",
        secret_key="hmac_secret",
    )
    sig2 = click_hmac_sha1(
        click_trans_id="click_tx_3",
        service_id="svc_42",
        click_paydoc_id="doc_1",
        amount="1000",
        action="0",
        sign_time="2026-05-18 13:00:00",
        merchant_user_id="user_77",
        secret_key="hmac_secret",
    )
    assert sig == sig2
    sig_diff = click_hmac_sha1(
        click_trans_id="click_tx_3",
        service_id="svc_42",
        click_paydoc_id="doc_1",
        amount="1000",
        action="0",
        sign_time="2026-05-18 13:00:00",
        merchant_user_id="user_77",
        secret_key="different_secret",
    )
    assert sig != sig_diff


def test_click_provider_soft_fails_without_keys() -> None:
    provider = ClickPaymentProvider(service_id="", merchant_id="", secret_key="")
    with pytest.raises(ProviderUnavailable):
        provider.verify_webhook({"action": "1"})


# --- 3. PayPal provider ----------------------------------------------------


def test_paypal_provider_soft_fails_without_creds() -> None:
    """Factory falls back to MockPaymentProvider when PayPal client_id is empty."""
    settings = Settings(  # type: ignore[call-arg]
        payment_provider="paypal",
        paypal_client_id="",
        paypal_client_secret="",
    )
    provider = build_payment_provider_for_currency(
        "USD", settings=settings, overrides={"USD": "paypal"}
    )
    assert isinstance(provider, MockPaymentProvider)


def test_paypal_provider_rejects_missing_webhook_headers() -> None:
    provider = PayPalPaymentProvider(client_id="cid", client_secret="csec", webhook_id="wh_test")
    with pytest.raises(InvalidWebhookSignature):
        provider.verify_webhook(headers={}, body={"event_type": "X", "id": "1"})


# --- 4. Factory routing ----------------------------------------------------


def test_factory_routes_uzs_to_payme_when_configured() -> None:
    settings = Settings(  # type: ignore[call-arg]
        payment_provider="mock",
        payme_merchant_id="merch_xyz",
        payme_secret_key="shh",
    )
    provider = build_payment_provider_for_currency("UZS", settings=settings)
    assert isinstance(provider, PaymePaymentProvider)


def test_factory_routes_usd_to_stripe_when_configured() -> None:
    settings = Settings(  # type: ignore[call-arg]
        payment_provider="mock",
        stripe_secret_key="sk_test",
        stripe_webhook_secret="whsec",
    )
    provider = build_payment_provider_for_currency("USD", settings=settings)
    assert isinstance(provider, StripeProvider)


def test_factory_falls_back_to_mock_for_unconfigured_currency() -> None:
    settings = Settings(payment_provider="mock")  # type: ignore[call-arg]
    # XYZ isn't in the default map and has no override → DEFAULT slot kicks in.
    provider = build_payment_provider_for_currency("XYZ", settings=settings)
    assert isinstance(provider, MockPaymentProvider)


def test_factory_respects_admin_override() -> None:
    settings = Settings(  # type: ignore[call-arg]
        payment_provider="mock",
        click_service_id="svc_42",
        click_merchant_id="merch_99",
        click_secret_key="click_secret",
    )
    provider = build_payment_provider_for_currency(
        "UZS", overrides={"UZS": "click"}, settings=settings
    )
    assert isinstance(provider, ClickPaymentProvider)


def test_factory_falls_back_to_mock_when_payme_keys_missing() -> None:
    settings = Settings(  # type: ignore[call-arg]
        payment_provider="mock",
        payme_merchant_id="",
        payme_secret_key="",
    )
    provider = build_payment_provider_for_currency("UZS", settings=settings)
    assert isinstance(provider, MockPaymentProvider)


def test_default_provider_by_currency_map_shape() -> None:
    assert DEFAULT_PROVIDER_BY_CURRENCY["UZS"] == "payme"
    assert DEFAULT_PROVIDER_BY_CURRENCY["USD"] == "stripe"
    assert DEFAULT_PROVIDER_BY_CURRENCY["EUR"] == "stripe"


# --- 5. Structural protocol conformance ------------------------------------


def _implements_protocol(obj: object) -> bool:
    """PaymentProvider is a structural Protocol — assert all members are present."""
    return (
        hasattr(obj, "name")
        and callable(getattr(obj, "create_payment_intent", None))
        and callable(getattr(obj, "confirm_payment_intent", None))
    )


def test_payme_provider_implements_payment_provider_protocol() -> None:
    provider = PaymePaymentProvider(merchant_id="m", secret_key="s")
    assert _implements_protocol(provider)
    assert provider.name == "payme"
    # Static-type check: assignment to the Protocol should pass mypy at the
    # call-site. The runtime structural assertion above is enough for pytest.
    typed: PaymentProvider = provider  # noqa: F841


def test_click_provider_implements_payment_provider_protocol() -> None:
    provider = ClickPaymentProvider(service_id="x", merchant_id="y", secret_key="z")
    assert _implements_protocol(provider)
    assert provider.name == "click"
    typed: PaymentProvider = provider  # noqa: F841


def test_paypal_provider_implements_payment_provider_protocol() -> None:
    provider = PayPalPaymentProvider(client_id="cid", client_secret="csec", webhook_id="wh")
    assert _implements_protocol(provider)
    assert provider.name == "paypal"
    typed: PaymentProvider = provider  # noqa: F841
