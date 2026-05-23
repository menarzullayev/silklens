// SILK-0113..0116 — typed social repository with DTOs.
// Domain layer (domain/social/) stays pure Dart; this data layer is the only
// place that imports SilkLensApiClient.

import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/data/api/clients/api_client_provider.dart';
import 'package:silklens/data/api/clients/silklens_api_client.dart';

// ---------------------------------------------------------------------------
// DTOs — kept in this file; no separate dto file needed for social (simple
// types, not generated from retrofit).
// ---------------------------------------------------------------------------

class SocialFeedItem {
  const SocialFeedItem({
    required this.id,
    required this.verb,
    required this.actorPubId,
    required this.actorDisplayName,
    required this.createdAt,
    this.actorAvatarUrl,
    this.targetKind,
    this.targetId,
    this.targetName,
    this.mediaUrl,
    this.likeCount = 0,
    this.commentCount = 0,
    this.payload,
  });

  factory SocialFeedItem.fromJson(Map<String, dynamic> j) => SocialFeedItem(
        id: j['id'] as String? ?? '',
        verb: j['verb'] as String? ?? 'visit',
        actorPubId: j['actor_pub_id'] as String? ?? '',
        actorDisplayName:
            j['actor_display_name'] as String? ?? 'Anonymous',
        actorAvatarUrl: j['actor_avatar_url'] as String?,
        targetKind: j['target_kind'] as String?,
        targetId: j['target_id'] as String?,
        targetName: j['target_name'] as String?,
        mediaUrl: j['media_url'] as String?,
        createdAt: j['created_at'] as String? ?? '',
        likeCount: (j['like_count'] as num?)?.toInt() ?? 0,
        commentCount: (j['comment_count'] as num?)?.toInt() ?? 0,
        payload: j['payload'] as Map<String, dynamic>?,
      );

  // Convenience: produce the Map shape that legacy page widgets expect so we
  // can pass through without rewriting every sub-widget in one shot.
  Map<String, dynamic> toPageMap() => {
        'id': id,
        'verb': verb,
        'actor_pub_id': actorPubId,
        'actor_display_name': actorDisplayName,
        'actor_avatar_url': actorAvatarUrl,
        'target_kind': targetKind,
        'target_id': targetId,
        'target_name': targetName,
        'media_url': mediaUrl,
        'created_at': createdAt,
        'like_count': likeCount,
        'comment_count': commentCount,
        if (payload != null) ...payload!,
      };

  final String id;
  final String verb;
  final String actorPubId;
  final String actorDisplayName;
  final String? actorAvatarUrl;
  final String? targetKind;
  final String? targetId;
  final String? targetName;
  final String? mediaUrl;
  final String createdAt;
  final int likeCount;
  final int commentCount;
  final Map<String, dynamic>? payload;
}

class SocialFeedPage {
  const SocialFeedPage({required this.items, this.nextCursor});
  final List<SocialFeedItem> items;
  final String? nextCursor;
}

class UserRef {
  const UserRef({
    required this.pubId,
    this.displayName,
    this.username,
    this.avatarUrl,
    this.residencyRegion,
    this.levelNumber,
    this.levelName,
    this.isFollowing = false,
  });

  factory UserRef.fromJson(Map<String, dynamic> j) => UserRef(
        pubId: j['pub_id'] as String? ?? '',
        displayName: j['display_name'] as String?,
        username: j['username'] as String?,
        avatarUrl: j['avatar_url'] as String?,
        residencyRegion: j['residency_region'] as String?,
        levelNumber: (j['level_number'] as num?)?.toInt(),
        levelName: j['level_name'] as String?,
        isFollowing: j['is_following'] as bool? ?? false,
      );

  Map<String, dynamic> toPageMap() => {
        'pub_id': pubId,
        'display_name': displayName,
        'username': username,
        'avatar_url': avatarUrl,
        'residency_region': residencyRegion,
        'level_number': levelNumber,
        'level_name': levelName,
        'is_following': isFollowing,
      };

  final String pubId;
  final String? displayName;
  final String? username;
  final String? avatarUrl;
  final String? residencyRegion;
  final int? levelNumber;
  final String? levelName;
  final bool isFollowing;

  UserRef copyWith({bool? isFollowing}) => UserRef(
        pubId: pubId,
        displayName: displayName,
        username: username,
        avatarUrl: avatarUrl,
        residencyRegion: residencyRegion,
        levelNumber: levelNumber,
        levelName: levelName,
        isFollowing: isFollowing ?? this.isFollowing,
      );
}

class FriendInvitation {
  const FriendInvitation({
    required this.id,
    required this.token,
    required this.status,
    required this.expiresAt,
  });

  factory FriendInvitation.fromJson(Map<String, dynamic> j) =>
      FriendInvitation(
        id: j['id'] as String? ?? '',
        token: j['token'] as String? ?? '',
        status: j['status'] as String? ?? 'pending',
        expiresAt: j['expires_at'] as String? ?? '',
      );

  final String id;
  final String token;
  final String status;
  final String expiresAt;
}

class SocialNotificationItem {
  const SocialNotificationItem({
    required this.id,
    required this.category,
    required this.title,
    required this.body,
    required this.isRead,
    required this.createdAt,
    this.iconUrl,
    this.actionUrl,
  });

