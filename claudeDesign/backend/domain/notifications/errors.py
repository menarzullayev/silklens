"""Notification-domain errors."""
# ruff: noqa: N818

from __future__ import annotations


class NotificationError(Exception):
    code: str = "notifications.unknown"
    status_code: int = 400


class TemplateNotFound(NotificationError):
    code = "notifications.template_not_found"
    status_code = 404


class CategoryNotFound(NotificationError):
    code = "notifications.category_not_found"
    status_code = 404


class NotificationNotFound(NotificationError):
    code = "notifications.notification_not_found"
    status_code = 404


class CriticalCategoryNotOptOut(NotificationError):
    code = "notifications.critical_no_opt_out"
    status_code = 422


class PushDeviceNotFound(NotificationError):
    code = "notifications.push_device_not_found"
    status_code = 404
