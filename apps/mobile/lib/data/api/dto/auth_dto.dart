// Wire DTOs for the `/v1/auth/*` endpoints.
//
// Mirrors `RegisterRequest`, `LoginRequest`, `RefreshRequest`,
// `LoginResponse`, `MeResponse`, `LogoutResponse`, `UserOut` and
// `TokenBundle` from services/api/src/api/routers/auth.py.

import "package:freezed_annotation/freezed_annotation.dart";

part "auth_dto.freezed.dart";
part "auth_dto.g.dart";

@freezed
class RegisterRequestDto with _$RegisterRequestDto {
  const factory RegisterRequestDto({
    required String email,
    required String password,
    @JsonKey(name: "display_name") String? displayName,
    @JsonKey(name: "preferred_locale")
    @Default("en")
    String preferredLocale,
    @JsonKey(name: "preferred_timezone")
    @Default("UTC")
    String preferredTimezone,
    @JsonKey(name: "tenant_id") String? tenantId,
    @JsonKey(name: "residency_region")
    @Default("global")
    String residencyRegion,
  }) = _RegisterRequestDto;

  factory RegisterRequestDto.fromJson(Map<String, dynamic> json) =>
      _$RegisterRequestDtoFromJson(json);
}

@freezed
class LoginRequestDto with _$LoginRequestDto {
  const factory LoginRequestDto({
    required String email,
    required String password,
    @JsonKey(name: "tenant_id") String? tenantId,
  }) = _LoginRequestDto;

  factory LoginRequestDto.fromJson(Map<String, dynamic> json) =>
      _$LoginRequestDtoFromJson(json);
}

@freezed
class RefreshRequestDto with _$RefreshRequestDto {
  const factory RefreshRequestDto({
    @JsonKey(name: "refresh_token") required String refreshToken,
  }) = _RefreshRequestDto;

  factory RefreshRequestDto.fromJson(Map<String, dynamic> json) =>
      _$RefreshRequestDtoFromJson(json);
}

@freezed
class TokenBundleDto with _$TokenBundleDto {
  const factory TokenBundleDto({
    @JsonKey(name: "access_token") required String accessToken,
    @JsonKey(name: "refresh_token") required String refreshToken,
    @JsonKey(name: "token_type") @Default("Bearer") String tokenType,
    @JsonKey(name: "expires_in") required int expiresIn,
  }) = _TokenBundleDto;

  factory TokenBundleDto.fromJson(Map<String, dynamic> json) =>
      _$TokenBundleDtoFromJson(json);
}

@freezed
class UserDto with _$UserDto {
  const factory UserDto({
    required String id,
    @JsonKey(name: "pub_id") required String pubId,
    @JsonKey(name: "tenant_id") required String tenantId,
    @JsonKey(name: "residency_region") required String residencyRegion,
    @JsonKey(name: "trust_tier") @Default("anonymous") String trustTier,
    @JsonKey(name: "preferred_locale")
    @Default("en")
    String preferredLocale,
    @JsonKey(name: "preferred_timezone")
    @Default("UTC")
    String preferredTimezone,
    @JsonKey(name: "is_verified") @Default(false) bool isVerified,
    String? email,
    @JsonKey(name: "display_name") String? displayName,
    @JsonKey(name: "avatar_url") String? avatarUrl,
  }) = _UserDto;

  factory UserDto.fromJson(Map<String, dynamic> json) =>
      _$UserDtoFromJson(json);
}

@freezed
class LoginResponseDto with _$LoginResponseDto {
  const factory LoginResponseDto({
    required UserDto user,
    required TokenBundleDto tokens,
  }) = _LoginResponseDto;

  factory LoginResponseDto.fromJson(Map<String, dynamic> json) =>
      _$LoginResponseDtoFromJson(json);
}

@freezed
class MeResponseDto with _$MeResponseDto {
  const factory MeResponseDto({
    required UserDto user,
    @JsonKey(name: "session_id") required String sessionId,
    @JsonKey(name: "trust_tier") required String trustTier,
  }) = _MeResponseDto;

  factory MeResponseDto.fromJson(Map<String, dynamic> json) =>
      _$MeResponseDtoFromJson(json);
}

@freezed
class LogoutResponseDto with _$LogoutResponseDto {
  const factory LogoutResponseDto({
    @Default("ok") String status,
  }) = _LogoutResponseDto;

  factory LogoutResponseDto.fromJson(Map<String, dynamic> json) =>
      _$LogoutResponseDtoFromJson(json);
}
