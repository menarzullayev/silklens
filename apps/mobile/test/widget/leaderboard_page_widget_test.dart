import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:mocktail/mocktail.dart";
import "package:silklens/core/utils/result.dart";
import "package:silklens/data/repositories/gamification_repository_impl.dart";
import "package:silklens/domain/gamification/entities/leaderboard_entry.dart";
import "package:silklens/domain/gamification/repositories/gamification_repository.dart";
import "package:silklens/presentation/pages/gamification/leaderboard_page.dart";

import "test_helpers.dart";

class _Repo extends Mock implements GamificationRepository {}

void main() {
  testWidgets("LeaderboardPage renders entries from the API",
      (WidgetTester tester) async {
    final repo = _Repo();
    when(() => repo.leaderboard(
          scope: any(named: "scope"),
          page: any(named: "page"),
          pageSize: any(named: "pageSize"),
        )).thenAnswer((_) async => const Success<List<LeaderboardEntry>>(
          <LeaderboardEntry>[
            LeaderboardEntry(
              rank: 1,
              userPubId: "u1",
              displayName: "Alice",
              score: 1500,
            ),
          ],
        ));

    await tester.pumpWidget(
      wrapForWidgetTest(
        const LeaderboardPage(),
        overrides: <Override>[
          gamificationRepositoryProvider.overrideWithValue(repo),
        ],
      ),
    );

    await tester.pumpAndSettle();
    expect(find.text("Alice"), findsOneWidget);
    expect(find.textContaining("1500"), findsOneWidget);
  });
}
