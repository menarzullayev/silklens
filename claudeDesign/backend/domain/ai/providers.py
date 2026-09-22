"""Provider protocols — one per task type.

Every concrete provider (mock, anthropic, llava, kokoro …) implements one of
these Protocols. The resolver layer reads ``ai_fallback_chains`` and returns
ordered lists of provider instances; the service tries each in turn.

The protocols are deliberately tiny: ``task_type``, ``model_slug``, and a
single ``call(req) -> resp`` coroutine. Streaming variants will land in a
follow-up FAZA.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.domain.ai.entities import (
    AiTaskType,
    EmbeddingRequest,
    EmbeddingResponse,
    LlmRequest,
    LlmResponse,
    TranslationRequest,
    TranslationResponse,
    TtsRequest,
    TtsResponse,
    VisionRequest,
    VisionResponse,
)


@runtime_checkable
class VisionProvider(Protocol):
    task_type: AiTaskType
    model_slug: str

    async def call(self, req: VisionRequest) -> VisionResponse: ...


@runtime_checkable
class TtsProvider(Protocol):
    task_type: AiTaskType
    model_slug: str

    async def call(self, req: TtsRequest) -> TtsResponse: ...


@runtime_checkable
class LlmProvider(Protocol):
    task_type: AiTaskType
    model_slug: str

    async def call(self, req: LlmRequest) -> LlmResponse: ...


@runtime_checkable
class TranslationProvider(Protocol):
    task_type: AiTaskType
    model_slug: str

    async def call(self, req: TranslationRequest) -> TranslationResponse: ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    task_type: AiTaskType
    model_slug: str
    dimensions: int

    async def call(self, req: EmbeddingRequest) -> EmbeddingResponse: ...


AnyProvider = VisionProvider | TtsProvider | LlmProvider | TranslationProvider | EmbeddingProvider
