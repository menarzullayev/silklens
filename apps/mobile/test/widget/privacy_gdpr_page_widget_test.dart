import 'package:flutter_test/flutter_test.dart';
import 'package:silklens/data/api/clients/api_client_provider.dart';
import 'package:silklens/data/api/clients/silklens_api_client.dart';
import 'package:silklens/presentation/pages/settings/privacy_gdpr_page.dart';

import 'test_helpers.dart';

void main() {
  testWidgets('PrivacyGDPRPage renders without error', (tester) async {
    await tester.pumpWidget(
      wrapForWidgetTest(
        const PrivacyGDPRPage(),
        overrides: [
          silkLensApiClientProvider.overrideWithValue(_FakeApiClient()),
        ],
      ),
    );
    await tester.pump();
    expect(tester.takeException(), isNull);
  });
}

/// Fake client — no network calls are made during initial render.
class _FakeApiClient extends Fake implements SilkLensApiClient {}
