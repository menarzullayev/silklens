"""Request-scoped trace_id binding for structlog + Prometheus.

The middleware runs *outside* :class:`BearerContextMiddleware` so every log
emitted during a request — including auth-decode failures — carries a
``trace_id``. Three things happen per request:

1. **Resolve trace_id** — pull the W3C ``traceparent`` header if present and
   extract the hex trace ID. Otherwise generate a fresh UUID4 hex. The same
   value is exposed on ``request.state.trace_id`` for downstream code and
   echoed back via the ``X-Trace-Id`` response header.
2. **Bind contextvars** — ``structlog.contextvars.bind_contextvars`` puts
   ``trace_id``, ``method``, and ``route`` into the merge-contextvars dict so
   every log line for this request is automatically correlated.
3. **Increment custom metrics** — after ``call_next`` we record the duration
   + status into the ``silklens_http_*`` counter/histogram defined in
   ``src.core.metrics``.

Contextvars are always cleared in a ``finally`` block to prevent leakage
across requests sharing a worker thread.
"""

from __future__ import annotations

import re
import time
import uuid
from typing import TYPE_CHECKING

import structlog
from starlette.middleware.base import BaseHTTPMiddleware

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from starlette.requests import Request
    from starlette.responses import Response
    from starlette.types import ASGIApp


# W3C traceparent format: ``00-<32 hex trace>-<16 hex span>-<2 hex flags>``.
_TRACEPARENT_RE = re.compile(r"^[0-9a-f]{2}-([0-9a-f]{32})-[0-9a-f]{16}-[0-9a-f]{2}$")


def _extract_trace_id(header_value: str | None) -> str:
    if header_value:
        match = _TRACEPARENT_RE.match(header_value.strip().lower())
        if match:
            return match.group(1)
    return uuid.uuid4().hex


class TraceContextMiddleware(BaseHTTPMiddleware):
    """Bind ``trace_id`` to structlog + record HTTP metrics."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(  # type: ignore[override]
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        from src.core import metrics  # local import keeps import cycles loose

        trace_id = _extract_trace_id(request.headers.get("traceparent"))
        request.state.trace_id = trace_id

        # Route template is only known after FastAPI resolves the path; fall
        # back to the raw URL path for unmatched requests (404 etc.).
        path_template = request.scope.get("path") or request.url.path
        method = request.method

        structlog.contextvars.bind_contextvars(
            trace_id=trace_id,
            method=method,
            route=path_template,
        )

        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            # Resolved route template if FastAPI matched one.
            matched = request.scope.get("route")
            if matched is not None and getattr(matched, "path", None):
                path_template = matched.path  # type: ignore[assignment]
            response.headers["X-Trace-Id"] = trace_id
            return response
        finally:
            elapsed = time.perf_counter() - started
            labels = (method, path_template, str(status_code))
            try:
                metrics.http_requests_total.labels(*labels).inc()
                metrics.http_request_duration_seconds.labels(*labels).observe(elapsed)
            except Exception:  # noqa: S110
                # Metric failures must never break a real response.
                pass
            structlog.contextvars.clear_contextvars()
