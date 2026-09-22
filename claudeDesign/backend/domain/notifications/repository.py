"""Notification repository protocols."""

from __future__ import annotations

from datetime import datetime, time
from typing import Protocol
from uuid import UUID

from src.domain.notifications.entities import (
    Notification,
    NotificationChannel,
    NotificationPreference,
    NotificationTemplate,
    NotificationTemplateVersion,
    PushDevice,
    QuietHours,
)


class NotificationRepository(Protocol):
    # --- inbox ---
    async def list_inbox(
        self,
        user_id: UUID,
        residency_region: str,
        *,
        unread_only: bool,
        limit: int,
        before: datetime | None,
    ) -> tuple[tuple[Notification, ...], bool]: ...

    async def mark_read(
        self, notification_id: UUID, user_id: UUID, residency_region: str
    ) -> Notification | None: ...

    async def mark_all_read(self, user_id: UUID, residency_region: str) -> int: ...

    async def insert(
        self,
        *,
        recipient_user_id: UUID,
        residency_region: str,
        category_slug: str,
        title: str,
        body_md: str,
        template_id: UUID | None,
        action_url: str | None,
    ) -> Notification: ...

    # --- templates ---
    async def get_template(self, slug: str) -> NotificationTemplate | None: ...

    async def get_template_version(
        self, template_id: UUID, language_tag: str
    ) -> NotificationTemplateVersion | None: ...

    async def category_is_critical(self, slug: str) -> bool | None: ...

    # --- preferences ---
    async def list_preferences(
        self, user_id: UUID, residency_region: str
    ) -> tuple[NotificationPreference, ...]: ...

    async def upsert_preference(
        self,
        user_id: UUID,
        residency_region: str,
        category_slug: str,
        channel: NotificationChannel,
        enabled: bool,
    ) -> None: ...

    # --- push devices ---
    async def register_push_device(
        self,
        *,
        user_id: UUID,
        residency_region: str,
        platform: str,
        installation_id: str,
        fcm_token: str | None,
        apns_token: str | None,
    ) -> PushDevice: ...

    async def unregister_push_device(
        self, user_id: UUID, residency_region: str, installation_id: str
    ) -> bool: ...

    async def list_active_devices(
        self, user_id: UUID, residency_region: str
    ) -> tuple[PushDevice, ...]: ...

    # --- quiet hours ---
    async def get_quiet_hours(self, user_id: UUID, residency_region: str) -> QuietHours | None: ...

    async def upsert_quiet_hours(
        self,
        *,
        user_id: UUID,
        residency_region: str,
        timezone: str,
        start_time: time,
        end_time: time,
        weekdays: tuple[int, ...],
    ) -> QuietHours: ...

    # --- jobs ---
    async def enqueue_delivery_job(
        self,
        *,
        kind: str,
        payload: dict[str, object],
    ) -> UUID: ...

    async def record_delivery_log(
        self,
        *,
        notification_id: UUID | None,
        recipient_user_id: UUID,
        residency_region: str,
        channel: str,
        provider: str | None,
        provider_message_id: str | None,
        status: str,
        error: str | None = None,
    ) -> None: ...
