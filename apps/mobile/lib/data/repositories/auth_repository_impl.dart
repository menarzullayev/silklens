// Concrete [AuthRepository] backed by the retrofit-generated REST client.
//
// Responsibilities (per Clean Architecture, ADR-0003):
//   * Catch ApiException / DioException / NetworkException and translate
//     into domain Failure values inside `Result`.
//   * Persist tokens into [SecureTokenStorage] on success and a JSON
//     snapshot of the user so cold-boot can paint a logged-in shell.
//   * Stay out of presentation concerns — providers wire this up.

import "dart:async";
import "dart:convert";

import "package:dio/dio.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/core/error/exceptions.dart";
import "package:silklens/core/error/failures.dart";
import "package:silklens/core/logging/app_logger.dart";
import "package:silklens/core/storage/secure_token_storage.dart";
import "package:silklens/core/utils/result.dart";
import "package:silklens/data/api/clients/api_client_provider.dart";
import "package:silklens/data/api/clients/silklens_api_client.dart";
import "package:silklens/data/api/dto/auth_dto.dart";
import "package:silklens/domain/identity/entities/auth_session.dart";
import "package:silklens/domain/identity/entities/auth_user.dart";
import "package:silklens/domain/identity/repositories/auth_repository.dart";

class AuthRepositoryImpl implements AuthRepository {
  AuthRepositoryImpl({
    required SilkLensApiClient api,
    required SecureTokenStorage tokenStorage,
    Clock? clock,
  })  : _api = api,
        _storage = tokenStorage,
        _clock = clock ?? const _SystemClock();

  final SilkLensApiClient _api;
  final SecureTokenStorage _storage;
  final Clock _clock;

  @override
  Future<Result<AuthSession>> signUp({
    required String email,
    required String password,
    String? displayName,
    String? preferredLocale,
  }) async {
    try {
      final response = await _api.register(
        RegisterRequestDto(
          email: email,
          password: password,
          displayName: displayName,
          preferredLocale: preferredLocale ?? "en",
        ),
      );
      final session = _sessionFromResponse(response);
      await _persist(session);
      return Success<AuthSession>(session);
    } on ApiException catch (e, st) {
      return FailureResult<AuthSession>(_apiToFailure(e, st));
    } on NetworkException catch (e, st) {
      return FailureResult<AuthSession>(
        NetworkFailure(e.message, cause: e, stackTrace: st),
      );
    } on DioException catch (e, st) {
      return FailureResult<AuthSession>(_dioToFailure(e, st));
    }
  }

  @override
  Future<Result<AuthSession>> signIn({
    required String email,
    required String password,
  }) async {
    try {
      final response = await _api.login(
        LoginRequestDto(email: email, password: password),
      );
      final session = _sessionFromResponse(response);
      await _persist(session);
      return Success<AuthSession>(session);
    } on ApiException catch (e, st) {
      return FailureResult<AuthSession>(_apiToFailure(e, st));
    } on NetworkException catch (e, st) {
      return FailureResult<AuthSession>(
        NetworkFailure(e.message, cause: e, stackTrace: st),
      );
    } on DioException catch (e, st) {
      return FailureResult<AuthSession>(_dioToFailure(e, st));
    }
  }

  @override
  Future<Result<void>> signOut() async {
    try {
      await _api.logout();
    } on Exception catch (error, stackTrace) {
      // Don't fail sign-out if the server returns an error — the user
      // still expects the local session to be cleared.
      AppLogger.instance.w(
        "Logout API call failed; clearing local session anyway.",
        error: error,
        stackTrace: stackTrace,
      );
    }
    await _storage.clear();
    return const Success<void>(null);
  }

  @override
  Future<Result<AuthSession>> refresh() async {
    final refreshToken = await _storage.readRefreshToken();
    if (refreshToken == null || refreshToken.isEmpty) {
      return const FailureResult<AuthSession>(
        AuthFailure("No refresh token in secure storage."),
      );
    }
    try {
      final response =
          await _api.refresh(RefreshRequestDto(refreshToken: refreshToken));
      final session = _sessionFromResponse(response);
      await _persist(session);
      return Success<AuthSession>(session);
    } on ApiException catch (e, st) {
      // Refresh failed — caller must clear the session.
      return FailureResult<AuthSession>(_apiToFailure(e, st));
    } on DioException catch (e, st) {
      return FailureResult<AuthSession>(_dioToFailure(e, st));
    }
  }

