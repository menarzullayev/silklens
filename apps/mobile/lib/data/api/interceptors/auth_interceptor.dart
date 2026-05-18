// Attaches Bearer tokens to outgoing requests. Refresh logic is intentionally
// stubbed; FAZA 2 identity service will fill it in.

import "package:dio/dio.dart";
import "package:silklens/core/storage/secure_token_storage.dart";

class AuthInterceptor extends Interceptor {
  AuthInterceptor({required this.tokenStorage});

  final SecureTokenStorage tokenStorage;

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    // Skip auth endpoints (register, login, refresh) — they mustn't be
    // forced to carry stale tokens.
    if (_isAuthEndpoint(options.path)) {
      handler.next(options);
      return;
    }
    final token = await tokenStorage.readAccessToken();
    if (token != null && token.isNotEmpty) {
      options.headers["Authorization"] = "Bearer $token";
    }
    handler.next(options);
  }

  bool _isAuthEndpoint(String path) =>
      path.contains("/auth/login") ||
      path.contains("/auth/register") ||
      path.contains("/auth/refresh");
}
