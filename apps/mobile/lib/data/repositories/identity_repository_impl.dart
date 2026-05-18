// Backwards-compat shim. The canonical implementation is
// [AuthRepositoryImpl]; this class wraps it so the legacy
// [IdentityRepository] interface keeps working until callers migrate.

import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/core/utils/result.dart";
import "package:silklens/data/repositories/auth_repository_impl.dart"
    show authRepositoryProvider;
import "package:silklens/domain/identity/entities/auth_session.dart";
import "package:silklens/domain/identity/repositories/auth_repository.dart";
import "package:silklens/domain/identity/repositories/identity_repository.dart";

class IdentityRepositoryImpl implements IdentityRepository {
  IdentityRepositoryImpl({required AuthRepository auth}) : _auth = auth;

  final AuthRepository _auth;

  @override
  Future<AuthSession?> currentSession() => _auth.currentSession();

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
}

final Provider<IdentityRepository> identityRepositoryProvider =
    Provider<IdentityRepository>(
  (Ref ref) => IdentityRepositoryImpl(auth: ref.watch(authRepositoryProvider)),
  name: "identityRepositoryProvider",
);
