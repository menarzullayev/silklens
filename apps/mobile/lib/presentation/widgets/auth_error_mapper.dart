// Maps domain [Failure] values into a localized user-facing message.
// Centralized so sign-in / sign-up / forgot-password show consistent copy.

import "package:silklens/core/error/failures.dart";
import "package:silklens/l10n/app_localizations.dart";

String mapFailure(Failure failure, AppLocalizations? l10n) {
  // Server errors with backend codes -- pull from the cause when present.
  final cause = failure.cause;
  String? code;
  if (cause != null) {
    final asString = cause.toString();
    final match = RegExp(r"identity\.[a-z_]+").firstMatch(asString);
    if (match != null) code = match.group(0);
  }

  switch (code) {
    case "identity.invalid_credentials":
      return l10n?.authErrorInvalidCredentials ?? "Invalid credentials";
    case "identity.rate_limited":
      return l10n?.authErrorRateLimited ?? "Too many attempts";
    case "identity.email_taken":
    case "identity.email_in_use":
      return l10n?.authErrorEmailTaken ?? "Email already in use";
    case "identity.weak_password":
      return l10n?.authErrorPasswordWeak ?? "Password too weak";
  }

  if (failure is NetworkFailure) {
    return l10n?.authErrorNetwork ?? "Network error";
  }
  if (failure is ValidationFailure) {
    if (failure.fieldErrors.isNotEmpty) {
      return failure.fieldErrors.values.first;
    }
    return failure.message;
  }
  if (failure is AuthFailure) {
    return l10n?.authErrorInvalidCredentials ?? failure.message;
  }
  if (failure is ServerFailure) {
    if (failure.statusCode == 429) {
      return l10n?.authErrorRateLimited ?? "Rate limited";
    }
    if (failure.statusCode == 409) {
      return l10n?.authErrorEmailTaken ?? "Email taken";
    }
  }
  return l10n?.authErrorUnknown ?? "Something went wrong";
}
