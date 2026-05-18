// Wire DTO for `GET /v1/branding`.
//
// Mirrors `BrandingPublicOut` in services/api/src/api/routers/public_meta.py:
//   tenant_slug, app_name (jsonb i18n), logo_url, logo_dark_url,
//   primary_color, accent_color, splash_url, font_family,
//   theme_mode_default, extra (jsonb).

import "package:freezed_annotation/freezed_annotation.dart";

part "branding_dto.freezed.dart";
part "branding_dto.g.dart";

@freezed
class BrandingDto with _$BrandingDto {
  const factory BrandingDto({
    @JsonKey(name: "tenant_slug") required String tenantSlug,
    @JsonKey(name: "app_name")
    @Default(<String, String>{})
    Map<String, String> appName,
    @JsonKey(name: "logo_url") String? logoUrl,
    @JsonKey(name: "logo_dark_url") String? logoDarkUrl,
    @JsonKey(name: "primary_color") String? primaryColor,
    @JsonKey(name: "accent_color") String? accentColor,
    @JsonKey(name: "splash_url") String? splashUrl,
    @JsonKey(name: "font_family") String? fontFamily,
    @JsonKey(name: "theme_mode_default")
    @Default("system")
    String themeModeDefault,
    @Default(<String, dynamic>{}) Map<String, dynamic> extra,
  }) = _BrandingDto;

  factory BrandingDto.fromJson(Map<String, dynamic> json) =>
      _$BrandingDtoFromJson(json);
}
