// Offline cache row for a heritage item.
//
// Backs two use cases:
//   * L1 — every list/detail fetch is mirrored so the next cold-boot has
//     a fast first paint (saved=false).
//   * L2 — user-pinned ("Saved") rows that survive even when the API isn't
//     reachable (saved=true).
//
// jsonb-i18n fields (name / summary_md / description_md / tags) are stored
// as JSON strings; the repository decodes them when hydrating Heritage.

import "package:isar/isar.dart";

part "cached_heritage.g.dart";

@collection
class CachedHeritage {
  CachedHeritage({
    required this.heritageId,
    required this.kindSlug,
    this.nameJson = "{}",
    this.summaryMdJson = "{}",
    this.descriptionMdJson = "{}",
    this.tagsJson = "[]",
    this.status = "draft",
    this.countryCode,
    this.latitude,
    this.longitude,
    this.periodStartYear,
    this.periodEndYear,
    this.unescoInscriptionYear,
    this.heroMediaUrl,
    this.revision = 0,
    this.saved = false,
    this.cachedAt,
  });

  Id id = Isar.autoIncrement;

  @Index(unique: true, replace: true)
  late String heritageId;

  late String kindSlug;

  late String nameJson;
  late String summaryMdJson;
  late String descriptionMdJson;
  late String tagsJson;

  String status;
  String? countryCode;
  double? latitude;
  double? longitude;
  int? periodStartYear;
  int? periodEndYear;
  int? unescoInscriptionYear;
  String? heroMediaUrl;
  int revision;

  @Index()
  bool saved;

  DateTime? cachedAt;
}
