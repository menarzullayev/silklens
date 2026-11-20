"""Fine-tuning repository protocol — domain layer must not import SQLAlchemy (ADR-0003)."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.domain.finetuning.entities import (
    ExampleKind,
    ExampleSourceKind,
    FinetuningDataset,
    FinetuningExample,
    FinetuningJob,
    JobKind,
    JobProvider,
)


class FinetuningRepository(Protocol):
    async def list_datasets(self) -> list[FinetuningDataset]: ...

    async def get_dataset_by_slug(self, slug: str) -> FinetuningDataset | None: ...

    async def get_dataset_by_id(self, dataset_id: UUID) -> FinetuningDataset | None: ...

    async def list_approved_examples(self, dataset_id: UUID) -> list[FinetuningExample]: ...

    async def list_pending_examples(
        self, dataset_id: UUID, limit: int
    ) -> list[FinetuningExample]: ...

    async def add_example(
        self,
        *,
        dataset_id: UUID,
        kind: ExampleKind,
        input_text: str,
        output_text: str,
        source_kind: ExampleSourceKind,
        language_tag: str,
    ) -> FinetuningExample: ...

    async def get_example(self, example_id: UUID) -> FinetuningExample | None: ...

    async def approve_example(
        self, example_id: UUID, *, approved_by: UUID
    ) -> FinetuningExample: ...

    async def create_job(
        self,
        *,
        dataset_id: UUID,
        provider: JobProvider,
        base_model_slug: str,
        job_kind: JobKind,
        hyperparams: dict,
    ) -> FinetuningJob: ...

    async def get_job(self, job_id: UUID) -> FinetuningJob | None: ...
