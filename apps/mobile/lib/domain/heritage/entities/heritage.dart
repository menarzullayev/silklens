// Pure-Dart heritage entity. No Flutter, no Isar, no Dio imports here —
// this layer must compile against `dart:core` alone (per ADR-0003 mirrored
// on mobile).
//
// The entity mirrors the backend `HeritageOut` schema (see
// `services/api/src/api/routers/heritage.py`). Localized fields (`name`,
// `summary_md`, `description_md`) are jsonb maps keyed by BCP-47 language
// tag — we keep the same shape on the client so the presentation layer can
// pick the right translation reactively to the active locale.

import "package:freezed_annotation/freezed_annotation.dart";

part "heritage.freezed.dart";

@freezed
class Heritage with _$Heritage {
  const factory Heritage({
    required String id,
    required String pubId,
    required String kindSlug,
    required Map<String, String> name,
    @Default(<String, String>{}) Map<String, String> summaryMd,
    @Default(<String, String>{}) Map<String, String> descriptionMd,
    @Default(<String>[]) List<String> tags,
    @Default("draft") String status,
    String? countryCode,
    String? adminPath,
    double? latitude,
    double? longitude,
    int? periodStartYear,
    int? periodEndYear,
    int? unescoInscriptionYear,
    String? heroMediaUrl,
    @Default(0) int confidenceScore,
    @Default(0) int revision,
    @Default(<String>[]) List<String> mediaUrls,
  }) = _Heritage;

  const Heritage._();

  /// Convenience accessor for the legacy single-string id (== pubId on
  /// the wire). The list-page hero key and Isar cache use this.
  String get heritageId => pubId;

  bool get hasGeolocation => latitude != null && longitude != null;
  bool get isPublished => status == "published";
  bool get isUnescoListed => unescoInscriptionYear != null;

  /// Returns the localized name for [languageCode], falling back to
  /// English, then to any available translation. Empty string only if the
  /// entity has no name map at all (which should never happen in practice
  /// — `name` is non-null on the backend).
  String localizedName(String languageCode) =>
      _pick(name, languageCode);

  String localizedSummary(String languageCode) =>
      _pick(summaryMd, languageCode);

  String localizedDescription(String languageCode) =>
      _pick(descriptionMd, languageCode);

  /// Display-ready period label, e.g. "1417 – 1420" or "9th c. BCE".
  String? get periodLabel {
    final start = periodStartYear;
    final end = periodEndYear;
    if (start == null && end == null) return null;
    if (start != null && end != null && start != end) {
      return "${_yearLabel(start)} – ${_yearLabel(end)}";
    }
    final canonical = start ?? end!;
    return _yearLabel(canonical);
  }

  static String _yearLabel(int y) =>
      y < 0 ? "${-y} BCE" : y.toString();

  static String _pick(Map<String, String> bag, String code) {
    if (bag.isEmpty) return "";
    final exact = bag[code];
    if (exact != null && exact.isNotEmpty) return exact;
    final fallback = bag["en"] ?? bag["uz"] ?? bag["ru"] ?? bag["zh"];
    if (fallback != null && fallback.isNotEmpty) return fallback;
    return bag.values.firstWhere(
      (String v) => v.isNotEmpty,
      orElse: () => "",
    );
  }
}

/// Filters accepted by the list endpoint. Mirrors backend `HeritageFilters`.
@freezed
class HeritageFilters with _$HeritageFilters {
  const factory HeritageFilters({
    String? kindSlug,
    String? countryCode,
    String? status,
    String? search,
    @Default(20) int limit,
    @Default(0) int offset,
  }) = _HeritageFilters;
}

/// Paged response envelope — keeps total + offset visible so the
/// presentation layer can drive infinite scroll without round-tripping.
@freezed
class HeritagePage with _$HeritagePage {
  const factory HeritagePage({
    required List<Heritage> items,
    required int total,
    required int limit,
    required int offset,
  }) = _HeritagePage;

  const HeritagePage._();

  bool get hasMore => offset + items.length < total;
}
