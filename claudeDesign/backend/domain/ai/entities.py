"""AI domain entities — pure Python, framework-free.

Request / response dataclasses are immutable so any caller (FastAPI router, a
Celery worker, a test fixture) can pass them through layers without worrying
about accidental mutation. The ``AiTaskType`` enum mirrors the CHECK constraint
on ``ai_models.task_type`` (migration 0030).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID


class AiTaskType(StrEnum):
    """Mirror of ``ai_models.task_type`` CHECK constraint (migration 0030)."""

    VISION = "vision"
    TEXT = "text"
    TTS = "tts"
    TRANSLATION = "translation"
    EMBEDDING = "embedding"
    ASR = "asr"
    MODERATION = "moderation"


# --- Vision -----------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class VisionRequest:
    """Recognise a heritage subject in an image."""

    image_bytes: bytes
    mime_type: str
    language: str = "en"
    media_asset_id: UUID | None = None


@dataclass(slots=True, frozen=True)
class VisionCandidate:
    label: str
    confidence: float
    heritage_pub_id: str | None = None


@dataclass(slots=True, frozen=True)
class VisionResponse:
    label: str
    confidence: float
    candidates: tuple[VisionCandidate, ...] = field(default_factory=tuple)
    language: str = "en"
    model_slug: str = ""


# --- TTS --------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class TtsRequest:
    text: str
    language: str = "en"
    voice_id: str | None = None


@dataclass(slots=True, frozen=True)
class TtsResponse:
    audio_bytes: bytes
    mime_type: str = "audio/mpeg"
    duration_ms: int = 0
    model_slug: str = ""


# --- LLM --------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class LlmRequest:
    prompt: str
    system: str | None = None
    language: str = "en"
    max_output_tokens: int = 1024


@dataclass(slots=True, frozen=True)
class LlmResponse:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    model_slug: str = ""
    injection_score: float = 0.0


# --- Translation ------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class TranslationRequest:
    text: str
    source_lang: str
    target_lang: str


@dataclass(slots=True, frozen=True)
class TranslationResponse:
    text: str
    source_lang: str
    target_lang: str
    confidence: int = 80
    model_slug: str = ""


# --- Embeddings -------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class EmbeddingRequest:
    text: str
    language: str = "en"


@dataclass(slots=True, frozen=True)
class EmbeddingResponse:
    vector: tuple[float, ...]
    dimensions: int
    model_slug: str = ""


# --- Vector search ----------------------------------------------------------


@dataclass(slots=True, frozen=True)
class VectorSearchHit:
    heritage_id: UUID
    heritage_pub_id: str
    score: float
    name: dict[str, str] = field(default_factory=dict)
    kind_slug: str | None = None
    country_code: str | None = None
