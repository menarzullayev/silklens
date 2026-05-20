// Dio singleton, fully wired with interceptors.
//
// Per ADR-0003 (mirrored on mobile), the data layer is the only place that
// knows about Dio. Repositories see `dio` but the domain never does.

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:pretty_dio_logger/pretty_dio_logger.dart';
import 'package:silklens/core/env/app_environment.dart';
import 'package:silklens/core/storage/secure_token_storage.dart';
import 'package:silklens/data/api/interceptors/auth_interceptor.dart';
import 'package:silklens/data/api/interceptors/error_interceptor.dart';
import 'package:silklens/data/api/interceptors/telemetry_interceptor.dart';
import 'package:silklens/presentation/router/app_router.dart';

Dio buildDio({
  required AppEnvironment env,
  required SecureTokenStorage tokenStorage,
  OnSessionLost? onSessionLost,
}) {
  final dio = Dio(
    BaseOptions(
      baseUrl: env.apiBaseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 30),
      sendTimeout: const Duration(seconds: 30),
      headers: <String, String>{
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-Client': 'silklens-mobile',
      },
    ),
  );

  dio.interceptors.addAll(<Interceptor>[
    AuthInterceptor(
      tokenStorage: tokenStorage,
      refreshBaseUrl: env.apiBaseUrl,
      onSessionLost: onSessionLost,
    ),
    TelemetryInterceptor(),
    ErrorInterceptor(),
    if (kDebugMode)
      PrettyDioLogger(
        requestHeader: true,
        requestBody: true,
        responseBody: false,
        maxWidth: 100,
      ),
  ]);

  return dio;
}

final Provider<Dio> dioProvider = Provider<Dio>(
  (Ref ref) => buildDio(
    env: ref.watch(appEnvironmentProvider),
    tokenStorage: ref.watch(secureTokenStorageProvider),
    // Read the router lazily inside the callback to avoid a dependency cycle:
    // dioProvider → appRouterProvider would form a circular graph because the
    // router itself may depend on auth state.  ref.read() inside an async
    // callback is safe — the provider is already built by the time the
    // interceptor fires.
    onSessionLost: () async {
      ref.read(appRouterProvider).go('/auth/choice');
    },
  ),
  name: 'dioProvider',
);
