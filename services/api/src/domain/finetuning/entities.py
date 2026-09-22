"""Fine-tuning domain entities.

All entities are immutable dataclasses (slots=True, frozen=True) following the
Clean Architecture convention used throughout SilkLens (ADR-0003).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class DatasetPurpose(StrEnum):
    HERITAGE_QA = "heritage_qa"
    CULTURAL_CLASSIFICATION = "cultural_classification"
    TRANSLATION_QUALITY = "translation_quality"
    AUDIO_GUIDE_STYLE = "audio_guide_style"
    MODERATION = "moderation"


class TargetModelKind(StrEnum):
    LLM = "llm"
    VISION = "vision"
    TTS = "tts"
    TRANSLATION = "translation"
    EMBEDDING = "embedding"


class DatasetStatus(StrEnum):
    COLLECTING = "collecting"
    CURATING = "curating"
    READY = "ready"
    TRAINING = "training"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ExampleKind(StrEnum):
    PROMPT_RESPONSE = "prompt_response"
    CLASSIFICATION = "classification"
    CONVERSATION = "conversation"
    PREFERENCE = "preference"


class ExampleSourceKind(StrEnum):
    MANUAL = "manual"
    AI_APPROVED = "ai_approved"
    USER_FEEDBACK = "user_feedback"
    EXPERT_REVIEW = "expert_review"


class JobProvider(StrEnum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    HUGGINGFACE_LOCAL = "huggingface_local"
    MISTRAL = "mistral"


class JobKind(StrEnum):
    SUPERVISED = "supervised"
    RLHF = "rlhf"
    DPO = "dpo"
    LORA_ADAPTER = "lora_adapter"


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EvalKind(StrEnum):
    BLEU = "bleu"
    ROUGE = "rouge"
    HUMAN_PREFERENCE = "human_preference"
    TASK_ACCURACY = "task_accuracy"
    PERPLEXITY = "perplexity"


# ---------------------------------------------------------------------------
# Dataclass entities
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class FinetuningDataset:
    id: UUID
    tenant_id: UUID
    slug: str
    name: dict[str, str]
    purpose: DatasetPurpose
    target_model_kind: TargetModelKind
    status: DatasetStatus
    example_count: int
    min_quality_score: Decimal
    created_at: datetime
    updated_at: datetime
    description_md: str | None = None


@dataclass(slots=True, frozen=True)
class FinetuningExample:
    id: UUID
    dataset_id: UUID
    kind: ExampleKind
    input_text: str
    output_text: str
    source_kind: ExampleSourceKind
    language_tag: str
    is_approved: bool
    created_at: datetime
    input_metadata: dict[str, Any] = None  # type: ignore[assignment]
    output_metadata: dict[str, Any] = None  # type: ignore[assignment]
    quality_score: Decimal | None = None
    source_id: UUID | None = None
    approved_by: UUID | None = None
    approved_at: datetime | None = None

    def __post_init__(self) -> None:
        # dataclass frozen=True means we use object.__setattr__
        if self.input_metadata is None:
            object.__setattr__(self, "input_metadata", {})
        if self.output_metadata is None:
            object.__setattr__(self, "output_metadata", {})


@dataclass(slots=True, frozen=True)
class FinetuningJob:
    id: UUID
    dataset_id: UUID
    provider: JobProvider
    base_model_slug: str
    job_kind: JobKind
    status: JobStatus
    hyperparams: dict[str, Any]
    created_at: datetime
    provider_job_id: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    output_model_slug: str | None = None
    eval_metrics: dict[str, Any] = None  # type: ignore[assignment]
    cost_usd: Decimal | None = None

    def __post_init__(self) -> None:
        if self.eval_metrics is None:
            object.__setattr__(self, "eval_metrics", {})


@dataclass(slots=True, frozen=True)
class FinetuningEval:
    id: UUID
    job_id: UUID
    eval_kind: EvalKind
    score: Decimal
    benchmark_name: str
    eval_dataset_size: int
    created_at: datetime
