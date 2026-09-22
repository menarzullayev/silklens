import 'package:flutter_test/flutter_test.dart';
import 'package:silklens/presentation/pages/social/notifications_page.dart';
import 'package:silklens/presentation/providers/social_provider.dart';

import 'test_helpers.dart';

void main() {
  testWidgets('NotificationsPage renders without error when list is empty',
      (tester) async {
    await tester.pumpWidget(
      wrapForWidgetTest(
        const NotificationsPage(),
        overrides: [
          notificationsProvider.overrideWith(_StubNotificationsNotifier.new),
        ],
      ),
    );
    await tester.pump();
    expect(tester.takeException(), isNull);
  });
}

class _StubNotificationsNotifier extends NotificationsNotifier {
  @override
  NotificationsState build() => const NotificationsState();

  // NotificationsPage calls refresh() via Future.microtask in initState.
  // The real implementation calls socialRepositoryProvider (not mocked here),
  // so we override to a no-op to keep the test hermetic.
  @override
  Future<void> refresh({bool unreadOnly = false}) async {}
}
