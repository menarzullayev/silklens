import "package:freezed_annotation/freezed_annotation.dart";
import "package:silklens/domain/identity/entities/auth_user.dart";

part "auth_session.freezed.dart";
part "auth_session.g.dart";

@freezed
class AuthSession with _$AuthSession {
  const factory AuthSession({
    required AuthUser user,
    required String accessToken,
    required String refreshToken,
    required DateTime expiresAt,
    @Default("Bearer") String tokenType,
  }) = _AuthSession;

  const AuthSession._();

  factory AuthSession.fromJson(Map<String, dynamic> json) =>
      _$AuthSessionFromJson(json);

  bool get isExpired => DateTime.now().toUtc().isAfter(expiresAt);

  /// True ~30s before expiry — used by the auth interceptor to proactively
  /// refresh before the access token actually fails.
  bool get needsRefresh =>
      DateTime.now().toUtc().add(const Duration(seconds: 30)).isAfter(expiresAt);
}
