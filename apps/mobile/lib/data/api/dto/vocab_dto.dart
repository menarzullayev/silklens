// Wire DTOs for `GET /v1/vocab/{slug}` — mirrors `VocabOut` /
// `VocabTermOut` from services/api/src/api/routers/public_meta.py.
//
// Heritage list/detail screens use heritage_kinds; profile language picker
// uses `languages`. Both share the same shape.

import "package:freezed_annotation/freezed_annotation.dart";

part "vocab_dto.freezed.dart";
part "vocab_dto.g.dart";

@freezed
class VocabTermDto with _$VocabTermDto {
  const factory VocabTermDto({
    required String slug,
    @JsonKey(name: "display_name")
    @Default(<String, String>{})
    Map<String, String> displayName,
    @Default(<String, String>{}) Map<String, String> description,
    @JsonKey(name: "parent_slug") String? parentSlug,
    @JsonKey(name: "sort_order") @Default(0) int sortOrder,
  }) = _VocabTermDto;

  factory VocabTermDto.fromJson(Map<String, dynamic> json) =>
      _$VocabTermDtoFromJson(json);
}

@freezed
class VocabDto with _$VocabDto {
  const factory VocabDto({
    @JsonKey(name: "vocabulary_slug") required String vocabularySlug,
    @JsonKey(name: "is_hierarchical") @Default(false) bool isHierarchical,
    @Default(<VocabTermDto>[]) List<VocabTermDto> items,
  }) = _VocabDto;

  factory VocabDto.fromJson(Map<String, dynamic> json) =>
      _$VocabDtoFromJson(json);
}
