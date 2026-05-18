"""Health / version endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_ok(http: AsyncClient) -> None:
    response = await http.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "silklens-api"
    assert payload["env"] == "test"
    assert payload["version"]


@pytest.mark.asyncio
async def test_version(http: AsyncClient) -> None:
    response = await http.get("/version")
    assert response.status_code == 200
    body = response.json()
    assert "version" in body
    assert body["version"].count(".") == 2  # SemVer
