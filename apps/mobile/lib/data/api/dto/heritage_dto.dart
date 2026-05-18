import "package:freezed_annotation/freezed_annotation.dart";

part "heritage_dto.freezed.dart";
part "heritage_dto.g.dart";

@freezed
class HeritageDto with _$HeritageDto {
  const factory HeritageDto({
    required String id,
    required String name,
    String? description,
    double? latitude,
    double? longitude,
    @Default(<String>[]) List<String> mediaUrls,
    String? regionId,
    String? languageCode,
  }) = _HeritageDto;

  factory HeritageDto.fromJson(Map<String, dynamic> json) =>
      _$HeritageDtoFromJson(json);
}
