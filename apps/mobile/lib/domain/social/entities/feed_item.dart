// Social feed item — a heterogeneous entry that wraps the underlying actor +
// the action (review / check-in / badge unlock / follow). The presentation
// layer renders different cards per [kind].

enum FeedItemKind { review, checkIn, badgeUnlock, follow, comment, story }

class FeedItem {
  const FeedItem({
    required this.id,
    required this.kind,
    required this.actorName,
    required this.timestamp,
    this.actorAvatarUrl,
    this.actorCountryCode,
    this.placeId,
    this.placeName,
    this.photoUrls = const [],
    this.likesCount = 0,
    this.commentsCount = 0,
    this.isLiked = false,
    this.isBookmarked = false,
    this.xpEarned,
    this.badgeName,
  });

  factory FeedItem.fromJson(Map<String, dynamic> j) => FeedItem(
        id: j['id'] as String,
        kind: FeedItemKind.values.firstWhere(
          (k) => k.name == j['kind'],
          orElse: () => FeedItemKind.checkIn,
        ),
        actorName: j['actor_name'] as String,
        timestamp: DateTime.parse(j['timestamp'] as String),
        actorAvatarUrl: j['actor_avatar_url'] as String?,
        actorCountryCode: j['actor_country_code'] as String?,
        placeId: j['place_id'] as String?,
        placeName: j['place_name'] as String?,
        photoUrls: (j['photo_urls'] as List?)?.cast<String>() ?? [],
        likesCount: j['likes_count'] as int? ?? 0,
        commentsCount: j['comments_count'] as int? ?? 0,
        isLiked: j['is_liked'] as bool? ?? false,
        isBookmarked: j['is_bookmarked'] as bool? ?? false,
        xpEarned: j['xp_earned'] as int?,
        badgeName: j['badge_name'] as String?,
      );

  final String id;
  final FeedItemKind kind;
  final String actorName;
  final DateTime timestamp;
  final String? actorAvatarUrl;
  final String? actorCountryCode;
  final String? placeId;
  final String? placeName;
  final List<String> photoUrls;
  final int likesCount;
  final int commentsCount;
  final bool isLiked;
  final bool isBookmarked;
  final int? xpEarned;
  final String? badgeName;
}
