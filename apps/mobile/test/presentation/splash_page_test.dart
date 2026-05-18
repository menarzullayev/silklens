// Widget test for SplashPage.
//
// Per Project-Decisions §1 the app name is dynamic, so the assertion is
// "the localized appName is rendered", not "the literal string SilkLens".
// The default in-repo bundles return "SilkLens" for `en`, but the test would
// still pass for any tenant rebranded build because we read the same key.

import "package:flutter/material.dart";
import "package:flutter_localizations/flutter_localizations.dart";
import "package:flutter_test/flutter_test.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/l10n/app_localizations.dart";
import "package:silklens/presentation/pages/splash_page.dart";

void main() {
  testWidgets("SplashPage renders the localized app name", (WidgetTester tester) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(
          locale: Locale("en"),
          supportedLocales: AppLocalizations.supportedLocales,
          localizationsDelegates: <LocalizationsDelegate<Object?>>[
            AppLocalizations.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
          ],
          home: SplashPage(),
        ),
      ),
    );

    // First frame.
    await tester.pump();

    expect(find.byKey(const Key("splash.logo")), findsOneWidget);
    expect(find.byKey(const Key("splash.app_name")), findsOneWidget);

    final BuildContext context = tester.element(find.byKey(const Key("splash.app_name")));
    final String expected = AppLocalizations.of(context)!.appName;
    expect(find.text(expected), findsOneWidget);
  });
}
