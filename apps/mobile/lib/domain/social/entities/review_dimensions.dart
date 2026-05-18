// Multi-dimensional review per backend `review_dimensions` schema. Each
// dimension is a 1–5 star rating; nulls mean "not rated".

import "package:freezed_annotation/freezed_annotation.dart";

part "review_dimensions.freezed.dart";

@freezed
class ReviewDimensions with _$ReviewDimensions {
  const factory ReviewDimensions({
    int? history,
    int? photos,
    int? access,
    int? value,
    int? atmosphere,
    int? familyFriendly,
  }) = _ReviewDimensions;

  const ReviewDimensions._();

  /// True if at least one dimension has been rated.
  bool get hasAnyRating =>
      history != null ||
      photos != null ||
      access != null ||
      value != null ||
      atmosphere != null ||
      familyFriendly != null;
}

@freezed
class ReviewDraft with _$ReviewDraft {
  const factory ReviewDraft({
    required String heritagePubId,
    required ReviewDimensions dimensions,
    String? body,
    @Default("en") String language,
  }) = _ReviewDraft;
}
