"""AI endpoints.

POST /v1/ai/recognize                        — vision recognition (auth required, quota'd)
POST /v1/ai/chat                             — LLM chat with conversation persistence
POST /v1/ai/translate                        — translation w/ TM cache (auth optional)
POST /v1/ai/tts                              — text-to-speech, persisted to media_assets
POST /v1/ai/search                           — pgvector semantic search (public)
GET  /v1/ai/conversations                    — list user's conversation sessions
GET  /v1/ai/conversations/{session_id}/messages — messages for a session
DELETE /v1/ai/conversations/{session_id}     — soft-delete a session
GET  /v1/ai/models                           — list ai_models registry (ai:configure)
GET  /v1/ai/fallback-chains                  — list chains + steps (ai:configure)
PATCH /v1/ai/models/{slug}                   — toggle is_enabled / sort_order (ai:configure)
"""

from __future__ import annotations

from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.settings import get_settings
from src.domain.ai.errors import AiError
from src.domain.ai.service import AiService
from src.infrastructure.ai.media_bridge import SqlMediaBridge
from src.infrastructure.ai.repository import SqlAiRepository
from src.infrastructure.ai.resolver import ProviderResolver
from src.middleware.auth import (
    AuthContext,
    OptionalUserDep,
    require_permission,
    require_user,
)
from src.middleware.ratelimit import rate_limit

router = APIRouter(prefix="/v1/ai", tags=["ai"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


# --- DI helpers ------------------------------------------------------------


def _build_service(db: AsyncSession, *, tenant_id: UUID, attach_media: bool = True) -> AiService:
    settings = get_settings()
    resolver = ProviderResolver(db, use_mocks=settings.ai_use_mock_providers)
    media = SqlMediaBridge(db) if attach_media else None
    return AiService(
        repository=SqlAiRepository(db),
        resolver=resolver,
        media=media,
        tenant_id=tenant_id,
    )


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
    conversation_id: UUID | None = None


class ConversationSessionOut(BaseModel):
    id: UUID
    title: str | None
    context_kind: str
    language_tag: str
    message_count: int
    last_message_at: str | None
    created_at: str


class ConversationListOut(BaseModel):
    items: list[ConversationSessionOut]
    limit: int
    offset: int


class ConversationMessageOut(BaseModel):
    id: UUID
    role: str
    content_text: str
    model_slug: str | None
    created_at: str


class ConversationMessagesOut(BaseModel):
    items: list[ConversationMessageOut]
    limit: int
    offset: int


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


class AsrOut(BaseModel):
    text: str
    detected_language: str
    confidence: float
    command_intent: str | None
    command_params: dict[str, Any]
    stub: bool = False


class SearchFilters(BaseModel):
    kind_slug: str | None = None
    country_code: str | None = None


class SearchIn(BaseModel):
    query: str = Field(min_length=1, max_length=512)
    language: str = "en"
    kind: Literal["heritage_text"] = "heritage_text"
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
    name: dict[str, Any]
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
    conditions: dict[str, Any]


class ChainOut(BaseModel):
    slug: str
    task_type: str
    name: dict[str, Any]
    is_active: bool
    steps: list[ChainStepOut]


# --- Routes ---------------------------------------------------------------


@router.post(
    "/recognize",
    response_model=RecognizeOut,
    dependencies=[Depends(rate_limit("10/minute", per="user", scope="ai:recognize"))],
)
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


@router.post(
    "/chat",
    response_model=ChatOut,
    dependencies=[Depends(rate_limit("30/minute", per="user", scope="ai:chat"))],
)
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

    # ---- Conversation persistence ----------------------------------------
    region = ctx.residency_region.value
    conv_id: UUID | None = payload.conversation_id

    if conv_id is not None:
        # Verify the session belongs to this user before updating it.
        owner_row = await db.execute(
            text(
                """
                SELECT id FROM conversation_sessions
                WHERE id = :sid
                  AND user_id = :uid
                  AND residency_region = :region
                  AND is_active = true
                """
            ),
            {"sid": str(conv_id), "uid": ctx.user_id, "region": region},
        )
        if owner_row.fetchone() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "conversation.not_found", "message": "Conversation not found"},
            )
        await db.execute(
            text(
                """
                UPDATE conversation_sessions
                SET message_count = message_count + 2,
                    last_message_at = now(),
                    updated_at = now()
                WHERE id = :sid AND residency_region = :region
                """
            ),
            {"sid": str(conv_id), "region": region},
        )
    else:
        # Create a new session and capture the generated id.
        new_id = await db.scalar(
            text(
                """
                INSERT INTO conversation_sessions
                    (user_id, residency_region, tenant_id, language_tag,
                     message_count, last_message_at)
                VALUES
                    (:uid, :region, :tenant, :lang, 2, now())
                RETURNING id
                """
            ),
            {
                "uid": ctx.user_id,
                "region": region,
                "tenant": str(ctx.tenant_id),
                "lang": payload.language or "en",
            },
        )
        conv_id = new_id

    # Persist user turn.
    await db.execute(
        text(
            """
            INSERT INTO conversation_messages
                (session_id, residency_region, role, content_text, input_tokens)
            VALUES
                (:sid, :region, 'user', :content, :tokens)
            """
        ),
        {
            "sid": str(conv_id),
            "region": region,
            "content": payload.prompt,
            "tokens": resp.input_tokens,
        },
    )
    # Persist assistant turn.
    await db.execute(
        text(
            """
            INSERT INTO conversation_messages
                (session_id, residency_region, role, content_text,
                 output_tokens, model_slug)
            VALUES
                (:sid, :region, 'assistant', :content, :tokens, :model)
            """
        ),
        {
            "sid": str(conv_id),
            "region": region,
            "content": resp.text,
            "tokens": resp.output_tokens,
            "model": resp.model_slug,
        },
    )
    # ---- end persistence ------------------------------------------------

    await db.commit()
    return ChatOut(
        text=resp.text,
        input_tokens=resp.input_tokens,
        output_tokens=resp.output_tokens,
        model_slug=resp.model_slug,
        conversation_id=conv_id,
    )


