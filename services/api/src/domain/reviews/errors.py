"""Review-domain errors."""
# ruff: noqa: N818

from __future__ import annotations


class ReviewError(Exception):
    code: str = "review.unknown"
    status_code: int = 400


class ReviewNotFound(ReviewError):
    code = "review.not_found"
    status_code = 404


class HeritageNotFoundForReview(ReviewError):
    code = "review.heritage_not_found"
    status_code = 404


class DuplicateReview(ReviewError):
    code = "review.duplicate"
    status_code = 409


class InvalidRating(ReviewError):
    code = "review.invalid_rating"
    status_code = 422


class UnknownReactionType(ReviewError):
    code = "review.unknown_reaction"
    status_code = 422


class CommentParentNotFound(ReviewError):
    code = "review.comment_parent_not_found"
    status_code = 404


class CommentDepthExceeded(ReviewError):
    code = "review.comment_depth_exceeded"
    status_code = 422


class InvalidVote(ReviewError):
    code = "review.invalid_vote"
    status_code = 422
