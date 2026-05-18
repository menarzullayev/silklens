import "package:freezed_annotation/freezed_annotation.dart";

part "version_dto.freezed.dart";
part "version_dto.g.dart";

@freezed
class VersionDto with _$VersionDto {
  const factory VersionDto({
    required String version,
    required String commit,
  }) = _VersionDto;

  factory VersionDto.fromJson(Map<String, dynamic> json) =>
      _$VersionDtoFromJson(json);
}
