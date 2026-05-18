// Current XP + level + streak for the authenticated user. Mapped from
// /v1/me/xp + /v1/me/streak.

import "package:freezed_annotation/freezed_annotation.dart";

part "xp_summary.freezed.dart";

@freezed
class XpSummary with _$XpSummary {
  const factory XpSummary({
    required int totalXp,
    required int level,
    required int xpIntoCurrentLevel,
    required int xpForNextLevel,
    @Default(0) int streakDays,
    DateTime? lastActiveDate,
  }) = _XpSummary;

  const XpSummary._();

  double get levelProgress {
    if (xpForNextLevel <= 0) return 1;
    return (xpIntoCurrentLevel / xpForNextLevel).clamp(0.0, 1.0);
  }
}
