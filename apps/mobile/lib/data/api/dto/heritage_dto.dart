// Wire DTO for the heritage endpoints. Mirrors the backend
// `HeritageOut` and `HeritagePageOut` (see services/api/.../heritage.py).
//
// We deliberately keep parsing forgiving — JSONB strings come in as
// Map<String, dynamic> and we coerce to Map<String, String> at the
// boundary. Bad / missing translations degrade to empty strings (the
// presentation layer falls back gracefully).

import "package:freezed_annotation/freezed_annotation.dart";

part "heritage_dto.freezed.dart";
part "heritage_dto.g.dart";

@freezed
class HeritageDto with _$HeritageDto {
  const factory HeritageDto({
    required String id,
    @JsonKey(name: "pub_id") required String pubId,
    @JsonKey(name: "kind_slug") required String kindSlug,
    @Default(<String, String>{}) Map<String, String> name,
    @JsonKey(name: "summary_md")
    @Default(<String, String>{})
    Map<String, String> summaryMd,
    @JsonKey(name: "description_md")
    @Default(<String, String>{})
    Map<String, String> descriptionMd,
    @Default(<String>[]) List<String> tags,
    @Default("draft") String status,
    @JsonKey(name: "country_code") String? countryCode,
    @JsonKey(name: "admin_path") String? adminPath,
    double? latitude,
    double? longitude,
    @JsonKey(name: "period_start_year") int? periodStartYear,
    @JsonKey(name: "period_end_year") int? periodEndYear,
    @JsonKey(name: "unesco_inscription_year") int? unescoInscriptionYear,
    @JsonKey(name: "hero_media_id") String? heroMediaId,
    @JsonKey(name: "hero_media_url") String? heroMediaUrl,
    @JsonKey(name: "confidence_score") @Default(0) int confidenceScore,
    @Default(0) int revision,
    @JsonKey(name: "media_urls") @Default(<String>[]) List<String> mediaUrls,
  }) = _HeritageDto;

  factory HeritageDto.fromJson(Map<String, dynamic> json) =>
      _$HeritageDtoFromJson(json);
}

@freezed
class HeritagePageDto with _$HeritagePageDto {
  const factory HeritagePageDto({
    @Default(<HeritageDto>[]) List<HeritageDto> items,
    @Default(0) int total,
    @Default(20) int limit,
    @Default(0) int offset,
  }) = _HeritagePageDto;

  factory HeritagePageDto.fromJson(Map<String, dynamic> json) =>
      _$HeritagePageDtoFromJson(json);
}
