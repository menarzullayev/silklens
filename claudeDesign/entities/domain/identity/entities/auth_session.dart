import 'package:silklens/domain/identity/entities/auth_user.dart';

class AuthSession {
  const AuthSession({
    required this.accessToken,
    required this.refreshToken,
    required this.user,
    this.expiresIn = 900,
    this.tokenType = 'Bearer',
    this.expiresAt,
    this.email,
  });
  final String accessToken;
  final String refreshToken;
  final AuthUser user;
  final int expiresIn;
  final String tokenType;
  final DateTime? expiresAt;
  final String? email;

  bool get isExpired {
    if (expiresAt == null) return false;
    return DateTime.now().isAfter(expiresAt!);
  }
}
