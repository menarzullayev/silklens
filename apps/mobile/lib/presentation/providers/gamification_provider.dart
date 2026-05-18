// Gamification state: XP / badges / leaderboard.

import "package:flutter/foundation.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/data/repositories/gamification_repository_impl.dart";
import "package:silklens/domain/gamification/entities/badge.dart";
import "package:silklens/domain/gamification/entities/leaderboard_entry.dart";
import "package:silklens/domain/gamification/entities/xp_summary.dart";

class XpSummaryController extends AsyncNotifier<XpSummary?> {
  @override
  Future<XpSummary?> build() async {
    final repo = ref.read(gamificationRepositoryProvider);
    final result = await repo.xpSummary();
    return result.successOrNull;
  }

  Future<void> refresh() async {
    state = const AsyncValue<XpSummary?>.loading();
    state = AsyncValue<XpSummary?>.data(await build());
  }
}

final AsyncNotifierProvider<XpSummaryController, XpSummary?>
    xpSummaryProvider = AsyncNotifierProvider<XpSummaryController, XpSummary?>(
  XpSummaryController.new,
  name: "xpSummaryProvider",
);

class BadgesController extends AsyncNotifier<List<Badge>> {
  @override
  Future<List<Badge>> build() async {
    final repo = ref.read(gamificationRepositoryProvider);
    final result = await repo.badges();
    return result.successOrNull ?? const <Badge>[];
  }
}

final AsyncNotifierProvider<BadgesController, List<Badge>> badgesProvider =
    AsyncNotifierProvider<BadgesController, List<Badge>>(
  BadgesController.new,
  name: "badgesProvider",
);

/// Listener fires when a new badge is unlocked — wire to a Lottie / animation
/// at the page level. Returns the slug of the newest unlock or `null`.
final StateProvider<String?> newlyUnlockedBadgeProvider =
    StateProvider<String?>(
  (Ref ref) {
    ref.listen<AsyncValue<List<Badge>>>(badgesProvider,
        (AsyncValue<List<Badge>>? prev, AsyncValue<List<Badge>> next) {
      final prevList = prev?.valueOrNull ?? const <Badge>[];
      final nextList = next.valueOrNull ?? const <Badge>[];
      final prevSlugs = prevList
          .where((Badge b) => b.isUnlocked)
          .map((Badge b) => b.slug)
          .toSet();
      for (final Badge b in nextList) {
        if (b.isUnlocked && !prevSlugs.contains(b.slug)) {
          ref.controller.state = b.slug;
          return;
        }
      }
    });
    return null;
  },
  name: "newlyUnlockedBadgeProvider",
);

@immutable
class LeaderboardState {
  const LeaderboardState({
    required this.scope,
    required this.entries,
    this.isLoading = false,
  });

  final LeaderboardScope scope;
  final List<LeaderboardEntry> entries;
  final bool isLoading;

  LeaderboardState copyWith({
    LeaderboardScope? scope,
    List<LeaderboardEntry>? entries,
    bool? isLoading,
  }) =>
      LeaderboardState(
        scope: scope ?? this.scope,
        entries: entries ?? this.entries,
        isLoading: isLoading ?? this.isLoading,
      );
}

class LeaderboardController extends Notifier<LeaderboardState> {
  @override
  LeaderboardState build() => const LeaderboardState(
        scope: LeaderboardScope.weekly,
        entries: <LeaderboardEntry>[],
      );

  Future<void> setScope(LeaderboardScope scope) async {
    state = state.copyWith(scope: scope, isLoading: true);
    final repo = ref.read(gamificationRepositoryProvider);
    final result = await repo.leaderboard(scope: scope);
    state = state.copyWith(
      entries: result.successOrNull ?? const <LeaderboardEntry>[],
      isLoading: false,
    );
  }

  Future<void> refresh() => setScope(state.scope);
}

final NotifierProvider<LeaderboardController, LeaderboardState>
    leaderboardControllerProvider =
    NotifierProvider<LeaderboardController, LeaderboardState>(
  LeaderboardController.new,
  name: "leaderboardControllerProvider",
);