  factory SocialNotificationItem.fromJson(Map<String, dynamic> j) =>
      SocialNotificationItem(
        id: j['id'] as String? ?? '',
        // Backend uses category_slug; fallback to kind for legacy shape
        category:
            j['category_slug'] as String? ?? j['kind'] as String? ?? 'system',
        // Backend uses title; fallback to text/body for legacy shape
        title: j['title'] as String? ??
            j['text'] as String? ??
            j['body'] as String? ??
            '',
        body: j['body'] as String? ?? j['text'] as String? ?? '',
        iconUrl: j['icon_url'] as String?,
        actionUrl: j['action_url'] as String?,
        // read_at present → read; fallback to is_read bool for legacy shape
        isRead:
            j['read_at'] != null || (j['is_read'] as bool? ?? false),
        createdAt: j['created_at'] as String? ??
            j['timestamp'] as String? ??
            '',
      );

  Map<String, dynamic> toPageMap() => {
        'id': id,
        'kind': category,
        'category_slug': category,
        'title': title,
        'text': title,
        'body': body,
        'icon_url': iconUrl,
        'action_url': actionUrl,
        'is_read': isRead,
        'created_at': createdAt,
        'timestamp': createdAt,
      };

  final String id;
  final String category;
  final String title;
  final String body;
  final String? iconUrl;
  final String? actionUrl;
  final bool isRead;
  final String createdAt;

  SocialNotificationItem copyWith({bool? isRead}) =>
      SocialNotificationItem(
        id: id,
        category: category,
        title: title,
        body: body,
        iconUrl: iconUrl,
        actionUrl: actionUrl,
        isRead: isRead ?? this.isRead,
        createdAt: createdAt,
      );
}

class NotificationsPage {
  const NotificationsPage({
    required this.items,
    required this.hasMore,
    this.nextBefore,
  });
  final List<SocialNotificationItem> items;
  final bool hasMore;
  final String? nextBefore;
}

// ---------------------------------------------------------------------------
// SocialRepositoryImpl
// ---------------------------------------------------------------------------

class SocialRepositoryImpl {
  const SocialRepositoryImpl(this._client);

  final SilkLensApiClient _client;

  // Feed

  Future<SocialFeedPage> getFeed({int limit = 20, String? before}) async {
    final data = await _client.getSocialFeed(limit: limit, before: before);
    final items = (data['items'] as List?) ?? [];
    return SocialFeedPage(
      items: items
          .map((e) => SocialFeedItem.fromJson(e as Map<String, dynamic>))
          .toList(),
      nextCursor: data['next_cursor'] as String?,
    );
  }

  // Following / Followers

  Future<List<UserRef>> getFollowing(
    String pubId, {
    int limit = 50,
    int offset = 0,
  }) async {
    final data =
        await _client.getFollowing(pubId, limit: limit, offset: offset);
    final items = (data['items'] as List?) ?? [];
    return items
        .map((e) => UserRef.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<List<UserRef>> getFollowers(
    String pubId, {
    int limit = 50,
    int offset = 0,
  }) async {
    final data =
        await _client.getFollowers(pubId, limit: limit, offset: offset);
    final items = (data['items'] as List?) ?? [];
    return items
        .map((e) => UserRef.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<void> follow(String pubId) => _client.followUser(pubId);
  Future<void> unfollow(String pubId) => _client.unfollowUser(pubId);
  Future<void> block(String pubId, {String? reason}) =>
      _client.blockUser(pubId, reason: reason);
  Future<void> unblock(String pubId) => _client.unblockUser(pubId);

  // Friend Invitations

  Future<FriendInvitation> createInvitation({
    String? targetPubId,
    String? targetEmail,
    String? message,
  }) async {
    final data = await _client.createFriendInvite(
      targetPubId: targetPubId,
      targetEmail: targetEmail,
      message: message,
    );
    return FriendInvitation.fromJson(data);
  }

  Future<FriendInvitation> acceptInvitation(String token) async {
    final data = await _client.acceptFriendInvitation(token);
    return FriendInvitation.fromJson(data);
  }

  // Notifications

  Future<NotificationsPage> getNotifications({
    bool unreadOnly = false,
    int limit = 30,
    String? before,
  }) async {
    final data = await _client.getNotifications(
      unreadOnly: unreadOnly,
      limit: limit,
      before: before,
    );
    final items = (data['items'] as List?) ?? [];
    return NotificationsPage(
      items: items
          .map(
            (e) => SocialNotificationItem.fromJson(
              e as Map<String, dynamic>,
            ),
          )
          .toList(),
      hasMore: (data['has_more'] as bool?) ?? false,
      nextBefore: data['next_before'] as String?,
    );
  }

  Future<void> markRead(String notificationId) async {
    await _client.markNotificationRead(notificationId);
  }

  Future<int> markAllRead() async {
    final data = await _client.markAllNotificationsRead();
    return (data['updated'] as num?)?.toInt() ?? 0;
  }
}

final socialRepositoryProvider = Provider<SocialRepositoryImpl>((ref) {
  return SocialRepositoryImpl(ref.watch(silkLensApiClientProvider));
});
