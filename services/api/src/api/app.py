"""FastAPI app factory.

Routers per bounded context are added incrementally as each FAZA lands. At
FAZA 1 only the operational ``/health`` and ``/version`` endpoints exist so
the deployment / Docker Compose stack is verifiable end-to-end.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src import __version__
from src.api.routers import (
    admin,
    ai,
    ai_utilities,
    ar,
    auth,
    billing,
    carbon,
    compliance,
    coupons,
    crowd,
    cultural_tips,
    emergency,
    enterprise_sla,
    expenses,
    finetuning,
    food_guide,
    fundraising,
    gamification,
    government,
    health,
    heritage,
    i18n,
    kids_mode,
    listings,
    media,
    memory_book,
    mfa,
    mood_travel,
    notifications,
    offline,
    onboarding,
    partnerships,
    phase3_stubs,
    photo_guide,
    public_meta,
    reseller,
    review_analysis,
    reviews,
    search,
    social,
    storyteller,
    tickets,
    trips,
    virtual_tours,
    weather,
)
from src.core.database import dispose_engine, get_engine
from src.core.logging import configure_logging, get_logger
from src.core.metrics import register_db_pool_metrics
from src.core.observability import init_sentry, init_tracing
from src.core.settings import get_settings
from src.infrastructure.media.minio_client import get_minio_client
from src.middleware.auth import BearerContextMiddleware
from src.middleware.ratelimit import get_rate_limiter, reset_rate_limiter
from src.middleware.trace import TraceContextMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging()
    log = get_logger("silklens.lifespan")
    settings = get_settings()
    log.info("api.startup", version=__version__)

    # Observability bootstrap. Both initializers no-op when DSN/endpoint is
    # unreachable so dev/test stays quiet.
    init_sentry()
    init_tracing(app)

    # Bind SQLAlchemy pool metrics; non-fatal if engine init fails (e.g.
    # offline test runs that never touch the DB).
    try:
        register_db_pool_metrics(get_engine())
    except Exception as exc:
        log.debug("metrics.db_pool_register_failed", error=str(exc))

    # Bootstrap the primary media bucket; non-fatal so tests/dev keep working
    # when the MinIO container is offline or a fake client is injected.
    try:
        get_minio_client().ensure_bucket(settings.minio_bucket_media)
    except Exception as exc:
        log.warning("media.minio.bucket_bootstrap_failed", error=str(exc))

    # Eagerly materialize the rate limiter so the Redis connection failure
    # (if any) shows up at startup rather than on the first 429 path.
    try:
        get_rate_limiter()
    except Exception as exc:
        log.warning("ratelimit.bootstrap_failed", error=str(exc))

    try:
        yield
    finally:
        await dispose_engine()
        # Drop the limiter singleton so a fresh app (e.g. test reload)
        # rebuilds it from current settings.
        reset_rate_limiter()
        log.info("api.shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="SilkLens API",
        version=__version__,
        docs_url="/docs" if settings.env != "prod" else None,
        redoc_url="/redoc" if settings.env != "prod" else None,
        openapi_url="/openapi.json" if settings.env != "prod" else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Bearer-token decoding runs once per request; binds AuthContext to
    # request.state.auth (or None). Public endpoints simply ignore it.
    app.add_middleware(BearerContextMiddleware)
    # Rate-limit middleware sits after the bearer middleware so the global
    # default uses the per-user key when a token is present. SEC-005.
    get_rate_limiter().install(app)
    # Trace ID binding runs outermost so every log line — including auth
    # decode failures — carries trace_id, method, route in structlog context.
    app.add_middleware(TraceContextMiddleware)
    # Sanitize obviously-malformed inputs (null bytes in JSON, query ints over
    # int64) before they reach handlers and crash the asyncpg encoder. Added
    # outermost so the 422 is emitted with proper trace_id propagation.
    from src.middleware.request_sanitize import RequestSanitizeMiddleware

    app.add_middleware(RequestSanitizeMiddleware)

    # Prometheus instrumentation. The instrumentator exposes ``/metrics`` and
    # adds RED-method metrics; our custom counters live in src.core.metrics
    # and share the default registry so they're emitted on the same endpoint.
    if settings.metrics_enabled:
        try:
            from prometheus_fastapi_instrumentator import Instrumentator

            Instrumentator(
                should_group_status_codes=False,
                should_ignore_untemplated=True,
            ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
        except Exception:
            # Instrumentator is best-effort — never block app startup on it.
            get_logger("silklens.observability").debug("metrics.instrumentator_failed")

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(mfa.router)
    app.include_router(heritage.router)
    app.include_router(ai.router)
    app.include_router(media.router)
    app.include_router(social.router)
    app.include_router(reviews.router)
    app.include_router(review_analysis.router)
    app.include_router(ar.router)
    app.include_router(gamification.router)
    app.include_router(billing.router)
    app.include_router(coupons.router)
    app.include_router(notifications.router)
    app.include_router(admin.router)
    app.include_router(public_meta.router)
    app.include_router(compliance.router)
    app.include_router(search.router)
    app.include_router(reseller.router)
    app.include_router(partnerships.router)
    app.include_router(virtual_tours.router)
    app.include_router(offline.router)
    app.include_router(finetuning.router)
    app.include_router(enterprise_sla.router)
    app.include_router(fundraising.router)
    app.include_router(emergency.router)
    app.include_router(onboarding.router)
    app.include_router(weather.router)
    app.include_router(cultural_tips.router)
    app.include_router(expenses.router)
    app.include_router(storyteller.router)
    app.include_router(crowd.router)
    app.include_router(listings.router)
    app.include_router(tickets.router)
    app.include_router(trips.router)
    app.include_router(mood_travel.router)
    app.include_router(ai_utilities.router)
    app.include_router(i18n.router)
    app.include_router(kids_mode.router)
    app.include_router(photo_guide.router)
    app.include_router(food_guide.router)
    app.include_router(carbon.router)
    app.include_router(government.router)
    app.include_router(memory_book.router)
    app.include_router(phase3_stubs.router)

    # Inject auth-related response codes (401/403/422) into the OpenAPI spec
    # for every route that depends on require_user / require_permission /
    # request bodies. FastAPI's auto-OpenAPI omits codes raised by deps,
    # which schemathesis correctly flags as "undocumented status code".
    _inject_auth_responses(app)

    # StrictQueryParamsMiddleware needs the populated route table, so wire
    # it AFTER include_router calls. It still sits outside the request
    # processing stack because middleware-add prepends to the chain.
    from src.middleware.request_sanitize import StrictQueryParamsMiddleware

    app.add_middleware(StrictQueryParamsMiddleware, fastapi_app=app)

    return app


def _inject_auth_responses(app: FastAPI) -> None:
    """Walk routes and add 401/403/422 to ``responses`` where deps raise them.

    Detection is structural — looks for the wrapped ``require_user`` and
    ``require_permission`` callables (or their dependency closures) in each
    route's dependant tree. Avoids touching routes that already declared
    a code explicitly (the route author wins).
    """
    from fastapi.routing import APIRoute

    # SilkLens speaks several error shapes simultaneously, all under ``detail``:
    #   * envelope: ``{code: str, message: str}`` (most explicit raises)
    #   * raw string: FastAPI's default for ``HTTPException(detail="...")``
    #     (e.g., the body-parse 400 emits ``"There was an error parsing the body"``)
    #   * validation list: ``[{loc, msg, type}]`` from request validation
    # OpenAPI consumers (and schemathesis) need a schema that admits all three.
    error_envelope_schema = {
        "type": "object",
        "required": ["detail"],
        "properties": {
            "detail": {
                "anyOf": [
                    {
                        "type": "object",
                        "required": ["code", "message"],
                        "properties": {
                            "code": {"type": "string"},
                            "message": {"type": "string"},
                        },
                        "additionalProperties": True,
                    },
                    {"type": "string"},
                    {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": True,
                        },
                    },
                ]
            }
        },
    }

    error_envelope_content = {"application/json": {"schema": error_envelope_schema}}

    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        deps_permission = _route_requires_permission(route)
        is_write = any(m in route.methods for m in ("POST", "PUT", "PATCH", "DELETE"))
        accepts_payload = is_write or _route_has_query_params(route)

        # ``route.responses`` is the dict FastAPI serialises into OpenAPI.
        # Honour explicit declarations from the @router.<method>(responses=...)
        # decorator — only add codes that aren't there yet.
        # Auth endpoints that mint tokens still return 401 on bad credentials,
        # public GETs can return 404 when referenced data is missing — so
        # document 401 / 404 broadly rather than gating on dependency tree.
        if 401 not in route.responses:
            route.responses[401] = {
                "description": "Authentication required or credentials invalid.",
                "content": error_envelope_content,
            }
        if deps_permission and 403 not in route.responses:
            route.responses[403] = {
                "description": "Caller lacks the required permission.",
                "content": error_envelope_content,
            }
        # 400 covers body-parse failures (malformed JSON) and explicit
        # bad-request raises (e.g. unknown enum value). FastAPI's body
        # parser surfaces this on any route that accepts a payload.
        if accepts_payload and 400 not in route.responses:
            route.responses[400] = {
                "description": "Malformed request body or unparseable input.",
                "content": error_envelope_content,
            }
        # Any route may surface 404 when its underlying lookup misses — even
        # public GETs without path params (e.g. /branding) resolve a row by
        # ``current tenant`` and 404 if the tenant has no record yet.
        if 404 not in route.responses:
            route.responses[404] = {
                "description": "Referenced resource not found.",
                "content": error_envelope_content,
            }
        # 409 covers idempotency / unique-constraint conflicts on writes.
        if is_write and 409 not in route.responses:
            route.responses[409] = {
                "description": "Conflict with current resource state.",
                "content": error_envelope_content,
            }
        # SEC-005: /auth/login returns 423 after credential-stuffing lockout.
        # The threshold and Retry-After header live in the route handler.
        if route.path == "/v1/auth/login" and 423 not in route.responses:
            route.responses[423] = {
                "description": "Account locked after repeated failures (SEC-005).",
                "content": error_envelope_content,
            }

    # Override the cached OpenAPI factory so the HTTPValidationError schema
    # accepts both shapes that the codebase emits:
    #   * canonical FastAPI ValidationError -- ``detail: [{loc, msg, type}]``
    #     (auto-generated for body validation failures + our middleware)
    #   * SilkLens envelope -- ``detail: {code, message}``
    #     (used throughout routers for business-rule HTTPException raises)
    # Without this, schemathesis flags every envelope-style 422 as
    # "Response violates schema".
    original_openapi = app.openapi

    def _openapi_with_unified_422() -> dict[str, object]:
        schema = original_openapi()
        components = schema.setdefault("components", {})
        schemas = components.setdefault("schemas", {})
        schemas["HTTPValidationError"] = {
            "title": "HTTPValidationError",
            "type": "object",
            "properties": {
                "detail": {
                    "anyOf": [
                        {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/ValidationError"},
                        },
                        {
                            "type": "object",
                            "required": ["code", "message"],
                            "properties": {
                                "code": {"type": "string"},
                                "message": {"type": "string"},
                            },
                            "additionalProperties": True,
                        },
                        {"type": "string"},
                    ]
                }
            },
        }
        return schema

    app.openapi = _openapi_with_unified_422  # type: ignore[method-assign]
    # Drop the cached spec so the next /openapi.json call regenerates with
    # the new HTTPValidationError union.
    app.openapi_schema = None


def _route_requires_permission(route: object) -> bool:
    """True if any dependant call name contains ``require_permission``.

    ``require_permission`` is a factory that returns a closure, so the
    closure name (not the factory) is what ends up on the dependant. We
    detect by ``__qualname__`` substring to keep this resilient to
    refactors.
    """
    dependant = getattr(route, "dependant", None)
    if dependant is None:
        return False
    return _dependant_matches_qualname(dependant, "require_permission")


def _route_has_query_params(route: object) -> bool:
    dependant = getattr(route, "dependant", None)
    if dependant is None:
        return False
    return bool(getattr(dependant, "query_params", None))


def _dependant_matches_qualname(dependant: object, fragment: str) -> bool:
    call = getattr(dependant, "call", None)
    if call is not None and fragment in getattr(call, "__qualname__", ""):
        return True
    for sub in getattr(dependant, "dependencies", ()) or ():
        if _dependant_matches_qualname(sub, fragment):
            return True
    return False
