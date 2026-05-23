"""OpenAI Whisper ASR provider for voice commands. SILK-0066.

Uses OpenAI's ``whisper-1`` model to transcribe audio bytes into text and
detects a high-level navigation intent so the mobile client can act hands-free
(e.g. "next stop", "play audio", "explain this place").

Production extras:
* File-size guard (25 MB — Whisper API hard limit).
* Supported language allowlist (ISO 639-1); unknown hints are dropped.
* HTML/script tag stripping to prevent prompt injection via audio.
* Text length capped at 2 000 chars (reasonable narration limit).
* Retry w/ exponential back-off (3 attempts, tenacity).
* structlog latency event emitted on every call.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.core.logging import get_logger
from src.domain.ai.entities import AiTaskType

log = get_logger("silklens.ai.openai_asr")

_MAX_AUDIO_BYTES = 25 * 1024 * 1024  # Whisper API hard limit
_MAX_TEXT_CHARS = 2000

# ISO 639-1 codes Whisper performs well on for SilkLens target markets.
_SUPPORTED_LANGS = frozenset({"uz", "ru", "en", "zh", "de", "ko", "ar", "fr", "es", "ja"})

# Command intent patterns — matched in order (most specific first).
_COMMAND_PATTERNS: list[tuple[str, str]] = [
    (r"(tushuntir|explain|расскажи|tell me about|erklatib ber)", "EXPLAIN_PLACE"),
    (r"(tarjima|translate|переведи|翻译)", "TRANSLATE"),
    (r"(keyingi|next|следующий|다음|nächste)", "NEXT_STOP"),
    (r"(qanday boraman|how (do i get|to get)|как добраться|路怎么走)", "NAVIGATE"),
    (r"(yordam|help|помощь|帮助|hilfe)", "HELP"),
    (r"(bron|chipta|ticket|билет|预订)", "BOOK_TICKET"),
    (r"(audio|ovoz|sound|звук|play guide)", "PLAY_AUDIO"),
    (r"(to'xtat|stop|остановить|停止)", "STOP_AUDIO"),
]


def _detect_intent(text: str) -> str | None:
    lowered = text.lower()
    for pattern, intent in _COMMAND_PATTERNS:
        if re.search(pattern, lowered):
            return intent
    return None


def _sanitize(text: str) -> str:
    """Strip HTML/script tags (prompt-injection guard) and cap length."""
    return re.sub(r"<[^>]+>", "", text)[:_MAX_TEXT_CHARS]


@dataclass(slots=True, frozen=True)
class AsrResult:
    """Transcription result returned by :class:`OpenAiAsrProvider`."""

    text: str
    detected_language: str
    confidence: float
    command_intent: str | None
    command_params: dict[str, Any] = field(default_factory=dict)


class OpenAiAsrProvider:
    """Whisper ASR for voice-command input.

    Structurally satisfies the ASR provider protocol (no formal base class
    per Clean Architecture — structural typing only).
    """

    task_type = AiTaskType.ASR
    model_slug = "openai-whisper-1"

    def __init__(self, api_key: str, model: str = "whisper-1") -> None:
        if not api_key:
            from src.domain.ai.errors import AiProviderUnavailable

            raise AiProviderUnavailable("openai_asr", "OPENAI_API_KEY missing")
        self._api_key = api_key
        self._model = model
        self.model_slug = f"openai-{model}"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    async def transcribe(self, audio_bytes: bytes, language: str | None = None) -> AsrResult:
        """Transcribe ``audio_bytes`` and return :class:`AsrResult`.

        ``language`` is a BCP-47 hint (e.g. ``"uz"``, ``"en-US"``); only the
        primary subtag is forwarded to Whisper.  Unknown subtags are silently
        dropped so the model uses its own language detection.
        """
        from src.domain.ai.errors import AiProviderUnavailable, AiTimeout, AiValidationError

        if not audio_bytes:
            raise AiValidationError("audio", "Audio bytes cannot be empty")
        if len(audio_bytes) > _MAX_AUDIO_BYTES:
            raise AiValidationError("audio", "Audio file too large (max 25 MB)")

        form_data: dict[str, str] = {
            "model": self._model,
            "response_format": "verbose_json",
        }
        if language:
            lang_code = language.split("-")[0].lower()
            if lang_code in _SUPPORTED_LANGS:
                form_data["language"] = lang_code

        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    data=form_data,
                    files={"file": ("audio.webm", audio_bytes, "audio/webm")},
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.TimeoutException as exc:
            raise AiTimeout(f"Whisper ASR timeout: {exc}") from exc
        except httpx.HTTPStatusError as exc:
            raise AiProviderUnavailable(
                "openai_asr",
                f"HTTP {exc.response.status_code}: {exc.response.text[:200]}",
            ) from exc

        latency_ms = int((time.perf_counter() - started) * 1000)
        raw_text = _sanitize(data.get("text", "").strip())
        detected_lang = data.get("language") or (
            language.split("-")[0].lower() if language else "en"
        )
        intent = _detect_intent(raw_text)

        log.info(
            "ai.openai_asr.transcribe",
            model=self._model,
            detected_lang=detected_lang,
            chars=len(raw_text),
            intent=intent,
            latency_ms=latency_ms,
        )

        return AsrResult(
            text=raw_text,
            detected_language=detected_lang,
            # Whisper ``verbose_json`` does not expose a top-level confidence
            # score; 0.9 is a reasonable prior for the model's typical WER.
            confidence=0.9,
            command_intent=intent,
            command_params={},
        )
