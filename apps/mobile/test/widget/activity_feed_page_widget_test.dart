import 'package:flutter_test/flutter_test.dart';
import 'package:silklens/presentation/pages/social/activity_feed_page.dart';
import 'package:silklens/presentation/providers/social_provider.dart';

import 'test_helpers.dart';

void main() {
  testWidgets('ActivityFeedPage renders without error when feed is empty',
      (tester) async {
    await tester.pumpWidget(
      wrapForWidgetTest(
        const ActivityFeedPage(),
        overrides: [
          feedProvider.overrideWith((_) async => <Map<String, dynamic>>[]),
        ],
      ),
    );
    // One extra pump for the FutureProvider to resolve.
    await tester.pump();
    await tester.pump();
    expect(tester.takeException(), isNull);
  });
}
