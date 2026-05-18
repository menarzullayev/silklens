"""AI application service.

Coordinates provider resolution, persistence to ``ai_generations`` +
``ai_cost_ledger`` + ``ai_translation_memory``, and the heritage vector-search
join. All DB I/O is hand-written SQL (asyncpg-safe via SQLAlchemy text bindings)
so we don't fight an ORM mapping for partitioned / vector tables.

The service is provider-agnostic: callers inject a ``ProviderResolver`` (or any
object exposing ``async def resolve(task_type) -> list[provider]``). Mock-only
test wiring passes an in-memory resolver; production wiring resolves against
``ai_fallback_chains`` rows.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

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
    AiError,
    AiProviderUnavailable,
    AiQuotaExceeded,
    AiValidationError,
)

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


def _jsonb(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _vector_literal(vector: tuple[float, ...]) -> str:
    """pgvector parses ``[0.1, 0.2, ...]`` text literals; safer than asyncpg binding."""
    return "[" + ",".join(f"{v:.6f}" for v in vector) + "]"


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
        session: AsyncSession,
        resolver: ProviderResolverProtocol,
        media: MediaRepositoryProtocol | None = None,
        tenant_id: UUID,
    ) -> None:
        self._session = session
        self._resolver = resolver
        self._media = media
        self._tenant_id = tenant_id

    # ------------------------------------------------------------------
    # Provider invocation w/ fallback walk
    # ------------------------------------------------------------------

    async def _walk_providers(self, providers: list, req: object) -> object:
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

    async def _resolve_model_version_id(self, model_slug: str) -> UUID | None:
        row = (
            await self._session.execute(
                text(
                    """
                    SELECT mv.id
                    FROM ai_model_versions mv
                    JOIN ai_models m ON m.id = mv.model_id
                    WHERE m.slug = :slug AND mv.is_current
                    LIMIT 1
                    """
                ),
                {"slug": model_slug},
            )
        ).scalar_one_or_none()
        if row is not None:
            return row
        # Fallback: any version of that model.
        return (
            await self._session.execute(
                text(
                    """
                    SELECT mv.id
                    FROM ai_model_versions mv
                    JOIN ai_models m ON m.id = mv.model_id
                    WHERE m.slug = :slug
                    ORDER BY mv.created_at DESC
                    LIMIT 1
                    """
                ),
                {"slug": model_slug},
            )
        ).scalar_one_or_none()

    async def _resolve_model_id(self, model_slug: str) -> UUID | None:
        return (
            await self._session.execute(
                text("SELECT id FROM ai_models WHERE slug = :slug"),
                {"slug": model_slug},
            )
        ).scalar_one_or_none()

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
        output_jsonb: dict | None = None,
    ) -> None:
        mv_id = await self._resolve_model_version_id(model_slug)
        if mv_id is None:
            # Skip the log row rather than raise: the call itself succeeded
            # and persistence is observability, not part of the contract.
            return
        await self._session.execute(
            text(
                """
                INSERT INTO ai_generations (
                    tenant_id, user_id, model_version_id, task_type,
                    input_hash, input_summary, output_text, output_jsonb,
                    input_tokens, output_tokens, latency_ms, cost_estimate, status
                )
                VALUES (
                    :tenant, :uid, :mv_id, :task,
                    :ih, :summary, :out_text, CAST(:out_json AS jsonb),
                    :in_tok, :out_tok, :latency, :cost, 'ok'
                )
                """
            ),
            {
                "tenant": self._tenant_id,
                "uid": user_id,
                "mv_id": mv_id,
                "task": task_type.value,
                "ih": _sha256(input_summary),
                "summary": input_summary[:512],
                "out_text": output_text,
                "out_json": _jsonb(output_jsonb) if output_jsonb is not None else None,
                "in_tok": input_tokens,
                "out_tok": output_tokens,
                "latency": latency_ms,
                "cost": cost,
            },
        )

        model_id = await self._resolve_model_id(model_slug)
        if model_id is not None:
            await self._session.execute(
                text(
                    """
                    INSERT INTO ai_cost_ledger (
                        tenant_id, user_id, model_id, kind,
                        tokens_in, tokens_out, cost
                    )
                    VALUES (:tenant, :uid, :mid, :kind, :tin, :tout, :cost)
                    """
                ),
                {
                    "tenant": self._tenant_id,
                    "uid": user_id,
                    "mid": model_id,
                    "kind": task_type.value,
                    "tin": input_tokens,
                    "tout": output_tokens,
                    "cost": cost,
                },
            )
            if user_id is not None:
                today = datetime.now(UTC).date()
                await self._session.execute(
                    text(
                        """
                        INSERT INTO ai_token_usage (
                            user_id, model_id, day,
                            input_tokens, output_tokens, cost, request_count
                        )
                        VALUES (:uid, :mid, :day, :tin, :tout, :cost, 1)
                        ON CONFLICT (user_id, model_id, day) DO UPDATE
                        SET input_tokens  = ai_token_usage.input_tokens  + EXCLUDED.input_tokens,
                            output_tokens = ai_token_usage.output_tokens + EXCLUDED.output_tokens,
                            cost          = ai_token_usage.cost          + EXCLUDED.cost,
                            request_count = ai_token_usage.request_count + 1,
                            updated_at    = now()
                        """
                    ),
                    {
                        "uid": user_id,
                        "mid": model_id,
                        "day": today,
                        "tin": input_tokens,
                        "tout": output_tokens,
                        "cost": cost,
                    },
                )

    async def _emit_event(
        self, *, name: str, aggregate_kind: str, aggregate_id: UUID, payload: dict
    ) -> None:
        await self._session.execute(
            text(
                """
                SELECT app.emit_event(
                    :tenant, :name, :kind, :aid, CAST(:payload AS jsonb)
                )
                """
            ),
            {
                "tenant": self._tenant_id,
                "name": name,
                "kind": aggregate_kind,
                "aid": aggregate_id,
                "payload": _jsonb(payload),
            },
        )

    # ------------------------------------------------------------------
    # Quota enforcement
    # ------------------------------------------------------------------

    async def _has_premium_entitlement(self, user_id: UUID, feature_key: str) -> bool:
        row = (
            await self._session.execute(
                text(
                    """
                    SELECT 1 FROM entitlements
                    WHERE user_id = :uid
                      AND feature_key = :fk
                      AND granted
                      AND (effective_until IS NULL OR effective_until > now())
                    LIMIT 1
                    """
                ),
                {"uid": user_id, "fk": feature_key},
            )
        ).one_or_none()
        return row is not None

    async def _daily_requests(self, user_id: UUID, task_type: AiTaskType) -> int:
        today = datetime.now(UTC).date()
        row = (
            await self._session.execute(
                text(
                    """
                    SELECT COALESCE(SUM(u.request_count), 0)
                    FROM ai_token_usage u
                    JOIN ai_models m ON m.id = u.model_id
                    WHERE u.user_id = :uid
                      AND u.day = :day
                      AND m.task_type = :task
                    """
                ),
                {"uid": user_id, "day": today, "task": task_type.value},
            )
        ).scalar_one_or_none()
        return int(row or 0)

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
            raise AiValidationError("target_lang", "must differ from source_lang")

        source_hash = _sha256(text_input)
        # Look up TM
        hit = (
            await self._session.execute(
                text(
                    """
                    SELECT tm.target_text, tm.confidence, m.slug
                    FROM ai_translation_memory tm
                    JOIN ai_model_versions mv ON mv.id = tm.model_version_id
                    JOIN ai_models m ON m.id = mv.model_id
                    WHERE tm.source_hash = :h
                      AND tm.source_lang = :s
                      AND tm.target_lang = :t
                    ORDER BY tm.last_hit_at DESC NULLS LAST, tm.created_at DESC
                    LIMIT 1
                    """
                ),
                {"h": source_hash, "s": source_lang, "t": target_lang},
            )
        ).one_or_none()

        if hit is not None:
            mapping = hit._mapping
            # Bump hit_count
            await self._session.execute(
                text(
                    """
                    UPDATE ai_translation_memory
                    SET hit_count = hit_count + 1,
                        last_hit_at = now()
                    WHERE source_hash = :h
                      AND source_lang = :s
                      AND target_lang = :t
                    """
                ),
                {"h": source_hash, "s": source_lang, "t": target_lang},
            )
            return TranslationResponse(
                text=mapping["target_text"],
                source_lang=source_lang,
                target_lang=target_lang,
                confidence=int(mapping["confidence"]),
                model_slug=str(mapping["slug"]),
            )

        providers = await self._resolver.resolve_translation()
        req = TranslationRequest(text=text_input, source_lang=source_lang, target_lang=target_lang)
        resp: TranslationResponse = await self._walk_providers(providers, req)  # type: ignore[assignment]

        mv_id = await self._resolve_model_version_id(resp.model_slug)
        if mv_id is not None:
            await self._session.execute(
                text(
                    """
                    INSERT INTO ai_translation_memory (
                        source_hash, source_lang, target_lang, model_version_id,
                        source_text, target_text, confidence, hit_count, last_hit_at
                    )
                    VALUES (:h, :s, :t, :mv, :src, :tgt, :conf, 0, NULL)
                    ON CONFLICT (source_hash, source_lang, target_lang, model_version_id)
                    DO NOTHING
                    """
                ),
                {
                    "h": source_hash,
                    "s": source_lang,
                    "t": target_lang,
                    "mv": mv_id,
                    "src": text_input,
                    "tgt": resp.text,
                    "conf": resp.confidence,
                },
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
            mv_id = await self._resolve_model_version_id(resp.model_slug)
            if mv_id is not None:
                await self._session.execute(
                    text(
                        """
                        INSERT INTO ai_prompt_injection_log (
                            user_id, session_id, input_text, score,
                            classifier_model_version_id, action
                        )
                        VALUES (:uid, :sid, :preview, :score, :mv, 'flagged')
                        """
                    ),
                    {
                        "uid": user_id,
                        "sid": session_id,
                        "preview": prompt[:512],
                        "score": resp.injection_score,
                        "mv": mv_id,
                    },
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
        filters: dict | None = None,
        limit: int = 10,
    ) -> list[VectorSearchHit]:
        if not query_text.strip():
            raise AiValidationError("query", "must not be empty")
        if kind != "heritage_text":
            # Phase-1 only ships the heritage text channel; future kinds:
            # heritage_image (CLIP-768), chunks (RAG).
            raise AiValidationError("kind", f"unsupported kind '{kind}'")
        filters = filters or {}
        limit = max(1, min(limit, 50))

        emb = await self.embed_text(text_input=query_text, language=language)
        vec_literal = _vector_literal(emb.vector)

        clauses: list[str] = []
        params: dict[str, object] = {"limit": limit, "lang": language}
        if filters.get("kind_slug"):
            clauses.append("h.kind_slug = :kind_slug")
            params["kind_slug"] = filters["kind_slug"]
        if filters.get("country_code"):
            clauses.append("h.country_code = :country_code")
            params["country_code"] = str(filters["country_code"]).upper()

        where = ""
        if clauses:
            where = "AND " + " AND ".join(clauses)

        rows = (
            await self._session.execute(
                text(
                    f"""
                    SELECT
                        h.id           AS heritage_id,
                        h.pub_id       AS pub_id,
                        h.name         AS name,
                        h.kind_slug    AS kind_slug,
                        h.country_code AS country_code,
                        (e.embedding <=> CAST(:vec AS vector)) AS distance
                    FROM embeddings_heritage_text_e5_1024 e
                    JOIN heritage_objects h ON h.id = e.heritage_id
                    WHERE h.deleted_at IS NULL
                      AND e.language_tag = :lang
                      {where}
                    ORDER BY e.embedding <=> CAST(:vec AS vector)
                    LIMIT :limit
                    """  # noqa: S608 — where is built from a closed set of bound params
                ),
                {**params, "vec": vec_literal},
            )
        ).all()

        hits: list[VectorSearchHit] = []
        for r in rows:
            m = r._mapping
            distance = float(m["distance"])
            hits.append(
                VectorSearchHit(
                    heritage_id=m["heritage_id"],
                    heritage_pub_id=m["pub_id"],
                    score=max(0.0, 1.0 - distance),
                    name=dict(m["name"]) if m["name"] else {},
                    kind_slug=m["kind_slug"],
                    country_code=m["country_code"],
                )
            )
        return hits
