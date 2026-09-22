import 'package:flutter_test/flutter_test.dart';
import 'package:silklens/domain/gamification/entities/streak_entity.dart';
import 'package:silklens/presentation/pages/gamification/streak_widget.dart';
import 'package:silklens/presentation/providers/gamification_provider.dart';

import 'test_helpers.dart';

const _stubStreak = StreakEntity(
  currentStreak: 5,
  bestStreak: 10,
  weekDays: [true, true, false, true, false, true, false],
  milestones: [],
);

void main() {
  testWidgets('StreakPage renders current streak count', (tester) async {
    await tester.pumpWidget(
      wrapForWidgetTest(
        const StreakPage(),
        overrides: [
          streakProvider.overrideWith((ref) async => _stubStreak),
        ],
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('5'), findsAtLeastNWidgets(1));
    expect(tester.takeException(), isNull);
  });
}
