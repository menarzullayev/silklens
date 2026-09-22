"""Mock providers that return deterministic stub responses.

These exist because the real local stack (LLaVA / Kokoro / NLLB) lives on a
GPU server we can't reach from FAZA-1 dev/CI. Every domain test exercises
these — production wiring just swaps the resolver to return real providers.

The outputs are deterministic so tests can assert on labels and lengths.
"""

from __future__ import annotations

import hashlib

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
    VisionCandidate,
    VisionRequest,
    VisionResponse,
)


class MockVisionProvider:
    task_type = AiTaskType.VISION
    model_slug = "llava-1.6-34b"

    async def call(self, req: VisionRequest) -> VisionResponse:
        # Deterministic pick driven by image bytes hash so the same image
        # always yields the same label (great for cache assertions in tests).
        digest = hashlib.sha256(req.image_bytes or b"").hexdigest()
        labels = ["madrasa", "mosque", "minaret", "caravanserai", "mausoleum"]
        idx = int(digest[:2], 16) % len(labels)
        primary = labels[idx]
        return VisionResponse(
            label=primary,
            confidence=0.87,
            candidates=tuple(
                VisionCandidate(label=lbl, confidence=0.87 - 0.1 * i)
                for i, lbl in enumerate([primary, *[lbl for lbl in labels if lbl != primary][:2]])
            ),
            language=req.language,
            model_slug=self.model_slug,
        )


class MockTtsProvider:
    task_type = AiTaskType.TTS
    model_slug = "kokoro-82m"

    async def call(self, req: TtsRequest) -> TtsResponse:
        # 1-byte stub: enough to exercise the upload + media-asset path
        # without actually synthesising audio.
        return TtsResponse(
            audio_bytes=b"\x00",
            mime_type="audio/mpeg",
            duration_ms=max(100, len(req.text) * 50),
            model_slug=self.model_slug,
        )


class MockLlmProvider:
    task_type = AiTaskType.TEXT
    model_slug = "claude-opus-4-7"

    async def call(self, req: LlmRequest) -> LlmResponse:
        reply = f"[mock-llm reply to: {req.prompt[:80]}]"
        return LlmResponse(
            text=reply,
            input_tokens=len(req.prompt.split()),
            output_tokens=len(reply.split()),
            model_slug=self.model_slug,
            injection_score=0.05,
        )


class MockTranslationProvider:
    task_type = AiTaskType.TRANSLATION
    model_slug = "nllb-200-distilled-600m"

    async def call(self, req: TranslationRequest) -> TranslationResponse:
        # Deterministic prefix so tests can assert routing + cache reuse.
        return TranslationResponse(
            text=f"[{req.target_lang}] {req.text}",
            source_lang=req.source_lang,
            target_lang=req.target_lang,
            confidence=82,
            model_slug=self.model_slug,
        )


class MockEmbeddingProvider:
    task_type = AiTaskType.EMBEDDING
    model_slug = "multilingual-e5-large"
    dimensions = 1024

    async def call(self, req: EmbeddingRequest) -> EmbeddingResponse:
        # Repeat the sha256 digest until we hit the model dimension; this
        # keeps outputs deterministic but still varies per input.
        digest = hashlib.sha256(req.text.encode("utf-8")).digest()
        floats: list[float] = []
        i = 0
        while len(floats) < self.dimensions:
            byte = digest[i % len(digest)]
            floats.append((byte / 255.0) - 0.5)
            i += 1
        return EmbeddingResponse(
            vector=tuple(floats[: self.dimensions]),
            dimensions=self.dimensions,
            model_slug=self.model_slug,
        )
