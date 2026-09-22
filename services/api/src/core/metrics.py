"""Custom Prometheus metrics for SilkLens.

All metrics live in the **default** prometheus registry so the
``prometheus-fastapi-instrumentator`` ``/metrics`` exporter picks them up
automatically. Names follow the ``silklens_<domain>_<metric>_<unit>`` convention
documented in `docs/architecture/07-infra-analytics-events.md` §11.

Three buckets of metrics:

1. **HTTP** — ``silklens_http_*`` counterpart to the instrumentator's built-in
   metrics. We keep our own counter + histogram so dashboards can pivot on
   ``route`` regardless of whether the request reached FastAPI's routing layer
   (e.g. early 422s on validation never bind a route on the built-in metric).
2. **AI** — per-provider/model inference latency + token usage so we can wire
   the AI fallback chain dashboard.
3. **Business** — signups, heritage views, revenue. Incremented from the
   relevant service path (identity, heritage, billing) so the counter
   movements line up 1:1 with domain events in ``event_log``.

The module also exposes ``register_db_pool_metrics(engine)`` which attaches a
SQLAlchemy ``pool`` event listener to keep two gauges fresh
(``silklens_db_pool_size`` and ``silklens_db_pool_in_use``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine


# --- HTTP --------------------------------------------------------------------

http_requests_total = Counter(
    "silklens_http_requests_total",
    "Total HTTP requests handled by the API.",
    labelnames=("method", "route", "status"),
)

http_request_duration_seconds = Histogram(
    "silklens_http_request_duration_seconds",
    "HTTP request duration in seconds.",
    labelnames=("method", "route", "status"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)


# --- AI ----------------------------------------------------------------------

ai_inference_duration_seconds = Histogram(
    "silklens_ai_inference_duration_seconds",
    "AI inference latency in seconds.",
    labelnames=("provider", "model", "task_type"),
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

ai_tokens_used_total = Counter(
    "silklens_ai_tokens_used_total",
    "Tokens consumed by AI inference; direction=in|out.",
    labelnames=("provider", "model", "direction"),
)


# --- Database pool -----------------------------------------------------------

db_pool_size = Gauge(
    "silklens_db_pool_size",
    "Configured SQLAlchemy pool size (checked-out + idle capacity).",
)

db_pool_in_use = Gauge(
    "silklens_db_pool_in_use",
    "Currently checked-out SQLAlchemy connections.",
)


# --- Business ----------------------------------------------------------------

business_signups_total = Counter(
    "silklens_business_signups_total",
    "Successful user signups (post email-uniqueness check).",
)

business_heritage_views_total = Counter(
    "silklens_business_heritage_views_total",
    "Heritage object detail-page views, partitioned by country.",
    labelnames=("country",),
)

business_revenue_usd_total = Counter(
    "silklens_business_revenue_usd_total",
    "Captured revenue in USD-equivalent, summed post-payment success.",
)


def register_db_pool_metrics(engine: AsyncEngine) -> None:
    """Wire SQLAlchemy ``pool`` events into the two gauges.

    The async engine wraps a sync ``sqlalchemy.pool.Pool`` accessible via
    ``engine.sync_engine.pool``. We listen on ``checkout``/``checkin`` and
    refresh ``db_pool_size`` from the pool's configured capacity. Failures
    are swallowed: a misconfigured pool should never crash startup.
    """

    try:
        from sqlalchemy import event

        sync_engine = engine.sync_engine
        pool = sync_engine.pool

        def _refresh(*_args: object) -> None:
            try:
                size_fn = getattr(pool, "size", None)
                checked_out_fn = getattr(pool, "checkedout", None)
                if callable(size_fn):
                    db_pool_size.set(size_fn())
                if callable(checked_out_fn):
                    db_pool_in_use.set(checked_out_fn())
            except Exception:
                # Observability — never break the actual DB request.
                return

        event.listen(sync_engine, "checkout", _refresh)
        event.listen(sync_engine, "checkin", _refresh)
        _refresh()
    except Exception:
        # Non-fatal; metrics will simply stay at 0.
        return


def reset_for_tests(registry: CollectorRegistry | None = None) -> None:
    """Test helper — zero out every counter/histogram via private API.

    Prometheus counters are monotonic by design; the only sanctioned way to
    reset them in tests is to clear the underlying ``_metrics`` mapping. This
    helper makes that intent explicit at call sites.
    """

    _ = registry  # currently unused; reserved for future per-test registries.
    for metric in (
        http_requests_total,
        http_request_duration_seconds,
        ai_inference_duration_seconds,
        ai_tokens_used_total,
        business_signups_total,
        business_heritage_views_total,
        business_revenue_usd_total,
    ):
        metric._metrics.clear()
