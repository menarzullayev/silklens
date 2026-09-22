"""Virtual-tour domain errors."""
# ruff: noqa: N818

from __future__ import annotations


class VirtualTourError(Exception):
    code: str = "virtual_tour.unknown"
    status_code: int = 400


class TourNotFound(VirtualTourError):
    code = "virtual_tour.not_found"
    status_code = 404

    def __init__(self, slug: str) -> None:
        super().__init__(f"virtual tour '{slug}' not found")
        self.slug = slug


class TourNotPublished(VirtualTourError):
    code = "virtual_tour.not_published"
    status_code = 422

    def __init__(self, slug: str) -> None:
        super().__init__(f"virtual tour '{slug}' is not published")
        self.slug = slug


class DuplicateTourSlug(VirtualTourError):
    code = "virtual_tour.duplicate_slug"
    status_code = 409

    def __init__(self, slug: str) -> None:
        super().__init__(f"slug '{slug}' is already taken")
        self.slug = slug


class InvalidTourTransition(VirtualTourError):
    code = "virtual_tour.invalid_transition"
    status_code = 422

    def __init__(self, current: str, target: str) -> None:
        super().__init__(f"cannot transition tour from '{current}' to '{target}'")
        self.current = current
        self.target = target


class TourValidationError(VirtualTourError):
    code = "virtual_tour.validation_failed"
    status_code = 422

    def __init__(self, field: str, reason: str) -> None:
        super().__init__(f"{field}: {reason}")
        self.field = field
        self.reason = reason
