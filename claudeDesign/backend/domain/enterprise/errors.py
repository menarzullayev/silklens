"""Enterprise SLA domain errors."""

from __future__ import annotations


class EnterpriseDomainError(Exception):
    """Base class for enterprise domain errors."""


class TierNotFoundError(EnterpriseDomainError):
    def __init__(self, slug: str) -> None:
        super().__init__(f"SLA tier not found: {slug!r}")


class SubscriptionNotFoundError(EnterpriseDomainError):
    def __init__(self, account_id: object) -> None:
        super().__init__(f"No active subscription for account {account_id}")


class IncidentNotFoundError(EnterpriseDomainError):
    def __init__(self, incident_id: object) -> None:
        super().__init__(f"Incident not found: {incident_id}")


class IncidentAlreadyResolvedError(EnterpriseDomainError):
    def __init__(self, incident_id: object) -> None:
        super().__init__(f"Incident {incident_id} is already resolved")
