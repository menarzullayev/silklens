import "package:freezed_annotation/freezed_annotation.dart";

part "auth_user.freezed.dart";
part "auth_user.g.dart";

@freezed
class AuthUser with _$AuthUser {
  const factory AuthUser({
    required String id,
    @JsonKey(name: "pub_id") required String pubId,
    @JsonKey(name: "tenant_id") required String tenantId,
    @JsonKey(name: "residency_region")
    @Default("global")
    String residencyRegion,
    String? email,
    @JsonKey(name: "display_name") String? displayName,
    @JsonKey(name: "avatar_url") String? avatarUrl,
    @Default(<String>[]) List<String> roles,
    @JsonKey(name: "trust_tier") @Default("anonymous") String trustTier,
    @JsonKey(name: "preferred_locale") @Default("uz") String preferredLocale,
    @JsonKey(name: "preferred_timezone") @Default("UTC") String preferredTimezone,
    @JsonKey(name: "is_verified") @Default(false) bool isVerified,
    @JsonKey(name: "created_at") DateTime? createdAt,
  }) = _AuthUser;

  const AuthUser._();

  factory AuthUser.fromJson(Map<String, dynamic> json) =>
      _$AuthUserFromJson(json);

  bool get isAuthenticated => trustTier != "anonymous";
  String get preferredLanguage => preferredLocale.split("-").first;
}
