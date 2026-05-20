// IdentityRepositoryImpl — adapts the legacy IdentityRepository protocol to
// the canonical AuthRepository implementation.
//
// New code should depend on AuthRepository directly. This shim exists only so
// that presentation code that was written against the older IdentityRepository
// interface continues to compile and work without modification.

import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/core/utils/result.dart';
import 'package:silklens/data/repositories/auth_repository_impl.dart';
import 'package:silklens/domain/identity/entities/auth_session.dart';
import 'package:silklens/domain/identity/repositories/identity_repository.dart';

class IdentityRepositoryImpl implements IdentityRepository {
  IdentityRepositoryImpl(this._auth);

  final AuthRepository _auth;

  @override
  Future<Result<AuthSession>> loginWithEmail({
    required String email,
    required String password,
  }) =>
      _auth.signIn(email: email, password: password);

  @override
  Future<Result<AuthSession>> register({
    required String email,
    required String password,
    String? displayName,
  }) =>
      _auth.signUp(
        email: email,
        password: password,
        displayName: displayName,
      );

  @override
  Future<Result<AuthSession>> refresh() => _auth.refresh();

  @override
  Future<Result<void>> logout() => _auth.signOut();

  @override
  Future<AuthSession?> currentSession() => _auth.currentSession();
}

// ── Riverpod provider ─────────────────────────────────────────────────────────

final Provider<IdentityRepository> identityRepositoryProvider =
    Provider<IdentityRepository>(
  (Ref ref) => IdentityRepositoryImpl(
    ref.watch(authRepositoryProvider),
  ),
  name: 'identityRepositoryProvider',
);
