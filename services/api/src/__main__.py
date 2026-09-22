"""``python -m src`` entry point — runs the API under uvicorn."""

from __future__ import annotations

import uvicorn

from src.core.settings import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "src.api.app:create_app",
        host=settings.api_host,
        port=settings.api_port,
        factory=True,
        reload=settings.env == "dev",
        log_config=None,  # logging configured in src.core.logging
    )


if __name__ == "__main__":
    main()
