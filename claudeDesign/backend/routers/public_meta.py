"""Public meta endpoints — branding + vocabularies.

These power the mobile app's startup configuration: theme + app name + the
controlled vocabularies that drive dropdowns (languages, heritage kinds,
residency regions, etc.). No authentication required.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session

router = APIRouter(prefix="/v1", tags=["public"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

_DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"


# --- Schemas --------------------------------------------------------------


class BrandingPublicOut(BaseModel):
    tenant_slug: str
    app_name: dict[str, str]
    logo_url: str | None
    logo_dark_url: str | None
    primary_color: str | None
    accent_color: str | None
    splash_url: str | None
    font_family: str | None
    theme_mode_default: str | None
    extra: dict[str, Any]


class VocabTermOut(BaseModel):
    slug: str
    display_name: dict[str, str]
    description: dict[str, str]
    parent_slug: str | None
    sort_order: int


class VocabOut(BaseModel):
    vocabulary_slug: str
    is_hierarchical: bool
    items: list[VocabTermOut]


# --- Routes ---------------------------------------------------------------


@router.get("/branding", response_model=BrandingPublicOut)
async def get_public_branding(
    request: Request,
    db: SessionDep,
    tenant: Annotated[str | None, Query(min_length=2, max_length=64)] = None,
) -> BrandingPublicOut:
    """Resolve branding for the requesting host.

    Resolution order:
      1. `?tenant=<slug>` query parameter (admin preview)
      2. Host header matched against `tenant_domains.domain`
      3. The platform default tenant.
    """
    tenant_slug: str | None = tenant
    tenant_id: str = _DEFAULT_TENANT_ID

    if tenant_slug is not None:
        row = (
            await db.execute(
                text("SELECT id, slug::text AS slug FROM tenants WHERE slug = :s"),
                {"s": tenant_slug},
            )
        ).one_or_none()
        if row is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "tenant.not_found", "message": tenant_slug},
            )
        tenant_id = str(row._mapping["id"])
        tenant_slug = row._mapping["slug"]
    else:
        host = (request.headers.get("host") or "").split(":")[0].lower()
        if host:
            row = (
                await db.execute(
                    text(
                        """
                        SELECT t.id, t.slug::text AS slug
                        FROM tenant_domains d
                        JOIN tenants t ON t.id = d.tenant_id
                        WHERE d.domain = :host AND d.verified_at IS NOT NULL
                        LIMIT 1
                        """
                    ),
                    {"host": host},
                )
            ).one_or_none()
            if row is not None:
                tenant_id = str(row._mapping["id"])
                tenant_slug = row._mapping["slug"]
        if tenant_slug is None:
            row = (
                await db.execute(
                    text("SELECT slug::text AS slug FROM tenants WHERE id = :id"),
                    {"id": tenant_id},
                )
            ).one()
            tenant_slug = row._mapping["slug"]

    row = (
        await db.execute(
            text(
                """
                SELECT app_name, logo_url, logo_dark_url, primary_color, accent_color,
                       splash_url, font_family, theme_mode_default, extra
                FROM tenant_branding WHERE tenant_id = :tid
                """
            ),
            {"tid": tenant_id},
        )
    ).one_or_none()
    if row is None:
        return BrandingPublicOut(
            tenant_slug=tenant_slug,
            app_name={},
            logo_url=None,
            logo_dark_url=None,
            primary_color=None,
            accent_color=None,
            splash_url=None,
            font_family=None,
            theme_mode_default="system",
            extra={},
        )
    m = row._mapping
    return BrandingPublicOut(
        tenant_slug=tenant_slug,
        app_name=dict(m["app_name"]) if m["app_name"] else {},
        logo_url=m["logo_url"],
        logo_dark_url=m["logo_dark_url"],
        primary_color=m["primary_color"],
        accent_color=m["accent_color"],
        splash_url=m["splash_url"],
        font_family=m["font_family"],
        theme_mode_default=m["theme_mode_default"],
        extra=dict(m["extra"]) if m["extra"] else {},
    )


@router.get("/vocab/{vocab_slug}", response_model=VocabOut)
async def get_vocabulary(vocab_slug: str, db: SessionDep) -> VocabOut:
    vocab_row = (
        await db.execute(
            text(
                """
                SELECT id, slug, is_hierarchical
                FROM controlled_vocabularies WHERE slug = :s
                """
            ),
            {"s": vocab_slug},
        )
    ).one_or_none()
    if vocab_row is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "vocabulary.not_found", "message": vocab_slug},
        )
    vocab_id = vocab_row._mapping["id"]

    result = await db.execute(
        text(
            """
            SELECT
                t.slug,
                t.display_name,
                t.description,
                p.slug AS parent_slug,
                t.sort_order
            FROM vocabulary_terms t
            LEFT JOIN vocabulary_terms p ON p.id = t.parent_id
            WHERE t.vocabulary_id = :vid AND t.is_active
            ORDER BY t.sort_order, t.slug
            """
        ),
        {"vid": vocab_id},
    )
    items = [
        VocabTermOut(
            slug=r._mapping["slug"],
            display_name=dict(r._mapping["display_name"]) if r._mapping["display_name"] else {},
            description=dict(r._mapping["description"]) if r._mapping["description"] else {},
            parent_slug=r._mapping["parent_slug"],
            sort_order=int(r._mapping["sort_order"]),
        )
        for r in result.all()
    ]
    return VocabOut(
        vocabulary_slug=vocab_slug,
        is_hierarchical=bool(vocab_row._mapping["is_hierarchical"]),
        items=items,
    )
