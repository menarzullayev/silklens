// AuthRepositoryImpl — full implementation wired to SilkLensApiClient +
// SecureTokenStorage.
//
// All fallible operations return Result<T> so callers can exhaustively pattern-
// match without try/catch.  currentSession() is the only method that returns a
// nullable directly — it is intentionally non-failable (storage reads never
// throw in practice, and an absent token simply means "anonymous user").

import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/core/error/failures.dart';
import 'package:silklens/core/storage/secure_token_storage.dart';
import 'package:silklens/core/utils/result.dart';
import 'package:silklens/data/api/clients/api_client_provider.dart';
import 'package:silklens/data/api/clients/silklens_api_client.dart';
import 'package:silklens/data/api/dto/auth_dto.dart';
import 'package:silklens/domain/identity/entities/auth_session.dart';
import 'package:silklens/domain/identity/entities/auth_user.dart';
import 'package:silklens/domain/identity/repositories/auth_repository.dart';

class AuthRepositoryImpl implements AuthRepository {
  AuthRepositoryImpl(this._client, this._tokenStorage);

  final SilkLensApiClient _client;
  final SecureTokenStorage _tokenStorage;

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  /// Maps a [DioException] into the appropriate domain [Failure].
  Failure _mapDio(DioException e) {
    final statusCode = e.response?.statusCode;
    if (e.type == DioExceptionType.connectionError ||
        e.type == DioExceptionType.connectionTimeout ||
        e.type == DioExceptionType.receiveTimeout ||
        e.type == DioExceptionType.sendTimeout) {
      return NetworkFailure(
        'Network error: ${e.message}',
        cause: e,
        stackTrace: e.stackTrace,
      );
    }
    if (statusCode == 401 || statusCode == 403) {
      return AuthFailure(
        _extractMessage(e) ?? 'Authentication failed ($statusCode)',
        cause: e,
        stackTrace: e.stackTrace,
      );
    }
    if (statusCode == 422) {
      return ValidationFailure(
        _extractMessage(e) ?? 'Validation error',
      );
    }
    return ServerFailure(
      _extractMessage(e) ?? 'Server error ($statusCode)',
      statusCode: statusCode,
      cause: e,
      stackTrace: e.stackTrace,
    );
  }

  String? _extractMessage(DioException e) {
    try {
      final data = e.response?.data;
      if (data is Map<String, dynamic>) {
        return data['detail'] as String? ?? data['message'] as String?;
      }
    } catch (_) {}
    return null;
  }

  Failure _mapUnknown(Object e, StackTrace st) =>
      UnknownFailure(e.toString(), cause: e, stackTrace: st);

  /// Converts a [UserDto] to a domain [AuthUser].
  AuthUser _userFromDto(UserDto dto) => AuthUser(
        id: dto.id,
        pubId: dto.pubId,
        tenantId: dto.tenantId,
        residencyRegion: dto.residencyRegion,
        trustTier: dto.trustTier,
        preferredLocale: dto.preferredLocale,
        isVerified: dto.isVerified,
      );

  /// Persists tokens and the user snapshot after a successful auth response.
  Future<void> _persistSession({
    required String accessToken,
    required String refreshToken,
    required AuthUser user,
  }) async {
    await Future.wait([
      _tokenStorage.writeAccessToken(accessToken),
      _tokenStorage.writeRefreshToken(refreshToken),
      _tokenStorage.writeUserSnapshot(jsonEncode(user.toJson())),
    ]);
  }

  // ---------------------------------------------------------------------------
  // AuthRepository implementation
  // ---------------------------------------------------------------------------

  @override
  Future<Result<AuthSession>> signIn({
    required String email,
    required String password,
  }) async {
    try {
      final resp = await _client.login(
        LoginRequestDto(email: email, password: password),
      );
      final user = _userFromDto(resp.user);
      final session = AuthSession(
        accessToken: resp.tokens.accessToken,
        refreshToken: resp.tokens.refreshToken,
        user: user,
        expiresIn: resp.tokens.expiresIn,
        tokenType: resp.tokens.tokenType,
        expiresAt: DateTime.now().add(Duration(seconds: resp.tokens.expiresIn)),
        email: email,
      );
      await _persistSession(
        accessToken: session.accessToken,
        refreshToken: session.refreshToken,
        user: user,
      );
      return Success(session);
    } on DioException catch (e) {
      return FailureResult(_mapDio(e));
    } catch (e, st) {
      return FailureResult(_mapUnknown(e, st));
    }
  }

  @override
  Future<Result<AuthSession>> signUp({
    required String email,
    required String password,
    String? displayName,
    String? preferredLocale,
  }) async {
    try {
      final resp = await _client.register(
        RegisterRequestDto(
          email: email,
          password: password,
          displayName: displayName,
          preferredLocale: preferredLocale ?? 'en',
        ),
      );
      final user = _userFromDto(resp.user);
      final session = AuthSession(
        accessToken: resp.tokens.accessToken,
        refreshToken: resp.tokens.refreshToken,
        user: user,
        expiresIn: resp.tokens.expiresIn,
        tokenType: resp.tokens.tokenType,
        expiresAt: DateTime.now().add(Duration(seconds: resp.tokens.expiresIn)),
        email: email,
      );
      await _persistSession(
        accessToken: session.accessToken,
        refreshToken: session.refreshToken,
        user: user,
      );
      return Success(session);
    } on DioException catch (e) {
      return FailureResult(_mapDio(e));
    } catch (e, st) {
      return FailureResult(_mapUnknown(e, st));
    }
  }

