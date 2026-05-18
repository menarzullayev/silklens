# ruff: noqa: N818
"""Partnership domain errors."""

from __future__ import annotations


class PartnershipError(Exception):
    """Base class for partnership domain errors."""


class AgreementNotFound(PartnershipError):
    def __init__(self, agreement_id: object) -> None:
        super().__init__(f"Partnership agreement not found: {agreement_id}")


class TierNotFound(PartnershipError):
    def __init__(self, tier_slug: str) -> None:
        super().__init__(f"Partnership tier not found: {tier_slug!r}")


class InvalidStatusTransition(PartnershipError):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(f"Cannot transition agreement from {current!r} to {target!r}")


class BadgeAlreadyIssued(PartnershipError):
    def __init__(self, agreement_id: object, badge_kind: str) -> None:
        super().__init__(f"Active badge {badge_kind!r} already issued for agreement {agreement_id}")


class InvalidMouUrl(PartnershipError):
    def __init__(self, url: str) -> None:
        super().__init__(f"MOU URL must start with https://: {url!r}")
