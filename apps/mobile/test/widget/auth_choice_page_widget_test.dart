import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/l10n/app_localizations.dart';
import 'package:silklens/presentation/pages/auth/auth_choice_page.dart';

// AuthChoicePage uses context.go() callbacks and AnimationController.
// Wrapping in GoRouter satisfies the router requirement; the animation
// controller is self-contained and needs no additional mocking.
Widget _wrapWithRouter() {
  final router = GoRouter(
    routes: [
      GoRoute(path: '/', builder: (_, __) => const AuthChoicePage()),
      GoRoute(
        path: '/auth/sign-in',
        builder: (_, __) => const Scaffold(body: Text('sign-in')),
      ),
      GoRoute(
        path: '/auth/sign-up',
        builder: (_, __) => const Scaffold(body: Text('sign-up')),
      ),
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
  testWidgets('AuthChoicePage renders without error', (tester) async {
    await tester.pumpWidget(_wrapWithRouter());
    await tester.pump();
    expect(tester.takeException(), isNull);
  });
}
