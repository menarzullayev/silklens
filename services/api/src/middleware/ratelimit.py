"""Rate-limit + brute-force middleware.

Fixes SEC-005. Wraps :class:`slowapi.Limiter` so the rest of the codebase
sees a single entry point.

Layers, top to bottom:

1. **Global default** — every request is bound to ``200/minute`` using a
   composite key (``user:<uuid>`` if the bearer middleware already decoded
   one, otherwise ``ip:<client.host>``). Enforced by
   :class:`slowapi.middleware.SlowAPIMiddleware` attached in
   :func:`src.api.app.create_app`.
2. **Per-route override** — sensitive endpoints (auth, AI inference, media
   upload) declare a tighter limit via :meth:`RateLimiter.dependency`.
   These dependencies share the same Redis-backed storage so a malicious
   client can't burn through 200/min just by spraying ``/login``.

Storage is Redis in every environment. Tests run a local Redis (port 6381
per the dev Docker stack); the ``SILKLENS_RATE_LIMIT_ENABLED`` flag lets
unit tests disable the limiter explicitly when they want to assert
non-rate-limit behaviour without mocking the storage.

On a 429 we return our standard envelope::

    {"detail": {"code": "rate.limited",
                "message": "rate limit exceeded: 5 per 1 minute"}}

with a ``Retry-After`` header (integer seconds) so well-behaved clients
back off.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Final
from uuid import UUID

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from limits import RateLimitItem, parse
from limits.storage import MemoryStorage, RedisStorage, storage_from_string
from limits.strategies import MovingWindowRateLimiter
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from src.core.logging import get_logger
from src.core.settings import get_settings

log = get_logger("silklens.ratelimit")

DEFAULT_LIMIT: Final[str] = "200/minute"


def _identity_key(request: Request) -> str:
    """Composite key: user-id when authenticated, else IP.

    The bearer middleware runs before any rate-limit dependency so
    ``request.state.auth`` is already populated for authenticated callers.
    For anonymous traffic we fall back to ``request.client.host`` (and
    finally to a sentinel string so the limiter never crashes on a
    headless test transport with no client peer).
    """
    auth = getattr(request.state, "auth", None)
    if auth is not None:
        user_id = getattr(auth, "user_id", None)
        if isinstance(user_id, UUID):
            return f"user:{user_id}"
    # X-Forwarded-For takes precedence so the API can sit behind a proxy.
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return f"ip:{fwd.split(',')[0].strip()}"
    if request.client and request.client.host:
        return f"ip:{request.client.host}"
    return "ip:unknown"


def _ip_key(request: Request) -> str:
    """Force per-IP keying regardless of bearer presence (used on login)."""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return f"ip:{fwd.split(',')[0].strip()}"
    if request.client and request.client.host:
        return f"ip:{request.client.host}"
    return "ip:unknown"


def _user_key(request: Request) -> str:
    """Force per-user keying. Caller MUST guard the route with ``require_user``
    so ``request.state.auth`` is populated; falls back to IP if the bearer is
    missing (defence-in-depth — the route would 401 anyway)."""
    auth = getattr(request.state, "auth", None)
    if auth is not None:
        user_id = getattr(auth, "user_id", None)
        if isinstance(user_id, UUID):
            return f"user:{user_id}"
    return _ip_key(request)


@dataclass(slots=True)
class _RouteLimit:
    item: RateLimitItem
    key_func: Callable[[Request], str]
    raw: str


class RateLimiter:
    """Facade over :class:`slowapi.Limiter` + a private async strategy.

    Two responsibilities:

    * Configure a single :class:`slowapi.Limiter` instance and attach its
      middleware/handler to a :class:`fastapi.FastAPI` app.
    * Provide a :meth:`dependency` factory that routes can mount via
      ``dependencies=[Depends(...)]`` for tighter, per-scope limits.

    Per-route enforcement uses the same backing storage so the global
    default and the per-route limits are coherent (one 5/min login limit
    consumes one request from the 200/min global budget too).
    """

    def __init__(
        self,
        *,
        storage_uri: str | None = None,
        default_limit: str = DEFAULT_LIMIT,
        enabled: bool = True,
    ) -> None:
        self._enabled = enabled
        self._default_limit = default_limit
        self._storage_uri = storage_uri
        # slowapi's Limiter is the global front-door. It also exposes the
        # underlying `limits` storage we reuse for per-route checks.
        self._limiter = Limiter(
            key_func=_identity_key,
            default_limits=[default_limit] if enabled else [],
            storage_uri=storage_uri,
            headers_enabled=True,
            enabled=enabled,
        )
        # For per-route dependencies we hold our own strategy bound to the
        # same storage. Going through slowapi.limit() is awkward because
        # that path is decorator-only and we want pure-dependency wiring.
        self._strategy = MovingWindowRateLimiter(self._limiter.limiter.storage)

    # --- App wiring -----------------------------------------------------

    @property
    def limiter(self) -> Limiter:
        return self._limiter

    @property
    def enabled(self) -> bool:
        return self._enabled

    def install(self, app: FastAPI) -> None:
        """Attach the global limiter to a FastAPI app."""
        app.state.limiter = self._limiter
        app.add_exception_handler(RateLimitExceeded, self._on_rate_limit_exceeded)
        app.add_middleware(SlowAPIMiddleware)

    async def reset(self) -> None:
        """Test-only: clear the backing storage between tests."""
        storage = self._limiter.limiter.storage
        if isinstance(storage, MemoryStorage):
            storage.reset()
        elif isinstance(storage, RedisStorage):
            # `reset()` blasts every limit key under the configured prefix.
            storage.reset()

    # --- Per-route dependency factory -----------------------------------

    def dependency(
        self,
        limit: str,
        *,
        per: str = "ip",
        scope: str | None = None,
    ) -> Callable[[Request], Awaitable[None]]:
        """Return a FastAPI dependency that enforces ``limit`` per ``per``.

        * ``per="ip"`` keys on the caller's IP (use for unauthenticated
          endpoints like ``/login`` so an attacker can't drain a victim's
          per-user budget without knowing their session).
        * ``per="user"`` keys on the bearer user-id (use for authenticated,
          quota-style endpoints like AI inference).

        ``scope`` namespaces the limit so different routes with the same
        rate share a name visibly in storage but never collide.
        """
        item = parse(limit)
        key_func = _user_key if per == "user" else _ip_key
        route_scope = scope or f"{limit}:{per}"
        route_limit = _RouteLimit(item=item, key_func=key_func, raw=limit)

        async def _check(request: Request) -> None:
            if not self._enabled:
                return
            key = route_limit.key_func(request)
            try:
                allowed = await self._hit(route_limit.item, route_scope, key)
            except Exception as exc:  # pragma: no cover — storage outage
                # Fail-open: a Redis hiccup must not take the API down.
                log.warning("ratelimit.storage_error", error=str(exc))
                return
            if not allowed:
                reset_in = await self._reset_in(route_limit.item, route_scope, key)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "code": "rate.limited",
                        "message": f"rate limit exceeded: {route_limit.raw}",
                    },
                    headers={"Retry-After": str(max(1, reset_in))},
                )

        return _check

    async def _hit(self, item: RateLimitItem, scope: str, key: str) -> bool:
        # MovingWindowRateLimiter is sync over a (possibly) sync storage.
        # Wrap in to_thread only if we ever swap to a blocking client; the
        # in-process redis-py call is fast enough to inline here.
        return self._strategy.hit(item, scope, key)

    async def _reset_in(self, item: RateLimitItem, scope: str, key: str) -> int:
        try:
            reset_at, _remaining = self._strategy.get_window_stats(item, scope, key)
        except Exception:  # pragma: no cover
            return item.get_expiry()
        import time

        return max(1, int(reset_at - time.time()))

    # --- Exception handler ---------------------------------------------

    @staticmethod
    def _on_rate_limit_exceeded(request: Request, exc: Exception) -> JSONResponse:
        # slowapi's global middleware catches RateLimitExceeded for the
        # default 200/min budget and routes it here; the 429 envelope must
        # match the per-route HTTPException above.
        limit_str = "default"
        retry_after = 60
        if isinstance(exc, RateLimitExceeded) and exc.limit is not None:
            limit_obj = exc.limit.limit
            limit_str = f"{limit_obj.amount} per {limit_obj.GRANULARITY.name}"
            retry_after = max(1, int(limit_obj.get_expiry()))
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": {
                    "code": "rate.limited",
                    "message": f"rate limit exceeded: {limit_str}",
                }
            },
            headers={"Retry-After": str(retry_after)},
        )


# --- Singleton wiring ------------------------------------------------------

_rate_limiter: RateLimiter | None = None


def rate_limit(limit: str, *, per: str = "ip", scope: str) -> Callable[[Request], Awaitable[None]]:
    """Module-level factory: returns a per-route dependency closure that
    re-resolves the singleton limiter on every request.

    The indirection matters: routers wire ``Depends(rate_limit(...))`` once
    at import time, but tests need to flip the limiter on/off mid-suite.
    Resolving via :func:`get_rate_limiter` inside the closure keeps the
    indirection cheap and respects :func:`reset_rate_limiter`.
    """

    async def _check(request: Request) -> None:
        limiter = get_rate_limiter()
        if not limiter.enabled:
            return
        # ``dependency()`` parses the limit each call which is fine — the
        # parsed item is tiny and we'd otherwise have to plumb a cache map
        # through ``reset_rate_limiter`` anyway.
        check = limiter.dependency(limit, per=per, scope=scope)
        await check(request)

    _check.__name__ = f"rate_limit__{scope.replace(':', '_')}"
    return _check


def get_rate_limiter() -> RateLimiter:
    """Lazy singleton used by routers + app factory.

    First call materializes the limiter using settings; tests can override
    by calling :func:`reset_rate_limiter` to drop the cache.
    """
    global _rate_limiter
    if _rate_limiter is None:
        settings = get_settings()
        # In tests we still want the limiter wired so we can assert 429s,
        # but we route through the local Redis the dev stack already has.
        try:
            storage_from_string(settings.redis_url)
            storage_uri = settings.redis_url
        except Exception as exc:  # pragma: no cover
            log.warning("ratelimit.redis_unavailable", error=str(exc))
            storage_uri = "memory://"
        _rate_limiter = RateLimiter(
            storage_uri=storage_uri,
            default_limit=DEFAULT_LIMIT,
            enabled=settings.rate_limit_enabled,
        )
    return _rate_limiter


def reset_rate_limiter() -> None:
    """Drop the singleton so the next ``get_rate_limiter`` re-reads settings."""
    global _rate_limiter
    _rate_limiter = None


__all__ = [
    "DEFAULT_LIMIT",
    "RateLimiter",
    "get_rate_limiter",
    "rate_limit",
    "reset_rate_limiter",
]
