"""Provider resolver — reads ``ai_fallback_chains`` from Postgres.

For each task type the resolver walks ``ai_fallback_chains`` + steps in
``step_order``, instantiating the corresponding provider class. Mock mode
(controlled by ``settings.ai_use_mock_providers``) skips the DB read entirely
and returns the deterministic mock providers — useful for tests + first-boot
dev.

The mapping ``model_slug → provider class`` is intentionally explicit (a
small dict). Adding a new real provider means adding a class to
``infrastructure.ai`` and a row to the dict; the resolver picks it up
automatically once the admin enables the model.

**Real-Anthropic preference (FAZA 4):** when mocks are disabled AND an
``ANTHROPIC_API_KEY`` is present in the environment the resolver prepends a
real :class:`AnthropicLlmProvider` to every TEXT-task chain, so it tries the
real model first and falls through to whatever the DB chain configured (mock
included). With the key missing the resolver is unchanged.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.core.settings import get_settings
from src.domain.ai.entities import AiTaskType
from src.infrastructure.ai.anthropic_provider import AnthropicLlmProvider
from src.infrastructure.ai.mock_providers import (
    MockEmbeddingProvider,
    MockLlmProvider,
    MockTranslationProvider,
    MockTtsProvider,
    MockVisionProvider,
)

log = get_logger("silklens.ai.resolver")


# Model-slug → concrete provider factory. Anything missing falls back to the
# task-type default mock so the system stays functional pre-GPU.
_PROVIDER_FACTORIES: dict[str, Callable[[], Any]] = {
    "claude-opus-4-7": lambda: AnthropicLlmProvider(model_id="claude-opus-4-7"),
    "claude-sonnet-4-6": lambda: AnthropicLlmProvider(model_id="claude-sonnet-4-6"),
    "claude-haiku-4-5-20251001": lambda: AnthropicLlmProvider(model_id="claude-haiku-4-5-20251001"),
    # Local-only models stay on mocks until the GPU server is reachable.
    "llava-1.6-34b": MockVisionProvider,
    "llava-1.6-vicuna-7b": MockVisionProvider,
    "internvl-2-26b": MockVisionProvider,
    "kokoro-82m": MockTtsProvider,
    "piper-uz-female": MockTtsProvider,
    "nllb-200-distilled-600m": MockTranslationProvider,
    "nllb-200-3.3b": MockTranslationProvider,
    "multilingual-e5-large": MockEmbeddingProvider,
}


_TASK_DEFAULT_MOCK: dict[AiTaskType, Callable[[], Any]] = {
    AiTaskType.VISION: MockVisionProvider,
    AiTaskType.TTS: MockTtsProvider,
    AiTaskType.TEXT: MockLlmProvider,
    AiTaskType.TRANSLATION: MockTranslationProvider,
    AiTaskType.EMBEDDING: MockEmbeddingProvider,
}


class ProviderResolver:
    """Reads ``ai_fallback_chains`` and returns ordered provider instances."""

    def __init__(self, session: AsyncSession, *, use_mocks: bool = False) -> None:
        self._session = session
        self._use_mocks = use_mocks

    async def _resolve(self, task_type: AiTaskType) -> list[Any]:
        if self._use_mocks:
            return [_TASK_DEFAULT_MOCK[task_type]()]

        rows = (
            await self._session.execute(
                text(
                    """
                    SELECT m.slug
                    FROM ai_fallback_chains c
                    JOIN ai_fallback_chain_steps s ON s.chain_id = c.id
                    JOIN ai_models m ON m.id = s.model_id
                    WHERE c.task_type = :task
                      AND c.is_active
                      AND m.is_enabled
                    ORDER BY s.step_order
                    """
                ),
                {"task": task_type.value},
            )
        ).all()

        out: list[Any] = []
        for r in rows:
            slug = r._mapping["slug"]
            factory = _PROVIDER_FACTORIES.get(slug)
            if factory is None:
                log.warning("ai.resolver.no_factory", model_slug=slug)
                continue
            try:
                out.append(factory())
            except Exception as exc:  # pragma: no cover — defensive
                log.warning("ai.resolver.factory_failed", model_slug=slug, error=str(exc))
                continue

        # FAZA-4 preference: if mocks are disabled and an ANTHROPIC_API_KEY is
        # present, ensure a real Anthropic provider is the first choice for
        # TEXT tasks even when the DB chain hasn't been seeded with it.
        if task_type is AiTaskType.TEXT and os.environ.get("ANTHROPIC_API_KEY"):
            model = get_settings().anthropic_model_default
            already_real = any(isinstance(p, AnthropicLlmProvider) for p in out)
            if not already_real:
                try:
                    out.insert(0, AnthropicLlmProvider(model_id=model))
                except Exception as exc:  # pragma: no cover — defensive
                    log.warning("ai.resolver.anthropic_init_failed", error=str(exc))

        if not out:
            # Better to fall back to a mock than to fail the whole request when
            # the registry is empty (e.g. fresh install pre-seed).
            log.info("ai.resolver.fallback_to_mock", task_type=task_type.value)
            out.append(_TASK_DEFAULT_MOCK[task_type]())
        # Always end the chain with a deterministic mock so a transient
        # Anthropic 5xx doesn't take the whole request down.
        if task_type is AiTaskType.TEXT and not isinstance(out[-1], MockLlmProvider):
            out.append(MockLlmProvider())
        return out

    async def resolve_vision(self) -> list[Any]:
        return await self._resolve(AiTaskType.VISION)

    async def resolve_tts(self) -> list[Any]:
        return await self._resolve(AiTaskType.TTS)

    async def resolve_llm(self) -> list[Any]:
        return await self._resolve(AiTaskType.TEXT)

    async def resolve_translation(self) -> list[Any]:
        return await self._resolve(AiTaskType.TRANSLATION)

    async def resolve_embedding(self) -> list[Any]:
        return await self._resolve(AiTaskType.EMBEDDING)
