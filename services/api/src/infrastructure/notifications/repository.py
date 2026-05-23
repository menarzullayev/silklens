"""SQL implementation of `NotificationRepository`."""

from __future__ import annotations

import json
from datetime import datetime, time
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.notifications.entities import (
    Notification,
    NotificationChannel,
    NotificationPreference,
    NotificationTemplate,
    NotificationTemplateVersion,
    PushDevice,
    PushPlatform,
    QuietHours,
)


def _json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)


_NOTIFICATION_COLS = """
    id, recipient_user_id, residency_region, template_id, category_slug,
    title, body_md, action_url, related_object_kind, related_object_id,
    is_read, read_at, created_at
"""


def _row_to_notification(row: object) -> Notification:
    m = row._mapping
    return Notification(
        id=m["id"],
        recipient_user_id=m["recipient_user_id"],
        residency_region=m["residency_region"],
        template_id=m["template_id"],
        category_slug=m["category_slug"],
        title=m["title"],
        body_md=m["body_md"],
        action_url=m["action_url"],
        related_object_kind=m["related_object_kind"],
        related_object_id=m["related_object_id"],
        is_read=bool(m["is_read"]),
        read_at=m["read_at"],
        created_at=m["created_at"],
    )


class SqlNotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    # --- inbox ---

    async def list_inbox(
        self,
        user_id: UUID,
        residency_region: str,
        *,
        unread_only: bool,
        limit: int,
        before: datetime | None,
    ) -> tuple[tuple[Notification, ...], bool]:
        clauses = ["recipient_user_id = :uid", "residency_region = :region"]
        params: dict[str, object] = {
            "uid": user_id,
            "region": residency_region,
            "limit": limit + 1,
        }
        if unread_only:
            clauses.append("is_read = false")
        if before is not None:
            clauses.append("created_at < :before")
            params["before"] = before
        where = " AND ".join(clauses)
        result = await self._s.execute(
            text(
                f"""
                SELECT {_NOTIFICATION_COLS}
                FROM notifications
                WHERE {where}
                ORDER BY created_at DESC
                LIMIT :limit
                """  # noqa: S608
            ),
            params,
        )
        rows = result.all()
        has_more = len(rows) > limit
        items = tuple(_row_to_notification(r) for r in rows[:limit])
        return items, has_more

    async def mark_read(
        self, notification_id: UUID, user_id: UUID, residency_region: str
    ) -> Notification | None:
        result = await self._s.execute(
            text(
                f"""
                UPDATE notifications
                SET is_read = true, read_at = now()
                WHERE id = :id AND recipient_user_id = :uid
                  AND residency_region = :region
                RETURNING {_NOTIFICATION_COLS}
                """  # noqa: S608
            ),
            {"id": notification_id, "uid": user_id, "region": residency_region},
        )
        row = result.one_or_none()
        await self._s.commit()
        return _row_to_notification(row) if row else None

    async def mark_all_read(self, user_id: UUID, residency_region: str) -> int:
        result = await self._s.execute(
            text(
                """
                UPDATE notifications SET is_read = true, read_at = now()
                WHERE recipient_user_id = :uid AND residency_region = :region
                  AND is_read = false
                RETURNING id
                """
            ),
            {"uid": user_id, "region": residency_region},
        )
        rows = result.all()
        await self._s.commit()
        return len(rows)

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
    ) -> Notification:
        result = await self._s.execute(
            text(
                f"""
                INSERT INTO notifications (
                    recipient_user_id, residency_region, template_id,
                    category_slug, title, body_md, action_url
                ) VALUES (
                    :uid, :region, :tid, :cat, :title, :body, :url
                )
                RETURNING {_NOTIFICATION_COLS}
                """  # noqa: S608
            ),
            {
                "uid": recipient_user_id,
                "region": residency_region,
                "tid": template_id,
                "cat": category_slug,
                "title": title,
                "body": body_md,
                "url": action_url,
            },
        )
        await self._s.commit()
        return _row_to_notification(result.one())

    # --- templates ---

    async def get_template(self, slug: str) -> NotificationTemplate | None:
        row = (
            await self._s.execute(
                text(
                    """
                    SELECT id, slug, category_slug, channels, default_priority, is_active
                    FROM notification_templates
                    WHERE slug = :slug
                    """
                ),
                {"slug": slug},
            )
        ).one_or_none()
        if row is None:
            return None
        m = row._mapping
        return NotificationTemplate(
            id=m["id"],
            slug=m["slug"],
            category_slug=m["category_slug"],
            channels=tuple(m["channels"]) if m["channels"] else (),
            default_priority=int(m["default_priority"]),
            is_active=bool(m["is_active"]),
        )

    async def get_template_version(
        self, template_id: UUID, language_tag: str
    ) -> NotificationTemplateVersion | None:
        row = (
            await self._s.execute(
                text(
                    """
                    SELECT template_id, version, language_tag, subject, body_md,
                           push_title, push_body, action_url_template
                    FROM notification_template_versions
                    WHERE template_id = :tid AND language_tag = :lang
                    ORDER BY version DESC
                    LIMIT 1
                    """
                ),
                {"tid": template_id, "lang": language_tag},
            )
        ).one_or_none()
        if row is None:
            return None
        m = row._mapping
        return NotificationTemplateVersion(
            template_id=m["template_id"],
            version=int(m["version"]),
            language_tag=m["language_tag"],
            body_md=m["body_md"],
            subject=m["subject"],
            push_title=m["push_title"],
            push_body=m["push_body"],
            action_url_template=m["action_url_template"],
        )

    async def category_is_critical(self, slug: str) -> bool | None:
        row = (
            await self._s.execute(
                text("SELECT is_critical FROM notification_categories WHERE slug = :s"),
                {"s": slug},
            )
        ).one_or_none()
        return bool(row[0]) if row else None

    # --- preferences ---

    async def list_preferences(
        self, user_id: UUID, residency_region: str
    ) -> tuple[NotificationPreference, ...]:
        result = await self._s.execute(
            text(
                """
                SELECT user_id, residency_region, category_slug, channel, enabled
                FROM notification_preferences
                WHERE user_id = :uid AND residency_region = :region
                """
            ),
            {"uid": user_id, "region": residency_region},
        )
        out: list[NotificationPreference] = []
        for r in result.all():
            m = r._mapping
            out.append(
                NotificationPreference(
                    user_id=m["user_id"],
                    residency_region=m["residency_region"],
                    category_slug=m["category_slug"],
                    channel=NotificationChannel(m["channel"]),
                    enabled=bool(m["enabled"]),
                )
            )
        return tuple(out)

    async def upsert_preference(
        self,
        user_id: UUID,
        residency_region: str,
        category_slug: str,
        channel: NotificationChannel,
        enabled: bool,
    ) -> None:
        await self._s.execute(
            text(
                """
                INSERT INTO notification_preferences (
                    user_id, residency_region, category_slug, channel, enabled
                ) VALUES (:uid, :region, :cat, :channel, :enabled)
                ON CONFLICT (user_id, residency_region, category_slug, channel)
                DO UPDATE SET enabled = EXCLUDED.enabled
                """
            ),
            {
                "uid": user_id,
                "region": residency_region,
                "cat": category_slug,
                "channel": channel.value,
                "enabled": enabled,
            },
        )
        await self._s.commit()

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
    ) -> PushDevice:
        result = await self._s.execute(
            text(
                """
                INSERT INTO push_devices (
                    user_id, residency_region, platform, installation_id,
                    fcm_token, apns_token, last_seen_at, is_active
                ) VALUES (:uid, :region, :platform, :iid, :fcm, :apns, now(), true)
                ON CONFLICT (user_id, residency_region, installation_id)
                DO UPDATE SET
                    platform = EXCLUDED.platform,
                    fcm_token = EXCLUDED.fcm_token,
                    apns_token = EXCLUDED.apns_token,
                    last_seen_at = now(),
                    is_active = true
                RETURNING id, user_id, residency_region, platform, installation_id,
                          fcm_token, apns_token, is_active
                """
            ),
            {
                "uid": user_id,
                "region": residency_region,
                "platform": platform,
                "iid": installation_id,
                "fcm": fcm_token,
                "apns": apns_token,
            },
        )
        await self._s.commit()
        m = result.one()._mapping
        return PushDevice(
            id=m["id"],
            user_id=m["user_id"],
            residency_region=m["residency_region"],
            platform=PushPlatform(m["platform"]),
            installation_id=m["installation_id"],
            fcm_token=m["fcm_token"],
            apns_token=m["apns_token"],
            is_active=bool(m["is_active"]),
        )

    async def unregister_push_device(
        self, user_id: UUID, residency_region: str, installation_id: str
    ) -> bool:
        result = await self._s.execute(
            text(
                """
                UPDATE push_devices SET is_active = false
                WHERE user_id = :uid AND residency_region = :region
                  AND installation_id = :iid
                RETURNING id
                """
            ),
            {"uid": user_id, "region": residency_region, "iid": installation_id},
        )
        row = result.one_or_none()
        await self._s.commit()
        return row is not None

    async def list_active_devices(
        self, user_id: UUID, residency_region: str
    ) -> tuple[PushDevice, ...]:
        result = await self._s.execute(
            text(
                """
                SELECT id, user_id, residency_region, platform, installation_id,
                       fcm_token, apns_token, is_active
                FROM push_devices
                WHERE user_id = :uid AND residency_region = :region AND is_active
                """
            ),
            {"uid": user_id, "region": residency_region},
        )
        out: list[PushDevice] = []
        for r in result.all():
            m = r._mapping
            out.append(
                PushDevice(
                    id=m["id"],
                    user_id=m["user_id"],
                    residency_region=m["residency_region"],
                    platform=PushPlatform(m["platform"]),
                    installation_id=m["installation_id"],
                    fcm_token=m["fcm_token"],
                    apns_token=m["apns_token"],
                    is_active=bool(m["is_active"]),
                )
            )
        return tuple(out)

    # --- quiet hours ---

    async def get_quiet_hours(self, user_id: UUID, residency_region: str) -> QuietHours | None:
        row = (
            await self._s.execute(
                text(
                    """
                    SELECT user_id, residency_region, timezone, start_time, end_time, weekdays
                    FROM notification_quiet_hours
                    WHERE user_id = :uid AND residency_region = :region
                    """
                ),
                {"uid": user_id, "region": residency_region},
            )
        ).one_or_none()
        if row is None:
            return None
        m = row._mapping
        return QuietHours(
            user_id=m["user_id"],
            residency_region=m["residency_region"],
            timezone=m["timezone"],
            start_time=m["start_time"],
            end_time=m["end_time"],
            weekdays=tuple(int(w) for w in (m["weekdays"] or [])),
        )

    async def upsert_quiet_hours(
        self,
        *,
        user_id: UUID,
        residency_region: str,
        timezone: str,
        start_time: time,
        end_time: time,
        weekdays: tuple[int, ...],
    ) -> QuietHours:
        result = await self._s.execute(
            text(
                """
                INSERT INTO notification_quiet_hours (
                    user_id, residency_region, timezone, start_time, end_time, weekdays
                ) VALUES (:uid, :region, :tz, :start, :end, :weekdays)
                ON CONFLICT (user_id, residency_region) DO UPDATE
                  SET timezone = EXCLUDED.timezone,
                      start_time = EXCLUDED.start_time,
                      end_time = EXCLUDED.end_time,
                      weekdays = EXCLUDED.weekdays
                RETURNING user_id, residency_region, timezone, start_time, end_time, weekdays
                """
            ),
            {
                "uid": user_id,
                "region": residency_region,
                "tz": timezone,
                "start": start_time,
                "end": end_time,
                "weekdays": list(weekdays),
            },
        )
        await self._s.commit()
        m = result.one()._mapping
        return QuietHours(
            user_id=m["user_id"],
            residency_region=m["residency_region"],
            timezone=m["timezone"],
            start_time=m["start_time"],
            end_time=m["end_time"],
            weekdays=tuple(int(w) for w in (m["weekdays"] or [])),
        )

    # --- jobs / delivery log ---

    async def enqueue_delivery_job(
        self,
        *,
        kind: str,
        payload: dict[str, object],
    ) -> UUID:
        result = await self._s.execute(
            text(
                """
                INSERT INTO background_jobs (kind, payload)
                VALUES (:kind, CAST(:payload AS jsonb))
                RETURNING id
                """
            ),
            {"kind": kind, "payload": _json(payload)},
        )
        await self._s.commit()
        return UUID(str(result.scalar_one()))

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
    ) -> None:
        await self._s.execute(
            text(
                """
                INSERT INTO notification_delivery_log (
                    notification_id, recipient_user_id, residency_region,
                    channel, provider, provider_message_id, status, error
                ) VALUES (:nid, :uid, :region, :channel, :provider, :msg, :status, :error)
                """
            ),
            {
                "nid": notification_id,
                "uid": recipient_user_id,
                "region": residency_region,
                "channel": channel,
                "provider": provider,
                "msg": provider_message_id,
                "status": status,
                "error": error,
            },
        )
        await self._s.commit()
