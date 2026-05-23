class Heritage {
  const Heritage({
    required this.id,
    required this.pubId,
    required this.kindSlug,
    required this.name,
    required this.summaryMd,
    required this.descriptionMd,
    required this.tags,
    required this.status,
    this.countryCode,
    this.adminPath,
    this.latitude,
    this.longitude,
    this.periodStartYear,
    this.periodEndYear,
    this.heroMediaId,
    this.confidenceScore = 0,
    this.revision = 1,
    this.isSaved = false,
  });

  factory Heritage.fromJson(Map<String, dynamic> j) => Heritage(
        id: j['id'] as String,
        pubId: j['pub_id'] as String,
        kindSlug: j['kind_slug'] as String,
        name: (j['name'] as Map?)?.cast<String, String>() ?? {},
        summaryMd: (j['summary_md'] as Map?)?.cast<String, String>() ?? {},
        descriptionMd: (j['description_md'] as Map?)?.cast<String, String>() ?? {},
        tags: (j['tags'] as List?)?.cast<String>() ?? [],
        status: j['status'] as String? ?? 'published',
        countryCode: j['country_code'] as String?,
        adminPath: j['admin_path'] as String?,
        latitude: (j['latitude'] as num?)?.toDouble(),
        longitude: (j['longitude'] as num?)?.toDouble(),
        periodStartYear: j['period_start_year'] as int?,
        periodEndYear: j['period_end_year'] as int?,
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
  final String? adminPath;
  final double? latitude;
  final double? longitude;
  final int? periodStartYear;
  final int? periodEndYear;
  final String? heroMediaId;
  final int confidenceScore;
  final int revision;
  final bool isSaved;

  String localizedName(String lang) =>
      name[lang] ?? name['en'] ?? name['uz'] ?? name.values.firstOrNull ?? pubId;

  String localizedSummary(String lang) =>
      summaryMd[lang] ?? summaryMd['en'] ?? summaryMd.values.firstOrNull ?? '';

  String localizedDescription(String lang) =>
      descriptionMd[lang] ?? descriptionMd['en'] ?? descriptionMd.values.firstOrNull ?? '';
  String? get heroMediaUrl => null; // resolved by media service in FAZA 2+
  bool get hasGeolocation => latitude != null && longitude != null;
  String get periodLabel {
    if (periodStartYear == null) return '';
    if (periodEndYear == null) return periodStartYear.toString();
    return r'$periodStartYear – $periodEndYear';
  }

  bool get isUnescoListed => false; // from heritage_facts in FAZA 2+
  int? get unescoInscriptionYear => null;
  String get description => descriptionMd['en'] ?? descriptionMd.values.firstOrNull ?? '';
  Heritage copyWith({bool? isSaved}) => Heritage(
        id: id,
        pubId: pubId,
        kindSlug: kindSlug,
        name: name,
        summaryMd: summaryMd,
        descriptionMd: descriptionMd,
        tags: tags,
        status: status,
        countryCode: countryCode,
        adminPath: adminPath,
        latitude: latitude,
        longitude: longitude,
        periodStartYear: periodStartYear,
        periodEndYear: periodEndYear,
        heroMediaId: heroMediaId,
        confidenceScore: confidenceScore,
        revision: revision,
        isSaved: isSaved ?? this.isSaved,
      );
}

class HeritageFilters {
  const HeritageFilters({
    this.kindSlug,
    this.countryCode,
    this.status,
    this.search,
    this.limit = 20,
    this.offset = 0,
  });
  final String? kindSlug;
  final String? countryCode;
  final String? status;
  final String? search;
  final int limit;
  final int offset;

  HeritageFilters copyWith({
    String? kindSlug,
    String? countryCode,
    String? status,
    String? search,
    int? limit,
    int? offset,
  }) =>
      HeritageFilters(
        kindSlug: kindSlug ?? this.kindSlug,
        countryCode: countryCode ?? this.countryCode,
        status: status ?? this.status,
        search: search ?? this.search,
        limit: limit ?? this.limit,
        offset: offset ?? this.offset,
      );
}

class HeritagePage {
  const HeritagePage({
    required this.items,
    required this.total,
    required this.limit,
    required this.offset,
  });
  final List<Heritage> items;
  final int total;
  final int limit;
  final int offset;

  bool get hasMore => offset + items.length < total;
}
