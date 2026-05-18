// Placeholder identity repository. Returns ValidationFailure for all writes
// until the backend `/v1/auth/*` endpoints land (FAZA 2). Keeping the wiring
// in the tree means UI code can already call use cases against a real
// provider without conditionals.

import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/core/error/failures.dart";
import "package:silklens/core/storage/secure_token_storage.dart";
import "package:silklens/core/utils/result.dart";
import "package:silklens/domain/identity/entities/auth_session.dart";
import "package:silklens/domain/identity/repositories/identity_repository.dart";

class IdentityRepositoryImpl implements IdentityRepository {
  IdentityRepositoryImpl({required SecureTokenStorage tokenStorage})
      : _tokenStorage = tokenStorage;

  // ignore: unused_field — kept for forthcoming refresh + logout flows.
  final SecureTokenStorage _tokenStorage;

  @override
  Future<AuthSession?> currentSession() async => null;

  @override
  Future<Result<AuthSession>> loginWithEmail({
    required String email,
    required String password,
  }) async =>
      const FailureResult<AuthSession>(
        ValidationFailure("Identity service not wired yet — FAZA 2 deliverable."),
      );

  @override
  Future<Result<AuthSession>> register({
    required String email,
    required String password,
    String? displayName,
  }) async =>
      const FailureResult<AuthSession>(
        ValidationFailure("Identity service not wired yet — FAZA 2 deliverable."),
      );

  @override
  Future<Result<AuthSession>> refresh() async =>
      const FailureResult<AuthSession>(
        AuthFailure("No session to refresh."),
      );

  @override
  Future<Result<void>> logout() async {
    await _tokenStorage.clear();
    return const Success<void>(null);
  }
}

final Provider<IdentityRepository> identityRepositoryProvider =
    Provider<IdentityRepository>(
  (Ref ref) => IdentityRepositoryImpl(
    tokenStorage: ref.watch(secureTokenStorageProvider),
  ),
  name: "identityRepositoryProvider",
);
