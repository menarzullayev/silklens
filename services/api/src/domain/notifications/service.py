"""Notification application service.

Coordinates template rendering, preference enforcement, quiet-hours queueing,
and channel-specific dispatch. Channel client integrations (FCM/email/SMS) are
stubs in FAZA 1; real provider integration lands in FAZA 4.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from string import Template
from typing import Any, Protocol
from uuid import UUID

from src.domain.notifications.entities import (
    Notification,
    NotificationChannel,
    NotificationInboxPage,
    NotificationPreference,
    PushDevice,
    QuietHours,
    RenderedTemplate,
)
from src.domain.notifications.errors import (
    CategoryNotFound,
    CriticalCategoryNotOptOut,
    NotificationNotFound,
    TemplateNotFound,
)
from src.domain.notifications.repository import NotificationRepository


class PushClient(Protocol):
    async def send_push(
        self,
        *,
        token: str,
        title: str,
        body: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]: ...


class EmailClient(Protocol):
    async def send_email(
        self,
        *,
        to: str,
        subject: str,
        html: str | None,
        text: str | None,
    ) -> dict[str, Any]: ...


class SmsClient(Protocol):
    async def send_sms(self, *, to: str, body: str) -> dict[str, Any]: ...


@dataclass(slots=True, frozen=True)
class DispatchResult:
    notification: Notification | None
    channels_attempted: tuple[str, ...]
    channels_queued_quiet: tuple[str, ...]
    channels_blocked_pref: tuple[str, ...]


def _render(template: str, variables: dict[str, str]) -> str:
    """Safe substitute — unknown keys stay as `${var}` so no crash."""
    return Template(template).safe_substitute(variables)


def _is_within_quiet_hours(qh: QuietHours, now: datetime) -> bool:
    if now.weekday() not in qh.weekdays:
        return False
    t = now.time()
    if qh.start_time <= qh.end_time:
        return qh.start_time <= t <= qh.end_time
    # overnight window e.g. 22:00 - 08:00
    return t >= qh.start_time or t <= qh.end_time


class NotificationService:
    def __init__(
        self,
        *,
        repository: NotificationRepository,
        push: PushClient | None = None,
        email: EmailClient | None = None,
        sms: SmsClient | None = None,
    ) -> None:
        self._repo = repository
        self._push = push
        self._email = email
        self._sms = sms

    # ------------------------------------------------------------------
    # inbox
    # ------------------------------------------------------------------

    async def list_inbox(
        self,
        *,
        user_id: UUID,
        residency_region: str,
        unread_only: bool,
        limit: int,
        before: datetime | None,
    ) -> NotificationInboxPage:
        items, has_more = await self._repo.list_inbox(
            user_id,
            residency_region,
            unread_only=unread_only,
            limit=limit,
            before=before,
        )
        return NotificationInboxPage(
            items=items,
            has_more=has_more,
            next_before=items[-1].created_at if items and has_more else None,
        )

    async def mark_read(
        self, *, notification_id: UUID, user_id: UUID, residency_region: str
    ) -> Notification:
        updated = await self._repo.mark_read(notification_id, user_id, residency_region)
        if updated is None:
            raise NotificationNotFound(str(notification_id))
        return updated

    async def mark_all_read(self, *, user_id: UUID, residency_region: str) -> int:
        return await self._repo.mark_all_read(user_id, residency_region)

    # ------------------------------------------------------------------
    # preferences
    # ------------------------------------------------------------------

    async def list_preferences(
        self, *, user_id: UUID, residency_region: str
    ) -> tuple[NotificationPreference, ...]:
        return await self._repo.list_preferences(user_id, residency_region)

    async def update_preferences(
        self,
        *,
        user_id: UUID,
        residency_region: str,
        updates: tuple[tuple[str, NotificationChannel, bool], ...],
    ) -> None:
        for category_slug, channel, enabled in updates:
            critical = await self._repo.category_is_critical(category_slug)
            if critical is None:
                raise CategoryNotFound(category_slug)
            if critical and not enabled:
                raise CriticalCategoryNotOptOut(
                    f"category '{category_slug}' is critical and cannot be disabled"
                )
            await self._repo.upsert_preference(
                user_id, residency_region, category_slug, channel, enabled
            )

    # ------------------------------------------------------------------
    # push devices
    # ------------------------------------------------------------------

    async def register_push_device(
        self,
        *,
        user_id: UUID,
        residency_region: str,
        platform: str,
        installation_id: str,
        fcm_token: str | None,
        apns_token: str | None,
    ) -> PushDevice:
        return await self._repo.register_push_device(
            user_id=user_id,
            residency_region=residency_region,
            platform=platform,
            installation_id=installation_id,
            fcm_token=fcm_token,
            apns_token=apns_token,
        )

    async def unregister_push_device(
        self,
        *,
        user_id: UUID,
        residency_region: str,
        installation_id: str,
    ) -> bool:
        return await self._repo.unregister_push_device(user_id, residency_region, installation_id)

    # ------------------------------------------------------------------
    # quiet hours
    # ------------------------------------------------------------------

    async def update_quiet_hours(
        self,
        *,
        user_id: UUID,
        residency_region: str,
        timezone: str,
        start_time: time,
        end_time: time,
        weekdays: tuple[int, ...],
    ) -> QuietHours:
        return await self._repo.upsert_quiet_hours(
            user_id=user_id,
            residency_region=residency_region,
            timezone=timezone,
            start_time=start_time,
            end_time=end_time,
            weekdays=weekdays,
        )

    # ------------------------------------------------------------------
    # send_templated
    # ------------------------------------------------------------------

    async def send_templated(
        self,
        *,
        template_slug: str,
        recipient_user_id: UUID,
        residency_region: str,
        language_tag: str = "en",
        variables: dict[str, str] | None = None,
        channels: tuple[NotificationChannel, ...] | None = None,
        now: datetime | None = None,
    ) -> DispatchResult:
        variables = variables or {}
        tmpl = await self._repo.get_template(template_slug)
        if tmpl is None or not tmpl.is_active:
            raise TemplateNotFound(template_slug)

        version = await self._repo.get_template_version(tmpl.id, language_tag)
        if version is None:
            # Fall back to English.
            version = await self._repo.get_template_version(tmpl.id, "en")
        if version is None:
            raise TemplateNotFound(f"no usable version for template '{template_slug}'")

        rendered = RenderedTemplate(
            subject=_render(version.subject, variables) if version.subject else None,
            body_md=_render(version.body_md, variables),
            push_title=_render(version.push_title, variables) if version.push_title else None,
            push_body=_render(version.push_body, variables) if version.push_body else None,
            action_url=(
                _render(version.action_url_template, variables)
                if version.action_url_template
                else None
            ),
            channels=tmpl.channels,
        )

        effective_channels = tuple(c.value for c in channels) if channels else tmpl.channels
        prefs_index = {
            (p.category_slug, p.channel.value): p.enabled
            for p in await self._repo.list_preferences(recipient_user_id, residency_region)
        }

        # Critical categories can't be silenced.
        critical = await self._repo.category_is_critical(tmpl.category_slug)
        if critical is None:
            raise CategoryNotFound(tmpl.category_slug)

        blocked: list[str] = []
        eligible: list[str] = []
        for ch in effective_channels:
            enabled = prefs_index.get((tmpl.category_slug, ch), True)
            if not enabled and not critical:
                blocked.append(ch)
                continue
            eligible.append(ch)

        # Always materialise in-app notification when in_app is eligible.
        notification: Notification | None = None
        if NotificationChannel.IN_APP.value in eligible:
            notification = await self._repo.insert(
                recipient_user_id=recipient_user_id,
                residency_region=residency_region,
                category_slug=tmpl.category_slug,
                title=rendered.push_title or rendered.subject or template_slug,
                body_md=rendered.body_md,
                template_id=tmpl.id,
                action_url=rendered.action_url,
            )

        # Quiet hours: queue external channels for later; in_app is exempt.
        qh = await self._repo.get_quiet_hours(recipient_user_id, residency_region)
        check_time = now or datetime.now()
        queued: list[str] = []
        attempted: list[str] = []
        for ch in eligible:
            if ch == NotificationChannel.IN_APP.value:
                attempted.append(ch)
                continue
            if qh is not None and not critical and _is_within_quiet_hours(qh, check_time):
                await self._repo.enqueue_delivery_job(
                    kind="notification.deliver",
                    payload={
                        "channel": ch,
                        "user_id": str(recipient_user_id),
                        "residency_region": residency_region,
                        "template": template_slug,
                        "rendered": {
                            "subject": rendered.subject,
                            "body_md": rendered.body_md,
                            "push_title": rendered.push_title,
                            "push_body": rendered.push_body,
                            "action_url": rendered.action_url,
                        },
                    },
                )
                queued.append(ch)
                continue
            attempted.append(ch)
            await self._dispatch_channel(
                channel=ch,
                rendered=rendered,
                recipient_user_id=recipient_user_id,
                residency_region=residency_region,
                notification_id=notification.id if notification else None,
            )

        return DispatchResult(
            notification=notification,
            channels_attempted=tuple(attempted),
            channels_queued_quiet=tuple(queued),
            channels_blocked_pref=tuple(blocked),
        )

    async def _dispatch_channel(
        self,
        *,
        channel: str,
        rendered: RenderedTemplate,
        recipient_user_id: UUID,
        residency_region: str,
        notification_id: UUID | None,
    ) -> None:
        provider = None
        provider_message_id: str | None = None
        status = "sent"
        error: str | None = None

        try:
            if channel == NotificationChannel.PUSH.value and self._push is not None:
                # For each active device, fire push.
                devices = await self._repo.list_active_devices(recipient_user_id, residency_region)
                for device in devices:
                    token = device.fcm_token or device.apns_token
                    if not token:
                        continue
                    result = await self._push.send_push(
                        token=token,
                        title=rendered.push_title or rendered.subject or "Notification",
                        body=rendered.push_body or rendered.body_md,
                        payload={"action_url": rendered.action_url} if rendered.action_url else {},
                    )
                    provider = "fcm"
                    provider_message_id = str(result.get("message_id"))
            elif channel == NotificationChannel.EMAIL.value and self._email is not None:
                result = await self._email.send_email(
                    to=f"user-{recipient_user_id}@example.invalid",
                    subject=rendered.subject or "Notification",
                    html=None,
                    text=rendered.body_md,
                )
                provider = "smtp"
                provider_message_id = str(result.get("message_id"))
            elif channel == NotificationChannel.SMS.value and self._sms is not None:
                result = await self._sms.send_sms(
                    to="+0000000000",
                    body=rendered.body_md,
                )
                provider = "sms"
                provider_message_id = str(result.get("message_id"))
        except Exception as exc:
            status = "failed"
            error = str(exc)

        await self._repo.record_delivery_log(
            notification_id=notification_id,
            recipient_user_id=recipient_user_id,
            residency_region=residency_region,
            channel=channel,
            provider=provider,
            provider_message_id=provider_message_id,
            status=status,
            error=error,
        )
