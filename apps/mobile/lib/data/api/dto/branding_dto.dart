class BrandingDto {
  const BrandingDto({
    required this.tenantSlug,
    required this.appName,
    this.logoUrl,
    this.primaryColor = '#1A3A5C',
    this.themeModeDefault = 'system',
  });
  factory BrandingDto.fromJson(Map<String, dynamic> j) => BrandingDto(
        tenantSlug: j['tenant_slug'] as String? ?? 'silklens',
        appName: (j['app_name'] as Map?)?.cast<String, String>() ??
            {'en': 'SilkLens'},
        logoUrl: j['logo_url'] as String?,
        primaryColor: j['primary_color'] as String? ?? '#1A3A5C',
        themeModeDefault: j['theme_mode_default'] as String? ?? 'system',
      );
  final String tenantSlug;
  final Map<String, String> appName;
  final String? logoUrl;
  final String primaryColor;
  final String themeModeDefault;
}
