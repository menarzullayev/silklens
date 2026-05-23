"""AI application service.

Coordinates provider resolution and persistence to the AI catalog tables.
All DB I/O goes through :class:`src.domain.ai.repository.AiRepository`
(ADR-0003: domain layer must not import SQLAlchemy).

The service is provider-agnostic: callers inject a ``ProviderResolver`` (or any
object exposing ``async def resolve(task_type) -> list[provider]``). Mock-only
test wiring passes an in-memory resolver; production wiring resolves against
``ai_fallback_chains`` rows.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Protocol
from uuid import UUID

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
    VectorSearchHit,
    VisionRequest,
    VisionResponse,
)
from src.domain.ai.errors import (
    AiConflictError,
    AiError,
    AiProviderUnavailable,
    AiQuotaExceeded,
    AiValidationError,
)
from src.domain.ai.repository import AiRepository

if TYPE_CHECKING:
    from src.domain.ai.providers import (
        EmbeddingProvider,
        LlmProvider,
        TranslationProvider,
        TtsProvider,
        VisionProvider,
    )


# --- Adapter protocols -----------------------------------------------------


class ProviderResolverProtocol(Protocol):
    """Returns ordered providers for a task type."""

    async def resolve_vision(self) -> list[VisionProvider]: ...
    async def resolve_tts(self) -> list[TtsProvider]: ...
    async def resolve_llm(self) -> list[LlmProvider]: ...
    async def resolve_translation(self) -> list[TranslationProvider]: ...
    async def resolve_embedding(self) -> list[EmbeddingProvider]: ...


class MediaRepositoryProtocol(Protocol):
    """Minimal media contract; Agent A's MediaRepository implements this."""

    async def get_bytes(self, asset_id: UUID) -> tuple[bytes, str]:
        """Return (bytes, mime_type) for the asset."""
        ...

    async def store_generated(
        self,
        *,
        tenant_id: UUID,
        owner_user_id: UUID | None,
        kind: str,
        mime_type: str,
        payload: bytes,
        language_tag: str | None = None,
    ) -> tuple[UUID, str]:
        """Persist new generated asset + return (asset_id, signed_url)."""
        ...


# --- Helpers ---------------------------------------------------------------


def _sha256(text_input: str) -> bytes:
    return hashlib.sha256(text_input.encode("utf-8")).digest()


def _vector_literal(embedding: tuple[float, ...]) -> str:
    """Format a pgvector text literal (``[0.1,0.2,…]``).

    Float-only guard (SEC-014): callers built ``embedding`` from a provider
    response and we never want a non-numeric to escape into the formatted
    SQL literal. The check is cheap (one ``isinstance`` per dim) and removes
    a class of injection-by-mistake bugs.
    """
    if not embedding:
        raise AiValidationError("embedding", "must be non-empty")
    for v in embedding:
        if not isinstance(v, float):
            raise AiValidationError(
                "embedding", f"expected float component, got {type(v).__name__}"
            )
    return "[" + ",".join(f"{v:.6f}" for v in embedding) + "]"


# --- Service ---------------------------------------------------------------


