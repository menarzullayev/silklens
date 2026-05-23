import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/l10n/app_localizations.dart';
import 'package:silklens/presentation/pages/settings/settings_home_page.dart';

// GoRouter wrapper needed because SettingsHomePage calls context.pop() in its
// AppBar back button.
Widget _wrapWithRouter(Widget page) {
  final router = GoRouter(
    routes: [
      GoRoute(path: '/', builder: (_, __) => page),
    ],
  );
  return ProviderScope(
    child: MaterialApp.router(
      routerConfig: router,
      locale: const Locale('en'),
      supportedLocales: AppLocalizations.supportedLocales,
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ],
    ),
  );
}

void main() {
  testWidgets('SettingsHomePage renders without error', (tester) async {
    await tester.pumpWidget(_wrapWithRouter(const SettingsHomePage()));
    await tester.pump();
    expect(tester.takeException(), isNull);
  });
}
