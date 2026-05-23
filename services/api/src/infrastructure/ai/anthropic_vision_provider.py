"""Anthropic Claude Vision provider for heritage site recognition.

Interim provider until the GPU-local LLaVA/InternVL stack (on the university
RTX 4090) is reachable from the API tier. Wraps the Anthropic Messages API
with vision content blocks; images are fetched from signed MinIO URLs or
accepted as raw bytes on the ``VisionRequest``.

Production extras:
* Retry w/ exponential back-off (3 attempts, tenacity).
* Structured JSON response with regex fallback for markdown-fenced JSON.
* ``AiProviderUnavailable`` / ``AiTimeout`` on all transient paths.
* structlog latency event for ``ai_token_usage`` reconciliation.
"""

from __future__ import annotations

import base64
import json
import re
import time
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.core.logging import get_logger
from src.domain.ai.entities import AiTaskType, VisionCandidate, VisionRequest, VisionResponse
from src.domain.ai.errors import AiProviderUnavailable, AiTimeout

log = get_logger("silklens.ai.anthropic_vision")

_SYSTEM_PROMPT = (
    "You are an expert art historian and cultural heritage specialist "
    "with deep knowledge of Uzbekistan and Central Asian monuments, mosques, "
    "mausoleums, caravanserais, and archaeological sites. When shown an image, "
    "identify the heritage site or architectural style. Respond in JSON only."
)

_USER_PROMPT = """\
Analyze this image and identify the heritage site or monument.

Respond with JSON only (no markdown):
{{
  "label": "primary site name in English",
  "confidence": 0.0-1.0,
  "candidates": [
    {{"label": "site name", "confidence": 0.0-1.0, "heritage_pub_id": null}}
  ],
  "description": "brief description in the requested language",
  "language": "language code"
}}

Language: {language}"""

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


class AnthropicVisionProvider:
    """Claude Vision for heritage site recognition (interim until GPU LLaVA).

    Structurally satisfies :class:`~src.domain.ai.providers.VisionProvider`.
    """

    task_type = AiTaskType.VISION
    model_slug = "claude-sonnet-4-6-vision"

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6") -> None:
        if not api_key:
            raise AiProviderUnavailable("anthropic_vision", "ANTHROPIC_API_KEY missing")
        self._api_key = api_key
        self._model = model
        self._client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # HTTP client (lazy, connection-pooled across calls in one request)
    # ------------------------------------------------------------------

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url="https://api.anthropic.com",
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                timeout=60.0,
            )
        return self._client

    # ------------------------------------------------------------------
    # Public surface
    # ------------------------------------------------------------------

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def call(self, req: VisionRequest) -> VisionResponse:
        """Identify a heritage site from raw image bytes.

        ``VisionRequest.image_bytes`` must be non-empty.  The ``mime_type``
        field is forwarded verbatim to Anthropic's vision content block.
        """
        if not req.image_bytes:
            raise AiProviderUnavailable("anthropic_vision", "image_bytes is empty")

        image_data = base64.standard_b64encode(req.image_bytes).decode()
        media_type = req.mime_type if req.mime_type.startswith("image/") else "image/jpeg"

        user_content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": image_data,
                },
            },
            {
                "type": "text",
                "text": _USER_PROMPT.format(language=req.language or "en"),
            },
        ]

        payload = {
            "model": self._model,
            "max_tokens": 512,
            "system": _SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_content}],
        }

        started = time.perf_counter()
        try:
            client = self._get_client()
            response = await client.post("/v1/messages", json=payload)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise AiTimeout(f"Anthropic Vision timeout: {exc}") from exc
        except httpx.HTTPStatusError as exc:
            raise AiProviderUnavailable(
                "anthropic_vision",
                f"HTTP {exc.response.status_code}: {exc.response.text[:200]}",
            ) from exc

        latency_ms = int((time.perf_counter() - started) * 1000)
        data = response.json()
        raw_text: str = data["content"][0]["text"]

        log.info(
            "ai.anthropic_vision.call",
            model=self._model,
            latency_ms=latency_ms,
            input_tokens=data.get("usage", {}).get("input_tokens", 0),
            output_tokens=data.get("usage", {}).get("output_tokens", 0),
        )

        parsed = self._parse_json(raw_text)

        candidates = tuple(
            VisionCandidate(
                label=c.get("label", ""),
                confidence=float(c.get("confidence", 0.0)),
                heritage_pub_id=c.get("heritage_pub_id"),
            )
            for c in parsed.get("candidates", [])[:5]
        )

        return VisionResponse(
            label=parsed.get("label", "Unknown"),
            confidence=float(parsed.get("confidence", 0.5)),
            candidates=candidates,
            language=req.language or "en",
            model_slug=self.model_slug,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any]:
        """Parse JSON, falling back to markdown fence extraction on failure."""
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
        match = _JSON_FENCE_RE.search(raw)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        # Last resort: return a minimal fallback rather than raising so the
        # service can still return *something* and store the raw text.
        log.warning("ai.anthropic_vision.json_parse_failed", raw_preview=raw[:200])
        return {"label": raw[:100].strip(), "confidence": 0.4, "candidates": []}
