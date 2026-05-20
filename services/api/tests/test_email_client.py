"""Tests for the Resend / Stub email client and the get_email_client factory.

ResendEmailClient is unit-tested with httpx's MockTransport — no live API
calls. The factory test verifies the env-driven selection between Resend
and the stub.
"""

from __future__ import annotations

import httpx
import pytest
from pydantic import SecretStr

from src.infrastructure.notifications import email_client


# --- StubEmailClient --------------------------------------------------------


@pytest.mark.asyncio
async def test_stub_returns_message_id_and_never_raises() -> None:
    client = email_client.StubEmailClient()
    result = await client.send_email(
        to="x@example.com",
        subject="hi",
        html=None,
        text="body",
    )
    assert result["message_id"].startswith("stub_email_")


@pytest.mark.asyncio
async def test_stub_handles_html_only_or_text_only() -> None:
    client = email_client.StubEmailClient()
    for html, text in [(None, "t"), ("<p>h</p>", None), ("<p>h</p>", "t")]:
        result = await client.send_email(
            to="x@example.com", subject="s", html=html, text=text
        )
        assert "message_id" in result


# --- ResendEmailClient (httpx mocked) ---------------------------------------


@pytest.mark.asyncio
async def test_resend_posts_to_correct_endpoint_with_bearer(monkeypatch) -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("authorization")
        captured["body"] = request.read().decode()
        return httpx.Response(200, json={"id": "msg_test_123"})

    transport = httpx.MockTransport(handler)

    # Patch AsyncClient to use the mock transport
    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        email_client.httpx,
        "AsyncClient",
        lambda **kw: real_async_client(transport=transport, **kw),
    )

    client = email_client.ResendEmailClient(
        api_key="re_TEST_KEY_xxx",
        from_address="SilkLens <no-reply@example.com>",
    )
    result = await client.send_email(
        to="user@example.com",
        subject="Hi",
        html=None,
        text="Plain text body",
    )

    assert result["message_id"] == "msg_test_123"
    assert captured["url"] == "https://api.resend.com/emails"
    assert captured["auth"] == "Bearer re_TEST_KEY_xxx"
    assert "user@example.com" in captured["body"]
    assert "Plain text body" in captured["body"]


@pytest.mark.asyncio
async def test_resend_includes_html_when_provided(monkeypatch) -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.read().decode()
        return httpx.Response(200, json={"id": "msg_html"})

    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        email_client.httpx,
        "AsyncClient",
        lambda **kw: real_async_client(transport=transport, **kw),
    )

    client = email_client.ResendEmailClient("k", "f")
    await client.send_email(
        to="u@x.com",
        subject="s",
        html="<p>hello</p>",
        text="hello",
    )
    assert "<p>hello</p>" in captured["body"]


@pytest.mark.asyncio
async def test_resend_omits_html_when_none(monkeypatch) -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.read().decode()
        return httpx.Response(200, json={"id": "msg_no_html"})

    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        email_client.httpx,
        "AsyncClient",
        lambda **kw: real_async_client(transport=transport, **kw),
    )

    client = email_client.ResendEmailClient("k", "f")
    await client.send_email(to="u@x.com", subject="s", html=None, text="only text")

    # Plain-text-only is mail.ru-deliverability-critical — see CLAUDE.md §8.1
    assert "only text" in captured["body"]
    assert "<" not in captured["body"]  # no html tags leaked


@pytest.mark.asyncio
async def test_resend_raises_on_4xx_response(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            json={
                "statusCode": 403,
                "message": "Domain not verified",
                "name": "validation_error",
            },
        )

    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        email_client.httpx,
        "AsyncClient",
        lambda **kw: real_async_client(transport=transport, **kw),
    )

    client = email_client.ResendEmailClient("k", "f")
    with pytest.raises(httpx.HTTPStatusError):
        await client.send_email(to="u@x.com", subject="s", html=None, text="t")


# --- Factory ----------------------------------------------------------------


def test_factory_returns_stub_when_api_key_empty(monkeypatch) -> None:
    from src.core import settings as settings_module

    settings_module.get_settings.cache_clear()  # type: ignore[attr-defined]
    monkeypatch.setattr(
        settings_module.get_settings.__wrapped__,  # type: ignore[attr-defined]
        "__call__",
        lambda: type(
            "FakeSettings",
            (),
            {
                "resend_api_key": SecretStr(""),
                "email_from": "x@y.z",
            },
        )(),
        raising=False,
    )
    # Easier path: just monkeypatch get_settings to return a stub-config instance
    monkeypatch.setattr(
        email_client,
        "get_settings",
        lambda: type(
            "S", (), {"resend_api_key": SecretStr(""), "email_from": "x@y.z"}
        )(),
    )
    client = email_client.get_email_client()
    assert isinstance(client, email_client.StubEmailClient)


def test_factory_returns_resend_when_api_key_set(monkeypatch) -> None:
    monkeypatch.setattr(
        email_client,
        "get_settings",
        lambda: type(
            "S",
            (),
            {
                "resend_api_key": SecretStr("re_real_key"),
                "email_from": "SilkLens <no-reply@silklens.app>",
            },
        )(),
    )
    client = email_client.get_email_client()
    assert isinstance(client, email_client.ResendEmailClient)
