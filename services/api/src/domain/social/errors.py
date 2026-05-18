"""Social-domain errors."""
# ruff: noqa: N818

from __future__ import annotations


class SocialError(Exception):
    code: str = "social.unknown"
    status_code: int = 400


class UserNotFound(SocialError):
    code = "social.user_not_found"
    status_code = 404

    def __init__(self, pub_id: str) -> None:
        super().__init__(f"user '{pub_id}' not found")
        self.pub_id = pub_id


class CannotFollowSelf(SocialError):
    code = "social.cannot_follow_self"
    status_code = 422


class AlreadyFollowing(SocialError):
    code = "social.already_following"
    status_code = 409


class NotFollowing(SocialError):
    code = "social.not_following"
    status_code = 404


class CannotBlockSelf(SocialError):
    code = "social.cannot_block_self"
    status_code = 422


class CannotInviteSelf(SocialError):
    code = "social.cannot_invite_self"
    status_code = 422


class InvitationInvalid(SocialError):
    code = "social.invitation_invalid"
    status_code = 404


class InvitationExpired(SocialError):
    code = "social.invitation_expired"
    status_code = 410


class TargetRequired(SocialError):
    code = "social.target_required"
    status_code = 422

    def __init__(self) -> None:
        super().__init__("target_pub_id or target_email is required")


class BlockedByTarget(SocialError):
    code = "social.blocked_by_target"
    status_code = 403
