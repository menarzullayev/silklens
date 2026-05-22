"""OpenAI TTS provider (interim until GPU Kokoro/Piper).

Uses OpenAI's ``tts-1`` or ``tts-1-hd`` model to synthesise MP3 audio from
text. This bridges the gap while the on-prem Kokoro-82m / Piper-uz-female
models are integrated on the GPU server.

Production extras:
* Voice selection per BCP-47 language prefix.
* Text truncated to OpenAI's 4 096-char limit.
* Retry w/ exponential back-off (3 attempts, tenacity).
* Estimated duration (words / WPM) returned in ``TtsResponse``.
* structlog latency event emitted on every call.
"""

from __future__ import annotations

import time

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.core.logging import get_logger
from src.domain.ai.entities import AiTaskType, TtsRequest, TtsResponse
from src.domain.ai.errors import AiProviderUnavailable, AiTimeout, AiValidationError

log = get_logger("silklens.ai.openai_tts")

# OpenAI TTS character limit per request.
_MAX_CHARS = 4096

# Approximate speaking rate used for duration estimation (words per minute).
_WPM = 150

# Average characters per word used for word count estimation.
_CHARS_PER_WORD = 5

# Voice selection per BCP-47 language prefix (first component, lower-cased).
_VOICE_MAP: dict[str, str] = {
    "uz": "alloy",  # neutral tone; adequate for Uzbek until Piper-uz lands
    "ru": "shimmer",  # softer tone for Russian narration
    "en": "nova",  # clear, natural English
    "zh": "echo",  # works well for Mandarin
    "de": "fable",  # German
    "ko": "onyx",  # Korean
    "ar": "alloy",  # Arabic fallback
    "fr": "shimmer",  # French
    "es": "nova",  # Spanish
    "ja": "echo",  # Japanese
}
_DEFAULT_VOICE = "alloy"

_TTS_ENDPOINT = "https://api.openai.com/v1/audio/speech"


class OpenAiTtsProvider:
    """OpenAI TTS-1 for audio guides (interim until GPU Kokoro).

    Structurally satisfies :class:`~src.domain.ai.providers.TtsProvider`.
    """

    task_type = AiTaskType.TTS
    model_slug = "openai-tts-1"

    def __init__(self, api_key: str, model: str = "tts-1") -> None:
        if not api_key:
            raise AiProviderUnavailable("openai_tts", "OPENAI_API_KEY missing")
        self._api_key = api_key
        self._model = model  # "tts-1" (fast) or "tts-1-hd" (quality)
        self.model_slug = f"openai-{model}"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def call(self, req: TtsRequest) -> TtsResponse:
        """Synthesise speech from ``req.text`` and return MP3 bytes."""
        if not req.text or not req.text.strip():
            raise AiValidationError("text", "TTS text cannot be empty")

        # Truncate to API limit — the caller (AiService) should chunk long
        # narrations before reaching the provider.
        text = req.text[:_MAX_CHARS]
        lang = (req.language or "en").split("-")[0].lower()
        voice = _VOICE_MAP.get(lang, _DEFAULT_VOICE)

        payload = {
            "model": self._model,
            "input": text,
            "voice": voice,
            "response_format": "mp3",
            "speed": 0.95,  # slightly slower for heritage narration clarity
        }

        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    _TTS_ENDPOINT,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
                audio_bytes = response.content
        except httpx.TimeoutException as exc:
            raise AiTimeout(f"OpenAI TTS timeout: {exc}") from exc
        except httpx.HTTPStatusError as exc:
            raise AiProviderUnavailable(
                "openai_tts",
                f"HTTP {exc.response.status_code}: {exc.response.text[:200]}",
            ) from exc

        latency_ms = int((time.perf_counter() - started) * 1000)
        log.info(
            "ai.openai_tts.call",
            model=self._model,
            voice=voice,
            lang=lang,
            chars=len(text),
            audio_bytes=len(audio_bytes),
            latency_ms=latency_ms,
        )

        # OpenAI doesn't return duration; estimate from character count.
        estimated_words = len(text) / _CHARS_PER_WORD
        estimated_duration_ms = max(int((estimated_words / _WPM) * 60 * 1000), 1000)

        return TtsResponse(
            audio_bytes=audio_bytes,
            mime_type="audio/mpeg",
            duration_ms=estimated_duration_ms,
            model_slug=self.model_slug,
        )
