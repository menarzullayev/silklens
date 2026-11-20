// Normalizes Dio errors before they propagate to repositories.
//
// Repositories translate these (still adapter-level) exceptions into
// domain `Failure` values inside `core/utils/result.dart`.

import 'package:dio/dio.dart';
import 'package:silklens/core/error/exceptions.dart';

class ErrorInterceptor extends Interceptor {
  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    final wrapped = switch (err.type) {
      DioExceptionType.connectionTimeout ||
      DioExceptionType.sendTimeout ||
      DioExceptionType.receiveTimeout =>
        NetworkException('Network timeout: ${err.message}'),
      DioExceptionType.connectionError ||
      DioExceptionType.unknown =>
        NetworkException("Connection error: ${err.message ?? 'unknown'}"),
      DioExceptionType.badResponse => ApiException(
          err.response?.statusMessage ?? 'Bad response',
          statusCode: err.response?.statusCode,
        ),
      DioExceptionType.cancel => ApiException('Request cancelled'),
      DioExceptionType.badCertificate => NetworkException('Bad TLS certificate'),
    };
    handler.reject(
      DioException(
        requestOptions: err.requestOptions,
        error: wrapped,
        type: err.type,
        response: err.response,
        stackTrace: err.stackTrace,
      ),
    );
  }
}
