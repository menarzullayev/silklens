// Single row on a leaderboard. Backend returns them ordered by rank ASC.

import "package:freezed_annotation/freezed_annotation.dart";

part "leaderboard_entry.freezed.dart";

enum LeaderboardScope { weekly, monthly, allTime, friends }

@freezed
class LeaderboardEntry with _$LeaderboardEntry {
  const factory LeaderboardEntry({
    required int rank,
    required String userPubId,
    required String displayName,
    required int score,
    String? avatarUrl,
    String? country,
    @Default(false) bool isMe,
  }) = _LeaderboardEntry;
}
