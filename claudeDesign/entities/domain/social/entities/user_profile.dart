// Lightweight projection of another user's public profile.
//
// Backend returns the canonical user under their `pub_id` (UUIDv7) — we never
// expose the residency-partitioned internal id outside the server.

class UserProfile {
  const UserProfile({
    required this.pubId,
    this.displayName,
    this.avatarUrl,
    this.bio,
    this.countryCode,
    this.followersCount = 0,
    this.followingCount = 0,
    this.isFollowing = false,
  });

  factory UserProfile.fromJson(Map<String, dynamic> j) => UserProfile(
        pubId: j['pub_id'] as String? ?? '',
        displayName: j['display_name'] as String?,
        avatarUrl: j['avatar_url'] as String?,
        bio: j['bio'] as String?,
        countryCode: j['country_code'] as String?,
      );
  final String pubId;
  final String? displayName;
  final String? avatarUrl;
  final String? bio;
  final String? countryCode;
  final int followersCount;
  final int followingCount;
  final bool isFollowing;
}
