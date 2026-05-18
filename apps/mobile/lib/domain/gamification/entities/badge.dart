// Badge — both unlocked and locked badges are returned by /v1/me/badges; the
// `unlockedAt` field is null for locked entries and `criterionHint` is used
// in the locked-state UI.

import "package:freezed_annotation/freezed_annotation.dart";

part "badge.freezed.dart";

@freezed
class Badge with _$Badge {
  const factory Badge({
    required String slug,
    required String name,
    required String description,
    String? iconUrl,
    DateTime? unlockedAt,
    String? criterionHint,
    @Default(0) int xpValue,
  }) = _Badge;

  const Badge._();

  bool get isUnlocked => unlockedAt != null;
}
