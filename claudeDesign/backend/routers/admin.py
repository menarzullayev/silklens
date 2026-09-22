"""Admin endpoints — tenants, branding, system settings, feature flags.

All routes here are permission-gated via `require_permission`. Reads of secret
values are redacted for callers without `system:settings` (this is enforced at
the route layer rather than the SQL layer to keep the secret value on the
server even if downstream consumers later need it).
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.settings import get_settings
from src.infrastructure.ingestion.celery_tasks import _run_ingest_country, _run_ingest_qid
from src.infrastructure.search.celery_tasks import _run_bulk_reindex_all
from src.middleware.auth import AuthContext, require_permission

router = APIRouter(prefix="/v1/admin", tags=["admin"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


# --- Schemas ---------------------------------------------------------------


class TenantOut(BaseModel):
    id: UUID
    slug: str
    display_name: dict[str, str]
    status: str
    plan_tier: str
    created_at: datetime
    updated_at: datetime


class TenantsPage(BaseModel):
    items: list[TenantOut]
    total: int
    limit: int
    offset: int


class TenantCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")
    display_name: dict[str, str] = Field(min_length=1)


class TenantPatch(BaseModel):
    display_name: dict[str, str] | None = None
    status: str | None = Field(default=None, pattern="^(active|suspended|archived)$")
    plan_tier: str | None = Field(default=None, min_length=1, max_length=32)


class BrandingOut(BaseModel):
    app_name: dict[str, str]
    logo_url: str | None
    logo_dark_url: str | None
    primary_color: str | None
    accent_color: str | None
    splash_url: str | None
    font_family: str | None
    theme_mode_default: str | None
    extra: dict[str, Any]


class BrandingPut(BaseModel):
    app_name: dict[str, str] | None = None
    logo_url: str | None = Field(default=None, max_length=512)
    logo_dark_url: str | None = Field(default=None, max_length=512)
    primary_color: str | None = Field(default=None, pattern="^#[0-9A-Fa-f]{6}$")
    accent_color: str | None = Field(default=None, pattern="^#[0-9A-Fa-f]{6}$")
    splash_url: str | None = Field(default=None, max_length=512)
    font_family: str | None = Field(default=None, max_length=128)
    theme_mode_default: str | None = Field(
        default=None,
        pattern="^(light|dark|system|national|high_contrast)$",
    )
    extra: dict[str, Any] = Field(default_factory=dict)


class SystemSettingOut(BaseModel):
    key: str
    value: Any
    value_type: str
    scope: str
    description: str | None
    is_secret: bool


class SystemSettingPut(BaseModel):
    key: str = Field(min_length=2, max_length=128)
    value: Any
    value_type: str = Field(pattern="^(string|int|float|bool|json|duration|color|url)$")
    scope: str = Field(default="tenant", pattern="^(tenant|global|user_overrideable)$")
    description: str | None = Field(default=None, max_length=512)
    is_secret: bool = False


class FeatureFlagOut(BaseModel):
    key: str
    enabled: bool
    rollout_kind: str
    rollout_value: dict[str, Any]
    description: str | None


class FeatureFlagPut(BaseModel):
    enabled: bool
    rollout_kind: str = Field(
        default="boolean",
        pattern="^(boolean|percentage|user_allowlist|user_denylist|jsonl_rules)$",
    )
    rollout_value: dict[str, Any] = Field(default_factory=dict)
    description: str | None = Field(default=None, max_length=512)

    @field_validator("rollout_value")
    @classmethod
    def _ensure_dict(cls, v: Any) -> dict[str, Any]:
        if not isinstance(v, dict):
            raise ValueError("rollout_value must be an object")
        return v


def _json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)


# --- Routes: tenants -------------------------------------------------------


@router.get(
    "/tenants",
    response_model=TenantsPage,
    dependencies=[Depends(require_permission("tenant:read"))],
)
async def list_tenants(
    db: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TenantsPage:
    total = (
        await db.execute(text("SELECT count(*) FROM tenants WHERE deleted_at IS NULL"))
    ).scalar_one()
    result = await db.execute(
        text(
            """
            SELECT id, slug::text AS slug, display_name, status, plan_tier,
                   created_at, updated_at
            FROM tenants
            WHERE deleted_at IS NULL
            ORDER BY created_at ASC
            LIMIT :limit OFFSET :offset
            """
        ),
        {"limit": limit, "offset": offset},
    )
    items = [
        TenantOut(
            id=r._mapping["id"],
            slug=r._mapping["slug"],
            display_name=dict(r._mapping["display_name"]) if r._mapping["display_name"] else {},
            status=r._mapping["status"],
            plan_tier=r._mapping["plan_tier"],
            created_at=r._mapping["created_at"],
            updated_at=r._mapping["updated_at"],
        )
        for r in result.all()
    ]
    return TenantsPage(items=items, total=int(total), limit=limit, offset=offset)


@router.post(
    "/tenants",
    response_model=TenantOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("tenant:create"))],
)
async def create_tenant(payload: TenantCreate, db: SessionDep) -> TenantOut:
    existing = (
        await db.execute(
            text("SELECT 1 FROM tenants WHERE slug = :slug"),
            {"slug": payload.slug},
        )
    ).one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail={"code": "tenant.duplicate_slug", "message": "slug already in use"},
        )
    result = await db.execute(
        text(
            """
            INSERT INTO tenants (slug, display_name, status, plan_tier)
            VALUES (:slug, CAST(:display_name AS jsonb), 'active', 'free')
            RETURNING id, slug::text AS slug, display_name, status, plan_tier,
                      created_at, updated_at
            """
        ),
        {"slug": payload.slug, "display_name": _json(payload.display_name)},
    )
    m = result.one()._mapping
    await db.commit()
    return TenantOut(
        id=m["id"],
        slug=m["slug"],
        display_name=dict(m["display_name"]) if m["display_name"] else {},
        status=m["status"],
        plan_tier=m["plan_tier"],
        created_at=m["created_at"],
        updated_at=m["updated_at"],
    )


@router.patch(
    "/tenants/{slug}",
    response_model=TenantOut,
    dependencies=[Depends(require_permission("tenant:manage"))],
)
async def patch_tenant(slug: str, payload: TenantPatch, db: SessionDep) -> TenantOut:
    sets: list[str] = []
    params: dict[str, object] = {"slug": slug}
    if payload.display_name is not None:
        sets.append("display_name = CAST(:display_name AS jsonb)")
        params["display_name"] = _json(payload.display_name)
    if payload.status is not None:
        sets.append("status = :status")
        params["status"] = payload.status
    if payload.plan_tier is not None:
        sets.append("plan_tier = :plan_tier")
        params["plan_tier"] = payload.plan_tier
    if not sets:
        raise HTTPException(status_code=422, detail={"code": "tenant.empty_patch"})

    result = await db.execute(
        text(
            f"""
            UPDATE tenants SET {", ".join(sets)}
            WHERE slug = :slug
            RETURNING id, slug::text AS slug, display_name, status, plan_tier,
                      created_at, updated_at
            """  # noqa: S608
        ),
        params,
    )
    row = result.one_or_none()
    await db.commit()
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "tenant.not_found"})
    m = row._mapping
    return TenantOut(
        id=m["id"],
        slug=m["slug"],
        display_name=dict(m["display_name"]) if m["display_name"] else {},
        status=m["status"],
        plan_tier=m["plan_tier"],
        created_at=m["created_at"],
        updated_at=m["updated_at"],
    )


# --- Routes: branding ------------------------------------------------------


async def _resolve_tenant_id(db: AsyncSession, slug: str) -> UUID:
    row = (
        await db.execute(
            text("SELECT id FROM tenants WHERE slug = :slug"),
            {"slug": slug},
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "tenant.not_found"})
    return row[0]


@router.get(
    "/tenants/{slug}/branding",
    response_model=BrandingOut,
    dependencies=[Depends(require_permission("tenant:branding"))],
)
async def get_branding(slug: str, db: SessionDep) -> BrandingOut:
    tenant_id = await _resolve_tenant_id(db, slug)
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
        return BrandingOut(
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
    return BrandingOut(
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


@router.put(
    "/tenants/{slug}/branding",
    response_model=BrandingOut,
    dependencies=[Depends(require_permission("tenant:branding"))],
)
async def put_branding(slug: str, payload: BrandingPut, db: SessionDep) -> BrandingOut:
    tenant_id = await _resolve_tenant_id(db, slug)
    await db.execute(
        text(
            """
            INSERT INTO tenant_branding (
                tenant_id, app_name, logo_url, logo_dark_url, primary_color, accent_color,
                splash_url, font_family, theme_mode_default, extra
            ) VALUES (
                :tid,
                CAST(COALESCE(:app_name, '{}') AS jsonb),
                :logo, :logo_dark, :primary, :accent,
                :splash, :font, :mode,
                CAST(COALESCE(:extra, '{}') AS jsonb)
            )
            ON CONFLICT (tenant_id) DO UPDATE SET
                app_name = COALESCE(CAST(:app_name AS jsonb), tenant_branding.app_name),
                logo_url = COALESCE(:logo, tenant_branding.logo_url),
                logo_dark_url = COALESCE(:logo_dark, tenant_branding.logo_dark_url),
                primary_color = COALESCE(:primary, tenant_branding.primary_color),
                accent_color = COALESCE(:accent, tenant_branding.accent_color),
                splash_url = COALESCE(:splash, tenant_branding.splash_url),
                font_family = COALESCE(:font, tenant_branding.font_family),
                theme_mode_default = COALESCE(:mode, tenant_branding.theme_mode_default),
                extra = CAST(:extra AS jsonb)
            """
        ),
        {
            "tid": tenant_id,
            "app_name": _json(payload.app_name) if payload.app_name is not None else None,
            "logo": payload.logo_url,
            "logo_dark": payload.logo_dark_url,
            "primary": payload.primary_color,
            "accent": payload.accent_color,
            "splash": payload.splash_url,
            "font": payload.font_family,
            "mode": payload.theme_mode_default,
            "extra": _json(payload.extra),
        },
    )
    await db.commit()
    return await get_branding(slug, db)


# --- Routes: system_settings ----------------------------------------------


@router.get(
    "/system-settings",
    response_model=list[SystemSettingOut],
    dependencies=[Depends(require_permission("system:settings"))],
)
async def list_system_settings(
    db: SessionDep,
    tenant_id: Annotated[UUID | None, Query()] = None,
) -> list[SystemSettingOut]:
    params: dict[str, object] = {}
    where = ""
    if tenant_id is not None:
        where = "WHERE tenant_id = :tid"
        params["tid"] = tenant_id
    result = await db.execute(
        text(
            f"""
            SELECT key, value, value_type, scope, description, is_secret
            FROM system_settings {where}
            ORDER BY key
            """  # noqa: S608
        ),
        params,
    )
    out: list[SystemSettingOut] = []
    for r in result.all():
        m = r._mapping
        value: Any = m["value"]
        if m["is_secret"]:
            value = "***"
        out.append(
            SystemSettingOut(
                key=m["key"],
                value=value,
                value_type=m["value_type"],
                scope=m["scope"],
                description=m["description"],
                is_secret=bool(m["is_secret"]),
            )
        )
    return out


@router.put(
    "/system-settings",
    response_model=SystemSettingOut,
    dependencies=[Depends(require_permission("system:settings"))],
)
async def put_system_setting(
    payload: SystemSettingPut,
    db: SessionDep,
    tenant_id: Annotated[UUID | None, Query()] = None,
) -> SystemSettingOut:
    # Default to current tenant from the bearer (system_actor / super_admin
    # can target a specific tenant via query string).
    target = tenant_id or UUID("00000000-0000-0000-0000-000000000001")
    await db.execute(
        text(
            """
            INSERT INTO system_settings (
                tenant_id, key, value, value_type, scope, description, is_secret
            ) VALUES (
                :tid, :key, CAST(:value AS jsonb), :vtype, :scope, :desc, :secret
            )
            ON CONFLICT (tenant_id, key) DO UPDATE SET
                value = EXCLUDED.value,
                value_type = EXCLUDED.value_type,
                scope = EXCLUDED.scope,
                description = EXCLUDED.description,
                is_secret = EXCLUDED.is_secret
            """
        ),
        {
            "tid": target,
            "key": payload.key,
            "value": _json(payload.value),
            "vtype": payload.value_type,
            "scope": payload.scope,
            "desc": payload.description,
            "secret": payload.is_secret,
        },
    )
    await db.commit()
    row = (
        await db.execute(
            text(
                """
                SELECT key, value, value_type, scope, description, is_secret
                FROM system_settings
                WHERE tenant_id = :tid AND key = :key
                """
            ),
            {"tid": target, "key": payload.key},
        )
    ).one()
    m = row._mapping
    return SystemSettingOut(
        key=m["key"],
        value="***" if m["is_secret"] else m["value"],
        value_type=m["value_type"],
        scope=m["scope"],
        description=m["description"],
        is_secret=bool(m["is_secret"]),
    )


# --- Routes: feature_flags ------------------------------------------------


@router.get(
    "/feature-flags",
    response_model=list[FeatureFlagOut],
    dependencies=[Depends(require_permission("system:feature_flags"))],
)
async def list_feature_flags(
    db: SessionDep,
    tenant_id: Annotated[UUID | None, Query()] = None,
) -> list[FeatureFlagOut]:
    params: dict[str, object] = {}
    where = ""
    if tenant_id is not None:
        where = "WHERE tenant_id = :tid OR tenant_id IS NULL"
        params["tid"] = tenant_id
    result = await db.execute(
        text(
            f"""
            SELECT flag_key, enabled, rollout_kind, rollout_value, description
            FROM feature_flags {where}
            ORDER BY flag_key
            """  # noqa: S608
        ),
        params,
    )
    return [
        FeatureFlagOut(
            key=r._mapping["flag_key"],
            enabled=bool(r._mapping["enabled"]),
            rollout_kind=r._mapping["rollout_kind"],
            rollout_value=dict(r._mapping["rollout_value"]) if r._mapping["rollout_value"] else {},
            description=r._mapping["description"],
        )
        for r in result.all()
    ]


@router.put(
    "/feature-flags/{key}",
    response_model=FeatureFlagOut,
    dependencies=[Depends(require_permission("system:feature_flags"))],
)
async def put_feature_flag(
    key: str,
    payload: FeatureFlagPut,
    db: SessionDep,
    tenant_id: Annotated[UUID | None, Query()] = None,
) -> FeatureFlagOut:
    target = tenant_id or UUID("00000000-0000-0000-0000-000000000001")
    await db.execute(
        text(
            """
            INSERT INTO feature_flags (
                tenant_id, flag_key, enabled, rollout_kind, rollout_value, description
            ) VALUES (:tid, :k, :enabled, :kind, CAST(:value AS jsonb), :desc)
            ON CONFLICT (tenant_id, flag_key) DO UPDATE SET
                enabled = EXCLUDED.enabled,
                rollout_kind = EXCLUDED.rollout_kind,
                rollout_value = EXCLUDED.rollout_value,
                description = EXCLUDED.description
            """
        ),
        {
            "tid": target,
            "k": key,
            "enabled": payload.enabled,
            "kind": payload.rollout_kind,
            "value": _json(payload.rollout_value),
            "desc": payload.description,
        },
    )
    await db.commit()
    row = (
        await db.execute(
            text(
                """
                SELECT flag_key, enabled, rollout_kind, rollout_value, description
                FROM feature_flags
                WHERE tenant_id = :tid AND flag_key = :k
                """
            ),
            {"tid": target, "k": key},
        )
    ).one()
    m = row._mapping
    return FeatureFlagOut(
        key=m["flag_key"],
        enabled=bool(m["enabled"]),
        rollout_kind=m["rollout_kind"],
        rollout_value=dict(m["rollout_value"]) if m["rollout_value"] else {},
        description=m["description"],
    )


# --- Routes: search index admin ------------------------------------------


class SearchIndexStatusEntry(BaseModel):
    slug: str
    language_tier: str
    current_doc_count: int
    target_doc_count: int
    last_rebuilt_at: datetime | None
    is_active: bool


class SearchIndexStatus(BaseModel):
    indices: list[SearchIndexStatusEntry]


class SearchRebuildOut(BaseModel):
    enqueued: bool
    indexed: int
    failed: int


@router.get(
    "/search/status",
    response_model=SearchIndexStatus,
    dependencies=[Depends(require_permission("system:settings"))],
)
async def search_status(db: SessionDep) -> SearchIndexStatus:
    rows = (
        await db.execute(
            text(
                """
                SELECT slug, language_tier, current_doc_count, target_doc_count,
                       last_rebuilt_at, is_active
                FROM search_index_mappings
                WHERE kind = 'heritage'
                ORDER BY slug
                """
            )
        )
    ).all()
    return SearchIndexStatus(
        indices=[
            SearchIndexStatusEntry(
                slug=r._mapping["slug"],
                language_tier=r._mapping["language_tier"],
                current_doc_count=int(r._mapping["current_doc_count"]),
                target_doc_count=int(r._mapping["target_doc_count"]),
                last_rebuilt_at=r._mapping["last_rebuilt_at"],
                is_active=bool(r._mapping["is_active"]),
            )
            for r in rows
        ]
    )


@router.post(
    "/search/rebuild",
    response_model=SearchRebuildOut,
    dependencies=[Depends(require_permission("system:settings"))],
)
async def search_rebuild() -> SearchRebuildOut:
    # We run synchronously here when Celery isn't available (dev / test).
    # Production deploys override this via the worker; the body is the same
    # async helper either way so we never diverge.
    result = await _run_bulk_reindex_all()
    return SearchRebuildOut(
        enqueued=True,
        indexed=result["indexed"],
        failed=result["failed"],
    )


# --- Routes: Wikidata ingestion admin ------------------------------------


class IngestionCountryIn(BaseModel):
    country_code: str = Field(min_length=2, max_length=2)
    limit: int = Field(default=50, ge=1, le=500)


class IngestionQidIn(BaseModel):
    qid: str = Field(min_length=2, max_length=32, pattern=r"^Q[1-9][0-9]*$")


class IngestionCountryOut(BaseModel):
    discovered: int
    created: int
    skipped: int
    failed: int


class IngestionQidOut(BaseModel):
    qid: str
    found: bool
    created: bool
    heritage_id: UUID | None = None
    pub_id: str | None = None


class JobRowOut(BaseModel):
    id: UUID
    kind: str
    status: str
    payload: dict[str, Any]
    requested_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None


class JobListOut(BaseModel):
    items: list[JobRowOut]


@router.post(
    "/ingestion/wikidata",
    response_model=IngestionCountryOut,
    dependencies=[Depends(require_permission("tenant:manage"))],
)
async def ingest_wikidata_country(
    payload: IngestionCountryIn,
    db: SessionDep,
    ctx: Annotated[AuthContext, Depends(require_permission("tenant:manage"))],
) -> IngestionCountryOut:
    job_id = (
        await db.execute(
            text(
                """
                INSERT INTO background_jobs (kind, payload, status, started_at)
                VALUES ('wikidata.ingest_country', CAST(:p AS jsonb), 'running', now())
                RETURNING id
                """
            ),
            {
                "p": _json(
                    {
                        "country_code": payload.country_code.upper(),
                        "limit": payload.limit,
                        "actor": str(ctx.user_id),
                    }
                ),
            },
        )
    ).scalar_one()
    await db.commit()
    try:
        result = await _run_ingest_country(
            country_code=payload.country_code.upper(),
            limit=payload.limit,
            actor=ctx.user_id,
        )
    except Exception as exc:
        await db.execute(
            text(
                """
                UPDATE background_jobs
                SET status = 'failed', finished_at = now(), error = :e
                WHERE id = :id
                """
            ),
            {"e": str(exc)[:1024], "id": job_id},
        )
        await db.commit()
        raise HTTPException(
            status_code=502,
            detail={"code": "ingestion.upstream_failed", "message": str(exc)},
        ) from exc

    await db.execute(
        text(
            """
            UPDATE background_jobs
            SET status = 'done',
                finished_at = now(),
                payload = payload || CAST(:r AS jsonb)
            WHERE id = :id
            """
        ),
        {"r": _json({"result": result}), "id": job_id},
    )
    await db.commit()
    return IngestionCountryOut(**result)


@router.post(
    "/ingestion/wikidata/qid",
    response_model=IngestionQidOut,
    dependencies=[Depends(require_permission("tenant:manage"))],
)
async def ingest_wikidata_qid(
    payload: IngestionQidIn,
    ctx: Annotated[AuthContext, Depends(require_permission("tenant:manage"))],
) -> IngestionQidOut:
    try:
        result = await _run_ingest_qid(qid=payload.qid, actor=ctx.user_id)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "ingestion.upstream_failed", "message": str(exc)},
        ) from exc
    return IngestionQidOut(
        qid=result["qid"],
        found=bool(result.get("found", False)),
        created=bool(result.get("created", False)),
        heritage_id=UUID(result["heritage_id"]) if result.get("heritage_id") else None,
        pub_id=result.get("pub_id"),
    )


@router.get(
    "/ingestion/jobs",
    response_model=JobListOut,
    dependencies=[Depends(require_permission("tenant:manage"))],
)
async def list_ingestion_jobs(
    db: SessionDep,
    status_filter: Annotated[
        str | None,
        Query(alias="status", pattern="^(queued|running|done|failed|cancelled)$"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> JobListOut:
    params: dict[str, Any] = {"limit": limit}
    where = "WHERE kind LIKE 'wikidata.%' OR kind LIKE 'ingestion.%'"
    if status_filter:
        where += " AND status = :status"
        params["status"] = status_filter
    rows = (
        await db.execute(
            text(
                f"""
                SELECT id, kind, status, payload, requested_at, started_at,
                       finished_at, error
                FROM background_jobs
                {where}
                ORDER BY requested_at DESC
                LIMIT :limit
                """  # noqa: S608
            ),
            params,
        )
    ).all()
    return JobListOut(
        items=[
            JobRowOut(
                id=r._mapping["id"],
                kind=r._mapping["kind"],
                status=r._mapping["status"],
                payload=dict(r._mapping["payload"]) if r._mapping["payload"] else {},
                requested_at=r._mapping["requested_at"],
                started_at=r._mapping["started_at"],
                finished_at=r._mapping["finished_at"],
                error=r._mapping["error"],
            )
            for r in rows
        ]
    )


# Touch the settings import so ruff doesn't flag it; we keep the symbol
# available because future admin routes (Sentry, OTLP, etc.) will need it.
_ = get_settings
