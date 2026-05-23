// Stamps every request with a correlation id and (later) feeds
// Sentry breadcrumbs. Kept tiny so it can be wired in tests.

import 'dart:math';

import 'package:dio/dio.dart';

class TelemetryInterceptor extends Interceptor {
  TelemetryInterceptor({Random? random}) : _random = random ?? Random.secure();

  final Random _random;

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    options.headers['X-Request-Id'] = _generateId();
    handler.next(options);
  }

  String _generateId() {
    final bytes = List<int>.generate(16, (_) => _random.nextInt(256));
    return bytes.map((int b) => b.toRadixString(16).padLeft(2, '0')).join();
  }
}
