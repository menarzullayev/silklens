import "package:freezed_annotation/freezed_annotation.dart";

part "review.freezed.dart";

/// User-generated review of a heritage item. CRDT mode for `text` is
/// `LWW + optimistic lock` per Master Architecture §8.
@freezed
class Review with _$Review {
  const factory Review({
    required String id,
    required String heritageId,
    required String authorId,
    required int rating,
    String? text,
    DateTime? createdAt,
    DateTime? updatedAt,
    String? hlcStamp,
  }) = _Review;
}
