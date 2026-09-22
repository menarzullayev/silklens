# ruff: noqa: N818
"""Fundraising domain errors."""

from __future__ import annotations


class FundraisingError(Exception):
    """Base class for fundraising domain errors."""


class InvestorNotFound(FundraisingError):
    def __init__(self, investor_id: object) -> None:
        super().__init__(f"Investor not found: {investor_id}")


class RoundNotFound(FundraisingError):
    def __init__(self, round_id: object) -> None:
        super().__init__(f"Fundraising round not found: {round_id}")


class DocumentNotFound(FundraisingError):
    def __init__(self, document_id: object) -> None:
        super().__init__(f"Data-room document not found: {document_id}")


class DuplicateCommitment(FundraisingError):
    def __init__(self, investor_id: object, round_id: object) -> None:
        super().__init__(
            f"Commitment already exists for investor {investor_id} in round {round_id}"
        )


class InvalidStatusTransition(FundraisingError):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(f"Cannot transition from {current!r} to {target!r}")
