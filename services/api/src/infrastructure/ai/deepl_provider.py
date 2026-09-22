"""DeepL translation provider (interim until GPU NLLB-200).

Wraps the DeepL REST v2 API.  Uzbek and other Central Asian languages not
supported by DeepL are explicitly rejected with ``AiValidationError`` — the
resolver should route those through the NLLB mock (or, later, the real
NLLB-200 provider on the GPU server).

Free-tier keys end with ``:fx``; the provider auto-selects the correct base
URL so the same class works for both tiers.

Production extras:
* BCP-47 → DeepL language-code normalisation.
* 5 000-char truncation to match DeepL per-text limit.
* HTTP 456 (quota exceeded) mapped to ``AiProviderUnavailable``.
* Retry w/ exponential back-off (3 attempts, tenacity).
* structlog latency event on every call.
"""

from __future__ import annotations

import time
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.core.logging import get_logger
from src.domain.ai.entities import AiTaskType, TranslationRequest, TranslationResponse
from src.domain.ai.errors import AiProviderUnavailable, AiTimeout, AiValidationError

log = get_logger("silklens.ai.deepl")

# Maximum characters DeepL accepts in a single ``text`` element.
_MAX_CHARS = 5000

# BCP-47 prefix → DeepL language code mapping.
_DEEPL_LANG_MAP: dict[str, str] = {
    "en": "EN-US",
    "ru": "RU",
    "de": "DE",
    "zh": "ZH",
    "ko": "KO",
    "ar": "AR",
    "fr": "FR",
    "es": "ES",
    "ja": "JA",
    "it": "IT",
    "pt": "PT-BR",
    "pl": "PL",
    "nl": "NL",
    "tr": "TR",
    "uk": "UK",
    "cs": "CS",
    "ro": "RO",
    "fi": "FI",
    "sv": "SV",
    "da": "DA",
    "hu": "HU",
    "el": "EL",
    "bg": "BG",
    "sk": "SK",
    "sl": "SL",
    "lv": "LV",
    "lt": "LT",
    "et": "ET",
    "id": "ID",
}

# Languages not supported by DeepL — callers should route these through NLLB.
_UNSUPPORTED_SOURCES: frozenset[str] = frozenset(
    {"uz", "kk", "tk", "tg", "ky", "mn", "tt", "az", "ba"}
)

_DEEPL_FREE_BASE = "https://api-free.deepl.com"
_DEEPL_PRO_BASE = "https://api.deepl.com"


class DeepLTranslationProvider:
    """DeepL Free/Pro translation (interim until GPU NLLB-200).

    Structurally satisfies :class:`~src.domain.ai.providers.TranslationProvider`.
    """

    task_type = AiTaskType.TRANSLATION
    model_slug = "deepl-translate"

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise AiProviderUnavailable("deepl", "DEEPL_API_KEY missing")
        self._api_key = api_key
        # Free-tier keys end with ":fx"; route to the free-tier subdomain.
        self._base_url = _DEEPL_FREE_BASE if api_key.endswith(":fx") else _DEEPL_PRO_BASE

    def supports(self, source_lang: str, target_lang: str) -> bool:
        """Return True when DeepL can handle this language pair.

        Routers and the AiService may call this before ``call()`` to decide
        whether to use this provider or fall through to the NLLB chain.
        """
        src = source_lang.split("-")[0].lower()
        tgt = target_lang.split("-")[0].lower()
        return src not in _UNSUPPORTED_SOURCES and tgt in _DEEPL_LANG_MAP

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    async def call(self, req: TranslationRequest) -> TranslationResponse:
        """Translate ``req.text`` from ``source_lang`` to ``target_lang``."""
        src_raw = (req.source_lang or "en").split("-")[0].lower()
        tgt_raw = req.target_lang.split("-")[0].lower()

        if src_raw in _UNSUPPORTED_SOURCES:
            raise AiValidationError(
                "source_lang",
                f"DeepL does not support '{src_raw}'. "
                "Use the NLLB provider for Uzbek/Kazakh/Turkmen.",
            )

        target_code = _DEEPL_LANG_MAP.get(tgt_raw)
        if not target_code:
            raise AiValidationError(
                "target_lang",
                f"DeepL does not support target language '{tgt_raw}'",
            )

        # source_code = None → DeepL auto-detects, which is more accurate.
        source_code = _DEEPL_LANG_MAP.get(src_raw)

        payload: dict[str, Any] = {
            "text": [req.text[:_MAX_CHARS]],
            "target_lang": target_code,
        }
        if source_code:
            payload["source_lang"] = source_code

        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self._base_url}/v2/translate",
                    headers={
                        "Authorization": f"DeepL-Auth-Key {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise AiTimeout(f"DeepL timeout: {exc}") from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 456:
                raise AiProviderUnavailable("deepl", "quota exceeded (HTTP 456)") from exc
            raise AiProviderUnavailable(
                "deepl",
                f"HTTP {exc.response.status_code}: {exc.response.text[:200]}",
            ) from exc

        latency_ms = int((time.perf_counter() - started) * 1000)
        data = response.json()
        translation = data["translations"][0]
        translated_text: str = translation["text"]
        detected: str = translation.get("detected_source_language", src_raw or "").lower()

        log.info(
            "ai.deepl.call",
            source_lang=detected or src_raw,
            target_lang=tgt_raw,
            chars_in=len(req.text),
            chars_out=len(translated_text),
            latency_ms=latency_ms,
        )

        return TranslationResponse(
            text=translated_text,
            source_lang=detected or src_raw,
            target_lang=tgt_raw,
            # DeepL does not return a numeric confidence; 95 is a conservative
            # constant consistent with DeepL's reported accuracy figures.
            confidence=95,
            model_slug=self.model_slug,
        )
