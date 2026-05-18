// Tenant branding payload (Project-Decisions §1, §21).
// Drives the dynamic app name, colors, and theme tokens from the admin panel.

import "package:freezed_annotation/freezed_annotation.dart";

part "tenant_branding_dto.freezed.dart";
part "tenant_branding_dto.g.dart";

@freezed
class TenantBrandingDto with _$TenantBrandingDto {
  const factory TenantBrandingDto({
    required String tenantId,
    required String appName,
    String? primaryColorHex,
    String? secondaryColorHex,
    String? accentColorHex,
    String? logoUrl,
    String? splashImageUrl,
    @Default("light") String defaultThemeMode,
    @Default(false) bool nationalAccents,
  }) = _TenantBrandingDto;

  factory TenantBrandingDto.fromJson(Map<String, dynamic> json) =>
      _$TenantBrandingDtoFromJson(json);
}
