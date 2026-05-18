import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:mocktail/mocktail.dart";
import "package:silklens/core/utils/result.dart";
import "package:silklens/data/repositories/gamification_repository_impl.dart";
import "package:silklens/domain/gamification/entities/badge.dart" as gam;
import "package:silklens/domain/gamification/repositories/gamification_repository.dart";
import "package:silklens/presentation/pages/gamification/badges_page.dart";

import "test_helpers.dart";

class _Repo extends Mock implements GamificationRepository {}

void main() {
  testWidgets("BadgesPage renders a grid of badges",
      (WidgetTester tester) async {
    final repo = _Repo();
    when(() => repo.badges()).thenAnswer(
      (_) async => Success<List<gam.Badge>>(<gam.Badge>[
        gam.Badge(
          slug: "explorer",
          name: "Explorer",
          description: "Visited 5 sites",
          unlockedAt: DateTime.utc(2026),
        ),
        const gam.Badge(
          slug: "scholar",
          name: "Scholar",
          description: "Read 50 facts",
          criterionHint: "50 facts",
        ),
      ]),
    );

    await tester.pumpWidget(
      wrapForWidgetTest(
        const BadgesPage(),
        overrides: <Override>[
          gamificationRepositoryProvider.overrideWithValue(repo),
        ],
      ),
    );

    await tester.pumpAndSettle();
    expect(find.byKey(const Key("gamification.badges.grid")), findsOneWidget);
    expect(find.text("Explorer"), findsOneWidget);
    expect(find.text("Scholar"), findsOneWidget);
  });

  testWidgets("BadgesPage shows empty state when no badges",
      (WidgetTester tester) async {
    final repo = _Repo();
    when(() => repo.badges()).thenAnswer(
      (_) async => const Success<List<gam.Badge>>(<gam.Badge>[]),
    );

    await tester.pumpWidget(
      wrapForWidgetTest(
        const BadgesPage(),
        overrides: <Override>[
          gamificationRepositoryProvider.overrideWithValue(repo),
        ],
      ),
    );

    await tester.pumpAndSettle();
    expect(find.byKey(const Key("gamification.badges.empty")), findsOneWidget);
  });
}
