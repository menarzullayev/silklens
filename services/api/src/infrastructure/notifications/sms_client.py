"""SMS client stub."""

from __future__ import annotations

import uuid
from typing import Any

from src.core.logging import get_logger

log = get_logger("silklens.notifications.sms")


class StubSmsClient:
    async def send_sms(self, *, to: str, body: str) -> dict[str, Any]:
        message_id = f"stub_sms_{uuid.uuid4().hex}"
        log.info(
            "sms.send.stub",
            to=to,
            body_length=len(body),
            message_id=message_id,
        )
        return {"message_id": message_id}
