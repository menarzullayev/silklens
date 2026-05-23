"""Email client implementations.

Supported providers (selected via ``SILKLENS_EMAIL_PROVIDER``):

* ``resend``  — Resend REST API  (https://resend.com)
               Free tier: 3 000 emails/month, 100/day.
* ``brevo``   — Brevo SMTP relay (smtp-relay.brevo.com:587)
               Free tier: 9 000 emails/month, 300/day.
* fallback    — ``StubEmailClient`` — logs only, never sends.
               Activated automatically when the selected provider
               has no credentials set.

Switch providers with a single env-var change — no code redeploy:

    SILKLENS_EMAIL_PROVIDER=resend   # default
    SILKLENS_EMAIL_PROVIDER=brevo

``get_email_client()`` reads settings and returns the right instance.
"""

from __future__ import annotations

import asyncio
import smtplib
import uuid
from email.message import EmailMessage
from typing import Any

import httpx

from src.core.logging import get_logger
from src.core.settings import get_settings

log = get_logger("silklens.notifications.email")


# ---------------------------------------------------------------------------
# Resend
# ---------------------------------------------------------------------------


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
                provider="resend",
                to=to,
                subject=subject,
                status=r.status_code,
                body=r.text[:200],
            )
            r.raise_for_status()

        data = r.json()
        message_id: str = data.get("id", f"resend_{uuid.uuid4().hex}")
        log.info("email.send.ok", provider="resend", to=to, subject=subject, message_id=message_id)
        return {"message_id": message_id}


# ---------------------------------------------------------------------------
# Brevo SMTP relay
# ---------------------------------------------------------------------------


class BrevoSmtpEmailClient:
    """Async email client backed by the Brevo SMTP relay.

    Brevo uses standard SMTP/STARTTLS on port 587.  Python's ``smtplib`` is
    synchronous, so each send is offloaded to a thread-pool executor so the
    FastAPI event loop is never blocked.

    Deliverability notes:
    * Brevo shares IP pools with high reputation — Gmail/Outlook inbox rates
      are consistently good on the free tier.
    * Plain-text body only keeps mail.ru happy (see CLAUDE.md §8.1).
    * The ``From`` header must match a sender verified in the Brevo dashboard
      (Settings → Senders & IP → Senders).
    """

    def __init__(
        self,
        *,
        host: str,
        port: int,
        login: str,
        password: str,
        from_address: str,
    ) -> None:
        self._host = host
        self._port = port
        self._login = login
        self._password = password
        self._from = from_address

    async def send_email(
        self,
        *,
        to: str,
        subject: str,
        html: str | None,
        text: str | None,
    ) -> dict[str, Any]:
        loop = asyncio.get_event_loop()
        try:
            message_id = await loop.run_in_executor(
                None,
                self._send_sync,
                to,
                subject,
                html,
                text,
            )
        except smtplib.SMTPException as exc:
            log.error(
                "email.send.failed",
                provider="brevo",
                to=to,
                subject=subject,
                error=str(exc),
            )
            raise

        log.info("email.send.ok", provider="brevo", to=to, subject=subject, message_id=message_id)
        return {"message_id": message_id}

    # -- sync helper (runs in thread pool) -----------------------------------

    def _send_sync(
        self,
        to: str,
        subject: str,
        html: str | None,
        text: str | None,
    ) -> str:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self._from
        msg["To"] = to

        # Plain-text first (mail.ru / HTML-blocking providers).
        if text:
            msg.set_content(text)
        # Attach HTML as alternative part when provided (future-proofing).
        if html:
            msg.add_alternative(html, subtype="html")

        with smtplib.SMTP(self._host, self._port, timeout=15) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(self._login, self._password)
            smtp.send_message(msg)

        return f"brevo_{uuid.uuid4().hex}"


# ---------------------------------------------------------------------------
# Stub (dev / test fallback)
# ---------------------------------------------------------------------------


class StubEmailClient:
    """Logs but never sends — activated when no provider credentials are set."""

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


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

#: Union type for callers that want full typing without importing each class.
AnyEmailClient = ResendEmailClient | BrevoSmtpEmailClient | StubEmailClient


def get_email_client() -> AnyEmailClient:
    """Return the configured email client.

    Selection logic (``SILKLENS_EMAIL_PROVIDER``):

    ``resend``
        Requires ``SILKLENS_RESEND_API_KEY``.
        Falls back to StubEmailClient if the key is empty.

    ``brevo``
        Requires ``SILKLENS_BREVO_SMTP_LOGIN`` + ``SILKLENS_BREVO_SMTP_PASSWORD``.
        Falls back to StubEmailClient if either is empty.

    Anything else / no credentials → StubEmailClient.
    """
    settings = get_settings()
    provider = (settings.email_provider or "resend").lower().strip()

    if provider == "brevo":
        login = settings.brevo_smtp_login
        password = settings.brevo_smtp_password.get_secret_value()
        if login and password:
            return BrevoSmtpEmailClient(
                host=settings.brevo_smtp_host,
                port=settings.brevo_smtp_port,
                login=login,
                password=password,
                from_address=settings.email_from,
            )
        log.warning(
            "email.brevo_missing_credentials",
            hint="Set SILKLENS_BREVO_SMTP_LOGIN + SILKLENS_BREVO_SMTP_PASSWORD",
            fallback="stub",
        )

    elif provider == "resend":
        api_key = settings.resend_api_key.get_secret_value()
        if api_key:
            return ResendEmailClient(api_key, settings.email_from)
        log.warning(
            "email.resend_missing_api_key",
            hint="Set SILKLENS_RESEND_API_KEY",
            fallback="stub",
        )

    else:
        log.warning("email.unknown_provider", provider=provider, fallback="stub")

    return StubEmailClient()
