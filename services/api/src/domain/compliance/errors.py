"""Compliance-domain errors.

Names describe the condition (per identity-domain precedent), so we keep N818
silenced; the slugs surface to the client as ``compliance.<reason>`` codes.
"""
# ruff: noqa: N818

from __future__ import annotations


class ComplianceError(Exception):
    code: str = "compliance.unknown"
    status_code: int = 400


class LegalDocumentNotFound(ComplianceError):
    code = "compliance.legal_document_not_found"
    status_code = 404


class LegalDocumentVersionExists(ComplianceError):
    code = "compliance.legal_document_version_exists"
    status_code = 409


class ConsentNotFound(ComplianceError):
    code = "compliance.consent_not_found"
    status_code = 404


class GdprRequestNotFound(ComplianceError):
    code = "compliance.gdpr_request_not_found"
    status_code = 404


class DuplicateGdprRequest(ComplianceError):
    code = "compliance.duplicate_gdpr_request"
    status_code = 409


class DeletionAlreadyScheduled(ComplianceError):
    code = "compliance.deletion_already_scheduled"
    status_code = 409


class GracePeriodExpired(ComplianceError):
    code = "compliance.grace_period_expired"
    status_code = 410


class InvalidGdprState(ComplianceError):
    code = "compliance.invalid_gdpr_state"
    status_code = 409
