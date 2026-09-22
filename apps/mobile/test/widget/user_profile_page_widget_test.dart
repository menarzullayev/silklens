import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:silklens/data/api/clients/api_client_provider.dart';
import 'package:silklens/data/api/clients/silklens_api_client.dart';
import 'package:silklens/presentation/pages/profile/user_profile_page.dart';
import 'package:silklens/presentation/providers/auth_provider.dart';
import 'package:silklens/presentation/providers/locale_provider.dart';
import 'package:silklens/presentation/providers/profile_stats_provider.dart';

import 'test_helpers.dart';

void main() {
  testWidgets('UserProfilePage renders without error', (tester) async {
    await tester.pumpWidget(
      wrapForWidgetTest(
        const UserProfilePage(),
        overrides: [
          authProvider.overrideWith(_StubAuthNotifier.new),
          activeLocaleProvider.overrideWith(_StubLocaleController.new),
          profileStatsProvider.overrideWith(_StubProfileStatsNotifier.new),
          silkLensApiClientProvider.overrideWithValue(_FakeApiClient()),
        ],
      ),
    );
    await tester.pump();
    expect(tester.takeException(), isNull);
  });
}

class _StubAuthNotifier extends AuthNotifier {
  @override
  AuthState build() => const AuthUnauthenticated();
}

class _StubLocaleController extends LocaleController {
  @override
  Locale build() => const Locale('en');
}

class _StubProfileStatsNotifier extends ProfileStatsNotifier {
  @override
  ProfileStats build() => const ProfileStats();
}

class _FakeApiClient extends Fake implements SilkLensApiClient {}
