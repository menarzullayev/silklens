// Domain protocol for the auth subsystem.
//
// Implementations live in `lib/data/repositories/auth_repository_impl.dart`.
// The presentation layer only ever sees this interface — Clean Architecture
// invariant per ADR-0003 mirrored on mobile.

import 'package:silklens/core/utils/result.dart';
import 'package:silklens/domain/identity/entities/auth_session.dart';
import 'package:silklens/domain/identity/entities/auth_user.dart';

abstract interface class AuthRepository {
  /// Register a new account. Backend auto-logs-in via the 201 response, so
  /// the returned [AuthSession] is immediately usable.
  Future<Result<AuthSession>> signUp({
    required String email,
    required String password,
    String? displayName,
    String? preferredLocale,
  });

  /// Email + password sign-in. Returns the new [AuthSession].
  Future<Result<AuthSession>> signIn({
    required String email,
    required String password,
  });

  /// Revoke the current session on the server and clear local tokens.
  Future<Result<void>> signOut();

  /// Rotate the refresh token. Returns a fresh [AuthSession]; on failure
  /// (revoked family / network error) the caller MUST sign the user out.
  Future<Result<AuthSession>> refresh();

  /// Reads the persisted session from secure storage. Returns `null` when
  /// the user is anonymous (cold-boot path).
  Future<AuthSession?> currentSession();

  /// Hits `/v1/auth/me` and returns the up-to-date user. Used by the splash
  /// page silent-refresh flow and the profile page.
  Future<Result<AuthUser>> currentUser();

  /// Sign in or register via Google OAuth access token.
  Future<Result<AuthSession>> signInWithGoogle(String accessToken);

  /// Verify the 6-digit OTP sent to [email] after registration.
  Future<Result<bool>> verifyEmail({required String email, required String code});

  /// Request a fresh OTP for [email] (authenticated user only).
  Future<Result<bool>> resendVerification({
    required String email,
  });
}
