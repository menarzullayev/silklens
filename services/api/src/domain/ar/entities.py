"""AR gamification domain entities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class ArChallengeKind(StrEnum):
    HISTORICAL_RIDDLE = "historical_riddle"
    OBJECT_HUNT = "object_hunt"
    RECONSTRUCTION_QUIZ = "reconstruction_quiz"
    PHOTO_SPOT = "photo_spot"
    TIME_PERIOD_GUESS = "time_period_guess"


class ArDifficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


class ArSessionKind(StrEnum):
    SOLO = "solo"
    GROUP = "group"


class ArOverlayKind(StrEnum):
    INFO_CARD = "info_card"
    HISTORICAL_PHOTO = "historical_photo"
    MODEL_3D = "3d_model"
    AUDIO_HOTSPOT = "audio_hotspot"
    MEASUREMENT_GUIDE = "measurement_guide"


class ArAnchorProvider(StrEnum):
    GOOGLE_CLOUD_AR = "google_cloud_ar"
    APPLE_AR = "apple_ar"
    ARCORE = "arcore"
    MARKER_BASED = "marker_based"


@dataclass(slots=True, frozen=True)
class ArChallenge:
    id: UUID
    heritage_id: UUID
    tenant_id: UUID
    slug: str
    title: dict[str, Any]
    description_md: dict[str, Any]
    kind: ArChallengeKind
    difficulty: ArDifficulty
    reward_xp: int
    time_limit_seconds: int | None
    ar_anchor_lat: float
    ar_anchor_lng: float
    ar_anchor_altitude_m: float | None
    trigger_radius_m: float
    clue_text_md: dict[str, Any]
    correct_answer: dict[str, Any]
    hint_text_md: dict[str, Any] | None
    is_active: bool
    completion_count: int
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True, frozen=True)
class ArCompletion:
    id: UUID
    challenge_id: UUID
    user_id: UUID
    residency_region: str
    completed_at: datetime
    time_taken_seconds: int
    score: int
    hint_used: bool
    photo_media_id: UUID | None
    xp_awarded: int


@dataclass(slots=True, frozen=True)
class ArSession:
    id: UUID
    user_id: UUID
    residency_region: str
    heritage_id: UUID | None
    session_kind: ArSessionKind
    started_at: datetime
    ended_at: datetime | None
    max_participants: int
    session_code: str | None
    created_at: datetime


@dataclass(slots=True, frozen=True)
class ArOverlay:
    id: UUID
    heritage_id: UUID
    tenant_id: UUID
    overlay_kind: ArOverlayKind
    position_data: dict[str, Any]
    content_md: dict[str, Any]
    media_asset_id: UUID | None
    is_active: bool
    display_from_date: str | None
    display_until_date: str | None
    created_at: datetime


@dataclass(slots=True, frozen=True)
class ArSpatialAnchor:
    id: UUID
    heritage_id: UUID
    anchor_provider: ArAnchorProvider
    anchor_id: str
    anchor_data: dict[str, Any]
    created_at: datetime
    expires_at: datetime | None


@dataclass(slots=True, frozen=True)
class ArChallengeDraft:
    """Input DTO for creating a new AR challenge."""

    heritage_id: UUID
    tenant_id: UUID
    slug: str
    title: dict[str, Any]
    description_md: dict[str, Any]
    kind: ArChallengeKind
    difficulty: ArDifficulty
    reward_xp: int
    ar_anchor_lat: float
    ar_anchor_lng: float
    clue_text_md: dict[str, Any]
    correct_answer: dict[str, Any]
    time_limit_seconds: int | None = None
    ar_anchor_altitude_m: float | None = None
    trigger_radius_m: float = 50.0
    hint_text_md: dict[str, Any] | None = None
