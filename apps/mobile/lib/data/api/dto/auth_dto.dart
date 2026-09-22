// Plain Dart DTOs for /v1/auth/* endpoints — no code generation needed.
// Mirrors auth.py response schemas.

class RegisterRequestDto {
  const RegisterRequestDto({
    required this.email,
    required this.password,
    this.displayName,
    this.preferredLocale = 'en',
    this.preferredTimezone = 'UTC',
    this.residencyRegion = 'global',
  });

  final String email;
  final String password;
  final String? displayName;
  final String preferredLocale;
  final String preferredTimezone;
  final String residencyRegion;

  Map<String, dynamic> toJson() => {
        'email': email,
        'password': password,
        if (displayName != null) 'display_name': displayName,
        'preferred_locale': preferredLocale,
        'preferred_timezone': preferredTimezone,
        'residency_region': residencyRegion,
      };
}

class LoginRequestDto {
  const LoginRequestDto({required this.email, required this.password});
  final String email;
  final String password;
  Map<String, dynamic> toJson() => {'email': email, 'password': password};
}

class RefreshRequestDto {
  const RefreshRequestDto({required this.refreshToken});
  final String refreshToken;
  Map<String, dynamic> toJson() => {'refresh_token': refreshToken};
}

class TokenBundleDto {
  const TokenBundleDto({
    required this.accessToken,
    required this.refreshToken,
    this.tokenType = 'Bearer',
    this.expiresIn = 900,
  });

  factory TokenBundleDto.fromJson(Map<String, dynamic> j) => TokenBundleDto(
        accessToken: j['access_token'] as String,
        refreshToken: j['refresh_token'] as String,
        tokenType: j['token_type'] as String? ?? 'Bearer',
        expiresIn: j['expires_in'] as int? ?? 900,
      );
  final String accessToken;
  final String refreshToken;
  final String tokenType;
  final int expiresIn;
}

class UserDto {
  const UserDto({
    required this.id,
    required this.pubId,
    required this.tenantId,
    required this.residencyRegion,
    this.trustTier = 'new',
    this.preferredLocale = 'en',
    this.isVerified = false,
  });

  factory UserDto.fromJson(Map<String, dynamic> j) => UserDto(
        id: j['id'] as String,
        pubId: j['pub_id'] as String,
        tenantId: j['tenant_id'] as String,
        residencyRegion: j['residency_region'] as String,
        trustTier: j['trust_tier'] as String? ?? 'new',
        preferredLocale: j['preferred_locale'] as String? ?? 'en',
        isVerified: j['is_verified'] as bool? ?? false,
      );
  final String id;
  final String pubId;
  final String tenantId;
  final String residencyRegion;
  final String trustTier;
  final String preferredLocale;
  final bool isVerified;
}

class LoginResponseDto {
  const LoginResponseDto({required this.user, required this.tokens});

  factory LoginResponseDto.fromJson(Map<String, dynamic> j) => LoginResponseDto(
        user: UserDto.fromJson(j['user'] as Map<String, dynamic>),
        tokens: TokenBundleDto.fromJson(j['tokens'] as Map<String, dynamic>),
      );
  final UserDto user;
  final TokenBundleDto tokens;
}

class MeResponseDto {
  const MeResponseDto({
    required this.user,
    required this.sessionId,
    required this.trustTier,
  });

  factory MeResponseDto.fromJson(Map<String, dynamic> j) => MeResponseDto(
        user: UserDto.fromJson(j['user'] as Map<String, dynamic>),
        sessionId: j['session_id'] as String,
        trustTier: j['trust_tier'] as String,
      );
  final UserDto user;
  final String sessionId;
  final String trustTier;
}

class LogoutResponseDto {
  const LogoutResponseDto({this.status = 'ok'});
  factory LogoutResponseDto.fromJson(Map<String, dynamic> j) =>
      LogoutResponseDto(status: j['status'] as String? ?? 'ok');
  final String status;
}

class VerifyEmailRequestDto {
  const VerifyEmailRequestDto({required this.email, required this.code});
  final String email;
  final String code;
  Map<String, dynamic> toJson() => {'email': email, 'code': code};
}

class VerifyEmailResponseDto {
  const VerifyEmailResponseDto({required this.verified});
  factory VerifyEmailResponseDto.fromJson(Map<String, dynamic> j) =>
      VerifyEmailResponseDto(verified: j['verified'] as bool? ?? false);
  final bool verified;
}

class ResendVerificationRequestDto {
  const ResendVerificationRequestDto({required this.email});
  final String email;
  Map<String, dynamic> toJson() => {'email': email};
}

class ResendVerificationResponseDto {
  const ResendVerificationResponseDto({required this.sent});
  factory ResendVerificationResponseDto.fromJson(Map<String, dynamic> j) =>
      ResendVerificationResponseDto(sent: j['sent'] as bool? ?? false);
  final bool sent;
}
