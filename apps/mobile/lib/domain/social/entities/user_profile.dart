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
    this.xp = 0,
    this.levelNumber = 1,
    this.levelName,
    this.placesCount = 0,
  });

  factory UserProfile.fromJson(Map<String, dynamic> j) => UserProfile(
        pubId: j['pub_id'] as String? ?? '',
        displayName: j['display_name'] as String?,
        avatarUrl: j['avatar_url'] as String?,
        bio: j['bio'] as String?,
        countryCode: j['country_code'] as String?,
        followersCount: j['followers_count'] as int? ?? 0,
        followingCount: j['following_count'] as int? ?? 0,
        isFollowing: j['is_following'] as bool? ?? false,
        xp: j['xp'] as int? ?? 0,
        levelNumber: j['level_number'] as int? ?? 1,
        levelName: j['level_name'] as String?,
        placesCount: j['places_count'] as int? ?? 0,
      );

  final String pubId;
  final String? displayName;
  final String? avatarUrl;
  final String? bio;
  final String? countryCode;
  final int followersCount;
  final int followingCount;
  final bool isFollowing;
  final int xp;
  final int levelNumber;
  final String? levelName;
  final int placesCount;
}
