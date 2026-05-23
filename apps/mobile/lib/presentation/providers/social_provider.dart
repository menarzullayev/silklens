// SILK-0113..0116 — typed Riverpod providers for social features.
// All state is driven by SocialRepositoryImpl; no Map<String,dynamic> leaks
// into the presentation layer.

import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/data/repositories/social_repository_impl.dart';

// ---------------------------------------------------------------------------
// Activity Feed — FutureProvider with cursor-based pagination state
// ---------------------------------------------------------------------------

/// Flat list consumed by ActivityFeedPage.
final feedProvider = FutureProvider<List<Map<String, dynamic>>>((ref) async {
  final page = await ref.watch(socialRepositoryProvider).getFeed();
  return page.items.map((i) => i.toPageMap()).toList();
});

// ---------------------------------------------------------------------------
// Notifications — stateful notifier supporting mark-read + filter
// ---------------------------------------------------------------------------

class NotificationsState {
  const NotificationsState({
    this.items = const [],
    this.isLoading = false,
    this.error,
    this.hasMore = false,
  });

  final List<SocialNotificationItem> items;
  final bool isLoading;
  final String? error;
  final bool hasMore;

  NotificationsState copyWith({
    List<SocialNotificationItem>? items,
    bool? isLoading,
    String? error,
    bool clearError = false,
    bool? hasMore,
  }) =>
      NotificationsState(
        items: items ?? this.items,
        isLoading: isLoading ?? this.isLoading,
        error: clearError ? null : (error ?? this.error),
        hasMore: hasMore ?? this.hasMore,
      );
}

class NotificationsNotifier extends Notifier<NotificationsState> {
  @override
  NotificationsState build() {
    Future.microtask(refresh);
    return const NotificationsState(isLoading: true);
  }

  Future<void> refresh({bool unreadOnly = false}) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final page =
          await ref.read(socialRepositoryProvider).getNotifications(unreadOnly: unreadOnly);
      state = state.copyWith(
        items: page.items,
        isLoading: false,
        hasMore: page.hasMore,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  Future<void> markRead(String id) async {
    try {
      await ref.read(socialRepositoryProvider).markRead(id);
      state = state.copyWith(
        items: state.items.map((n) => n.id == id ? n.copyWith(isRead: true) : n).toList(),
      );
    } catch (_) {
      // Optimistic update stays; silently ignore network failure.
    }
  }

  Future<void> markAllRead() async {
    try {
      await ref.read(socialRepositoryProvider).markAllRead();
      state = state.copyWith(
        items: state.items.map((n) => n.copyWith(isRead: true)).toList(),
      );
    } catch (_) {}
  }
}

final notificationsProvider = NotifierProvider<NotificationsNotifier, NotificationsState>(
  NotificationsNotifier.new,
);

/// Unread badge count — derived from notificationsProvider.
final unreadCountProvider = Provider<int>((ref) {
  return ref.watch(notificationsProvider).items.where((n) => !n.isRead).length;
});

// ---------------------------------------------------------------------------
// Following / Followers — family notifier with follow/unfollow mutation
// ---------------------------------------------------------------------------

class FollowingListState {
  const FollowingListState({
    this.following = const [],
    this.followers = const [],
    this.isLoading = false,
    this.error,
  });

  final List<UserRef> following;
  final List<UserRef> followers;
  final bool isLoading;
  final String? error;

  FollowingListState copyWith({
    List<UserRef>? following,
    List<UserRef>? followers,
    bool? isLoading,
    String? error,
    bool clearError = false,
  }) =>
      FollowingListState(
        following: following ?? this.following,
        followers: followers ?? this.followers,
        isLoading: isLoading ?? this.isLoading,
        error: clearError ? null : (error ?? this.error),
      );
}

class FollowingListNotifier extends FamilyNotifier<FollowingListState, String> {
  @override
  FollowingListState build(String userPubId) {
    Future.microtask(() => _load(userPubId));
    return const FollowingListState(isLoading: true);
  }

  Future<void> _load(String userPubId) async {
    if (userPubId.isEmpty) {
      state = const FollowingListState();
      return;
    }
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final repo = ref.read(socialRepositoryProvider);
      final results = await Future.wait([
        repo.getFollowing(userPubId),
        repo.getFollowers(userPubId),
      ]);
      state = state.copyWith(
        following: results[0],
        followers: results[1],
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<void> follow(String pubId) async {
    try {
      await ref.read(socialRepositoryProvider).follow(pubId);
      // Optimistically mark as following in the followers list
      state = state.copyWith(
        followers: state.followers
            .map((u) => u.pubId == pubId ? u.copyWith(isFollowing: true) : u)
            .toList(),
      );
    } catch (_) {}
  }

  Future<void> unfollow(String pubId) async {
    try {
      await ref.read(socialRepositoryProvider).unfollow(pubId);
      state = state.copyWith(
        following: state.following.where((u) => u.pubId != pubId).toList(),
        followers: state.followers
            .map(
              (u) => u.pubId == pubId ? u.copyWith(isFollowing: false) : u,
            )
            .toList(),
      );
    } catch (_) {}
  }

  Future<void> reload(String userPubId) => _load(userPubId);
}

final followingListProvider =
    NotifierProviderFamily<FollowingListNotifier, FollowingListState, String>(
  FollowingListNotifier.new,
);

// ---------------------------------------------------------------------------
// Friend Invite — stateful notifier (token + expiry)
// ---------------------------------------------------------------------------

class FriendInviteState {
  const FriendInviteState({
    this.token,
    this.expiresAt,
    this.isLoading = false,
    this.error,
  });

  final String? token;
  final String? expiresAt;
  final bool isLoading;
  final String? error;

  FriendInviteState copyWith({
    String? token,
    String? expiresAt,
    bool? isLoading,
    String? error,
    bool clearError = false,
  }) =>
      FriendInviteState(
        token: token ?? this.token,
        expiresAt: expiresAt ?? this.expiresAt,
        isLoading: isLoading ?? this.isLoading,
        error: clearError ? null : (error ?? this.error),
      );
}

class FriendInviteNotifier extends Notifier<FriendInviteState> {
  @override
  FriendInviteState build() {
    Future.microtask(createInvite);
    return const FriendInviteState(isLoading: true);
  }

  Future<void> createInvite({String? message}) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final inv = await ref.read(socialRepositoryProvider).createInvitation(message: message);
      state = state.copyWith(
        token: inv.token,
        expiresAt: inv.expiresAt,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }
}

final friendInviteProvider = NotifierProvider<FriendInviteNotifier, FriendInviteState>(
  FriendInviteNotifier.new,
);
