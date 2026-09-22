import 'package:flutter_test/flutter_test.dart';
import 'package:silklens/data/api/clients/api_client_provider.dart';
import 'package:silklens/data/api/clients/silklens_api_client.dart';
import 'package:silklens/presentation/pages/settings/notification_prefs_page.dart';

import 'test_helpers.dart';

void main() {
  testWidgets('NotificationPrefsPage renders without error', (tester) async {
    await tester.pumpWidget(
      wrapForWidgetTest(
        const NotificationPrefsPage(),
        overrides: [
          silkLensApiClientProvider.overrideWithValue(_FakeApiClient()),
        ],
      ),
    );
    await tester.pump();
    expect(tester.takeException(), isNull);
  });
}

/// Fake client — no methods are called during initial render.
class _FakeApiClient extends Fake implements SilkLensApiClient {}