@router.post(
    "/translate",
    response_model=TranslateOut,
    dependencies=[Depends(rate_limit("60/minute", per="user", scope="ai:translate"))],
    responses={
        422: {"description": "source_lang must differ from target_lang, or unsupported pair"},
    },
)
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


@router.post(
    "/tts",
    response_model=TtsOut,
    dependencies=[Depends(rate_limit("10/minute", per="user", scope="ai:tts"))],
)
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


@router.post(
    "/asr",
    response_model=AsrOut,
    dependencies=[Depends(rate_limit("10/minute", per="user", scope="ai:asr"))],
)
async def transcribe_audio(
    ctx: Annotated[AuthContext, Depends(require_user)],
    db: SessionDep,
    media_asset_id: Annotated[UUID, Form(description="UUID of an uploaded audio asset")],
    language: Annotated[
        str | None,
        Form(min_length=2, max_length=10, description="BCP-47 language hint, e.g. uz, en, ru"),
    ] = None,
) -> AsrOut:
    """Transcribe audio to text (voice command input). SILK-0066.

    Upload audio via ``POST /v1/media/uploads`` first, then pass the returned
    asset UUID here.  Returns the transcription plus a detected command intent
    so the mobile client can act hands-free (EXPLAIN_PLACE, NEXT_STOP, …).

    When ``SILKLENS_OPENAI_API_KEY`` is absent a stub response is returned so
    the endpoint stays functional in dev/test without real credentials.
    """
    settings = get_settings()
    openai_key: str = settings.openai_api_key.get_secret_value() if settings.openai_api_key else ""
    if not openai_key:
        return AsrOut(
            text="",
            detected_language=language.split("-")[0].lower() if language else "en",
            confidence=0.0,
            command_intent=None,
            command_params={},
            stub=True,
        )

    from src.infrastructure.ai.openai_asr_provider import AsrResult, OpenAiAsrProvider

    # Fetch audio bytes from MinIO via the existing SqlMediaBridge pattern.
    media = SqlMediaBridge(db)
    try:
        audio_bytes, _mime = await media.get_bytes(media_asset_id)
    except AiError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "media.not_found", "message": str(exc)},
        ) from exc

    provider = OpenAiAsrProvider(
        api_key=openai_key,
        model=settings.openai_asr_model,
    )
    try:
        result: AsrResult = await provider.transcribe(audio_bytes, language=language)
    except AiError as exc:
        _raise_ai(exc)

    # Persist generation row for cost tracking (output_tokens ≈ word count).
    await db.execute(
        text(
            """
            INSERT INTO ai_generations
                (user_id, residency_region, task_type, model_slug,
                 input_tokens, output_tokens)
            VALUES
                (:uid, :region, 'asr', :model, 0, :out_tokens)
            """
        ),
        {
            "uid": ctx.user_id,
            "region": ctx.residency_region.value,
            "model": provider.model_slug,
            "out_tokens": len(result.text.split()),
        },
    )
    await db.commit()

    return AsrOut(
        text=result.text,
        detected_language=result.detected_language,
        confidence=result.confidence,
        command_intent=result.command_intent,
        command_params=result.command_params,
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


# --- Conversation history --------------------------------------------------


@router.get(
    "/conversations",
    response_model=ConversationListOut,
    dependencies=[Depends(rate_limit("60/minute", per="user", scope="ai:chat"))],
)
async def list_conversations(
    ctx: Annotated[AuthContext, Depends(require_user)],
    db: SessionDep,
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0, le=10_000_000),
) -> ConversationListOut:
    """List the authenticated user's active conversation sessions, newest first."""
    rows = await db.execute(
        text(
            """
            SELECT id, title, context_kind, language_tag, message_count,
                   last_message_at, created_at
            FROM conversation_sessions
            WHERE user_id = :uid
              AND residency_region = :region
              AND is_active = true
            ORDER BY last_message_at DESC NULLS LAST, created_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        {
            "uid": ctx.user_id,
            "region": ctx.residency_region.value,
            "limit": limit,
            "offset": offset,
        },
    )
    items = [
        ConversationSessionOut(
            id=r._mapping["id"],
            title=r._mapping["title"],
            context_kind=r._mapping["context_kind"],
            language_tag=r._mapping["language_tag"],
            message_count=r._mapping["message_count"],
            last_message_at=(
                r._mapping["last_message_at"].isoformat() if r._mapping["last_message_at"] else None
            ),
            created_at=r._mapping["created_at"].isoformat(),
        )
        for r in rows.fetchall()
    ]
    return ConversationListOut(items=items, limit=limit, offset=offset)


@router.get(
    "/conversations/{session_id}/messages",
    response_model=ConversationMessagesOut,
    dependencies=[Depends(rate_limit("60/minute", per="user", scope="ai:chat"))],
)
async def get_conversation_messages(
    session_id: UUID,
    ctx: Annotated[AuthContext, Depends(require_user)],
    db: SessionDep,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, le=10_000_000),
) -> ConversationMessagesOut:
    """Return ordered messages for a conversation session the caller owns."""
    owner_row = await db.execute(
        text(
            """
            SELECT id FROM conversation_sessions
            WHERE id = :sid
              AND user_id = :uid
              AND residency_region = :region
            """
        ),
        {
            "sid": str(session_id),
            "uid": ctx.user_id,
            "region": ctx.residency_region.value,
        },
    )
    if owner_row.fetchone() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "conversation.not_found", "message": "Conversation not found"},
        )

    rows = await db.execute(
        text(
            """
            SELECT id, role, content_text, model_slug, created_at
            FROM conversation_messages
            WHERE session_id = :sid
            ORDER BY created_at ASC
            LIMIT :limit OFFSET :offset
            """
        ),
        {"sid": str(session_id), "limit": limit, "offset": offset},
    )
    items = [
        ConversationMessageOut(
            id=r._mapping["id"],
            role=r._mapping["role"],
            content_text=r._mapping["content_text"],
            model_slug=r._mapping["model_slug"],
            created_at=r._mapping["created_at"].isoformat(),
        )
        for r in rows.fetchall()
    ]
    return ConversationMessagesOut(items=items, limit=limit, offset=offset)


@router.delete(
    "/conversations/{session_id}",
    dependencies=[Depends(rate_limit("30/minute", per="user", scope="ai:chat"))],
)
async def delete_conversation(
    session_id: UUID,
    ctx: Annotated[AuthContext, Depends(require_user)],
    db: SessionDep,
) -> dict[str, Any]:
    """Soft-delete a conversation session (sets is_active = false)."""
    result = await db.execute(
        text(
            """
            UPDATE conversation_sessions
            SET is_active = false, updated_at = now()
            WHERE id = :sid
              AND user_id = :uid
              AND residency_region = :region
            RETURNING id
            """
        ),
        {
            "sid": str(session_id),
            "uid": ctx.user_id,
            "region": ctx.residency_region.value,
        },
    )
    await db.commit()
    if result.fetchone() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "conversation.not_found", "message": "Conversation not found"},
        )
    return {"deleted": True, "session_id": str(session_id)}


# --- Admin -----------------------------------------------------------------


@router.get("/public-models")
async def list_public_models(db: SessionDep) -> list[dict[str, Any]]:
    """Public list of enabled AI models — no auth required. Used by mobile app.

    Note: the path lives under ``/public-models`` (not ``/models/public``)
    so it does not collide with the admin-only ``PATCH /models/{slug}``
    path; OpenAPI sees those as the same path and schemathesis flags PATCH
    on ``/models/public`` as a missing 405. Mobile clients have been
    updated to follow this URL.
    """
    # provider slug lives on ai_providers; join via provider_id.
    rows = await db.execute(
        text("""
            SELECT m.slug, m.name, m.task_type, p.slug AS provider_slug
            FROM ai_models m
            JOIN ai_providers p ON p.id = m.provider_id
            WHERE m.is_enabled = true
            ORDER BY m.sort_order, m.slug
        """)
    )
    return [
        {
            "slug": r.slug,
            "name": r.name,
            "task_type": r.task_type,
            "provider_slug": r.provider_slug,
        }
        for r in rows.fetchall()
    ]


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
    """List every chain + its ordered steps in a single round-trip (HIGH-6).

    Previously this iterated over chains and issued one ``SELECT … steps``
    per chain (classic 1+N). The repository now does a single LEFT JOIN +
    ``json_agg`` so the response time is constant regardless of N.
    """
    chains = await SqlAiRepository(db).list_fallback_chains()
    return [
        ChainOut(
            slug=c["slug"],
            task_type=c["task_type"],
            name=c["name"],
            is_active=c["is_active"],
            steps=[
                ChainStepOut(
                    step_order=s["step_order"],
                    model_slug=s["model_slug"],
                    max_latency_ms=s["max_latency_ms"],
                    conditions=s["conditions"],
                )
                for s in c["steps"]
            ],
        )
        for c in chains
    ]


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
