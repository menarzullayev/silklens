"""SqlAiRepository — concrete persistence for AiService.

All the ``text()`` calls that used to live in ``src/domain/ai/service.py``
moved here, satisfying the ADR-0003 rule that ``domain/*`` may not import
SQLAlchemy. The single-round-trip ``list_fallback_chains`` (HIGH-6)
replaces the per-chain N+1 walk in the router.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date as date_cls
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.ai.entities import AiTaskType
from src.domain.ai.repository import TranslationMemoryRow, VectorHitRow
from src.infrastructure._events import jdump


@dataclass(slots=True)
class _TmRow:
    target_text: str
    confidence: int
    model_slug: str


@dataclass(slots=True)
class _VectorHitRow:
    heritage_id: UUID
    heritage_pub_id: str
    name: dict[str, Any]
    kind_slug: str
    country_code: str | None
    distance: float


class SqlAiRepository:
    """SQL implementation of :class:`src.domain.ai.repository.AiRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ---------------- model lookup ----------------

    async def resolve_model_version_id(self, model_slug: str) -> UUID | None:
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
            return UUID(str(row))
        val = (
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
        return UUID(str(val)) if val is not None else None

    async def resolve_model_id(self, model_slug: str) -> UUID | None:
        return (
            await self._session.execute(
                text("SELECT id FROM ai_models WHERE slug = :slug"),
                {"slug": model_slug},
            )
        ).scalar_one_or_none()

    # ---------------- observability writes ----------------

    async def insert_generation(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID | None,
        model_version_id: UUID,
        task_type: AiTaskType,
        input_hash: bytes,
        input_summary: str,
        output_text: str | None,
        output_jsonb: dict[str, Any] | None,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        cost_estimate: float,
    ) -> None:
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
                "tenant": tenant_id,
                "uid": user_id,
                "mv_id": model_version_id,
                "task": task_type.value,
                "ih": input_hash,
                "summary": input_summary[:512],
                "out_text": output_text,
                "out_json": jdump(output_jsonb) if output_jsonb is not None else None,
                "in_tok": input_tokens,
                "out_tok": output_tokens,
                "latency": latency_ms,
                "cost": cost_estimate,
            },
        )

    async def insert_cost_ledger(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID | None,
        model_id: UUID,
        kind: AiTaskType,
        tokens_in: int,
        tokens_out: int,
        cost: float,
    ) -> None:
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
                "tenant": tenant_id,
                "uid": user_id,
                "mid": model_id,
                "kind": kind.value,
                "tin": tokens_in,
                "tout": tokens_out,
                "cost": cost,
            },
        )

    async def upsert_daily_token_usage(
        self,
        *,
        user_id: UUID,
        model_id: UUID,
        day: date_cls,
        tokens_in: int,
        tokens_out: int,
        cost: float,
    ) -> None:
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
                "day": day,
                "tin": tokens_in,
                "tout": tokens_out,
                "cost": cost,
            },
        )

    async def emit_event(
        self,
        *,
        tenant_id: UUID,
        name: str,
        aggregate_kind: str,
        aggregate_id: UUID,
        payload: dict[str, Any],
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
                "tenant": tenant_id,
                "name": name,
                "kind": aggregate_kind,
                "aid": aggregate_id,
                "payload": jdump(payload),
            },
        )

    # ---------------- quota ----------------

    async def has_premium_entitlement(self, user_id: UUID, feature_key: str) -> bool:
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

    async def daily_request_count(
        self, *, user_id: UUID, day: date_cls, task_type: AiTaskType
    ) -> int:
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
                {"uid": user_id, "day": day, "task": task_type.value},
            )
        ).scalar_one_or_none()
        return int(row or 0)

    # ---------------- translation memory ----------------

    async def lookup_translation_memory(
        self,
        *,
        source_hash: bytes,
        source_lang: str,
        target_lang: str,
    ) -> TranslationMemoryRow | None:
        row = (
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
        if row is None:
            return None
        m = row._mapping
        return _TmRow(
            target_text=str(m["target_text"]),
            confidence=int(m["confidence"]),
            model_slug=str(m["slug"]),
        )

    async def bump_translation_memory_hit(
        self, *, source_hash: bytes, source_lang: str, target_lang: str
    ) -> None:
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

    async def insert_translation_memory(
        self,
        *,
        source_hash: bytes,
        source_lang: str,
        target_lang: str,
        model_version_id: UUID,
        source_text: str,
        target_text: str,
        confidence: int,
    ) -> None:
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
                "mv": model_version_id,
                "src": source_text,
                "tgt": target_text,
                "conf": confidence,
            },
        )

    # ---------------- prompt injection ----------------

    async def insert_prompt_injection_log(
        self,
        *,
        user_id: UUID,
        session_id: UUID | None,
        input_text_preview: str,
        score: float,
        classifier_model_version_id: UUID,
    ) -> None:
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
                "preview": input_text_preview[:512],
                "score": score,
                "mv": classifier_model_version_id,
            },
        )

    # ---------------- vector search ----------------

    async def vector_search_heritage_text(
        self,
        *,
        vector_literal: str,
        language: str,
        limit: int,
        kind_slug: str | None,
        country_code: str | None,
    ) -> list[VectorHitRow]:
        clauses: list[str] = []
        params: dict[str, object] = {"limit": limit, "lang": language, "vec": vector_literal}
        if kind_slug is not None:
            clauses.append("h.kind_slug = :kind_slug")
            params["kind_slug"] = kind_slug
        if country_code is not None:
            clauses.append("h.country_code = :country_code")
            params["country_code"] = country_code.upper()
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
                params,
            )
        ).all()
        out: list[VectorHitRow] = []
        for r in rows:
            m = r._mapping
            out.append(
                _VectorHitRow(
                    heritage_id=m["heritage_id"],
                    heritage_pub_id=m["pub_id"],
                    name=dict(m["name"]) if m["name"] else {},
                    kind_slug=m["kind_slug"],
                    country_code=m["country_code"],
                    distance=float(m["distance"]),
                )
            )
        return out

    # ---------------- fallback chains (HIGH-6) ----------------

    async def list_fallback_chains(self) -> list[dict[str, Any]]:
        """Single round-trip; replaces the prior 1+N walk in the router.

        We let Postgres aggregate the steps via ``json_agg`` ordered by
        ``step_order``. ``filter (where m.id is not null)`` returns ``NULL``
        for chains without any steps; we normalise that to ``[]`` in Python.
        """
        rows = (
            await self._session.execute(
                text(
                    """
                    SELECT
                        c.id,
                        c.slug,
                        c.task_type,
                        c.name,
                        c.is_active,
                        COALESCE(
                            json_agg(
                                json_build_object(
                                    'step_order',     s.step_order,
                                    'model_slug',     m.slug,
                                    'max_latency_ms', s.max_latency_ms,
                                    'conditions',     s.conditions
                                )
                                ORDER BY s.step_order
                            ) FILTER (WHERE m.id IS NOT NULL),
                            '[]'::json
                        ) AS steps
                    FROM ai_fallback_chains c
                    LEFT JOIN ai_fallback_chain_steps s ON s.chain_id = c.id
                    LEFT JOIN ai_models m ON m.id = s.model_id
                    GROUP BY c.id, c.slug, c.task_type, c.name, c.is_active
                    ORDER BY c.task_type, c.slug
                    """
                )
            )
        ).all()
        out: list[dict[str, Any]] = []
        for r in rows:
            m = r._mapping
            steps_raw = m["steps"] or []
            out.append(
                {
                    "slug": m["slug"],
                    "task_type": m["task_type"],
                    "name": dict(m["name"]) if m["name"] else {},
                    "is_active": bool(m["is_active"]),
                    "steps": [
                        {
                            "step_order": int(s["step_order"]),
                            "model_slug": str(s["model_slug"]),
                            "max_latency_ms": s["max_latency_ms"],
                            "conditions": dict(s["conditions"]) if s["conditions"] else {},
                        }
                        for s in steps_raw
                    ],
                }
            )
        return out


__all__ = ["SqlAiRepository"]
