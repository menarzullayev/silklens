// Attaches the access-token bearer to outgoing requests and silently
// refreshes it on 401 `identity.token_expired`.
//
// Strategy:
//   * Skip auth + branding + vocab endpoints (anonymous), no token added.
//   * On 401 with `code == identity.token_expired`, call /v1/auth/refresh
//     using the stored refresh token. If successful, retry the original
//     request with the new access token.
//   * On 401 with `code == identity.token_invalid` (or any other refresh
//     failure), clear the local session and propagate the error so the
//     AuthNotifier can drop back to anonymous + the router can redirect.
//
// We deliberately do not lock requests during refresh — only one refresh
// at a time though, so concurrent 401s share the same Future.

import 'dart:async';

import 'package:dio/dio.dart';
import 'package:silklens/core/logging/app_logger.dart';
import 'package:silklens/core/storage/secure_token_storage.dart';

typedef OnSessionLost = Future<void> Function();

class AuthInterceptor extends Interceptor {
  AuthInterceptor({
    required this.tokenStorage,
    required this.refreshBaseUrl,
    this.onSessionLost,
  });

  final SecureTokenStorage tokenStorage;
  final String refreshBaseUrl;
  final OnSessionLost? onSessionLost;

  Future<String?>? _inflightRefresh;

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    if (_isAnonymousEndpoint(options.path)) {
      handler.next(options);
      return;
    }
    final token = await tokenStorage.readAccessToken();
    if (token != null && token.isNotEmpty) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    final response = err.response;
    if (response?.statusCode != 401) {
      handler.next(err);
      return;
    }
    final code = _extractErrorCode(response?.data);
    final isExpired = code == 'identity.token_expired';
    final isInvalid =
        code == 'identity.token_invalid' || code == 'identity.session_revoked';

    // Don't try to refresh the refresh endpoint itself.
    if (err.requestOptions.path.contains('/auth/refresh') ||
        err.requestOptions.path.contains('/auth/login') ||
        err.requestOptions.path.contains('/auth/register')) {
      handler.next(err);
      return;
    }

    if (isInvalid) {
      await _wipeAndLogout();
      handler.next(err);
      return;
    }

    if (!isExpired) {
      handler.next(err);
      return;
    }

    try {
      final newAccess = await (_inflightRefresh ??= _refresh());
      _inflightRefresh = null;
      if (newAccess == null || newAccess.isEmpty) {
        await _wipeAndLogout();
        handler.next(err);
        return;
      }
      // Retry the original request with the new token.
      final retried = await _retry(err.requestOptions, newAccess);
      handler.resolve(retried);
    } on Exception catch (error, stackTrace) {
      _inflightRefresh = null;
      AppLogger.instance.w(
        'Auth refresh failed; signing user out.',
        error: error,
        stackTrace: stackTrace,
      );
      await _wipeAndLogout();
      handler.next(err);
    }
  }

  Future<String?> _refresh() async {
    final refreshToken = await tokenStorage.readRefreshToken();
    if (refreshToken == null || refreshToken.isEmpty) return null;
    final dio = Dio(BaseOptions(baseUrl: refreshBaseUrl));
    final response = await dio.post<Map<String, Object?>>(
      '/v1/auth/refresh',
      data: <String, String>{'refresh_token': refreshToken},
      options: Options(
        headers: <String, String>{'Content-Type': 'application/json'},
        validateStatus: (int? s) => s != null && s < 500,
      ),
    );
    if (response.statusCode != 200) return null;
    final body = response.data;
    if (body == null) return null;
    final tokens = body['tokens'];
    if (tokens is! Map) return null;
    final access = tokens['access_token'];
    final refresh = tokens['refresh_token'];
    if (access is! String || refresh is! String) return null;
    await tokenStorage.writeAccessToken(access);
    await tokenStorage.writeRefreshToken(refresh);
    return access;
  }

  Future<Response<Object?>> _retry(
    RequestOptions original,
    String newAccess,
  ) async {
    final dio = Dio(BaseOptions(baseUrl: original.baseUrl));
    return dio.fetch<Object?>(
      original.copyWith(
        headers: <String, Object?>{
          ...original.headers,
          'Authorization': 'Bearer $newAccess',
        },
      ),
    );
  }

  Future<void> _wipeAndLogout() async {
    await tokenStorage.clear();
    final cb = onSessionLost;
    if (cb != null) await cb();
  }

  static String? _extractErrorCode(Object? data) {
    if (data is! Map) return null;
    final detail = data['detail'];
    if (detail is Map && detail['code'] is String) {
      return detail['code'] as String;
    }
    if (data['code'] is String) return data['code'] as String;
    return null;
  }

  bool _isAnonymousEndpoint(String path) =>
      path.contains('/auth/login') ||
      path.contains('/auth/register') ||
      path.contains('/auth/refresh') ||
      path.contains('/v1/branding') ||
      path.contains('/v1/vocab') ||
      path == '/version' ||
      path == '/health' ||
      path == '/ready';
}
