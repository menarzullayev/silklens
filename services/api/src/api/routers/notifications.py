"""Notifications API endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, time
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.domain.notifications.entities import Notification, NotificationChannel
from src.domain.notifications.errors import NotificationError
from src.domain.notifications.service import NotificationService
from src.infrastructure.notifications.email_client import StubEmailClient
from src.infrastructure.notifications.repository import SqlNotificationRepository
from src.infrastructure.notifications.sms_client import StubSmsClient
from src.middleware.auth import CurrentUserDep

router = APIRouter(prefix="/v1/notifications", tags=["notifications"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _service(db: AsyncSession) -> NotificationService:
    return NotificationService(
        repository=SqlNotificationRepository(db),
        push=None,  # FCM adapter not yet wired to domain PushClient protocol
        email=StubEmailClient(),
        sms=StubSmsClient(),
    )


def _raise(exc: NotificationError) -> None:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": str(exc)},
    ) from exc


# --- Schemas --------------------------------------------------------------


class NotificationOut(BaseModel):
    id: UUID
    category_slug: str
    title: str
    body_md: str
    action_url: str | None
    is_read: bool
    read_at: datetime | None
    created_at: datetime


class InboxOut(BaseModel):
    items: list[NotificationOut]
    has_more: bool
    next_before: datetime | None


class PreferenceOut(BaseModel):
    category_slug: str
    channel: NotificationChannel
    enabled: bool


class PreferencesGroupedOut(BaseModel):
    items: list[PreferenceOut]


class PreferenceUpdate(BaseModel):
    category_slug: str = Field(min_length=2, max_length=64)
    channel: NotificationChannel
    enabled: bool


class PushDeviceRegister(BaseModel):
    platform: str = Field(pattern="^(ios|android|web)$")
    installation_id: str = Field(min_length=2, max_length=128)
    fcm_token: str | None = Field(default=None, max_length=512)
    apns_token: str | None = Field(default=None, max_length=512)


class PushDeviceOut(BaseModel):
    id: UUID
    platform: str
    installation_id: str
    is_active: bool


class QuietHoursPut(BaseModel):
    timezone: str = Field(min_length=1, max_length=64)
    start_time: str = Field(pattern="^[0-2][0-9]:[0-5][0-9]$")
    end_time: str = Field(pattern="^[0-2][0-9]:[0-5][0-9]$")
    weekdays: list[int] = Field(min_length=1, max_length=7)

    @field_validator("weekdays")
    @classmethod
    def _weekdays_in_range(cls, v: list[int]) -> list[int]:
        for w in v:
            if w < 0 or w > 6:
                raise ValueError("weekday values must be between 0 (Mon) and 6 (Sun)")
        return sorted(set(v))


class QuietHoursOut(BaseModel):
    timezone: str
    start_time: str
    end_time: str
    weekdays: list[int]


# --- Helpers -------------------------------------------------------------


def _notif_out(n: Notification) -> NotificationOut:
    return NotificationOut(
        id=n.id,
        category_slug=n.category_slug,
        title=n.title,
        body_md=n.body_md,
        action_url=n.action_url,
        is_read=n.is_read,
        read_at=n.read_at,
        created_at=n.created_at if n.created_at is not None else datetime.now(UTC),
    )


# --- Routes: inbox -------------------------------------------------------


@router.get("", response_model=InboxOut)
async def list_inbox(
    ctx: CurrentUserDep,
    db: SessionDep,
    unread_only: Annotated[bool, Query()] = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    before: Annotated[datetime | None, Query()] = None,
) -> InboxOut:
    page = await _service(db).list_inbox(
        user_id=ctx.user_id,
        residency_region=ctx.residency_region.value,
        unread_only=unread_only,
        limit=limit,
        before=before,
    )
    return InboxOut(
        items=[_notif_out(n) for n in page.items],
        has_more=page.has_more,
        next_before=page.next_before,
    )


@router.post("/{notification_id}/read", response_model=NotificationOut)
async def mark_read(
    notification_id: UUID,
    ctx: CurrentUserDep,
    db: SessionDep,
) -> NotificationOut:
    try:
        notif = await _service(db).mark_read(
            notification_id=notification_id,
            user_id=ctx.user_id,
            residency_region=ctx.residency_region.value,
        )
    except NotificationError as exc:
        _raise(exc)
        raise
    return _notif_out(notif)


class MarkAllReadOut(BaseModel):
    updated: int


@router.post("/mark-all-read", response_model=MarkAllReadOut)
async def mark_all_read(ctx: CurrentUserDep, db: SessionDep) -> MarkAllReadOut:
    n = await _service(db).mark_all_read(
        user_id=ctx.user_id, residency_region=ctx.residency_region.value
    )
    return MarkAllReadOut(updated=n)


# --- Routes: preferences -------------------------------------------------


@router.get("/preferences", response_model=PreferencesGroupedOut)
async def list_preferences(ctx: CurrentUserDep, db: SessionDep) -> PreferencesGroupedOut:
    prefs = await _service(db).list_preferences(
        user_id=ctx.user_id, residency_region=ctx.residency_region.value
    )
    return PreferencesGroupedOut(
        items=[
            PreferenceOut(category_slug=p.category_slug, channel=p.channel, enabled=p.enabled)
            for p in prefs
        ]
    )


@router.patch("/preferences", response_model=PreferencesGroupedOut)
async def update_preferences(
    updates: list[PreferenceUpdate],
    ctx: CurrentUserDep,
    db: SessionDep,
) -> PreferencesGroupedOut:
    if not updates:
        raise HTTPException(status_code=422, detail={"code": "notifications.empty_updates"})
    svc = _service(db)
    try:
        await svc.update_preferences(
            user_id=ctx.user_id,
            residency_region=ctx.residency_region.value,
            updates=tuple((u.category_slug, u.channel, u.enabled) for u in updates),
        )
    except NotificationError as exc:
        _raise(exc)
        raise
    prefs = await svc.list_preferences(
        user_id=ctx.user_id, residency_region=ctx.residency_region.value
    )
    return PreferencesGroupedOut(
        items=[
            PreferenceOut(category_slug=p.category_slug, channel=p.channel, enabled=p.enabled)
            for p in prefs
        ]
    )


# --- Routes: push devices ------------------------------------------------


@router.post("/push-devices", response_model=PushDeviceOut, status_code=201)
async def register_push_device(
    payload: PushDeviceRegister, ctx: CurrentUserDep, db: SessionDep
) -> PushDeviceOut:
    if not payload.fcm_token and not payload.apns_token and payload.platform != "web":
        raise HTTPException(
            status_code=422,
            detail={
                "code": "notifications.push_missing_token",
                "message": "fcm_token or apns_token required for non-web platforms",
            },
        )
    device = await _service(db).register_push_device(
        user_id=ctx.user_id,
        residency_region=ctx.residency_region.value,
        platform=payload.platform,
        installation_id=payload.installation_id,
        fcm_token=payload.fcm_token,
        apns_token=payload.apns_token,
    )
    return PushDeviceOut(
        id=device.id,
        platform=device.platform.value,
        installation_id=device.installation_id,
        is_active=device.is_active,
    )


class UnregisterResult(BaseModel):
    removed: bool


@router.delete("/push-devices/{installation_id}", response_model=UnregisterResult)
async def unregister_push_device(
    installation_id: str, ctx: CurrentUserDep, db: SessionDep
) -> UnregisterResult:
    removed = await _service(db).unregister_push_device(
        user_id=ctx.user_id,
        residency_region=ctx.residency_region.value,
        installation_id=installation_id,
    )
    return UnregisterResult(removed=removed)


# --- Routes: quiet hours -------------------------------------------------


@router.put("/quiet-hours", response_model=QuietHoursOut)
async def update_quiet_hours(
    payload: QuietHoursPut, ctx: CurrentUserDep, db: SessionDep
) -> QuietHoursOut:
    start_h, start_m = payload.start_time.split(":")
    end_h, end_m = payload.end_time.split(":")
    qh = await _service(db).update_quiet_hours(
        user_id=ctx.user_id,
        residency_region=ctx.residency_region.value,
        timezone=payload.timezone,
        start_time=time(int(start_h), int(start_m)),
        end_time=time(int(end_h), int(end_m)),
        weekdays=tuple(payload.weekdays),
    )
    return QuietHoursOut(
        timezone=qh.timezone,
        start_time=qh.start_time.strftime("%H:%M"),
        end_time=qh.end_time.strftime("%H:%M"),
        weekdays=list(qh.weekdays),
    )
