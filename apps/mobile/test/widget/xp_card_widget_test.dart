import 'package:flutter_test/flutter_test.dart';
import 'package:silklens/presentation/pages/gamification/xp_card.dart';
import 'package:silklens/presentation/providers/gamification_provider.dart';

import 'test_helpers.dart';

void main() {
  testWidgets('XPDashboardPage renders without error', (tester) async {
    await tester.pumpWidget(
      wrapForWidgetTest(
        const XPDashboardPage(),
        overrides: [
          gamificationProvider.overrideWith(_StubGamificationNotifier.new),
        ],
      ),
    );
    await tester.pump();
    expect(tester.takeException(), isNull);
  });
}

class _StubGamificationNotifier extends GamificationNotifier {
  @override
  XpState build() => const XpState(isLoading: false, level: 3, currentXp: 300);
}
