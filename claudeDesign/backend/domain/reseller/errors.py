"""Reseller-domain errors."""
# ruff: noqa: N818

from __future__ import annotations


class ResellerError(Exception):
    code: str = "reseller.unknown"
    status_code: int = 400


class ApplicationNotFound(ResellerError):
    code = "reseller.application_not_found"
    status_code = 404


class DuplicateApplication(ResellerError):
    code = "reseller.duplicate_application"
    status_code = 409


class AlreadyApproved(ResellerError):
    code = "reseller.already_approved"
    status_code = 409


class AlreadyDecided(ResellerError):
    code = "reseller.already_decided"
    status_code = 409


class InvalidApplicationStatus(ResellerError):
    code = "reseller.invalid_status"
    status_code = 422


class ResellerValidationError(ResellerError):
    code = "reseller.validation_failed"
    status_code = 422

    def __init__(self, field: str, reason: str) -> None:
        super().__init__(f"{field}: {reason}")
        self.field = field
        self.reason = reason


class TenantNotFound(ResellerError):
    code = "reseller.tenant_not_found"
    status_code = 404


class RevenueShareConflict(ResellerError):
    """Sum of active parent shares for a child would exceed 100%."""

    code = "reseller.revenue_share_conflict"
    status_code = 422
