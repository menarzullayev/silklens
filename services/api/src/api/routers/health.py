"""Liveness / readiness / version endpoints."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src import __version__
from src.core.database import get_session
from src.core.settings import get_settings

router = APIRouter(tags=["meta"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str
    env: str
    version: str


class ReadyResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    db: bool


@router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(service=settings.service_name, env=settings.env, version=__version__)


@router.get("/ready", response_model=ReadyResponse)
async def ready(session: SessionDep) -> ReadyResponse:
    try:
        await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return ReadyResponse(status="ready" if db_ok else "not_ready", db=db_ok)


@router.get("/version")
async def version() -> dict[str, str]:
    return {"version": __version__}
