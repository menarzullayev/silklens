// Offline cache row for a heritage item.
//
// Mirrors `HeritageDto` but stores only what the home / map / detail
// pages need without a network round-trip.

import "package:isar/isar.dart";

part "cached_heritage.g.dart";

@collection
class CachedHeritage {
  CachedHeritage({
    required this.heritageId,
    required this.name,
    this.description,
    this.latitude,
    this.longitude,
    this.regionId,
    this.languageCode,
    this.cachedAt,
  });

  Id id = Isar.autoIncrement;

  @Index(unique: true, replace: true)
  late String heritageId;

  late String name;
  String? description;
  double? latitude;
  double? longitude;
  String? regionId;

  @Index()
  String? languageCode;

  DateTime? cachedAt;
}
