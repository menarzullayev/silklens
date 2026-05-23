// Domain-level failure types.
//
// Domain code never throws DioException or PostgrestException — those are
// adapter concerns. Adapters translate them into one of these.

import 'package:meta/meta.dart';

@immutable
sealed class Failure {
  const Failure(this.message, {this.cause, this.stackTrace});

  final String message;
  final Object? cause;
  final StackTrace? stackTrace;

  // Subclasses override to expose a stable name (runtimeType is mangled
  // by Flutter's tree-shake/minifier in release builds).
  String get _name => 'Failure';

  @override
  String toString() => '$_name($message)';
}

class NetworkFailure extends Failure {
  const NetworkFailure(super.message, {super.cause, super.stackTrace});
  @override
  String get _name => 'NetworkFailure';
}

class ServerFailure extends Failure {
  const ServerFailure(
    super.message, {
    this.statusCode,
    super.cause,
    super.stackTrace,
  });

  final int? statusCode;

  @override
  String get _name => 'ServerFailure';
}

class AuthFailure extends Failure {
  const AuthFailure(super.message, {super.cause, super.stackTrace});
  @override
  String get _name => 'AuthFailure';
}

class CacheFailure extends Failure {
  const CacheFailure(super.message, {super.cause, super.stackTrace});
  @override
  String get _name => 'CacheFailure';
}

class ValidationFailure extends Failure {
  const ValidationFailure(super.message,
      {this.fieldErrors = const <String, String>{}});

  final Map<String, String> fieldErrors;

  @override
  String get _name => 'ValidationFailure';
}

class UnknownFailure extends Failure {
  const UnknownFailure(super.message, {super.cause, super.stackTrace});
  @override
  String get _name => 'UnknownFailure';
}
