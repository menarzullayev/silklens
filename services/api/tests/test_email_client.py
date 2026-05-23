"""Tests for email client implementations and the get_email_client() factory.

Coverage:
* StubEmailClient       — always returns a message_id, never raises.
* ResendEmailClient     — HTTP mocked via httpx.MockTransport.
* BrevoSmtpEmailClient  — smtplib.SMTP mocked via unittest.mock.patch.
* get_email_client()    — factory selects provider from settings.
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest
from pydantic import SecretStr

from src.infrastructure.notifications import email_client

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_settings(**overrides: Any) -> Any:
    """Return a minimal settings-like object with sensible defaults."""
    defaults: dict[str, Any] = {
        "email_provider": "resend",
        "email_from": "SilkLens <test@example.com>",
        "resend_api_key": SecretStr(""),
        "brevo_smtp_host": "smtp-relay.brevo.com",
        "brevo_smtp_port": 587,
        "brevo_smtp_login": "",
        "brevo_smtp_password": SecretStr(""),
    }
    defaults.update(overrides)
    return type("FakeSettings", (), defaults)()


# ---------------------------------------------------------------------------
# StubEmailClient
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stub_returns_message_id() -> None:
    client = email_client.StubEmailClient()
    result = await client.send_email(to="x@example.com", subject="hi", html=None, text="body")
    assert result["message_id"].startswith("stub_email_")


@pytest.mark.asyncio
async def test_stub_handles_html_text_combinations() -> None:
    client = email_client.StubEmailClient()
    for html, text in [(None, "t"), ("<p>h</p>", None), ("<p>h</p>", "t")]:
        result = await client.send_email(to="x@example.com", subject="s", html=html, text=text)
        assert "message_id" in result


# ---------------------------------------------------------------------------
# ResendEmailClient (httpx mocked)
# ---------------------------------------------------------------------------


def _resend_mock_transport(
    status: int = 200,
    response_json: dict[str, Any] | None = None,
    capture: dict[str, Any] | None = None,
) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if capture is not None:
            capture["url"] = str(request.url)
            capture["auth"] = request.headers.get("authorization")
            capture["body"] = request.read().decode()
        return httpx.Response(status, json=response_json or {"id": "msg_test_ok"})

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_resend_posts_to_correct_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    transport = _resend_mock_transport(capture=captured)
    real = httpx.AsyncClient
    monkeypatch.setattr(
        email_client.httpx, "AsyncClient", lambda **kw: real(transport=transport, **kw)
    )

    client = email_client.ResendEmailClient(
        api_key="re_TEST", from_address="SilkLens <no-reply@x.com>"
    )
    result = await client.send_email(
        to="user@example.com", subject="Hi", html=None, text="Plain body"
    )

    assert result["message_id"] == "msg_test_ok"
    assert captured["url"] == "https://api.resend.com/emails"
    assert captured["auth"] == "Bearer re_TEST"
    assert "user@example.com" in captured["body"]
    assert "Plain body" in captured["body"]


@pytest.mark.asyncio
async def test_resend_plain_text_only_no_html_leaked(monkeypatch: pytest.MonkeyPatch) -> None:
    """Critical: plain-text-only path must not include HTML tags (mail.ru §8.1)."""
    captured: dict[str, Any] = {}
    transport = _resend_mock_transport(capture=captured)
    real = httpx.AsyncClient
    monkeypatch.setattr(
        email_client.httpx, "AsyncClient", lambda **kw: real(transport=transport, **kw)
    )

    client = email_client.ResendEmailClient("k", "f")
    await client.send_email(to="u@x.com", subject="s", html=None, text="only text")

    assert "only text" in captured["body"]
    assert "<" not in captured["body"]


@pytest.mark.asyncio
async def test_resend_raises_on_4xx(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = _resend_mock_transport(status=403, response_json={"message": "domain not verified"})
    real = httpx.AsyncClient
    monkeypatch.setattr(
        email_client.httpx, "AsyncClient", lambda **kw: real(transport=transport, **kw)
    )

    client = email_client.ResendEmailClient("k", "f")
    with pytest.raises(httpx.HTTPStatusError):
        await client.send_email(to="u@x.com", subject="s", html=None, text="t")


# ---------------------------------------------------------------------------
# BrevoSmtpEmailClient (smtplib mocked)
# ---------------------------------------------------------------------------


_BREVO_TEST_PWD = "s3cr3t-test-only"


def _make_brevo_client(
    host: str = "smtp-relay.brevo.com",
    port: int = 587,
    login: str = "test@smtp-brevo.com",
    password: str = _BREVO_TEST_PWD,
    from_address: str = "SilkLens <sender@example.com>",
) -> email_client.BrevoSmtpEmailClient:
    return email_client.BrevoSmtpEmailClient(
        host=host,
        port=port,
        login=login,
        password=password,
        from_address=from_address,
    )


@pytest.mark.asyncio
async def test_brevo_sends_via_smtp_starttls() -> None:
    """BrevoSmtpEmailClient must call STARTTLS + login + send_message."""
    mock_smtp_instance = MagicMock()

    with patch("smtplib.SMTP") as mock_smtp_class:
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_smtp_instance)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

        client = _make_brevo_client()
        result = await client.send_email(
            to="recv@example.com", subject="OTP", html=None, text="123456"
        )

    mock_smtp_instance.ehlo.assert_called()
    mock_smtp_instance.starttls.assert_called_once()
    mock_smtp_instance.login.assert_called_once_with("test@smtp-brevo.com", _BREVO_TEST_PWD)
    mock_smtp_instance.send_message.assert_called_once()

    assert result["message_id"].startswith("brevo_")


@pytest.mark.asyncio
async def test_brevo_message_has_correct_headers() -> None:
    """Subject, To, and From must appear in the sent EmailMessage."""
    sent_messages: list[EmailMessage] = []
    mock_smtp_instance = MagicMock()
    mock_smtp_instance.send_message.side_effect = lambda msg: sent_messages.append(msg)

    with patch("smtplib.SMTP") as mock_smtp_class:
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_smtp_instance)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

        client = _make_brevo_client(from_address="SilkLens <noreply@silklens.app>")
        await client.send_email(
            to="user@gmail.com",
            subject="Your OTP code",
            html=None,
            text="Your code: 847291",
        )

    assert len(sent_messages) == 1
    msg = sent_messages[0]
    assert msg["To"] == "user@gmail.com"
    assert msg["Subject"] == "Your OTP code"
    assert "SilkLens" in msg["From"]


@pytest.mark.asyncio
async def test_brevo_plain_text_only_when_html_is_none() -> None:
    """Plain-text-only send must not attach an HTML part."""
    sent_messages: list[EmailMessage] = []
    mock_smtp_instance = MagicMock()
    mock_smtp_instance.send_message.side_effect = lambda msg: sent_messages.append(msg)

    with patch("smtplib.SMTP") as mock_smtp_class:
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_smtp_instance)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

        client = _make_brevo_client()
        await client.send_email(to="u@x.com", subject="s", html=None, text="plain only")

    msg = sent_messages[0]
    # EmailMessage with only set_content() has no multipart structure.
    assert not msg.is_multipart()


@pytest.mark.asyncio
async def test_brevo_raises_on_smtp_error() -> None:
    """SMTPException must propagate so the caller can handle it."""
    mock_smtp_instance = MagicMock()
    mock_smtp_instance.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Auth failed")

    with patch("smtplib.SMTP") as mock_smtp_class:
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_smtp_instance)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

        client = _make_brevo_client()
        with pytest.raises(smtplib.SMTPAuthenticationError):
            await client.send_email(to="u@x.com", subject="s", html=None, text="t")


# ---------------------------------------------------------------------------
# Factory — get_email_client()
# ---------------------------------------------------------------------------


def test_factory_resend_provider_returns_resend_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        email_client,
        "get_settings",
        lambda: _fake_settings(email_provider="resend", resend_api_key=SecretStr("re_live_key")),
    )
    client = email_client.get_email_client()
    assert isinstance(client, email_client.ResendEmailClient)


def test_factory_brevo_provider_returns_brevo_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        email_client,
        "get_settings",
        lambda: _fake_settings(
            email_provider="brevo",
            brevo_smtp_login="user@smtp-brevo.com",
            brevo_smtp_password=SecretStr("pass"),
        ),
    )
    client = email_client.get_email_client()
    assert isinstance(client, email_client.BrevoSmtpEmailClient)


def test_factory_resend_missing_key_falls_back_to_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        email_client,
        "get_settings",
        lambda: _fake_settings(email_provider="resend", resend_api_key=SecretStr("")),
    )
    client = email_client.get_email_client()
    assert isinstance(client, email_client.StubEmailClient)


def test_factory_brevo_no_creds_falls_back_to_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        email_client,
        "get_settings",
        lambda: _fake_settings(
            email_provider="brevo",
            brevo_smtp_login="",
            brevo_smtp_password=SecretStr(""),
        ),
    )
    client = email_client.get_email_client()
    assert isinstance(client, email_client.StubEmailClient)


def test_factory_unknown_provider_falls_back_to_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        email_client,
        "get_settings",
        lambda: _fake_settings(email_provider="mailgun"),
    )
    client = email_client.get_email_client()
    assert isinstance(client, email_client.StubEmailClient)
