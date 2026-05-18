"""Email client stub."""

from __future__ import annotations

import uuid
from typing import Any

from src.core.logging import get_logger

log = get_logger("silklens.notifications.email")


class StubEmailClient:
    async def send_email(
        self,
        *,
        to: str,
        subject: str,
        html: str | None,
        text: str | None,
    ) -> dict[str, Any]:
        message_id = f"stub_email_{uuid.uuid4().hex}"
        log.info(
            "email.send.stub",
            to=to,
            subject=subject,
            message_id=message_id,
        )
        return {"message_id": message_id}
