"""Shared event-emit helper used across domain repositories.

`app.emit_event` hard-fails on an unregistered ``event_name`` (raises 23514).
For Wave-2 endpoints we want to emit ``follow.created.v1``, ``review.created.v1``
and similar without crashing the request when the event hasn't been seeded yet
(e.g. ``xp.awarded.v1`` is reserved for a future migration). This wrapper
checks the registry first and silently skips otherwise.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger

log = get_logger("silklens.events")


async def emit_event_if_registered(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    event_name: str,
    aggregate_type: str,
    aggregate_id: UUID,
    payload: dict[str, Any],
) -> UUID | None:
    """Emit an event only if the event_name exists and is not deprecated."""
    registered = (
        await session.execute(
            text(
                """
                SELECT 1 FROM event_types
                WHERE event_name = :name AND NOT is_deprecated
                LIMIT 1
                """
            ),
            {"name": event_name},
        )
    ).scalar_one_or_none()
    if registered is None:
        log.debug("events.skip_unregistered", event_name=event_name)
        return None
    row = await session.execute(
        text(
            """
            SELECT app.emit_event(
                :tenant, :name, :agg_type, :agg_id, CAST(:payload AS jsonb)
            )
            """
        ),
        {
            "tenant": tenant_id,
            "name": event_name,
            "agg_type": aggregate_type,
            "agg_id": aggregate_id,
            "payload": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        },
    )
    return row.scalar_one()


def jdump(payload: object) -> str:
    """Serialize any JSON-compatible value to a string for jsonb casting."""
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)
