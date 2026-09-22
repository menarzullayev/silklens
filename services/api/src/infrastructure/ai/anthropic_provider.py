"""Anthropic Claude LLM provider — production-ready.

Wraps the official ``anthropic`` Python SDK with three production extras
beyond the FAZA-1 stub:

* **Prompt caching** — the system prompt is wrapped in a
  ``cache_control = {"type": "ephemeral"}`` block so repeated requests with
  the same system instructions hit Anthropic's prompt cache (huge cost
  win on agents that reuse a long system).
* **Streaming** — ``chat_stream`` returns an ``AsyncIterator[str]`` yielding
  text chunks. No router consumes it yet; the provider is ready for FAZA-5
  agent integration.
* **Tool-use passthrough** — optional ``tools`` definitions are forwarded
  verbatim to Claude (placeholder for the agent layer).
* **Retry w/ exponential backoff** — 3 retries on 429/5xx via ``tenacity``.
* **Metrics** — every call emits a structlog event with ``latency_ms`` +
  ``tokens_in/out`` so the AiService persisting to ``ai_token_usage`` +
  ``ai_cost_ledger`` reconciles cleanly with what we billed upstream.
* **Soft-fail** — missing ``ANTHROPIC_API_KEY`` raises
  :class:`AiProviderUnavailable` so the resolver falls through to the next
  provider rather than the request 500ing.
"""

from __future__ import annotations

import os
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from src.core.logging import get_logger
from src.domain.ai.entities import AiTaskType, LlmRequest, LlmResponse
from src.domain.ai.errors import AiProviderUnavailable, AiTimeout

log = get_logger("silklens.ai.anthropic")


# Status codes that warrant a retry. Everything else fails fast (a 400 won't
# improve on a retry; a 429 / 5xx might).
_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


@dataclass(slots=True)
class _Usage:
    input_tokens: int = 0
    output_tokens: int = 0


def _is_retryable(exc: BaseException) -> bool:
    """tenacity predicate — only retry transient Anthropic failures."""
    try:
        import anthropic
    except ImportError:  # pragma: no cover — exercised via [ai] extra
        return False
    if isinstance(exc, anthropic.APITimeoutError):
        return True
    if isinstance(exc, anthropic.APIStatusError):
        return exc.status_code in _RETRYABLE_STATUS
    return isinstance(exc, anthropic.RateLimitError | anthropic.APIConnectionError)


class AnthropicLlmProvider:
    """Production Anthropic Claude provider with caching, retries + streaming."""

    task_type = AiTaskType.TEXT
    model_slug: str = "claude-opus-4-7"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model_id: str = "claude-opus-4-7",
        timeout_s: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._model_id = model_id
        self.model_slug = model_id
        self._timeout_s = timeout_s
        self._max_retries = max(1, max_retries)
        self._client: Any = None  # lazy

    # ------------------------------------------------------------------
    # SDK plumbing
    # ------------------------------------------------------------------

    def _ensure_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not self._api_key:
            raise AiProviderUnavailable("anthropic", "ANTHROPIC_API_KEY missing")
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover — covered by [ai] extra
            raise AiProviderUnavailable(
                "anthropic", "anthropic SDK not installed (install ai extras)"
            ) from exc
        self._client = anthropic.AsyncAnthropic(api_key=self._api_key, timeout=self._timeout_s)
        return self._client

    def _build_system_blocks(self, system: str | None) -> list[dict[str, Any]] | None:
        if not system:
            return None
        return [
            {
                "type": "text",
                "text": system,
                # Prompt caching — anything before this marker is cached
                # for ~5 minutes Anthropic-side.
                "cache_control": {"type": "ephemeral"},
            }
        ]

    def _retrying(self) -> AsyncRetrying:
        return AsyncRetrying(
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=8.0),
            retry=retry_if_exception(_is_retryable),
            reraise=True,
        )

    def _wrap_exception(self, exc: Exception) -> Exception:
        try:
            import anthropic
        except ImportError:  # pragma: no cover
            return AiProviderUnavailable("anthropic", str(exc))
        if isinstance(exc, anthropic.APITimeoutError):
            return AiTimeout(f"anthropic timeout: {exc}")
        return AiProviderUnavailable("anthropic", str(exc))

    # ------------------------------------------------------------------
    # Public surface
    # ------------------------------------------------------------------

    async def call(
        self,
        req: LlmRequest,
        *,
        tools: list[dict[str, Any]] | None = None,
    ) -> LlmResponse:
        """Single-shot LLM call. Records metrics + retries on transient errors."""
        client = self._ensure_client()
        system_blocks = self._build_system_blocks(req.system)
        kwargs: dict[str, Any] = {
            "model": self._model_id,
            "max_tokens": req.max_output_tokens,
            "messages": [{"role": "user", "content": req.prompt}],
        }
        if system_blocks is not None:
            kwargs["system"] = system_blocks
        if tools:
            kwargs["tools"] = tools

        started = time.perf_counter()
        try:
            async for attempt in self._retrying():
                with attempt:
                    message = await client.messages.create(**kwargs)
        except RetryError as exc:  # pragma: no cover — final retry exhausted
            inner = exc.last_attempt.exception() if exc.last_attempt else None
            cause: Exception = inner if isinstance(inner, Exception) else exc
            raise self._wrap_exception(cause) from exc
        except Exception as exc:  # pragma: no cover — network path
            raise self._wrap_exception(exc) from exc

        latency_ms = int((time.perf_counter() - started) * 1000)
        text_out = self._concat_text_blocks(message.content)
        usage = _Usage(
            input_tokens=int(getattr(message.usage, "input_tokens", 0) or 0),
            output_tokens=int(getattr(message.usage, "output_tokens", 0) or 0),
        )
        log.info(
            "ai.anthropic.call",
            model=self._model_id,
            latency_ms=latency_ms,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
        )
        return LlmResponse(
            text=text_out,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            model_slug=self.model_slug,
            injection_score=0.0,
        )

    async def chat_stream(
        self,
        req: LlmRequest,
        *,
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[str]:
        """Async iterator of text chunks from Anthropic's streaming API.

        Provider-ready; no router consumes this yet (FAZA-5 agent layer).
        Retries are intentionally **not** wrapped around the stream — once
        a stream has started, retrying it would replay token deltas.
        """
        client = self._ensure_client()
        system_blocks = self._build_system_blocks(req.system)
        kwargs: dict[str, Any] = {
            "model": self._model_id,
            "max_tokens": req.max_output_tokens,
            "messages": [{"role": "user", "content": req.prompt}],
        }
        if system_blocks is not None:
            kwargs["system"] = system_blocks
        if tools:
            kwargs["tools"] = tools

        started = time.perf_counter()
        try:
            async with client.messages.stream(**kwargs) as stream:
                async for chunk in stream.text_stream:
                    yield chunk
        except Exception as exc:  # pragma: no cover — network path
            raise self._wrap_exception(exc) from exc
        log.info(
            "ai.anthropic.stream.done",
            model=self._model_id,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _concat_text_blocks(content: Any) -> str:
        """Concatenate every ``type='text'`` block from an Anthropic response."""
        parts: list[str] = []
        for block in content or []:
            if getattr(block, "type", None) == "text":
                parts.append(getattr(block, "text", "") or "")
        return "".join(parts)
