"""AiRepository protocol — every persistence path AiService needs.

ADR-0003 requires the ``domain`` layer to be free of SQLAlchemy. AiService
previously baked ``text()`` calls into every public method, which made it
hard to unit-test (mocks had to fake an AsyncSession) and forced the
test harness to spin up Postgres for trivial business-logic checks.

This protocol is the seam: ``SqlAiRepository`` in
``src/infrastructure/ai/repository.py`` is the production implementation;
tests can supply an in-memory double.
"""

from __future__ import annotations

from datetime import date as date_cls
from typing import Any, Protocol
from uuid import UUID

from src.domain.ai.entities import AiTaskType


class TranslationMemoryRow(Protocol):
    """Row-shape returned by :meth:`AiRepository.lookup_translation_memory`.

    Pure-data attribute access; the implementation maps the SQL row to this.
    """

    target_text: str
    confidence: int
    model_slug: str


class VectorHitRow(Protocol):
    """Row-shape returned by :meth:`AiRepository.vector_search`."""

    heritage_id: UUID
    heritage_pub_id: str
    name: dict[str, Any]
    kind_slug: str
    country_code: str | None
    distance: float


class AiRepository(Protocol):
    """All SQL paths AiService depends on."""

    # ----- model + version lookup -----
    async def resolve_model_version_id(self, model_slug: str) -> UUID | None: ...
    async def resolve_model_id(self, model_slug: str) -> UUID | None: ...

    # ----- inference observability -----
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
    ) -> None: ...

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
    ) -> None: ...

    async def upsert_daily_token_usage(
        self,
        *,
        user_id: UUID,
        model_id: UUID,
        day: date_cls,
        tokens_in: int,
        tokens_out: int,
        cost: float,
    ) -> None: ...

    async def emit_event(
        self,
        *,
        tenant_id: UUID,
        name: str,
        aggregate_kind: str,
        aggregate_id: UUID,
        payload: dict[str, Any],
    ) -> None: ...

    # ----- quota -----
    async def has_premium_entitlement(self, user_id: UUID, feature_key: str) -> bool: ...
    async def daily_request_count(
        self, *, user_id: UUID, day: date_cls, task_type: AiTaskType
    ) -> int: ...

    # ----- translation memory -----
    async def lookup_translation_memory(
        self,
        *,
        source_hash: bytes,
        source_lang: str,
        target_lang: str,
    ) -> TranslationMemoryRow | None: ...

    async def bump_translation_memory_hit(
        self, *, source_hash: bytes, source_lang: str, target_lang: str
    ) -> None: ...

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
    ) -> None: ...

    # ----- prompt-injection -----
    async def insert_prompt_injection_log(
        self,
        *,
        user_id: UUID,
        session_id: UUID | None,
        input_text_preview: str,
        score: float,
        classifier_model_version_id: UUID,
    ) -> None: ...

    # ----- vector search -----
    async def vector_search_heritage_text(
        self,
        *,
        vector_literal: str,
        language: str,
        limit: int,
        kind_slug: str | None,
        country_code: str | None,
    ) -> list[VectorHitRow]: ...

    # ----- fallback chains (HIGH-6) -----
    async def list_fallback_chains(self) -> list[dict[str, Any]]:
        """Single round-trip: chains + steps joined via ``json_agg``.

        Each returned dict has keys ``slug``, ``task_type``, ``name``,
        ``is_active``, ``steps`` (list of dicts with ``step_order``,
        ``model_slug``, ``max_latency_ms``, ``conditions``).
        """
        ...


__all__ = ["AiRepository", "TranslationMemoryRow", "VectorHitRow"]
