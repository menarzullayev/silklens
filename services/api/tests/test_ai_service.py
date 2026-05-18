"""AI service + router integration tests.

All provider calls run through the deterministic ``MockProvider`` family so we
never touch the real Anthropic / LLaVA / Kokoro stack. The resolver is
short-circuited via ``ai_use_mock_providers = True`` at the settings layer,
which means the same code path that production uses (DB lookup → resolver →
provider) is exercised end-to-end, just with mocks at the leaf.

Tests cover: recognize / chat / translate (incl. TM reuse) / tts / vector
search ordering / admin model + chain endpoints / quota gate / validation.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.settings import get_settings
from src.domain.ai.entities import (
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
from src.domain.ai.service import AiService
from src.infrastructure.ai.media_bridge import InMemoryMediaBridge
from src.infrastructure.ai.mock_providers import (
    MockEmbeddingProvider,
    MockLlmProvider,
    MockTranslationProvider,
    MockTtsProvider,
    MockVisionProvider,
)

pytestmark = pytest.mark.integration


# --- Helpers ---------------------------------------------------------------


def _unique_email() -> str:
    return f"ai-{uuid.uuid4().hex[:10]}@silklens-test.com"


async def _register(http: AsyncClient) -> dict[str, Any]:
    response = await http.post(
        "/v1/auth/register",
        json={"email": _unique_email(), "password": "AiTestPassword12345"},
    )
    assert response.status_code == 201, response.text
    return response.json()


class _MemoryResolver:
    """Always returns one mock provider per task."""

    def __init__(self) -> None:
        self._vision = MockVisionProvider()
        self._tts = MockTtsProvider()
        self._llm = MockLlmProvider()
        self._translation = MockTranslationProvider()
        self._embedding = MockEmbeddingProvider()

    async def resolve_vision(self):
        return [self._vision]

    async def resolve_tts(self):
        return [self._tts]

    async def resolve_llm(self):
        return [self._llm]

    async def resolve_translation(self):
        return [self._translation]

    async def resolve_embedding(self):
        return [self._embedding]


def _default_tenant() -> uuid.UUID:
    return uuid.UUID(get_settings().default_tenant_id)


def _make_service(db: AsyncSession, *, media: InMemoryMediaBridge | None = None) -> AiService:
    return AiService(
        session=db,
        resolver=_MemoryResolver(),
        media=media or InMemoryMediaBridge(),
        tenant_id=_default_tenant(),
    )


# --- Mock provider unit checks (pure domain) -------------------------------


@pytest.mark.asyncio
async def test_mock_vision_returns_deterministic_label() -> None:
    provider = MockVisionProvider()
    resp = await provider.call(VisionRequest(image_bytes=b"hello-image", mime_type="image/jpeg"))
    assert isinstance(resp, VisionResponse)
    assert resp.confidence == 0.87
    assert len(resp.candidates) == 3
    assert isinstance(resp.candidates[0], VisionCandidate)
    # Stable across calls
    resp2 = await provider.call(VisionRequest(image_bytes=b"hello-image", mime_type="image/jpeg"))
    assert resp.label == resp2.label


@pytest.mark.asyncio
async def test_mock_translation_round_trip_marks_target_lang() -> None:
    provider = MockTranslationProvider()
    resp: TranslationResponse = await provider.call(
        TranslationRequest(text="Hello", source_lang="en", target_lang="uz")
    )
    assert resp.target_lang == "uz"
    assert resp.text.startswith("[uz]")
    assert resp.confidence > 0


@pytest.mark.asyncio
async def test_mock_embedding_returns_1024_dim_deterministic_vector() -> None:
    provider = MockEmbeddingProvider()
    a = await provider.call(EmbeddingRequest(text="madrasa"))
    b = await provider.call(EmbeddingRequest(text="madrasa"))
    c = await provider.call(EmbeddingRequest(text="something else"))
    assert isinstance(a, EmbeddingResponse)
    assert a.dimensions == 1024
    assert len(a.vector) == 1024
    assert a.vector == b.vector
    assert a.vector != c.vector


@pytest.mark.asyncio
async def test_mock_llm_and_tts_basic_shape() -> None:
    llm: LlmResponse = await MockLlmProvider().call(LlmRequest(prompt="What is Registan?"))
    assert llm.text.startswith("[mock-llm")
    assert llm.input_tokens > 0
    tts: TtsResponse = await MockTtsProvider().call(
        TtsRequest(text="Bukhara is a city", language="en")
    )
    assert tts.audio_bytes
    assert tts.duration_ms > 0


# --- Service-level integration with the DB --------------------------------


@pytest.mark.asyncio
async def test_recognize_image_writes_generation_and_event(
    db_session: AsyncSession,
) -> None:
    media = InMemoryMediaBridge()
    asset_id = uuid.uuid4()
    media.put(asset_id, b"some-image-bytes", "image/jpeg")
    service = _make_service(db_session, media=media)

    resp = await service.recognize_image(asset_id=asset_id, language="en", user_id=None)
    await db_session.commit()

    assert resp.label
    assert resp.model_slug == "llava-1.6-34b"

    event = (
        await db_session.execute(
            text(
                """
                SELECT event_name FROM event_outbox
                WHERE event_name = 'vision.recognition.v1'
                  AND aggregate_id = :aid
                ORDER BY created_at DESC LIMIT 1
                """
            ),
            {"aid": asset_id},
        )
    ).scalar_one_or_none()
    assert event == "vision.recognition.v1"


@pytest.mark.asyncio
async def test_translate_writes_tm_and_reuses_on_second_call(
    db_session: AsyncSession,
) -> None:
    service = _make_service(db_session)
    text_input = f"unique source text {uuid.uuid4().hex}"

    first = await service.translate(text_input=text_input, source_lang="en", target_lang="uz")
    await db_session.commit()
    assert first.text.startswith("[uz]")

    # TM row should now exist
    tm_count = (
        await db_session.execute(
            text(
                """
                SELECT count(*) FROM ai_translation_memory
                WHERE source_lang='en' AND target_lang='uz'
                  AND source_text = :s
                """
            ),
            {"s": text_input},
        )
    ).scalar_one()
    assert int(tm_count) == 1

    # Second call should hit TM (deterministic, but explicit prove via hit_count)
    second = await service.translate(text_input=text_input, source_lang="en", target_lang="uz")
    await db_session.commit()
    assert second.text == first.text

    hit_count = (
        await db_session.execute(
            text(
                """
                SELECT hit_count FROM ai_translation_memory
                WHERE source_lang='en' AND target_lang='uz'
                  AND source_text = :s
                """
            ),
            {"s": text_input},
        )
    ).scalar_one()
    assert int(hit_count) >= 1


@pytest.mark.asyncio
async def test_chat_returns_text_and_writes_token_usage(
    db_session: AsyncSession,
) -> None:
    # Pick any registered user — chat requires a user_id for quota tracking.
    user_id = uuid.uuid4()
    # Force a user_roles-style user existence isn't required; quotas just read
    # ai_token_usage by user_id. We can pass any UUID — the quota query simply
    # finds zero rows the first time around.
    service = _make_service(db_session)

    resp = await service.chat(
        prompt="Tell me about Samarkand",
        system="You are a heritage guide.",
        user_id=user_id,
    )
    await db_session.commit()
    assert resp.text.startswith("[mock-llm")
    assert resp.model_slug == "claude-opus-4-7"

    usage = (
        await db_session.execute(
            text(
                """
                SELECT request_count FROM ai_token_usage
                WHERE user_id = :uid
                ORDER BY day DESC LIMIT 1
                """
            ),
            {"uid": user_id},
        )
    ).scalar_one_or_none()
    assert usage is not None and int(usage) >= 1


@pytest.mark.asyncio
async def test_chat_quota_blocks_after_free_limit(
    db_session: AsyncSession,
) -> None:
    """Pre-seed ai_token_usage at the cap and expect 429-equivalent error."""
    from datetime import date

    user_id = uuid.uuid4()
    # Pick the LLM model id for chat
    model_id = (
        await db_session.execute(text("SELECT id FROM ai_models WHERE slug='claude-opus-4-7'"))
    ).scalar_one()
    await db_session.execute(
        text(
            """
            INSERT INTO ai_token_usage (
                user_id, model_id, day, input_tokens, output_tokens, cost, request_count
            )
            VALUES (:uid, :mid, :day, 0, 0, 0, :req)
            ON CONFLICT (user_id, model_id, day) DO UPDATE
            SET request_count = EXCLUDED.request_count
            """
        ),
        {
            "uid": user_id,
            "mid": model_id,
            "day": date.today(),
            "req": AiService.FREE_CHAT_DAILY + 1,
        },
    )
    await db_session.commit()

    service = _make_service(db_session)
    from src.domain.ai.errors import AiQuotaExceeded

    with pytest.raises(AiQuotaExceeded):
        await service.chat(prompt="hi", system=None, user_id=user_id)


@pytest.mark.asyncio
async def test_generate_tts_persists_asset_and_emits_event(
    db_session: AsyncSession,
) -> None:
    media = InMemoryMediaBridge()
    service = _make_service(db_session, media=media)

    asset_id, signed_url, resp = await service.generate_tts(
        text_input="Welcome to Bukhara",
        language="en",
        voice_id=None,
        user_id=None,
    )
    await db_session.commit()

    assert signed_url.startswith("memory://")
    assert resp.duration_ms > 0

    event = (
        await db_session.execute(
            text(
                """
                SELECT event_name FROM event_outbox
                WHERE event_name = 'tts.generated.v1'
                  AND aggregate_id = :aid
                """
            ),
            {"aid": asset_id},
        )
    ).scalar_one_or_none()
    assert event == "tts.generated.v1"


@pytest.mark.asyncio
async def test_vector_search_returns_seeded_heritage_in_order(
    db_session: AsyncSession,
) -> None:
    # Seed a heritage object + its e5_1024 embedding using the same mock
    # embedding function so the query vector matches exactly (distance 0).
    provider = MockEmbeddingProvider()
    pub_id = f"vs-{uuid.uuid4().hex[:8]}"

    query_text = f"unique heritage object name {uuid.uuid4().hex}"
    emb = await provider.call(EmbeddingRequest(text=query_text))
    vec_literal = "[" + ",".join(f"{v:.6f}" for v in emb.vector) + "]"

    heritage_id = (
        await db_session.execute(
            text(
                """
                INSERT INTO heritage_objects (
                    tenant_id, pub_id, kind_slug,
                    name, status, created_by, updated_by
                )
                VALUES (
                    :tenant, :pub_id, 'madrasa',
                    CAST(:name AS jsonb), 'published',
                    '00000000-0000-0000-0000-000000000002'::uuid,
                    '00000000-0000-0000-0000-000000000002'::uuid
                )
                RETURNING id
                """
            ),
            {
                "tenant": _default_tenant(),
                "pub_id": pub_id,
                "name": f'{{"en":"{query_text}"}}',
            },
        )
    ).scalar_one()

    mv_id = (
        await db_session.execute(
            text(
                """
                SELECT mv.id FROM ai_model_versions mv
                JOIN ai_models m ON m.id = mv.model_id
                WHERE m.slug = 'multilingual-e5-large' AND mv.is_current
                """
            )
        )
    ).scalar_one()

    await db_session.execute(
        text(
            """
            INSERT INTO embeddings_heritage_text_e5_1024 (
                heritage_id, model_version_id, language_tag,
                embedding, source_text_hash, chunk_index
            )
            VALUES (
                :hid, :mv, 'en',
                CAST(:vec AS vector),
                decode(repeat('00',32),'hex'),
                0
            )
            """
        ),
        {"hid": heritage_id, "mv": mv_id, "vec": vec_literal},
    )
    await db_session.commit()

    service = _make_service(db_session)
    hits = await service.vector_search(query_text=query_text, language="en", limit=5)
    await db_session.commit()
    assert hits, "expected at least one vector hit"
    top = hits[0]
    assert top.heritage_pub_id == pub_id
    assert top.score >= 0.99  # exact match → distance ~0


@pytest.mark.asyncio
async def test_translate_rejects_same_source_and_target(
    db_session: AsyncSession,
) -> None:
    service = _make_service(db_session)
    from src.domain.ai.errors import AiValidationError

    with pytest.raises(AiValidationError):
        await service.translate(text_input="hi", source_lang="en", target_lang="en")


# --- HTTP-level (router) tests --------------------------------------------


@pytest.mark.asyncio
async def test_chat_requires_authentication(http: AsyncClient) -> None:
    resp = await http.post("/v1/ai/chat", json={"prompt": "hi"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_translate_public_endpoint(http: AsyncClient) -> None:
    resp = await http.post(
        "/v1/ai/translate",
        json={"text": "hello world", "source_lang": "en", "target_lang": "uz"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["target_lang"] == "uz"
    assert body["text"].startswith("[uz]")


@pytest.mark.asyncio
async def test_models_endpoint_requires_ai_configure_permission(
    http: AsyncClient,
) -> None:
    # Anonymous → 401
    resp = await http.get("/v1/ai/models")
    assert resp.status_code == 401

    # Plain user → 403
    auth = await _register(http)
    resp = await http.get(
        "/v1/ai/models",
        headers={"Authorization": f"Bearer {auth['tokens']['access_token']}"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "identity.permission_denied"


@pytest.mark.asyncio
async def test_models_endpoint_lists_seeded_registry(
    http: AsyncClient, db_session: AsyncSession
) -> None:
    auth = await _register(http)
    # Grant super_admin so the ai:configure check passes.
    await db_session.execute(
        text(
            """
            INSERT INTO user_roles (
                user_id, residency_region, role_id, scope_tenant_id, granted_by
            )
            SELECT u.id, u.residency_region, r.id, NULL,
                   '00000000-0000-0000-0000-000000000002'::uuid
            FROM users u, roles r
            WHERE u.pub_id = :pid AND r.slug = 'super_admin'
            """
        ),
        {"pid": auth["user"]["pub_id"]},
    )
    await db_session.commit()

    resp = await http.get(
        "/v1/ai/models",
        headers={"Authorization": f"Bearer {auth['tokens']['access_token']}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    slugs = {m["slug"] for m in body}
    assert "claude-opus-4-7" in slugs
    assert "multilingual-e5-large" in slugs


@pytest.mark.asyncio
async def test_fallback_chains_endpoint_lists_chains(
    http: AsyncClient, db_session: AsyncSession
) -> None:
    auth = await _register(http)
    await db_session.execute(
        text(
            """
            INSERT INTO user_roles (
                user_id, residency_region, role_id, scope_tenant_id, granted_by
            )
            SELECT u.id, u.residency_region, r.id, NULL,
                   '00000000-0000-0000-0000-000000000002'::uuid
            FROM users u, roles r
            WHERE u.pub_id = :pid AND r.slug = 'super_admin'
            """
        ),
        {"pid": auth["user"]["pub_id"]},
    )
    await db_session.commit()
    resp = await http.get(
        "/v1/ai/fallback-chains",
        headers={"Authorization": f"Bearer {auth['tokens']['access_token']}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    slugs = {c["slug"] for c in body}
    assert {"vision_default", "tts_default", "translation_default", "chat_default"} <= slugs


@pytest.mark.asyncio
async def test_patch_model_toggles_is_enabled(http: AsyncClient, db_session: AsyncSession) -> None:
    auth = await _register(http)
    await db_session.execute(
        text(
            """
            INSERT INTO user_roles (
                user_id, residency_region, role_id, scope_tenant_id, granted_by
            )
            SELECT u.id, u.residency_region, r.id, NULL,
                   '00000000-0000-0000-0000-000000000002'::uuid
            FROM users u, roles r
            WHERE u.pub_id = :pid AND r.slug = 'super_admin'
            """
        ),
        {"pid": auth["user"]["pub_id"]},
    )
    await db_session.commit()

    headers = {"Authorization": f"Bearer {auth['tokens']['access_token']}"}
    # Flip to disabled
    resp = await http.patch(
        "/v1/ai/models/gpt-4o-mini",
        json={"is_enabled": False},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_enabled"] is False

    # Restore
    resp = await http.patch(
        "/v1/ai/models/gpt-4o-mini",
        json={"is_enabled": True},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["is_enabled"] is True


@pytest.mark.asyncio
async def test_translate_via_http_writes_tm(http: AsyncClient, db_session: AsyncSession) -> None:
    sample = f"http-tm probe {uuid.uuid4().hex}"
    resp = await http.post(
        "/v1/ai/translate",
        json={"text": sample, "source_lang": "en", "target_lang": "ru"},
    )
    assert resp.status_code == 200, resp.text

    tm_count = (
        await db_session.execute(
            text(
                """
                SELECT count(*) FROM ai_translation_memory
                WHERE source_lang='en' AND target_lang='ru' AND source_text = :s
                """
            ),
            {"s": sample},
        )
    ).scalar_one()
    assert int(tm_count) == 1


@pytest.mark.asyncio
async def test_search_validation_rejects_empty_query(http: AsyncClient) -> None:
    resp = await http.post(
        "/v1/ai/search",
        json={"query": ""},
    )
    assert resp.status_code == 422  # pydantic min_length=1


@pytest.mark.asyncio
async def test_search_invalid_kind_returns_422(http: AsyncClient) -> None:
    resp = await http.post(
        "/v1/ai/search",
        json={"query": "Registan", "kind": "heritage_image"},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["detail"]["code"] == "ai.validation_failed"
