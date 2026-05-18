"""AI endpoints.

POST /v1/ai/recognize        — vision recognition (auth required, quota'd)
POST /v1/ai/chat             — LLM chat (auth required, quota'd)
POST /v1/ai/translate        — translation w/ TM cache (auth optional)
POST /v1/ai/tts              — text-to-speech, persisted to media_assets
POST /v1/ai/search           — pgvector semantic search (public)
GET  /v1/ai/models           — list ai_models registry (ai:configure)
GET  /v1/ai/fallback-chains  — list chains + steps (ai:configure)
PATCH /v1/ai/models/{slug}   — toggle is_enabled / sort_order (ai:configure)
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.settings import get_settings
from src.domain.ai.errors import AiError
from src.domain.ai.service import AiService
from src.infrastructure.ai.media_bridge import SqlMediaBridge
from src.infrastructure.ai.resolver import ProviderResolver
from src.middleware.auth import (
    AuthContext,
    OptionalUserDep,
    require_permission,
    require_user,
)

router = APIRouter(prefix="/v1/ai", tags=["ai"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


# --- DI helpers ------------------------------------------------------------


def _build_service(db: AsyncSession, *, tenant_id: UUID, attach_media: bool = True) -> AiService:
    settings = get_settings()
    resolver = ProviderResolver(db, use_mocks=settings.ai_use_mock_providers)
    media = SqlMediaBridge(db) if attach_media else None
    return AiService(session=db, resolver=resolver, media=media, tenant_id=tenant_id)


def _raise_ai(exc: AiError) -> None:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": str(exc)},
    ) from exc


# --- Schemas ---------------------------------------------------------------


class RecognizeIn(BaseModel):
    media_asset_id: UUID
    language: str = Field(default="en", min_length=2, max_length=8)


class VisionCandidateOut(BaseModel):
    label: str
    confidence: float


class RecognizeOut(BaseModel):
    label: str
    confidence: float
    candidates: list[VisionCandidateOut]
    language: str
    model_slug: str


class ChatIn(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)
    system: str | None = Field(default=None, max_length=4000)
    conversation_id: UUID | None = None
    language: str = "en"


class ChatOut(BaseModel):
    text: str
    input_tokens: int
    output_tokens: int
    model_slug: str


class TranslateIn(BaseModel):
    text: str = Field(min_length=1, max_length=8000)
    source_lang: str = Field(min_length=2, max_length=8)
    target_lang: str = Field(min_length=2, max_length=8)


class TranslateOut(BaseModel):
    text: str
    source_lang: str
    target_lang: str
    confidence: int
    model_slug: str


class TtsIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    language: str = "en"
    voice_id: str | None = None


class TtsOut(BaseModel):
    media_asset_id: UUID
    signed_url: str
    duration_ms: int
    mime_type: str
    model_slug: str


class SearchFilters(BaseModel):
    kind_slug: str | None = None
    country_code: str | None = None


class SearchIn(BaseModel):
    query: str = Field(min_length=1, max_length=512)
    language: str = "en"
    kind: str = "heritage_text"
    filters: SearchFilters = Field(default_factory=SearchFilters)
    limit: int = Field(default=10, ge=1, le=50)


class SearchHitOut(BaseModel):
    heritage_pub_id: str
    score: float
    name: dict[str, str]
    kind_slug: str | None
    country_code: str | None


class SearchOut(BaseModel):
    items: list[SearchHitOut]


class ModelOut(BaseModel):
    slug: str
    name: dict
    task_type: str
    provider_slug: str
    is_enabled: bool
    sort_order: int


class ModelPatch(BaseModel):
    is_enabled: bool | None = None
    sort_order: int | None = Field(default=None, ge=0, le=10_000)


class ChainStepOut(BaseModel):
    step_order: int
    model_slug: str
    max_latency_ms: int | None
    conditions: dict


class ChainOut(BaseModel):
    slug: str
    task_type: str
    name: dict
    is_active: bool
    steps: list[ChainStepOut]


# --- Routes ---------------------------------------------------------------


@router.post("/recognize", response_model=RecognizeOut)
async def recognize(
    payload: RecognizeIn,
    db: SessionDep,
    ctx: Annotated[AuthContext, Depends(require_user)],
) -> RecognizeOut:
    service = _build_service(db, tenant_id=ctx.tenant_id)
    try:
        result = await service.recognize_image(
            asset_id=payload.media_asset_id,
            language=payload.language,
            user_id=ctx.user_id,
        )
    except AiError as exc:
        _raise_ai(exc)
    await db.commit()
    return RecognizeOut(
        label=result.label,
        confidence=result.confidence,
        candidates=[
            VisionCandidateOut(label=c.label, confidence=c.confidence) for c in result.candidates
        ],
        language=result.language,
        model_slug=result.model_slug,
    )


@router.post("/chat", response_model=ChatOut)
async def chat(
    payload: ChatIn,
    db: SessionDep,
    ctx: Annotated[AuthContext, Depends(require_user)],
) -> ChatOut:
    service = _build_service(db, tenant_id=ctx.tenant_id, attach_media=False)
    try:
        resp = await service.chat(
            prompt=payload.prompt,
            system=payload.system,
            user_id=ctx.user_id,
            session_id=ctx.session_id,
        )
    except AiError as exc:
        _raise_ai(exc)
    await db.commit()
    return ChatOut(
        text=resp.text,
        input_tokens=resp.input_tokens,
        output_tokens=resp.output_tokens,
        model_slug=resp.model_slug,
    )


@router.post("/translate", response_model=TranslateOut)
async def translate(
    payload: TranslateIn,
    db: SessionDep,
    ctx: OptionalUserDep,
) -> TranslateOut:
    settings = get_settings()
    tenant_id = ctx.tenant_id if ctx is not None else UUID(settings.default_tenant_id)
    service = _build_service(db, tenant_id=tenant_id, attach_media=False)
    try:
        resp = await service.translate(
            text_input=payload.text,
            source_lang=payload.source_lang,
            target_lang=payload.target_lang,
            user_id=ctx.user_id if ctx else None,
        )
    except AiError as exc:
        _raise_ai(exc)
    await db.commit()
    return TranslateOut(
        text=resp.text,
        source_lang=resp.source_lang,
        target_lang=resp.target_lang,
        confidence=resp.confidence,
        model_slug=resp.model_slug,
    )


@router.post("/tts", response_model=TtsOut)
async def tts(
    payload: TtsIn,
    db: SessionDep,
    ctx: Annotated[AuthContext, Depends(require_user)],
) -> TtsOut:
    service = _build_service(db, tenant_id=ctx.tenant_id)
    try:
        asset_id, signed_url, resp = await service.generate_tts(
            text_input=payload.text,
            language=payload.language,
            voice_id=payload.voice_id,
            user_id=ctx.user_id,
        )
    except AiError as exc:
        _raise_ai(exc)
    await db.commit()
    return TtsOut(
        media_asset_id=asset_id,
        signed_url=signed_url,
        duration_ms=resp.duration_ms,
        mime_type=resp.mime_type,
        model_slug=resp.model_slug,
    )


@router.post("/search", response_model=SearchOut)
async def search(
    payload: SearchIn,
    db: SessionDep,
    ctx: OptionalUserDep,
) -> SearchOut:
    settings = get_settings()
    tenant_id = ctx.tenant_id if ctx is not None else UUID(settings.default_tenant_id)
    service = _build_service(db, tenant_id=tenant_id, attach_media=False)
    try:
        hits = await service.vector_search(
            query_text=payload.query,
            language=payload.language,
            kind=payload.kind,
            filters=payload.filters.model_dump(exclude_none=True),
            limit=payload.limit,
        )
    except AiError as exc:
        _raise_ai(exc)
    # Embedding write is incidental — commit so the generation row + ledger persist.
    await db.commit()
    return SearchOut(
        items=[
            SearchHitOut(
                heritage_pub_id=h.heritage_pub_id,
                score=h.score,
                name=h.name,
                kind_slug=h.kind_slug,
                country_code=h.country_code,
            )
            for h in hits
        ]
    )


# --- Admin -----------------------------------------------------------------


@router.get(
    "/models",
    response_model=list[ModelOut],
    dependencies=[Depends(require_permission("ai:configure"))],
)
async def list_models(db: SessionDep) -> list[ModelOut]:
    rows = (
        await db.execute(
            text(
                """
                SELECT m.slug, m.name, m.task_type, p.slug AS provider_slug,
                       m.is_enabled, m.sort_order
                FROM ai_models m
                JOIN ai_providers p ON p.id = m.provider_id
                ORDER BY m.task_type, m.sort_order
                """
            )
        )
    ).all()
    return [
        ModelOut(
            slug=r._mapping["slug"],
            name=r._mapping["name"] or {},
            task_type=r._mapping["task_type"],
            provider_slug=r._mapping["provider_slug"],
            is_enabled=r._mapping["is_enabled"],
            sort_order=r._mapping["sort_order"],
        )
        for r in rows
    ]


@router.get(
    "/fallback-chains",
    response_model=list[ChainOut],
    dependencies=[Depends(require_permission("ai:configure"))],
)
async def list_fallback_chains(db: SessionDep) -> list[ChainOut]:
    chain_rows = (
        await db.execute(
            text(
                """
                SELECT id, slug, task_type, name, is_active
                FROM ai_fallback_chains
                ORDER BY task_type, slug
                """
            )
        )
    ).all()

    out: list[ChainOut] = []
    for chain in chain_rows:
        cm = chain._mapping
        steps = (
            await db.execute(
                text(
                    """
                    SELECT s.step_order, m.slug, s.max_latency_ms, s.conditions
                    FROM ai_fallback_chain_steps s
                    JOIN ai_models m ON m.id = s.model_id
                    WHERE s.chain_id = :cid
                    ORDER BY s.step_order
                    """
                ),
                {"cid": cm["id"]},
            )
        ).all()
        out.append(
            ChainOut(
                slug=cm["slug"],
                task_type=cm["task_type"],
                name=cm["name"] or {},
                is_active=cm["is_active"],
                steps=[
                    ChainStepOut(
                        step_order=s._mapping["step_order"],
                        model_slug=s._mapping["slug"],
                        max_latency_ms=s._mapping["max_latency_ms"],
                        conditions=s._mapping["conditions"] or {},
                    )
                    for s in steps
                ],
            )
        )
    return out


@router.patch(
    "/models/{slug}",
    response_model=ModelOut,
    dependencies=[Depends(require_permission("ai:configure"))],
)
async def patch_model(slug: str, patch: ModelPatch, db: SessionDep) -> ModelOut:
    if patch.is_enabled is None and patch.sort_order is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "ai.invalid_patch", "message": "no fields supplied"},
        )

    sets: list[str] = []
    params: dict[str, object] = {"slug": slug}
    if patch.is_enabled is not None:
        sets.append("is_enabled = :is_enabled")
        params["is_enabled"] = patch.is_enabled
    if patch.sort_order is not None:
        sets.append("sort_order = :sort_order")
        params["sort_order"] = patch.sort_order

    result = (
        await db.execute(
            text(
                f"""
                UPDATE ai_models
                SET {", ".join(sets)}
                WHERE slug = :slug
                RETURNING slug, name, task_type, provider_id, is_enabled, sort_order
                """  # noqa: S608 — sets is built from a closed set above
            ),
            params,
        )
    ).one_or_none()

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ai.model_not_found", "message": f"unknown slug '{slug}'"},
        )
    provider_slug = (
        await db.execute(
            text("SELECT slug FROM ai_providers WHERE id = :pid"),
            {"pid": result._mapping["provider_id"]},
        )
    ).scalar_one()
    await db.commit()
    m = result._mapping
    return ModelOut(
        slug=m["slug"],
        name=m["name"] or {},
        task_type=m["task_type"],
        provider_slug=provider_slug,
        is_enabled=m["is_enabled"],
        sort_order=m["sort_order"],
    )
