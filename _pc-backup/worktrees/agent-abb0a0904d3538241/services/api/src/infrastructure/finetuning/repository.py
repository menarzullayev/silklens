"""SQLAlchemy implementation of FinetuningRepository."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.finetuning.entities import (
    DatasetPurpose,
    DatasetStatus,
    ExampleKind,
    ExampleSourceKind,
    FinetuningDataset,
    FinetuningExample,
    FinetuningJob,
    JobKind,
    JobProvider,
    JobStatus,
    TargetModelKind,
)


def _row_to_dataset(row: dict) -> FinetuningDataset:
    return FinetuningDataset(
        id=row["id"],
        tenant_id=row["tenant_id"],
        slug=row["slug"],
        name=row["name"] if isinstance(row["name"], dict) else {},
        description_md=row.get("description_md"),
        purpose=DatasetPurpose(row["purpose"]),
        target_model_kind=TargetModelKind(row["target_model_kind"]),
        status=DatasetStatus(row["status"]),
        example_count=row["example_count"],
        min_quality_score=Decimal(str(row["min_quality_score"])),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_example(row: dict) -> FinetuningExample:
    return FinetuningExample(
        id=row["id"],
        dataset_id=row["dataset_id"],
        kind=ExampleKind(row["kind"]),
        input_text=row["input_text"],
        output_text=row["output_text"],
        input_metadata=row.get("input_metadata") or {},
        output_metadata=row.get("output_metadata") or {},
        quality_score=Decimal(str(row["quality_score"])) if row.get("quality_score") else None,
        source_kind=ExampleSourceKind(row["source_kind"]),
        source_id=row.get("source_id"),
        language_tag=row["language_tag"],
        is_approved=bool(row["is_approved"]),
        approved_by=row.get("approved_by"),
        approved_at=row.get("approved_at"),
        created_at=row["created_at"],
    )


def _row_to_job(row: dict) -> FinetuningJob:
    return FinetuningJob(
        id=row["id"],
        dataset_id=row["dataset_id"],
        provider=JobProvider(row["provider"]),
        base_model_slug=row["base_model_slug"],
        job_kind=JobKind(row["job_kind"]),
        status=JobStatus(row["status"]),
        hyperparams=row.get("hyperparams") or {},
        provider_job_id=row.get("provider_job_id"),
        started_at=row.get("started_at"),
        finished_at=row.get("finished_at"),
        output_model_slug=row.get("output_model_slug"),
        eval_metrics=row.get("eval_metrics") or {},
        cost_usd=Decimal(str(row["cost_usd"])) if row.get("cost_usd") else None,
        created_at=row["created_at"],
    )


class SqlFinetuningRepository:
    """Concrete async SQLAlchemy repository for the fine-tuning domain."""

    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    # ------------------------------------------------------------------
    # Datasets
    # ------------------------------------------------------------------

    async def list_datasets(self) -> list[FinetuningDataset]:
        rows = await self._db.execute(
            text(
                """
                SELECT id, tenant_id, slug, name, description_md, purpose,
                       target_model_kind, status, example_count, min_quality_score,
                       created_at, updated_at
                FROM finetuning_datasets
                ORDER BY created_at ASC
                """
            )
        )
        return [_row_to_dataset(dict(r._mapping)) for r in rows]

    async def get_dataset_by_slug(self, slug: str) -> FinetuningDataset | None:
        row = await self._db.execute(
            text(
                """
                SELECT id, tenant_id, slug, name, description_md, purpose,
                       target_model_kind, status, example_count, min_quality_score,
                       created_at, updated_at
                FROM finetuning_datasets
                WHERE slug = :slug
                """
            ),
            {"slug": slug},
        )
        r = row.first()
        return _row_to_dataset(dict(r._mapping)) if r else None

    async def get_dataset_by_id(self, dataset_id: UUID) -> FinetuningDataset | None:
        row = await self._db.execute(
            text(
                """
                SELECT id, tenant_id, slug, name, description_md, purpose,
                       target_model_kind, status, example_count, min_quality_score,
                       created_at, updated_at
                FROM finetuning_datasets
                WHERE id = :dataset_id
                """
            ),
            {"dataset_id": dataset_id},
        )
        r = row.first()
        return _row_to_dataset(dict(r._mapping)) if r else None

    # ------------------------------------------------------------------
    # Examples
    # ------------------------------------------------------------------

    async def list_approved_examples(self, dataset_id: UUID) -> list[FinetuningExample]:
        rows = await self._db.execute(
            text(
                """
                SELECT id, dataset_id, kind, input_text, output_text,
                       input_metadata, output_metadata, quality_score,
                       source_kind, source_id, language_tag,
                       is_approved, approved_by, approved_at, created_at
                FROM finetuning_examples
                WHERE dataset_id = :dataset_id AND is_approved = true
                ORDER BY quality_score DESC NULLS LAST, created_at ASC
                """
            ),
            {"dataset_id": dataset_id},
        )
        return [_row_to_example(dict(r._mapping)) for r in rows]

    async def list_pending_examples(
        self, dataset_id: UUID, limit: int = 50
    ) -> list[FinetuningExample]:
        rows = await self._db.execute(
            text(
                """
                SELECT id, dataset_id, kind, input_text, output_text,
                       input_metadata, output_metadata, quality_score,
                       source_kind, source_id, language_tag,
                       is_approved, approved_by, approved_at, created_at
                FROM finetuning_examples
                WHERE dataset_id = :dataset_id AND is_approved = false
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            {"dataset_id": dataset_id, "limit": limit},
        )
        return [_row_to_example(dict(r._mapping)) for r in rows]

    async def add_example(
        self,
        *,
        dataset_id: UUID,
        kind: ExampleKind,
        input_text: str,
        output_text: str,
        source_kind: ExampleSourceKind,
        language_tag: str,
    ) -> FinetuningExample:
        row = await self._db.execute(
            text(
                """
                INSERT INTO finetuning_examples
                    (dataset_id, kind, input_text, output_text,
                     source_kind, language_tag)
                VALUES
                    (:dataset_id, :kind, :input_text, :output_text,
                     :source_kind, :language_tag)
                RETURNING id, dataset_id, kind, input_text, output_text,
                          input_metadata, output_metadata, quality_score,
                          source_kind, source_id, language_tag,
                          is_approved, approved_by, approved_at, created_at
                """
            ),
            {
                "dataset_id": dataset_id,
                "kind": kind,
                "input_text": input_text,
                "output_text": output_text,
                "source_kind": source_kind,
                "language_tag": language_tag,
            },
        )
        r = row.first()
        assert r is not None, "INSERT RETURNING must return a row"
        # Bump example_count on the dataset
        await self._db.execute(
            text(
                "UPDATE finetuning_datasets SET example_count = example_count + 1 "
                "WHERE id = :dataset_id"
            ),
            {"dataset_id": dataset_id},
        )
        return _row_to_example(dict(r._mapping))

    async def get_example(self, example_id: UUID) -> FinetuningExample | None:
        row = await self._db.execute(
            text(
                """
                SELECT id, dataset_id, kind, input_text, output_text,
                       input_metadata, output_metadata, quality_score,
                       source_kind, source_id, language_tag,
                       is_approved, approved_by, approved_at, created_at
                FROM finetuning_examples
                WHERE id = :example_id
                """
            ),
            {"example_id": example_id},
        )
        r = row.first()
        return _row_to_example(dict(r._mapping)) if r else None

    async def approve_example(self, example_id: UUID, *, approved_by: UUID) -> FinetuningExample:
        now = datetime.now(UTC)
        row = await self._db.execute(
            text(
                """
                UPDATE finetuning_examples
                SET is_approved = true,
                    approved_by = :approved_by,
                    approved_at = :now
                WHERE id = :example_id
                RETURNING id, dataset_id, kind, input_text, output_text,
                          input_metadata, output_metadata, quality_score,
                          source_kind, source_id, language_tag,
                          is_approved, approved_by, approved_at, created_at
                """
            ),
            {"example_id": example_id, "approved_by": approved_by, "now": now},
        )
        r = row.first()
        assert r is not None, "UPDATE RETURNING must return a row"
        return _row_to_example(dict(r._mapping))

    # ------------------------------------------------------------------
    # Jobs
    # ------------------------------------------------------------------

    async def create_job(
        self,
        *,
        dataset_id: UUID,
        provider: JobProvider,
        base_model_slug: str,
        job_kind: JobKind,
        hyperparams: dict,
    ) -> FinetuningJob:
        import json

        row = await self._db.execute(
            text(
                """
                INSERT INTO finetuning_jobs
                    (dataset_id, provider, base_model_slug, job_kind, hyperparams)
                VALUES
                    (:dataset_id, :provider, :base_model_slug, :job_kind,
                    CAST(:hyperparams AS jsonb))
                RETURNING id, dataset_id, provider, base_model_slug, job_kind, status,
                          hyperparams, provider_job_id, started_at, finished_at,
                          output_model_slug, eval_metrics, cost_usd, created_at
                """
            ),
            {
                "dataset_id": dataset_id,
                "provider": provider,
                "base_model_slug": base_model_slug,
                "job_kind": job_kind,
                "hyperparams": json.dumps(hyperparams),
            },
        )
        r = row.first()
        assert r is not None, "INSERT RETURNING must return a row"
        return _row_to_job(dict(r._mapping))

    async def get_job(self, job_id: UUID) -> FinetuningJob | None:
        row = await self._db.execute(
            text(
                """
                SELECT id, dataset_id, provider, base_model_slug, job_kind, status,
                       hyperparams, provider_job_id, started_at, finished_at,
                       output_model_slug, eval_metrics, cost_usd, created_at
                FROM finetuning_jobs
                WHERE id = :job_id
                """
            ),
            {"job_id": job_id},
        )
        r = row.first()
        return _row_to_job(dict(r._mapping)) if r else None
