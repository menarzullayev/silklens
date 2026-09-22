/// Heritage cache entry — plain Dart class (no isar annotations for now).
class CachedHeritage {
  CachedHeritage({
    required this.pubId,
    required this.nameJson,
    required this.summaryJson,
    required this.kindSlug,
    this.countryCode,
    this.latitude,
    this.longitude,
    this.heroMediaId,
    this.status = 'published',
    this.cachedAt,
  });

  final String pubId;
  final String nameJson;
  final String summaryJson;
  final String kindSlug;
  final String? countryCode;
  final double? latitude;
  final double? longitude;
  final String? heroMediaId;
  final String status;
  final DateTime? cachedAt;
}