  @override
  Future<AuthSession?> currentSession() async {
    final access = await _storage.readAccessToken();
    final refreshTok = await _storage.readRefreshToken();
    final userJson = await _storage.readUserSnapshot();
    if (access == null ||
        access.isEmpty ||
        refreshTok == null ||
        refreshTok.isEmpty ||
        userJson == null ||
        userJson.isEmpty) {
      return null;
    }
    try {
      final user =
          AuthUser.fromJson(json.decode(userJson) as Map<String, dynamic>);
      // We don't know the precise expiry without re-decoding the JWT, so we
      // mark it as expiring "now" — the splash page calls [refresh] before
      // dropping into the authenticated home, which gives us a fresh window.
      return AuthSession(
        user: user,
        accessToken: access,
        refreshToken: refreshTok,
        expiresAt: _clock.utcNow(),
      );
    } on FormatException catch (error, stackTrace) {
      AppLogger.instance.w(
        "Corrupt user snapshot in secure storage — clearing.",
        error: error,
        stackTrace: stackTrace,
      );
      await _storage.clear();
      return null;
    }
  }

  @override
  Future<Result<AuthUser>> currentUser() async {
    try {
      final response = await _api.me();
      final user = _userFromDto(response.user);
      await _storage.writeUserSnapshot(json.encode(user.toJson()));
      return Success<AuthUser>(user);
    } on ApiException catch (e, st) {
      return FailureResult<AuthUser>(_apiToFailure(e, st));
    } on DioException catch (e, st) {
      return FailureResult<AuthUser>(_dioToFailure(e, st));
    }
  }

  // --- helpers --------------------------------------------------------------

  AuthSession _sessionFromResponse(LoginResponseDto dto) => AuthSession(
        user: _userFromDto(dto.user),
        accessToken: dto.tokens.accessToken,
        refreshToken: dto.tokens.refreshToken,
        tokenType: dto.tokens.tokenType,
        expiresAt:
            _clock.utcNow().add(Duration(seconds: dto.tokens.expiresIn)),
      );

  AuthUser _userFromDto(UserDto dto) => AuthUser(
        id: dto.id,
        pubId: dto.pubId,
        tenantId: dto.tenantId,
        residencyRegion: dto.residencyRegion,
        email: dto.email,
        displayName: dto.displayName,
        avatarUrl: dto.avatarUrl,
        trustTier: dto.trustTier,
        preferredLocale: dto.preferredLocale,
        preferredTimezone: dto.preferredTimezone,
        isVerified: dto.isVerified,
      );

  Future<void> _persist(AuthSession session) async {
    await _storage.writeAccessToken(session.accessToken);
    await _storage.writeRefreshToken(session.refreshToken);
    await _storage.writeUserSnapshot(json.encode(session.user.toJson()));
  }

  Failure _apiToFailure(ApiException e, StackTrace st) {
    final code = e.statusCode;
    final msg = e.message;
    if (code == 400 && msg.contains("password")) {
      return ValidationFailure(msg, fieldErrors: <String, String>{
        "password": msg,
      });
    }
    if (code == 401) {
      return AuthFailure(msg, cause: e, stackTrace: st);
    }
    if (code == 403) {
      return AuthFailure(msg, cause: e, stackTrace: st);
    }
    if (code == 409) {
      return ValidationFailure(msg, fieldErrors: <String, String>{
        "email": msg,
      });
    }
    if (code == 429) {
      return ServerFailure(
        msg,
        statusCode: code,
        cause: e,
        stackTrace: st,
      );
    }
    return ServerFailure(msg, statusCode: code, cause: e, stackTrace: st);
  }

  Failure _dioToFailure(DioException e, StackTrace st) {
    final inner = e.error;
    if (inner is ApiException) return _apiToFailure(inner, st);
    if (inner is NetworkException) {
      return NetworkFailure(inner.message, cause: e, stackTrace: st);
    }
    return NetworkFailure(e.message ?? "Dio error", cause: e, stackTrace: st);
  }
}

abstract class Clock {
  const Clock();
  DateTime utcNow();
}

class _SystemClock extends Clock {
  const _SystemClock();
  @override
  DateTime utcNow() => DateTime.now().toUtc();
}

/// Provider wiring lives here (data layer) so the presentation layer never
/// needs to import data/*.
///
/// [silkLensApiClientProvider] is defined in
/// `lib/data/api/clients/api_client_provider.dart` — the single source of
/// truth for the retrofit client.
final Provider<AuthRepository> authRepositoryProvider =
    Provider<AuthRepository>(
  (Ref ref) => AuthRepositoryImpl(
    api: ref.watch(silkLensApiClientProvider),
    tokenStorage: ref.watch(secureTokenStorageProvider),
  ),
  name: "authRepositoryProvider",
);
