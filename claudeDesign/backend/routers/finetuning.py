"""Fine-tuning admin endpoints.

GET  /v1/admin/finetuning/datasets               — list all datasets
GET  /v1/admin/finetuning/datasets/{slug}        — dataset detail
GET  /v1/admin/finetuning/datasets/{slug}/export — JSONL download
POST /v1/admin/finetuning/datasets/{slug}/examples        — add manual example
GET  /v1/admin/finetuning/datasets/{slug}/examples/pending — pending approval queue
POST /v1/admin/finetuning/examples/{id}/approve  — approve example
POST /v1/admin/finetuning/jobs                   — scaffold training job
GET  /v1/admin/finetuning/jobs/{id}              — job status

All endpoints require the ``ai:configure`` permission (admin-only).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.domain.finetuning.entities import (
    DatasetPurpose,
    DatasetStatus,
    ExampleKind,
    ExampleSourceKind,
    JobKind,
    JobProvider,
    JobStatus,
    TargetModelKind,
)
from src.domain.finetuning.errors import FinetuningError
from src.domain.finetuning.service import FinetuningService
from src.infrastructure.finetuning.repository import SqlFinetuningRepository
from src.middleware.auth import AuthContext, require_permission

router = APIRouter(prefix="/v1/admin/finetuning", tags=["finetuning"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
AdminDep = Annotated[AuthContext, Depends(require_permission("ai:configure"))]


# ---------------------------------------------------------------------------
# DI helper
# ---------------------------------------------------------------------------


def _svc(db: AsyncSession) -> FinetuningService:
    return FinetuningService(repository=SqlFinetuningRepository(db))


def _raise(exc: FinetuningError) -> None:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": str(exc)},
    ) from exc


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class DatasetOut(BaseModel):
    id: UUID
    tenant_id: UUID
    slug: str
    name: dict
    description_md: str | None
    purpose: DatasetPurpose
    target_model_kind: TargetModelKind
    status: DatasetStatus
    example_count: int
    min_quality_score: Decimal


class ExampleOut(BaseModel):
    id: UUID
    dataset_id: UUID
    kind: ExampleKind
    input_text: str
    output_text: str
    quality_score: Decimal | None
    source_kind: ExampleSourceKind
    language_tag: str
    is_approved: bool
    approved_by: UUID | None
    approved_at: str | None


class JobOut(BaseModel):
    id: UUID
    dataset_id: UUID
    provider: JobProvider
    base_model_slug: str
    job_kind: JobKind
    status: JobStatus
    hyperparams: dict
    provider_job_id: str | None
    output_model_slug: str | None
    eval_metrics: dict
    cost_usd: Decimal | None


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class AddExampleIn(BaseModel):
    input_text: str = Field(min_length=1, max_length=32_000)
    output_text: str = Field(min_length=1, max_length=32_000)
    language: str = Field(default="uz", min_length=2, max_length=8)


class CreateJobIn(BaseModel):
    dataset_id: UUID
    provider: JobProvider
    base_model_slug: str = Field(min_length=1, max_length=256)
    job_kind: JobKind
    hyperparams: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/datasets", response_model=list[DatasetOut])
async def list_datasets(db: SessionDep, ctx: AdminDep) -> list[DatasetOut]:
    """List all fine-tuning datasets."""
    svc = _svc(db)
    datasets = await svc.list_datasets()
    return [
        DatasetOut(
            id=d.id,
            tenant_id=d.tenant_id,
            slug=d.slug,
            name=d.name,
            description_md=d.description_md,
            purpose=d.purpose,
            target_model_kind=d.target_model_kind,
            status=d.status,
            example_count=d.example_count,
            min_quality_score=d.min_quality_score,
        )
        for d in datasets
    ]


@router.get("/datasets/{slug}", response_model=DatasetOut)
async def get_dataset(slug: str, db: SessionDep, ctx: AdminDep) -> DatasetOut:
    """Return a single dataset by slug."""
    svc = _svc(db)
    try:
        d = await svc.get_dataset(slug)
    except FinetuningError as exc:
        _raise(exc)
    return DatasetOut(
        id=d.id,
        tenant_id=d.tenant_id,
        slug=d.slug,
        name=d.name,
        description_md=d.description_md,
        purpose=d.purpose,
        target_model_kind=d.target_model_kind,
        status=d.status,
        example_count=d.example_count,
        min_quality_score=d.min_quality_score,
    )


@router.get("/datasets/{slug}/export")
async def export_dataset(slug: str, db: SessionDep, ctx: AdminDep) -> Response:
    """Download all approved examples as JSONL (fine-tune ready format)."""
    svc = _svc(db)
    try:
        dataset = await svc.get_dataset(slug)
    except FinetuningError as exc:
        _raise(exc)

    jsonl = await svc.export_dataset(dataset.id)
    filename = f"finetuning_{slug}.jsonl"
    return Response(
        content=jsonl.encode("utf-8"),
        media_type="application/x-ndjson",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/datasets/{slug}/examples",
    response_model=ExampleOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_example(
    slug: str, payload: AddExampleIn, db: SessionDep, ctx: AdminDep
) -> ExampleOut:
    """Add a manually curated example to a dataset."""
    svc = _svc(db)
    try:
        dataset = await svc.get_dataset(slug)
        ex = await svc.add_manual_example(
            dataset_id=dataset.id,
            input_text=payload.input_text,
            output_text=payload.output_text,
            language=payload.language,
            actor=ctx.user_id,
        )
    except FinetuningError as exc:
        _raise(exc)
    await db.commit()
    return _example_out(ex)


@router.get("/datasets/{slug}/examples/pending", response_model=list[ExampleOut])
async def list_pending(
    slug: str,
    db: SessionDep,
    ctx: AdminDep,
    limit: int = 50,
) -> list[ExampleOut]:
    """List unapproved examples in a dataset (curator queue)."""
    svc = _svc(db)
    try:
        dataset = await svc.get_dataset(slug)
        examples = await svc.list_pending_examples(dataset.id, limit=limit)
    except FinetuningError as exc:
        _raise(exc)
    return [_example_out(ex) for ex in examples]


@router.post("/examples/{example_id}/approve", response_model=ExampleOut)
async def approve_example(example_id: UUID, db: SessionDep, ctx: AdminDep) -> ExampleOut:
    """Approve a pending example; requires ai:configure permission."""
    svc = _svc(db)
    try:
        ex = await svc.approve_example(example_id, actor=ctx.user_id)
    except FinetuningError as exc:
        _raise(exc)
    await db.commit()
    return _example_out(ex)


@router.post("/jobs", response_model=JobOut, status_code=status.HTTP_201_CREATED)
async def create_job(payload: CreateJobIn, db: SessionDep, ctx: AdminDep) -> JobOut:
    """Scaffold a fine-tuning job (status=pending; actual provider call deferred)."""
    svc = _svc(db)
    try:
        job = await svc.create_job(
            dataset_id=payload.dataset_id,
            provider=payload.provider,
            base_model_slug=payload.base_model_slug,
            job_kind=payload.job_kind,
            hyperparams=payload.hyperparams,
            actor=ctx.user_id,
        )
    except FinetuningError as exc:
        _raise(exc)
    await db.commit()
    return _job_out(job)


@router.get("/jobs/{job_id}", response_model=JobOut)
async def get_job(job_id: UUID, db: SessionDep, ctx: AdminDep) -> JobOut:
    """Return current status of a fine-tuning job."""
    svc = _svc(db)
    try:
        job = await svc.get_job(job_id)
    except FinetuningError as exc:
        _raise(exc)
    return _job_out(job)


# ---------------------------------------------------------------------------
# Internal mapping helpers
# ---------------------------------------------------------------------------


def _example_out(ex) -> ExampleOut:  # type: ignore[no-untyped-def]
    return ExampleOut(
        id=ex.id,
        dataset_id=ex.dataset_id,
        kind=ex.kind,
        input_text=ex.input_text,
        output_text=ex.output_text,
        quality_score=ex.quality_score,
        source_kind=ex.source_kind,
        language_tag=ex.language_tag,
        is_approved=ex.is_approved,
        approved_by=ex.approved_by,
        approved_at=ex.approved_at.isoformat() if ex.approved_at else None,
    )


def _job_out(job) -> JobOut:  # type: ignore[no-untyped-def]
    return JobOut(
        id=job.id,
        dataset_id=job.dataset_id,
        provider=job.provider,
        base_model_slug=job.base_model_slug,
        job_kind=job.job_kind,
        status=job.status,
        hyperparams=job.hyperparams,
        provider_job_id=job.provider_job_id,
        output_model_slug=job.output_model_slug,
        eval_metrics=job.eval_metrics,
        cost_usd=job.cost_usd,
    )
