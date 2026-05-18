"""Notification domain entities — pure Python, framework-free."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from enum import StrEnum
from uuid import UUID


class NotificationChannel(StrEnum):
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


class NotificationCategory(StrEnum):
    """Built-in categories — matches `notification_categories` seed."""

    ACCOUNT_SECURITY = "account_security"
    SOCIAL_ACTIVITY = "social_activity"
    GAMIFICATION = "gamification"
    CONTENT_UPDATES = "content_updates"
    MARKETING = "marketing"
    BILLING = "billing"
    SYSTEM_ALERTS = "system_alerts"
    RECOMMENDATIONS = "recommendations"


class PushPlatform(StrEnum):
    IOS = "ios"
    ANDROID = "android"
    WEB = "web"


@dataclass(slots=True, frozen=True)
class Notification:
    id: UUID
    recipient_user_id: UUID
    residency_region: str
    category_slug: str
    title: str
    body_md: str
    template_id: UUID | None = None
    action_url: str | None = None
    related_object_kind: str | None = None
    related_object_id: UUID | None = None
    is_read: bool = False
    read_at: datetime | None = None
    created_at: datetime | None = None


@dataclass(slots=True, frozen=True)
class NotificationTemplate:
    id: UUID
    slug: str
    category_slug: str
    channels: tuple[str, ...]
    default_priority: int
    is_active: bool


@dataclass(slots=True, frozen=True)
class NotificationTemplateVersion:
    template_id: UUID
    version: int
    language_tag: str
    body_md: str
    subject: str | None = None
    push_title: str | None = None
    push_body: str | None = None
    action_url_template: str | None = None


@dataclass(slots=True, frozen=True)
class NotificationPreference:
    user_id: UUID
    residency_region: str
    category_slug: str
    channel: NotificationChannel
    enabled: bool


@dataclass(slots=True, frozen=True)
class QuietHours:
    user_id: UUID
    residency_region: str
    timezone: str
    start_time: time
    end_time: time
    weekdays: tuple[int, ...]


@dataclass(slots=True, frozen=True)
class PushDevice:
    id: UUID
    user_id: UUID
    residency_region: str
    platform: PushPlatform
    installation_id: str
    fcm_token: str | None = None
    apns_token: str | None = None
    is_active: bool = True


@dataclass(slots=True, frozen=True)
class NotificationInboxPage:
    items: tuple[Notification, ...]
    has_more: bool
    next_before: datetime | None = None


@dataclass(slots=True, frozen=True)
class RenderedTemplate:
    subject: str | None
    body_md: str
    push_title: str | None
    push_body: str | None
    action_url: str | None
    channels: tuple[str, ...] = field(default_factory=tuple)
