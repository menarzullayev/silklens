"""Fine-tuning domain errors."""

from __future__ import annotations


class FinetuningError(Exception):
    status_code: int = 400
    code: str = "finetuning_error"

    def __init__(self, message: str = "") -> None:
        super().__init__(message)


class DatasetNotFoundError(FinetuningError):
    status_code = 404
    code = "dataset_not_found"

    def __init__(self, slug_or_id: str = "") -> None:
        super().__init__(f"Dataset not found: {slug_or_id}")


# Alias kept for backward compat within the package
DatasetNotFound = DatasetNotFoundError


class ExampleNotFoundError(FinetuningError):
    status_code = 404
    code = "example_not_found"

    def __init__(self, example_id: str = "") -> None:
        super().__init__(f"Example not found: {example_id}")


ExampleNotFound = ExampleNotFoundError


class JobNotFoundError(FinetuningError):
    status_code = 404
    code = "job_not_found"

    def __init__(self, job_id: str = "") -> None:
        super().__init__(f"Fine-tuning job not found: {job_id}")


JobNotFound = JobNotFoundError


class DatasetNotReadyError(FinetuningError):
    status_code = 409
    code = "dataset_not_ready"

    def __init__(self) -> None:
        super().__init__(
            "Dataset must be in 'ready' or 'curating' status to launch a training job."
        )


DatasetNotReady = DatasetNotReadyError


class AlreadyApprovedError(FinetuningError):
    status_code = 409
    code = "example_already_approved"

    def __init__(self) -> None:
        super().__init__("Example is already approved.")


AlreadyApproved = AlreadyApprovedError
