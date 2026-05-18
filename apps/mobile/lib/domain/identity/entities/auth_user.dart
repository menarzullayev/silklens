import "package:freezed_annotation/freezed_annotation.dart";

part "auth_user.freezed.dart";

@freezed
class AuthUser with _$AuthUser {
  const factory AuthUser({
    required String id,
    required String email,
    String? displayName,
    String? avatarUrl,
    @Default(<String>[]) List<String> roles,
    @Default("uz") String preferredLanguage,
    DateTime? createdAt,
  }) = _AuthUser;
}
