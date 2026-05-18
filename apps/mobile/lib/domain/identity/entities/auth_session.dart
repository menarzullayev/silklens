import "package:freezed_annotation/freezed_annotation.dart";
import "package:silklens/domain/identity/entities/auth_user.dart";

part "auth_session.freezed.dart";

@freezed
class AuthSession with _$AuthSession {
  const factory AuthSession({
    required AuthUser user,
    required String accessToken,
    required String refreshToken,
    required DateTime expiresAt,
  }) = _AuthSession;

  const AuthSession._();

  bool get isExpired => DateTime.now().toUtc().isAfter(expiresAt);
}
