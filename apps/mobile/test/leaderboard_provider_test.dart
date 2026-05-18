// Unit tests for [LeaderboardController].

import "package:flutter_test/flutter_test.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:mocktail/mocktail.dart";
import "package:silklens/core/utils/result.dart";
import "package:silklens/data/repositories/gamification_repository_impl.dart";
import "package:silklens/domain/gamification/entities/leaderboard_entry.dart";
import "package:silklens/domain/gamification/repositories/gamification_repository.dart";
import "package:silklens/presentation/providers/gamification_provider.dart";

class _MockRepo extends Mock implements GamificationRepository {}

void main() {
  const sample = <LeaderboardEntry>[
    LeaderboardEntry(rank: 1, userPubId: "u1", displayName: "Alice", score: 1200),
    LeaderboardEntry(rank: 2, userPubId: "u2", displayName: "Bob", score: 900),
  ];

  test("setScope loads entries and updates state", () async {
    final repo = _MockRepo();
    when(() => repo.leaderboard(
          scope: LeaderboardScope.weekly,
          page: any(named: "page"),
          pageSize: any(named: "pageSize"),
        )).thenAnswer((_) async => const Success<List<LeaderboardEntry>>(sample));

    final container = ProviderContainer(
      overrides: <Override>[gamificationRepositoryProvider.overrideWithValue(repo)],
    );
    await container
        .read(leaderboardControllerProvider.notifier)
        .setScope(LeaderboardScope.weekly);

    final state = container.read(leaderboardControllerProvider);
    expect(state.scope, LeaderboardScope.weekly);
    expect(state.entries, hasLength(2));
    expect(state.isLoading, isFalse);
  });

  test("setScope to friends scope hits backend with friends slug", () async {
    final repo = _MockRepo();
    when(() => repo.leaderboard(
          scope: any(named: "scope"),
          page: any(named: "page"),
          pageSize: any(named: "pageSize"),
        )).thenAnswer((_) async => const Success<List<LeaderboardEntry>>(<LeaderboardEntry>[]));

    final container = ProviderContainer(
      overrides: <Override>[gamificationRepositoryProvider.overrideWithValue(repo)],
    );
    await container
        .read(leaderboardControllerProvider.notifier)
        .setScope(LeaderboardScope.friends);

    verify(() => repo.leaderboard(
          scope: LeaderboardScope.friends,
          page: any(named: "page"),
          pageSize: any(named: "pageSize"),
        )).called(1);
  });
}
