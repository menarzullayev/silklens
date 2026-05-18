// Dio singleton, fully wired with interceptors.
//
// Per ADR-0003 (mirrored on mobile), the data layer is the only place that
// knows about Dio. Repositories see `dio` but the domain never does.

import "package:dio/dio.dart";
import "package:flutter/foundation.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:pretty_dio_logger/pretty_dio_logger.dart";
import "package:silklens/core/env/app_environment.dart";
import "package:silklens/core/storage/secure_token_storage.dart";
import "package:silklens/data/api/interceptors/auth_interceptor.dart";
import "package:silklens/data/api/interceptors/error_interceptor.dart";
import "package:silklens/data/api/interceptors/telemetry_interceptor.dart";

Dio buildDio({
  required AppEnvironment env,
  required SecureTokenStorage tokenStorage,
}) {
  final dio = Dio(
    BaseOptions(
      baseUrl: env.apiBaseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 30),
      sendTimeout: const Duration(seconds: 30),
      headers: <String, String>{
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Client": "silklens-mobile",
      },
    ),
  );

  dio.interceptors.addAll(<Interceptor>[
    AuthInterceptor(tokenStorage: tokenStorage),
    TelemetryInterceptor(),
    ErrorInterceptor(),
    if (kDebugMode)
      PrettyDioLogger(
        requestHeader: true,
        requestBody: true,
        responseHeader: false,
        responseBody: false,
        compact: true,
        maxWidth: 100,
      ),
  ]);

  return dio;
}

final Provider<Dio> dioProvider = Provider<Dio>(
  (Ref ref) => buildDio(
    env: ref.watch(appEnvironmentProvider),
    tokenStorage: ref.watch(secureTokenStorageProvider),
  ),
  name: "dioProvider",
);
