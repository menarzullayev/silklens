// Pure-Dart heritage entity. No Flutter, no Isar, no Dio imports here —
// this layer must compile against `dart:core` alone (per ADR-0003 mirrored
// on mobile).

import "package:freezed_annotation/freezed_annotation.dart";

part "heritage.freezed.dart";

@freezed
class Heritage with _$Heritage {
  const factory Heritage({
    required String id,
    required String name,
    String? description,
    double? latitude,
    double? longitude,
    @Default(<String>[]) List<String> mediaUrls,
    String? regionId,
    String? languageCode,
  }) = _Heritage;

  const Heritage._();

  bool get hasGeolocation => latitude != null && longitude != null;
}
