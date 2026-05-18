// Social feed item — a heterogeneous entry that wraps the underlying actor +
// the action (review / check-in / badge unlock / follow). The presentation
// layer renders different cards per [kind].

import "package:freezed_annotation/freezed_annotation.dart";
import "package:silklens/domain/social/entities/user_profile.dart";

part "feed_item.freezed.dart";

enum FeedItemKind {
  review,
  checkIn,
  badgeUnlock,
  follow,
  comment,
}

@freezed
class FeedItem with _$FeedItem {
  const factory FeedItem({
    required String id,
    required FeedItemKind kind,
    required UserProfile actor,
    required DateTime createdAt,
    String? heritagePubId,
    String? heritageName,
    String? badgeSlug,
    String? badgeName,
    String? text,
    int? rating,
  }) = _FeedItem;
}
