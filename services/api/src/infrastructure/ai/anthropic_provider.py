"""Anthropic Claude LLM provider.

Uses the official ``anthropic`` Python SDK with prompt caching (ephemeral
``cache_control`` on the system prompt) so repeated calls reusing the same
system message hit the Anthropic-side cache. The dependency is optional
(see ``pyproject.toml``); if the package or API key is absent we raise
``AiProviderUnavailable`` so the resolver can fall through to the next
provider.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from src.core.logging import get_logger
from src.domain.ai.entities import AiTaskType, LlmRequest, LlmResponse
from src.domain.ai.errors import AiProviderUnavailable, AiTimeout

log = get_logger("silklens.ai.anthropic")


@dataclass(slots=True)
class _Usage:
    input_tokens: int = 0
    output_tokens: int = 0


class AnthropicLlmProvider:
    """Anthropic Claude provider w/ prompt caching on the system block."""

    task_type = AiTaskType.TEXT
    model_slug: str = "claude-opus-4-7"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model_id: str = "claude-opus-4-7",
        timeout_s: float = 30.0,
    ) -> None:
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._model_id = model_id
        self.model_slug = model_id
        self._timeout_s = timeout_s
        self._client = None  # lazy

    def _ensure_client(self):  # type: ignore[no-untyped-def]
        if self._client is not None:
            return self._client
        if not self._api_key:
            raise AiProviderUnavailable("anthropic", "ANTHROPIC_API_KEY missing")
        try:
            import anthropic  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover — covered by [ai] extra
            raise AiProviderUnavailable(
                "anthropic", "anthropic SDK not installed (install ai extras)"
            ) from exc
        self._client = anthropic.AsyncAnthropic(api_key=self._api_key, timeout=self._timeout_s)
        return self._client

    async def call(self, req: LlmRequest) -> LlmResponse:
        client = self._ensure_client()

        # Prompt caching: mark the system prompt as ephemeral so repeated
        # requests reusing the same system reuse the Anthropic-side cache.
        system_blocks = None
        if req.system:
            system_blocks = [
                {
                    "type": "text",
                    "text": req.system,
                    "cache_control": {"type": "ephemeral"},
                }
            ]

        try:
            message = await client.messages.create(
                model=self._model_id,
                max_tokens=req.max_output_tokens,
                system=system_blocks,
                messages=[{"role": "user", "content": req.prompt}],
            )
        except Exception as exc:  # pragma: no cover — network path
            try:
                import anthropic  # type: ignore[import-not-found]
            except ImportError:
                anthropic = None  # type: ignore[assignment]
            if anthropic is not None and isinstance(exc, anthropic.APITimeoutError):
                raise AiTimeout(f"anthropic timeout: {exc}") from exc
            raise AiProviderUnavailable("anthropic", str(exc)) from exc

        # Concatenate text blocks from the response (vision models may also
        # emit image blocks, but we're text-only here).
        text_out_parts: list[str] = []
        for block in message.content:
            if getattr(block, "type", None) == "text":
                text_out_parts.append(getattr(block, "text", ""))
        text_out = "".join(text_out_parts)

        usage = _Usage(
            input_tokens=getattr(message.usage, "input_tokens", 0) or 0,
            output_tokens=getattr(message.usage, "output_tokens", 0) or 0,
        )
        return LlmResponse(
            text=text_out,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            model_slug=self.model_slug,
            injection_score=0.0,
        )
