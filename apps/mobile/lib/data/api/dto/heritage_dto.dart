class HeritageDto {
  const HeritageDto({
    required this.id,
    required this.pubId,
    required this.kindSlug,
    required this.name,
    this.summaryMd = const {},
    this.descriptionMd = const {},
    this.tags = const [],
    this.status = 'published',
    this.countryCode,
    this.latitude,
    this.longitude,
    this.periodStartYear,
    this.heroMediaId,
    this.confidenceScore = 0,
    this.revision = 1,
  });
  factory HeritageDto.fromJson(Map<String, dynamic> j) => HeritageDto(
        id: j['id'] as String,
        pubId: j['pub_id'] as String,
        kindSlug: j['kind_slug'] as String,
        name: (j['name'] as Map?)?.cast<String, String>() ?? {},
        summaryMd: (j['summary_md'] as Map?)?.cast<String, String>() ?? {},
        descriptionMd:
            (j['description_md'] as Map?)?.cast<String, String>() ?? {},
        tags: (j['tags'] as List?)?.cast<String>() ?? [],
        status: j['status'] as String? ?? 'published',
        countryCode: j['country_code'] as String?,
        latitude: (j['latitude'] as num?)?.toDouble(),
        longitude: (j['longitude'] as num?)?.toDouble(),
        periodStartYear: j['period_start_year'] as int?,
        heroMediaId: j['hero_media_id'] as String?,
        confidenceScore: j['confidence_score'] as int? ?? 0,
        revision: j['revision'] as int? ?? 1,
      );
  final String id;
  final String pubId;
  final String kindSlug;
  final Map<String, String> name;
  final Map<String, String> summaryMd;
  final Map<String, String> descriptionMd;
  final List<String> tags;
  final String status;
  final String? countryCode;
  final double? latitude;
  final double? longitude;
  final int? periodStartYear;
  final String? heroMediaId;
  final int confidenceScore;
  final int revision;
}

class HeritagePageDto {
  const HeritagePageDto({
    required this.items,
    required this.total,
    this.limit = 20,
    this.offset = 0,
  });
  factory HeritagePageDto.fromJson(Map<String, dynamic> j) => HeritagePageDto(
        items: (j['items'] as List?)
                ?.map((e) => HeritageDto.fromJson(e as Map<String, dynamic>))
                .toList() ??
            [],
        total: j['total'] as int? ?? 0,
        limit: j['limit'] as int? ?? 20,
        offset: j['offset'] as int? ?? 0,
      );
  final List<HeritageDto> items;
  final int total;
  final int limit;
  final int offset;
}
