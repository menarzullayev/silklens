"""Email client implementations.

``ResendEmailClient`` calls the Resend API (https://resend.com).
``StubEmailClient`` logs and returns a fake message ID — used in dev/test
when ``SILKLENS_RESEND_API_KEY`` is empty.

``get_email_client()`` selects the right implementation from settings.
"""

from __future__ import annotations

import uuid
from typing import Any

import httpx

from src.core.logging import get_logger
from src.core.settings import get_settings

log = get_logger("silklens.notifications.email")


class ResendEmailClient:
    """Thin async wrapper around the Resend REST API."""

    BASE_URL = "https://api.resend.com"

    def __init__(self, api_key: str, from_address: str) -> None:
        self._api_key = api_key
        self._from = from_address

    async def send_email(
        self,
        *,
        to: str,
        subject: str,
        html: str | None,
        text: str | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "from": self._from,
            "to": [to],
            "subject": subject,
        }
        if html:
            payload["html"] = html
        if text:
            payload["text"] = text

        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"{self.BASE_URL}/emails",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=payload,
            )

        if r.status_code not in (200, 201):
            log.error(
                "email.send.failed",
                to=to,
                subject=subject,
                status=r.status_code,
                body=r.text[:200],
            )
            r.raise_for_status()

        data = r.json()
        message_id: str = data.get("id", f"resend_{uuid.uuid4().hex}")
        log.info("email.send.ok", to=to, subject=subject, message_id=message_id)
        return {"message_id": message_id}


class StubEmailClient:
    """Logs but never sends — dev / test default."""

    async def send_email(
        self,
        *,
        to: str,
        subject: str,
        html: str | None = None,
        text: str | None = None,
    ) -> dict[str, Any]:
        message_id = f"stub_email_{uuid.uuid4().hex}"
        log.info(
            "email.send.stub",
            to=to,
            subject=subject,
            has_html=html is not None,
            has_text=text is not None,
            message_id=message_id,
        )
        return {"message_id": message_id}


def get_email_client() -> ResendEmailClient | StubEmailClient:
    """Return the appropriate email client based on settings."""
    settings = get_settings()
    api_key = settings.resend_api_key.get_secret_value()
    if api_key:
        return ResendEmailClient(api_key, settings.email_from)
    log.warning("email.stub_mode", reason="SILKLENS_RESEND_API_KEY not set")
    return StubEmailClient()
