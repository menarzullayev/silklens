// Lightweight projection of another user's public profile.
//
// Backend returns the canonical user under their `pub_id` (UUIDv7) — we never
// expose the residency-partitioned internal id outside the server.

import "package:freezed_annotation/freezed_annotation.dart";

part "user_profile.freezed.dart";

@freezed
class UserProfile with _$UserProfile {
  const factory UserProfile({
    required String pubId,
    required String displayName,
    String? handle,
    String? avatarUrl,
    String? bio,
    String? country,
    @Default(0) int followersCount,
    @Default(0) int followingCount,
    @Default(false) bool isFollowing,
  }) = _UserProfile;
}
