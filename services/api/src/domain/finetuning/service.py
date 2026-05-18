"""Fine-tuning application service.

Coordinates dataset curation, example management, and job scaffolding.
All DB I/O goes through FinetuningRepository; actual provider API calls
are deferred (status=pending) and handled by a background worker.
"""

from __future__ import annotations

import json
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
from src.domain.finetuning.errors import (
    AlreadyApproved,
    DatasetNotFound,
    ExampleNotFound,
    JobNotFound,
)
from src.domain.finetuning.repository import FinetuningRepository


class FinetuningService:
    """Application service for the fine-tuning bounded context."""

    def __init__(self, *, repository: FinetuningRepository) -> None:
        self._repo = repository

    # ------------------------------------------------------------------
    # Dataset queries
    # ------------------------------------------------------------------

    async def list_datasets(self) -> list[FinetuningDataset]:
        """Return all fine-tuning datasets (admin operation)."""
        return await self._repo.list_datasets()

    async def get_dataset(self, slug: str) -> FinetuningDataset:
        """Return a single dataset by slug; raises DatasetNotFound if absent."""
        dataset = await self._repo.get_dataset_by_slug(slug)
        if dataset is None:
            raise DatasetNotFound(slug)
        return dataset

    # ------------------------------------------------------------------
    # Dataset export
    # ------------------------------------------------------------------

    async def export_dataset(
        self,
        dataset_id: UUID,
    ) -> str:
        """Export all approved examples as JSONL (OpenAI / Anthropic fine-tune format).

        Each line is a JSON object:
          {"messages": [{"role": "user", "content": <input>},
                        {"role": "assistant", "content": <output>}]}

        Only prompt_response and conversation examples map cleanly to the
        chat-messages format.  Classification and preference examples are
        emitted with a ``kind`` discriminator so downstream tooling can route
        them appropriately.
        """
        dataset = await self._repo.get_dataset_by_id(dataset_id)
        if dataset is None:
            raise DatasetNotFound(str(dataset_id))

        examples = await self._repo.list_approved_examples(dataset_id)

        lines: list[str] = []
        for ex in examples:
            if ex.kind in (ExampleKind.PROMPT_RESPONSE, ExampleKind.CONVERSATION):
                record = {
                    "messages": [
                        {"role": "user", "content": ex.input_text},
                        {"role": "assistant", "content": ex.output_text},
                    ]
                }
            else:
                record = {
                    "kind": ex.kind,
                    "input": ex.input_text,
                    "output": ex.output_text,
                    "language": ex.language_tag,
                }
            lines.append(json.dumps(record, ensure_ascii=False))

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Example management
    # ------------------------------------------------------------------

    async def add_manual_example(
        self,
        *,
        dataset_id: UUID,
        input_text: str,
        output_text: str,
        language: str = "uz",
        actor: UUID,  # reserved for audit log; passed to repo in future
    ) -> FinetuningExample:
        """Add a manually curated training example to a dataset."""
        dataset = await self._repo.get_dataset_by_id(dataset_id)
        if dataset is None:
            raise DatasetNotFound(str(dataset_id))

        return await self._repo.add_example(
            dataset_id=dataset_id,
            kind=ExampleKind.PROMPT_RESPONSE,
            input_text=input_text,
            output_text=output_text,
            source_kind=ExampleSourceKind.MANUAL,
            language_tag=language,
        )

    async def list_pending_examples(
        self,
        dataset_id: UUID,
        limit: int = 50,
    ) -> list[FinetuningExample]:
        """Return unapproved examples for curator review."""
        dataset = await self._repo.get_dataset_by_id(dataset_id)
        if dataset is None:
            raise DatasetNotFound(str(dataset_id))
        return await self._repo.list_pending_examples(dataset_id, limit)

    async def approve_example(
        self,
        example_id: UUID,
        *,
        actor: UUID,
    ) -> FinetuningExample:
        """Mark an example as approved; raises AlreadyApproved if already done."""
        example = await self._repo.get_example(example_id)
        if example is None:
            raise ExampleNotFound(str(example_id))
        if example.is_approved:
            raise AlreadyApproved()
        return await self._repo.approve_example(example_id, approved_by=actor)

    # ------------------------------------------------------------------
    # Job management (scaffolded; actual provider call deferred)
    # ------------------------------------------------------------------

    async def create_job(
        self,
        *,
        dataset_id: UUID,
        provider: JobProvider,
        base_model_slug: str,
        job_kind: JobKind,
        hyperparams: dict,
        actor: UUID,  # reserved for audit log; passed to repo in future
    ) -> FinetuningJob:
        """Scaffold a fine-tuning job (status=pending).

        The job is persisted immediately so the admin can track it;
        a background worker is responsible for submitting to the provider
        and updating status/provider_job_id.
        """
        dataset = await self._repo.get_dataset_by_id(dataset_id)
        if dataset is None:
            raise DatasetNotFound(str(dataset_id))

        return await self._repo.create_job(
            dataset_id=dataset_id,
            provider=provider,
            base_model_slug=base_model_slug,
            job_kind=job_kind,
            hyperparams=hyperparams,
        )

    async def get_job(self, job_id: UUID) -> FinetuningJob:
        """Return job status; raises JobNotFound if absent."""
        job = await self._repo.get_job(job_id)
        if job is None:
            raise JobNotFound(str(job_id))
        return job
