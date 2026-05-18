import "package:silklens/core/utils/result.dart";
import "package:silklens/domain/identity/entities/auth_session.dart";

abstract interface class IdentityRepository {
  Future<Result<AuthSession>> loginWithEmail({
    required String email,
    required String password,
  });

  Future<Result<AuthSession>> register({
    required String email,
    required String password,
    String? displayName,
  });

  Future<Result<AuthSession>> refresh();

  Future<Result<void>> logout();

  /// Returns the cached session if any, hydrated from secure storage on boot.
  Future<AuthSession?> currentSession();
}
