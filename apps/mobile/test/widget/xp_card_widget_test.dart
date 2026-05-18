import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:mocktail/mocktail.dart";
import "package:silklens/core/utils/result.dart";
import "package:silklens/data/repositories/gamification_repository_impl.dart";
import "package:silklens/domain/gamification/entities/badge.dart";
import "package:silklens/domain/gamification/entities/leaderboard_entry.dart";
import "package:silklens/domain/gamification/entities/xp_summary.dart";
import "package:silklens/domain/gamification/repositories/gamification_repository.dart";
import "package:silklens/presentation/pages/gamification/xp_card.dart";

import "test_helpers.dart";

class _Repo extends Mock implements GamificationRepository {}

void main() {
  testWidgets("XpCard renders progress when data is available",
      (WidgetTester tester) async {
    final repo = _Repo();
    when(() => repo.xpSummary()).thenAnswer(
      (_) async => const Success<XpSummary>(
        XpSummary(
          totalXp: 450,
          level: 3,
          xpIntoCurrentLevel: 50,
          xpForNextLevel: 100,
          streakDays: 4,
        ),
      ),
    );
    when(() => repo.badges()).thenAnswer(
      (_) async => const Success<List<Badge>>(<Badge>[]),
    );
    when(() => repo.leaderboard(
          scope: any(named: "scope"),
          page: any(named: "page"),
          pageSize: any(named: "pageSize"),
        )).thenAnswer((_) async => const Success<List<LeaderboardEntry>>(<LeaderboardEntry>[]));

    await tester.pumpWidget(
      wrapForWidgetTest(
        const XpCard(),
        overrides: <Override>[
          gamificationRepositoryProvider.overrideWithValue(repo),
        ],
      ),
    );

    expect(find.byKey(const Key("gamification.xp_card")), findsOneWidget);
    await tester.pumpAndSettle();
    expect(find.textContaining("450 XP"), findsOneWidget);
    expect(find.byType(LinearProgressIndicator), findsOneWidget);
  });
}
