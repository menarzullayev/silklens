// Gamification contract — XP, badges, streaks, leaderboards. Mapped onto
// /v1/me/xp, /v1/me/badges, /v1/me/streak, /v1/leaderboards/*.

import "package:silklens/core/utils/result.dart";
import "package:silklens/domain/gamification/entities/badge.dart";
import "package:silklens/domain/gamification/entities/leaderboard_entry.dart";
import "package:silklens/domain/gamification/entities/xp_summary.dart";

abstract interface class GamificationRepository {
  Future<Result<XpSummary>> xpSummary();

  Future<Result<List<Badge>>> badges();

  Future<Result<List<LeaderboardEntry>>> leaderboard({
    required LeaderboardScope scope,
    int page = 1,
    int pageSize = 50,
  });
}
