// Backwards-compat shim — the canonical interface is `AuthRepository`
// (auth_repository.dart). This file is kept so any presentation code that
// already imported `IdentityRepository` keeps compiling. Both names point
// at the same protocol.

import 'package:silklens/core/utils/result.dart';
import 'package:silklens/domain/identity/entities/auth_session.dart';
import 'package:silklens/domain/identity/repositories/auth_repository.dart'
    show AuthRepository;
import 'package:silklens/domain/identity/repositories/identity_repository.dart'
    show AuthRepository;

export 'package:silklens/domain/identity/repositories/auth_repository.dart'
    show AuthRepository;

/// Legacy protocol — same shape as [AuthRepository] but with the older
/// method names. Use [AuthRepository] in new code.
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

  Future<AuthSession?> currentSession();
}
