import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:mocktail/mocktail.dart";
import "package:silklens/core/utils/result.dart";
import "package:silklens/data/repositories/gamification_repository_impl.dart";
import "package:silklens/domain/gamification/entities/xp_summary.dart";
import "package:silklens/domain/gamification/repositories/gamification_repository.dart";
import "package:silklens/presentation/pages/gamification/streak_widget.dart";

import "test_helpers.dart";

class _Repo extends Mock implements GamificationRepository {
  @override
  Future<Result<XpSummary>> xpSummary() async => const Success<XpSummary>(
        XpSummary(
          totalXp: 100,
          level: 1,
          xpIntoCurrentLevel: 10,
          xpForNextLevel: 100,
          streakDays: 7,
        ),
      );
}

void main() {
  testWidgets("StreakWidget shows day count", (WidgetTester tester) async {
    final repo = _Repo();
    await tester.pumpWidget(
      wrapForWidgetTest(
        const StreakWidget(),
        overrides: <Override>[
          gamificationRepositoryProvider.overrideWithValue(repo),
        ],
      ),
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const Key("gamification.streak")), findsOneWidget);
    expect(find.textContaining("7"), findsOneWidget);
  });
}
