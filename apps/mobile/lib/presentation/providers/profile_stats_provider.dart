// SILK-0117 — Profile stats provider
//
// Loads XP balance + follower/following counts in parallel for the current
// user. Pages watch [profileStatsProvider]; never call Dio directly.

import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/data/api/clients/api_client_provider.dart';
import 'package:silklens/presentation/providers/auth_provider.dart';

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

class ProfileStats {
  const ProfileStats({
    this.xp = 0,
    this.followersCount = 0,
    this.followingCount = 0,
    this.placesVisited = 0,
    this.isLoading = false,
    this.error,
  });

  final int xp;
  final int followersCount;
  final int followingCount;
  final int placesVisited;
  final bool isLoading;
  final String? error;

  ProfileStats copyWith({
    int? xp,
    int? followersCount,
    int? followingCount,
    int? placesVisited,
    bool? isLoading,
    String? error,
    bool clearError = false,
  }) =>
      ProfileStats(
        xp: xp ?? this.xp,
        followersCount: followersCount ?? this.followersCount,
        followingCount: followingCount ?? this.followingCount,
        placesVisited: placesVisited ?? this.placesVisited,
        isLoading: isLoading ?? this.isLoading,
        error: clearError ? null : (error ?? this.error),
      );
}

// ---------------------------------------------------------------------------
// Notifier
// ---------------------------------------------------------------------------

class ProfileStatsNotifier extends Notifier<ProfileStats> {
  @override
  ProfileStats build() {
    final user = ref.watch(currentUserProvider);
    if (user != null) {
      Future.microtask(() => load(user.pubId));
    }
    return const ProfileStats(isLoading: true);
  }

  Future<void> load(String pubId) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final client = ref.read(silkLensApiClientProvider);

      // Fetch XP, followers and following in parallel.
      final results = await Future.wait([
        client.getXpBalance(),
        client.getFollowers(pubId, limit: 1),
        client.getFollowing(pubId, limit: 1),
      ]);

      final xpData = results[0];
      final followersData = results[1];
      final followingData = results[2];

      final xp = (xpData['balance'] as num?)?.toInt() ??
          (xpData['xp'] as num?)?.toInt() ??
          0;
      final followersCount =
          (followersData['total'] as num?)?.toInt() ?? 0;
      final followingCount =
          (followingData['total'] as num?)?.toInt() ?? 0;
      // places_visited may be returned alongside XP in future; default 0.
      final places =
          (xpData['places_visited'] as num?)?.toInt() ?? 0;

      state = ProfileStats(
        xp: xp,
        followersCount: followersCount,
        followingCount: followingCount,
        placesVisited: places,
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<void> refresh(String pubId) => load(pubId);
}

final profileStatsProvider =
    NotifierProvider<ProfileStatsNotifier, ProfileStats>(
  ProfileStatsNotifier.new,
);
