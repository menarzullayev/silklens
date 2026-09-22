/// Branding cache entry — plain Dart class (no isar annotations for now).
class CachedBranding {
  CachedBranding({
    required this.tenantId,
    required this.appNameJson,
    required this.primaryColor,
    this.logoUrl,
    this.themeModeDefault = 'system',
    this.updatedAt,
  });

  final String tenantId;
  final String appNameJson; // JSON string e.g. '{"en":"SilkLens"}'
  final String primaryColor;
  final String? logoUrl;
  final String themeModeDefault;
  final DateTime? updatedAt;
}
