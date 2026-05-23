import 'package:flutter_test/flutter_test.dart';
import 'package:silklens/domain/gamification/entities/leaderboard_entry.dart';
import 'package:silklens/presentation/pages/gamification/leaderboard_page.dart';
import 'package:silklens/presentation/providers/gamification_provider.dart';

import 'test_helpers.dart';

void main() {
  testWidgets('LeaderboardPage renders without error when entries are empty',
      (tester) async {
    await tester.pumpWidget(
      wrapForWidgetTest(
        const LeaderboardPage(),
        overrides: [
          leaderboardEntriesProvider.overrideWith(
            (ref, arg) async => <LeaderboardEntry>[],
          ),
        ],
      ),
    );
    await tester.pump();
    expect(tester.takeException(), isNull);
  });
}
