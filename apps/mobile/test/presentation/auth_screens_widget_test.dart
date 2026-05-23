import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/presentation/pages/auth/sign_in_page.dart';
import 'package:silklens/presentation/pages/auth/sign_up_page.dart';
import 'package:silklens/presentation/providers/auth_provider.dart';

// Helper: wraps a widget in a GoRouter so context.go() calls do not throw.
Widget _wrapWithRouter(Widget page) {
  final router = GoRouter(
    routes: [
      GoRoute(path: '/', builder: (_, __) => page),
      GoRoute(path: '/home', builder: (_, __) => const Scaffold(body: Text('home'))),
      GoRoute(path: '/auth/sign-up', builder: (_, __) => const Scaffold(body: Text('sign-up'))),
      GoRoute(path: '/auth/sign-in', builder: (_, __) => const Scaffold(body: Text('sign-in'))),
      GoRoute(path: '/auth/forgot-password', builder: (_, __) => const Scaffold(body: Text('forgot'))),
      GoRoute(path: '/onboarding', builder: (_, __) => const Scaffold(body: Text('onboarding'))),
    ],
  );
  return ProviderScope(
    overrides: [
      authProvider.overrideWith(_StubUnauthNotifier.new),
    ],
    child: MaterialApp.router(routerConfig: router),
  );
}

void main() {
  testWidgets('SignInPage renders without error', (tester) async {
    await tester.pumpWidget(_wrapWithRouter(const SignInPage()));
    await tester.pump();
    expect(tester.takeException(), isNull);
  });

  testWidgets('SignUpPage renders without error', (tester) async {
    await tester.pumpWidget(_wrapWithRouter(const SignUpPage()));
    await tester.pump();
    expect(tester.takeException(), isNull);
  });
}

class _StubUnauthNotifier extends AuthNotifier {
  @override
  AuthState build() => const AuthUnauthenticated();
}
