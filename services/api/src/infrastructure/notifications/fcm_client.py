"""FCM push client stub.

FAZA 1 logs and returns a deterministic message id. Real Firebase Cloud
Messaging integration lands in FAZA 4 once the project key + APNs cert
custody policy ships.
"""

from __future__ import annotations

import uuid
from typing import Any

from src.core.logging import get_logger

log = get_logger("silklens.notifications.fcm")


class FcmPushClient:
    async def send_push(
        self,
        *,
        token: str,
        title: str,
        body: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        message_id = f"stub_{uuid.uuid4().hex}"
        log.info(
            "fcm.send_push.stub",
            token_prefix=token[:6] if token else "",
            message_id=message_id,
            title=title,
        )
        return {"message_id": message_id, "delivered": True}
