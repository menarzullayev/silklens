class TenantBrandingDto {
  const TenantBrandingDto(
      {this.appName = 'SilkLens', this.primaryColor = '#1A3A5C'});
  factory TenantBrandingDto.fromJson(Map<String, dynamic> j) =>
      TenantBrandingDto(
        appName: j['app_name'] as String? ?? 'SilkLens',
        primaryColor: j['primary_color'] as String? ?? '#1A3A5C',
      );
  final String appName;
  final String primaryColor;
}
