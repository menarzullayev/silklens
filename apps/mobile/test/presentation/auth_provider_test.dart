// Riverpod auth notifier behavior. Mocks the AuthRepository so we exercise
// only the state transitions, not the data layer.

import "package:flutter_test/flutter_test.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:mocktail/mocktail.dart";
import "package:silklens/core/error/failures.dart";
import "package:silklens/core/utils/result.dart";
import "package:silklens/data/repositories/auth_repository_impl.dart"
    show authRepositoryProvider;
import "package:silklens/domain/identity/entities/auth_session.dart";
import "package:silklens/domain/identity/entities/auth_user.dart";
import "package:silklens/domain/identity/repositories/auth_repository.dart";
import "package:silklens/presentation/providers/auth_provider.dart";

class _MockAuthRepository extends Mock implements AuthRepository {}

AuthSession _session({String email = "alice@example.com"}) => AuthSession(
      user: AuthUser(
        id: "u-1",
        pubId: "pub-1",
        tenantId: "t-1",
        email: email,
        trustTier: "verified",
      ),
      accessToken: "access-tok",
      refreshToken: "refresh-tok",
      expiresAt: DateTime.now().toUtc().add(const Duration(minutes: 15)),
    );

void main() {
  setUpAll(() {
    registerFallbackValue(_session());
  });

  group("AuthNotifier", () {
    late _MockAuthRepository repo;
    late ProviderContainer container;

    setUp(() {
      repo = _MockAuthRepository();
      when(() => repo.currentSession()).thenAnswer((_) async => null);
      container = ProviderContainer(
        overrides: <Override>[
          authRepositoryProvider.overrideWithValue(repo),
        ],
      );
      addTearDown(container.dispose);
    });

    test("bootstrap resolves to anonymous when no cached session", () async {
      // Reading the provider triggers bootstrap.
      final initial = container.read(authNotifierProvider);
      expect(initial.isLoading, isTrue);
      // Let the microtask in bootstrap flush.
      await Future<void>.delayed(Duration.zero);
      await Future<void>.delayed(Duration.zero);
      final after = container.read(authNotifierProvider);
      expect(after.isAnonymous, isTrue);
    });

    test("signIn success transitions to authenticated", () async {
      when(
        () => repo.signIn(
          email: any(named: "email"),
          password: any(named: "password"),
        ),
      ).thenAnswer((_) async => Success<AuthSession>(_session()));

      // Wait for bootstrap to settle.
      container.read(authNotifierProvider);
      await Future<void>.delayed(Duration.zero);
      await Future<void>.delayed(Duration.zero);

      final notifier = container.read(authNotifierProvider.notifier);
      final failure = await notifier.signIn(
        email: "alice@example.com",
        password: "Sup3rStrongPass!",
      );
      expect(failure, isNull);
      expect(container.read(authNotifierProvider).isAuthenticated, isTrue);
      expect(
        container.read(currentUserProvider)?.email,
        "alice@example.com",
      );
    });

    test("signIn failure preserves anonymous state and returns Failure",
        () async {
      when(
        () => repo.signIn(
          email: any(named: "email"),
          password: any(named: "password"),
        ),
      ).thenAnswer(
        (_) async => const FailureResult<AuthSession>(
          AuthFailure("invalid"),
        ),
      );

      container.read(authNotifierProvider);
      await Future<void>.delayed(Duration.zero);
      await Future<void>.delayed(Duration.zero);

      final notifier = container.read(authNotifierProvider.notifier);
      final failure = await notifier.signIn(
        email: "alice@example.com",
        password: "Sup3rStrongPass!",
      );
      expect(failure, isA<AuthFailure>());
      expect(container.read(authNotifierProvider).isAnonymous, isTrue);
    });

    test("signOut clears the session", () async {
      when(
        () => repo.signIn(
          email: any(named: "email"),
          password: any(named: "password"),
        ),
      ).thenAnswer((_) async => Success<AuthSession>(_session()));
      when(() => repo.signOut())
          .thenAnswer((_) async => const Success<void>(null));

      container.read(authNotifierProvider);
      await Future<void>.delayed(Duration.zero);
      await Future<void>.delayed(Duration.zero);

      final notifier = container.read(authNotifierProvider.notifier);
      await notifier.signIn(
          email: "alice@example.com", password: "Sup3rStrongPass!");
      expect(container.read(authNotifierProvider).isAuthenticated, isTrue);

      await notifier.signOut();
      expect(container.read(authNotifierProvider).isAnonymous, isTrue);
      verify(() => repo.signOut()).called(1);
    });

    test("debugSet directly forces a state (visible-for-testing)", () {
      final notifier = container.read(authNotifierProvider.notifier);
      notifier.debugSet(const AuthState.anonymous());
      expect(container.read(authNotifierProvider).isAnonymous, isTrue);
    });
  });
}