  @override
  Future<Result<void>> signOut() async {
    try {
      // Best-effort server-side revocation — ignore errors so the local
      // session is always cleared even if the server is unreachable.
      await _client.logout();
    } catch (_) {}
    try {
      await _tokenStorage.clear();
      return const Success(null);
    } catch (e, st) {
      return FailureResult(_mapUnknown(e, st));
    }
  }

  @override
  Future<Result<AuthSession>> refresh() async {
    final refreshToken = await _tokenStorage.readRefreshToken();
    if (refreshToken == null) {
      return const FailureResult(
        AuthFailure('No refresh token available — user must sign in again'),
      );
    }
    try {
      final resp = await _client.refresh(
        RefreshRequestDto(refreshToken: refreshToken),
      );
      final user = _userFromDto(resp.user);

      // Try to recover the cached email for the reconstructed session.
      String? cachedEmail;
      try {
        final snapshot = await _tokenStorage.readUserSnapshot();
        if (snapshot != null) {
          // email is not in AuthUser.toJson — fall back to null gracefully.
          cachedEmail = null;
        }
      } catch (_) {}

      final session = AuthSession(
        accessToken: resp.tokens.accessToken,
        refreshToken: resp.tokens.refreshToken,
        user: user,
        expiresIn: resp.tokens.expiresIn,
        tokenType: resp.tokens.tokenType,
        expiresAt: DateTime.now().add(Duration(seconds: resp.tokens.expiresIn)),
        email: cachedEmail,
      );
      await _persistSession(
        accessToken: session.accessToken,
        refreshToken: session.refreshToken,
        user: user,
      );
      return Success(session);
    } on DioException catch (e) {
      // Revoked / expired refresh token — clear local storage so the caller
      // knows the user must sign in from scratch.
      await _tokenStorage.clear();
      return FailureResult(_mapDio(e));
    } catch (e, st) {
      await _tokenStorage.clear();
      return FailureResult(_mapUnknown(e, st));
    }
  }

  @override
  Future<AuthSession?> currentSession() async {
    final accessToken = await _tokenStorage.readAccessToken();
    final refreshToken = await _tokenStorage.readRefreshToken();
    if (accessToken == null) return null;

    // Reconstruct user from cached snapshot when available.
    AuthUser? cachedUser;
    try {
      final snapshot = await _tokenStorage.readUserSnapshot();
      if (snapshot != null) {
        cachedUser = AuthUser.fromJson(
          jsonDecode(snapshot) as Map<String, dynamic>,
        );
      }
    } catch (_) {
      // Corrupted snapshot — proceed without cached user; caller should call
      // currentUser() or refresh() to get a fresh session.
    }

    if (cachedUser == null) return null;

    return AuthSession(
      accessToken: accessToken,
      refreshToken: refreshToken ?? '',
      user: cachedUser,
    );
  }

  @override
  Future<Result<AuthUser>> currentUser() async {
    try {
      final resp = await _client.me();
      final user = _userFromDto(resp.user);
      // Keep the cached snapshot up-to-date.
      await _tokenStorage.writeUserSnapshot(jsonEncode(user.toJson()));
      return Success(user);
    } on DioException catch (e) {
      return FailureResult(_mapDio(e));
    } catch (e, st) {
      return FailureResult(_mapUnknown(e, st));
    }
  }

  @override
  Future<Result<bool>> verifyEmail({
    required String email,
    required String code,
  }) async {
    try {
      final resp = await _client.verifyEmail(
        VerifyEmailRequestDto(email: email, code: code),
      );
      if (resp.verified) {
        // Refresh cached user snapshot so is_verified flips to true.
        try {
          await currentUser();
        } catch (_) {}
      }
      return Success(resp.verified);
    } on DioException catch (e) {
      return FailureResult(_mapDio(e));
    } catch (e, st) {
      return FailureResult(_mapUnknown(e, st));
    }
  }

  @override
  Future<Result<bool>> resendVerification({required String email}) async {
    try {
      final resp = await _client.resendVerification(
        ResendVerificationRequestDto(email: email),
      );
      return Success(resp.sent);
    } on DioException catch (e) {
      return FailureResult(_mapDio(e));
    } catch (e, st) {
      return FailureResult(_mapUnknown(e, st));
    }
  }

  @override
  Future<Result<AuthSession>> signInWithGoogle(String accessToken) async {
    try {
      final resp = await _client.googleSignIn(accessToken);
      final user = _userFromDto(resp.user);
      final session = AuthSession(
        accessToken: resp.tokens.accessToken,
        refreshToken: resp.tokens.refreshToken,
        user: user,
        expiresIn: resp.tokens.expiresIn,
        tokenType: resp.tokens.tokenType,
        expiresAt: DateTime.now().add(Duration(seconds: resp.tokens.expiresIn)),
      );
      await _persistSession(
        accessToken: session.accessToken,
        refreshToken: session.refreshToken,
        user: user,
      );
      return Success(session);
    } on DioException catch (e) {
      return FailureResult(_mapDio(e));
    } catch (e, st) {
      return FailureResult(_mapUnknown(e, st));
    }
  }
}

// ── Riverpod provider ────────────────────────────────────────────────────────

final Provider<AuthRepository> authRepositoryProvider =
    Provider<AuthRepository>(
  (Ref ref) => AuthRepositoryImpl(
    ref.watch(silkLensApiClientProvider),
    ref.watch(secureTokenStorageProvider),
  ),
  name: 'authRepositoryProvider',
);
