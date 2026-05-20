// Smoke-test the app boot path without external dependencies. We mount
// SilkLensApp inside a ProviderScope that supplies stub overrides so the
// real Isar + .env paths don't have to exist on a CI agent.

import 'package:flutter_test/flutter_test.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:integration_test/integration_test.dart';
import 'package:silklens/app/app.dart';
import 'package:silklens/core/env/app_environment.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('App boots without throwing', (WidgetTester tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: <Override>[
          appEnvironmentProvider.overrideWithValue(AppEnvironment.fallback()),
          // isarDatabaseProvider is intentionally left throwing; the only
          // screens reached in this smoke test (splash, onboarding) don't
          // touch the DB, so the override isn't needed yet.
        ],
        child: const SilkLensApp(),
      ),
    );
    await tester.pump();
    expect(tester.takeException(), isNull);
  });
}
