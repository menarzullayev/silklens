// Single row on a leaderboard. Backend returns them ordered by rank ASC.

enum LeaderboardScope { weekly, monthly, allTime, friends }

class LeaderboardEntry {
  const LeaderboardEntry({
    required this.rank,
    required this.userId,
    required this.displayName,
    required this.countryCode,
    required this.xp,
    this.delta = 0,
    this.isCurrentUser = false,
    this.avatarUrl,
    this.levelName,
  });

  factory LeaderboardEntry.fromJson(Map<String, dynamic> j) => LeaderboardEntry(
        rank: j['rank'] as int,
        userId: j['user_id'] as String,
        displayName: j['display_name'] as String,
        countryCode: j['country_code'] as String? ?? 'UZ',
        xp: j['xp'] as int,
        delta: j['delta'] as int? ?? 0,
        isCurrentUser: j['is_current_user'] as bool? ?? false,
        avatarUrl: j['avatar_url'] as String?,
        levelName: j['level_name'] as String?,
      );

  final int rank;
  final String userId;
  final String displayName;
  final String countryCode;
  final int xp;
  final int delta; // positive = moved up, negative = moved down
  final bool isCurrentUser;
  final String? avatarUrl;
  final String? levelName;
}
