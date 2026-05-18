// Persistent cache for the `/v1/branding` response so we can paint a
// branded splash on cold-boot even without network access.

import "package:isar/isar.dart";

part "cached_branding.g.dart";

@collection
class CachedBranding {
  CachedBranding({
    required this.tenantSlug,
    required this.appNameJson,
    this.logoUrl,
    this.logoDarkUrl,
    this.primaryColorHex,
    this.accentColorHex,
    this.splashUrl,
    this.fontFamily,
    this.themeModeDefault = "system",
    this.extraJson = "{}",
    this.fetchedAt,
  });

  Id id = Isar.autoIncrement;

  @Index(unique: true, replace: true)
  late String tenantSlug;

  late String appNameJson;
  String? logoUrl;
  String? logoDarkUrl;
  String? primaryColorHex;
  String? accentColorHex;
  String? splashUrl;
  String? fontFamily;
  String themeModeDefault;
  String extraJson;

  DateTime? fetchedAt;
}
