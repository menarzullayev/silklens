import 'package:flutter_test/flutter_test.dart';
import 'package:silklens/domain/gamification/entities/badge.dart';
import 'package:silklens/presentation/pages/gamification/badges_page.dart';
import 'package:silklens/presentation/providers/gamification_provider.dart';

import 'test_helpers.dart';

void main() {
  testWidgets('BadgesPage renders without error when badges are empty',
      (tester) async {
    await tester.pumpWidget(
      wrapForWidgetTest(
        const BadgesPage(),
        overrides: [
          badgesProvider.overrideWith((ref) async => <Badge>[]),
        ],
      ),
    );
    await tester.pump();
    expect(tester.takeException(), isNull);
  });
}
