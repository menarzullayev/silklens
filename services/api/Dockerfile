FROM python:3.12-slim-bookworm AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        libpq5 \
        && rm -rf /var/lib/apt/lists/*

# uv is faster than pip for resolution + install; pinned for reproducibility
RUN pip install --no-cache-dir uv==0.4.30

WORKDIR /app


FROM base AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /app/
RUN uv pip install --system --no-cache-dir -e ".[dev]"


FROM base AS runtime

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . /app

RUN useradd --create-home --uid 1000 silklens && chown -R silklens:silklens /app
USER silklens

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fs http://localhost:8000/health || exit 1

CMD ["python", "-m", "src"]