class AiService:
    """Application service for all AI capabilities.

    Construction is light (just dependency wiring). Each public method opens
    its own SQL flow so callers can use the service from any FastAPI route.
    """

    # Free-tier per-day recognition quota; premium users with the
    # ``ai_chat_unlimited`` entitlement bypass this gate.
    FREE_RECOGNITION_DAILY: int = 10
    FREE_CHAT_DAILY: int = 50

    def __init__(
        self,
        *,
        repository: AiRepository,
        resolver: ProviderResolverProtocol,
        media: MediaRepositoryProtocol | None = None,
        tenant_id: UUID,
    ) -> None:
        self._repo = repository
        self._resolver = resolver
        self._media = media
        self._tenant_id = tenant_id

    # ------------------------------------------------------------------
    # Provider invocation w/ fallback walk
    # ------------------------------------------------------------------

    async def _walk_providers(self, providers: list[Any], req: object) -> object:
        last_exc: Exception | None = None
        for prov in providers:
            try:
                return await prov.call(req)
            except AiError as exc:
                last_exc = exc
                continue
            except Exception as exc:  # pragma: no cover — defensive
                last_exc = exc
                continue
        if last_exc is None:
            raise AiProviderUnavailable("none", "no providers configured")
        if isinstance(last_exc, AiError):
            raise last_exc
        raise AiProviderUnavailable("unknown", str(last_exc))

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    async def _log_generation(
        self,
        *,
        task_type: AiTaskType,
        model_slug: str,
        user_id: UUID | None,
        input_summary: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: int = 0,
        cost: float = 0.0,
        output_text: str | None = None,
        output_jsonb: dict[str, Any] | None = None,
    ) -> None:
        # Observability — record inference latency + token usage. The slug
        # is split provider/model so the Grafana panel can group either way.
        # Failures are non-fatal; this is observability, not the contract.
        try:
            from src.core.metrics import (
                ai_inference_duration_seconds,
                ai_tokens_used_total,
            )

            if "/" in model_slug:
                provider, model_name = model_slug.split("/", 1)
            else:
                provider, model_name = "unknown", model_slug
            ai_inference_duration_seconds.labels(
                provider=provider, model=model_name, task_type=task_type.value
            ).observe(max(latency_ms, 0) / 1000.0)
            if input_tokens:
                ai_tokens_used_total.labels(
                    provider=provider, model=model_name, direction="in"
                ).inc(input_tokens)
            if output_tokens:
                ai_tokens_used_total.labels(
                    provider=provider, model=model_name, direction="out"
                ).inc(output_tokens)
        except Exception:  # noqa: S110  # nosec B110
            # Observability is best-effort — never break a real inference call.
            pass

        mv_id = await self._repo.resolve_model_version_id(model_slug)
        if mv_id is None:
            # Skip the log row rather than raise: the call itself succeeded
            # and persistence is observability, not part of the contract.
            return
        await self._repo.insert_generation(
            tenant_id=self._tenant_id,
            user_id=user_id,
            model_version_id=mv_id,
            task_type=task_type,
            input_hash=_sha256(input_summary),
            input_summary=input_summary,
            output_text=output_text,
            output_jsonb=output_jsonb,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cost_estimate=cost,
        )

        model_id = await self._repo.resolve_model_id(model_slug)
        if model_id is not None:
            await self._repo.insert_cost_ledger(
                tenant_id=self._tenant_id,
                user_id=user_id,
                model_id=model_id,
                kind=task_type,
                tokens_in=input_tokens,
                tokens_out=output_tokens,
                cost=cost,
            )
            if user_id is not None:
                today = datetime.now(UTC).date()
                await self._repo.upsert_daily_token_usage(
                    user_id=user_id,
                    model_id=model_id,
                    day=today,
                    tokens_in=input_tokens,
                    tokens_out=output_tokens,
                    cost=cost,
                )

    async def _emit_event(
        self, *, name: str, aggregate_kind: str, aggregate_id: UUID, payload: dict[str, Any]
    ) -> None:
        await self._repo.emit_event(
            tenant_id=self._tenant_id,
            name=name,
            aggregate_kind=aggregate_kind,
            aggregate_id=aggregate_id,
            payload=payload,
        )

    # ------------------------------------------------------------------
    # Quota enforcement
    # ------------------------------------------------------------------

    async def _has_premium_entitlement(self, user_id: UUID, feature_key: str) -> bool:
        return await self._repo.has_premium_entitlement(user_id, feature_key)

    async def _daily_requests(self, user_id: UUID, task_type: AiTaskType) -> int:
        today = datetime.now(UTC).date()
        return await self._repo.daily_request_count(user_id=user_id, day=today, task_type=task_type)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def recognize_image(
        self,
        *,
        asset_id: UUID,
        language: str,
        user_id: UUID | None,
    ) -> VisionResponse:
        if self._media is None:
            raise AiProviderUnavailable("media", "media repository not configured")

        # Quota gate (free users only)
        if user_id is not None and not await self._has_premium_entitlement(
            user_id, "ai_chat_unlimited"
        ):
            used = await self._daily_requests(user_id, AiTaskType.VISION)
            if used >= self.FREE_RECOGNITION_DAILY:
                raise AiQuotaExceeded("recognition", limit=self.FREE_RECOGNITION_DAILY)

        image_bytes, mime_type = await self._media.get_bytes(asset_id)
        providers = await self._resolver.resolve_vision()
        req = VisionRequest(
            image_bytes=image_bytes,
            mime_type=mime_type,
            language=language,
            media_asset_id=asset_id,
        )
        result: VisionResponse = await self._walk_providers(providers, req)  # type: ignore[assignment]
        await self._log_generation(
            task_type=AiTaskType.VISION,
            model_slug=result.model_slug,
            user_id=user_id,
            input_summary=f"asset:{asset_id} lang:{language}",
            output_jsonb={"label": result.label, "confidence": result.confidence},
        )
        await self._emit_event(
            name="vision.recognition.v1",
            aggregate_kind="media_asset",
            aggregate_id=asset_id,
            payload={
                "label": result.label,
                "confidence": result.confidence,
                "language": language,
                "model_slug": result.model_slug,
            },
        )
        return result

    async def generate_tts(
        self,
        *,
        text_input: str,
        language: str,
        voice_id: str | None,
        user_id: UUID | None,
    ) -> tuple[UUID, str, TtsResponse]:
        """Returns ``(media_asset_id, signed_url, tts_response)``."""
        if not text_input.strip():
            raise AiValidationError("text", "must not be empty")
        if self._media is None:
            raise AiProviderUnavailable("media", "media repository not configured")
        providers = await self._resolver.resolve_tts()
        req = TtsRequest(text=text_input, language=language, voice_id=voice_id)
        resp: TtsResponse = await self._walk_providers(providers, req)  # type: ignore[assignment]
        asset_id, signed_url = await self._media.store_generated(
            tenant_id=self._tenant_id,
            owner_user_id=user_id,
            kind="audio_tts",
            mime_type=resp.mime_type,
            payload=resp.audio_bytes,
            language_tag=language,
        )
        await self._log_generation(
            task_type=AiTaskType.TTS,
            model_slug=resp.model_slug,
            user_id=user_id,
            input_summary=f"tts:{language}:{len(text_input)}chars",
            output_jsonb={
                "asset_id": str(asset_id),
                "duration_ms": resp.duration_ms,
            },
        )
        await self._emit_event(
            name="tts.generated.v1",
            aggregate_kind="media_asset",
            aggregate_id=asset_id,
            payload={
                "language": language,
                "duration_ms": resp.duration_ms,
                "model_slug": resp.model_slug,
            },
        )
        return asset_id, signed_url, resp

    async def translate(
        self,
        *,
        text_input: str,
        source_lang: str,
        target_lang: str,
        user_id: UUID | None = None,
    ) -> TranslationResponse:
        if not text_input.strip():
            raise AiValidationError("text", "must not be empty")
        if source_lang == target_lang:
            raise AiConflictError("target_lang", "must differ from source_lang")

        source_hash = _sha256(text_input)
        hit = await self._repo.lookup_translation_memory(
            source_hash=source_hash,
            source_lang=source_lang,
            target_lang=target_lang,
        )
        if hit is not None:
            await self._repo.bump_translation_memory_hit(
                source_hash=source_hash,
                source_lang=source_lang,
                target_lang=target_lang,
            )
            return TranslationResponse(
                text=hit.target_text,
                source_lang=source_lang,
                target_lang=target_lang,
                confidence=hit.confidence,
                model_slug=hit.model_slug,
            )

        providers = await self._resolver.resolve_translation()
        req = TranslationRequest(text=text_input, source_lang=source_lang, target_lang=target_lang)
        resp: TranslationResponse = await self._walk_providers(providers, req)  # type: ignore[assignment]

        mv_id = await self._repo.resolve_model_version_id(resp.model_slug)
        if mv_id is not None:
            await self._repo.insert_translation_memory(
                source_hash=source_hash,
                source_lang=source_lang,
                target_lang=target_lang,
                model_version_id=mv_id,
                source_text=text_input,
                target_text=resp.text,
                confidence=resp.confidence,
            )

        await self._log_generation(
            task_type=AiTaskType.TRANSLATION,
            model_slug=resp.model_slug,
            user_id=user_id,
            input_summary=f"{source_lang}->{target_lang}:{len(text_input)}chars",
            output_text=resp.text,
        )
        return resp

    async def chat(
        self,
        *,
        prompt: str,
        system: str | None,
        user_id: UUID,
        session_id: UUID | None = None,
    ) -> LlmResponse:
        if not prompt.strip():
            raise AiValidationError("prompt", "must not be empty")

        if not await self._has_premium_entitlement(user_id, "ai_chat_unlimited"):
            used = await self._daily_requests(user_id, AiTaskType.TEXT)
            if used >= self.FREE_CHAT_DAILY:
                raise AiQuotaExceeded("chat", limit=self.FREE_CHAT_DAILY)

        providers = await self._resolver.resolve_llm()
        req = LlmRequest(prompt=prompt, system=system)
        resp: LlmResponse = await self._walk_providers(providers, req)  # type: ignore[assignment]

        # Injection log if classifier says > 0.5
        if resp.injection_score > 0.5:
            mv_id = await self._repo.resolve_model_version_id(resp.model_slug)
            if mv_id is not None:
                await self._repo.insert_prompt_injection_log(
                    user_id=user_id,
                    session_id=session_id,
                    input_text_preview=prompt,
                    score=resp.injection_score,
                    classifier_model_version_id=mv_id,
                )

        await self._log_generation(
            task_type=AiTaskType.TEXT,
            model_slug=resp.model_slug,
            user_id=user_id,
            input_summary=prompt[:512],
            input_tokens=resp.input_tokens,
            output_tokens=resp.output_tokens,
            output_text=resp.text,
        )
        return resp

    async def embed_text(self, *, text_input: str, language: str = "en") -> EmbeddingResponse:
        if not text_input.strip():
            raise AiValidationError("text", "must not be empty")
        providers = await self._resolver.resolve_embedding()
        req = EmbeddingRequest(text=text_input, language=language)
        resp: EmbeddingResponse = await self._walk_providers(providers, req)  # type: ignore[assignment]
        await self._log_generation(
            task_type=AiTaskType.EMBEDDING,
            model_slug=resp.model_slug,
            user_id=None,
            input_summary=text_input[:512],
            output_jsonb={"dim": resp.dimensions},
        )
        return resp

    async def vector_search(
        self,
        *,
        query_text: str,
        language: str = "en",
        kind: str = "heritage_text",
        filters: dict[str, Any] | None = None,
        limit: int = 10,
    ) -> list[VectorSearchHit]:
        if not query_text.strip():
            raise AiValidationError("query", "must not be empty")
        if kind != "heritage_text":
            raise AiValidationError("kind", f"unsupported kind '{kind}'")
        filters = filters or {}
        limit = max(1, min(limit, 50))

        emb = await self.embed_text(text_input=query_text, language=language)
        vec_literal = _vector_literal(emb.vector)

        hits_raw = await self._repo.vector_search_heritage_text(
            vector_literal=vec_literal,
            language=language,
            limit=limit,
            kind_slug=filters.get("kind_slug"),
            country_code=filters.get("country_code"),
        )
        return [
            VectorSearchHit(
                heritage_id=h.heritage_id,
                heritage_pub_id=h.heritage_pub_id,
                score=max(0.0, 1.0 - h.distance),
                name=h.name,
                kind_slug=h.kind_slug,
                country_code=h.country_code,
            )
            for h in hits_raw
        ]
