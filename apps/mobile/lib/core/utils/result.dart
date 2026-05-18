// Minimal `Result<S, F>` for use-case return values.
//
// We deliberately avoid pulling in `dartz` or `fpdart` — Dart 3 sealed
// classes give us exhaustive pattern matching for free.

import "package:meta/meta.dart";
import "package:silklens/core/error/failures.dart";

@immutable
sealed class Result<S> {
  const Result();

  bool get isSuccess => this is Success<S>;
  bool get isFailure => this is FailureResult<S>;

  S? get successOrNull => switch (this) {
        Success<S>(:final value) => value,
        FailureResult<S>() => null,
      };

  Failure? get failureOrNull => switch (this) {
        Success<S>() => null,
        FailureResult<S>(:final failure) => failure,
      };

  R fold<R>({
    required R Function(S value) onSuccess,
    required R Function(Failure failure) onFailure,
  }) =>
      switch (this) {
        Success<S>(:final value) => onSuccess(value),
        FailureResult<S>(:final failure) => onFailure(failure),
      };
}

class Success<S> extends Result<S> {
  const Success(this.value);
  final S value;
}

class FailureResult<S> extends Result<S> {
  const FailureResult(this.failure);
  final Failure failure;
}
