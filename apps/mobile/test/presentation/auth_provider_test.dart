import 'package:flutter_test/flutter_test.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/presentation/providers/auth_provider.dart';

void main() {
  group('AuthState sealed class hierarchy', () {
    test('AuthInitial is a subtype of AuthState', () {
      const s = AuthInitial();
      expect(s, isA<AuthState>());
    });

    test('AuthLoading is a subtype of AuthState', () {
      const s = AuthLoading();
      expect(s, isA<AuthState>());
    });

    test('AuthUnauthenticated is a subtype of AuthState', () {
      const s = AuthUnauthenticated();
      expect(s, isA<AuthState>());
      // Backwards-compat alias works
      expect(s, isA<AuthAnonymous>());
    });

    test('AuthError holds its message', () {
      const s = AuthError('invalid_credentials');
      expect(s.message, equals('invalid_credentials'));
      expect(s, isA<AuthState>());
    });

    test('isAuthenticatedProvider returns false when unauthenticated', () {
      final container = ProviderContainer(
        overrides: [
          authProvider.overrideWith(_StubUnauthNotifier.new),
        ],
      );
      addTearDown(container.dispose);
      expect(container.read(isAuthenticatedProvider), isFalse);
    });
  });
}

class _StubUnauthNotifier extends AuthNotifier {
  @override
  AuthState build() => const AuthUnauthenticated();
}
