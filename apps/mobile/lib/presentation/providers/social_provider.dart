import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/data/repositories/social_repository_impl.dart';

// ---------------------------------------------------------------------------
// Feed — FutureProvider (used by ActivityFeedPage)
// ---------------------------------------------------------------------------

final feedProvider =
    FutureProvider<List<Map<String, dynamic>>>((ref) async {
  final repo = ref.watch(socialRepositoryProvider);
  final data = await repo.getFeed();
  return ((data['items'] as List?) ?? []).cast<Map<String, dynamic>>();
});

// ---------------------------------------------------------------------------
// Following list for a given pub_id
// ---------------------------------------------------------------------------

final followingProvider = FutureProvider.family<
    List<Map<String, dynamic>>, String>((ref, pubId) async {
  final repo = ref.watch(socialRepositoryProvider);
  final data = await repo.getFollowing(pubId);
  return ((data['items'] as List?) ?? []).cast<Map<String, dynamic>>();
});

// ---------------------------------------------------------------------------
// Followers list for a given pub_id
// ---------------------------------------------------------------------------

final followersProvider = FutureProvider.family<
    List<Map<String, dynamic>>, String>((ref, pubId) async {
  final repo = ref.watch(socialRepositoryProvider);
  final data = await repo.getFollowers(pubId);
  return ((data['items'] as List?) ?? []).cast<Map<String, dynamic>>();
});

// ---------------------------------------------------------------------------
// Notifications — stateful notifier supporting mark-read
// ---------------------------------------------------------------------------

class NotificationsNotifier
    extends Notifier<List<Map<String, dynamic>>> {
  @override
  List<Map<String, dynamic>> build() {
    Future.microtask(refresh);
    return [];
  }

  Future<void> refresh() async {
    try {
      final repo = ref.read(socialRepositoryProvider);
      final data = await repo.getNotifications();
      state = ((data['items'] as List?) ?? [])
          .cast<Map<String, dynamic>>();
    } catch (_) {
      // Silently keep previous state on network error.
    }
  }

  Future<void> markRead(String id) async {
    try {
      await ref.read(socialRepositoryProvider).markRead(id);
      state = state
          .map((n) => n['id'] == id ? {...n, 'is_read': true} : n)
          .toList();
    } catch (_) {}
  }

  Future<void> markAllRead() async {
    try {
      await ref.read(socialRepositoryProvider).markAllRead();
      state = state.map((n) => {...n, 'is_read': true}).toList();
    } catch (_) {}
  }
}

final notificationsProvider =
    NotifierProvider<NotificationsNotifier, List<Map<String, dynamic>>>(
  NotificationsNotifier.new,
);

final unreadCountProvider = Provider<int>((ref) {
  final notifs = ref.watch(notificationsProvider);
  return notifs.where((n) => n['is_read'] != true).length;
});

// ---------------------------------------------------------------------------
// Friend Invite — stateful notifier for token + expiry
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

  Future<void> createInvite() async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final data =
          await ref.read(socialRepositoryProvider).createInvite();
      state = state.copyWith(
        token: data['token'] as String?,
        expiresAt: data['expires_at'] as String?,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }
}

final friendInviteProvider =
    NotifierProvider<FriendInviteNotifier, FriendInviteState>(
  FriendInviteNotifier.new,
);

// ---------------------------------------------------------------------------
// Following list with follow/unfollow mutation — stateful notifier
// ---------------------------------------------------------------------------

class FollowingListState {
  const FollowingListState({
    this.following = const [],
    this.followers = const [],
    this.isLoading = false,
    this.error,
  });

  final List<Map<String, dynamic>> following;
  final List<Map<String, dynamic>> followers;
  final bool isLoading;
  final String? error;

  FollowingListState copyWith({
    List<Map<String, dynamic>>? following,
    List<Map<String, dynamic>>? followers,
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

class FollowingListNotifier
    extends FamilyNotifier<FollowingListState, String> {
  @override
  FollowingListState build(String userPubId) {
    Future.microtask(() => _load(userPubId));
    return const FollowingListState(isLoading: true);
  }

  Future<void> _load(String userPubId) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final repo = ref.read(socialRepositoryProvider);
      final followingData = await repo.getFollowing(userPubId, limit: 50);
      final followersData = await repo.getFollowers(userPubId, limit: 50);
      state = state.copyWith(
        following: ((followingData['items'] as List?) ?? [])
            .cast<Map<String, dynamic>>(),
        followers: ((followersData['items'] as List?) ?? [])
            .cast<Map<String, dynamic>>(),
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
        followers: state.followers.map((u) {
          if (u['pub_id'] == pubId) return {...u, 'is_following': true};
          return u;
        }).toList(),
      );
    } catch (_) {}
  }

  Future<void> unfollow(String pubId) async {
    try {
      await ref.read(socialRepositoryProvider).unfollow(pubId);
      // Remove from following list + update followers list
      state = state.copyWith(
        following:
            state.following.where((u) => u['pub_id'] != pubId).toList(),
        followers: state.followers.map((u) {
          if (u['pub_id'] == pubId) return {...u, 'is_following': false};
          return u;
        }).toList(),
      );
    } catch (_) {}
  }

  Future<void> reload(String userPubId) => _load(userPubId);
}

final followingListProvider = NotifierProviderFamily<FollowingListNotifier,
    FollowingListState, String>(
  FollowingListNotifier.new,
);
