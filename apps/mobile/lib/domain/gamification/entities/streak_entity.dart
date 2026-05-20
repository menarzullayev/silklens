class StreakMilestone {
  const StreakMilestone({
    required this.days,
    required this.xpReward,
    required this.badgeSlug,
    this.isEarned = false,
  });

  final int days;
  final int xpReward;
  final String badgeSlug;
  final bool isEarned;
}

class StreakEntity {
  const StreakEntity({
    required this.currentStreak,
    required this.bestStreak,
    required this.weekDays,
    required this.milestones,
    this.lastActivityDate,
  });

  factory StreakEntity.fromJson(Map<String, dynamic> j) => StreakEntity(
    currentStreak: j['current_streak'] as int,
    bestStreak: j['best_streak'] as int,
    weekDays: (j['week_days'] as List).cast<bool>(),
    lastActivityDate: j['last_activity_date'] != null
        ? DateTime.parse(j['last_activity_date'] as String)
        : null,
    milestones: (j['milestones'] as List?)
            ?.map(
              (m) => StreakMilestone(
                days: (m as Map<String, dynamic>)['days'] as int,
                xpReward: m['xp_reward'] as int,
                badgeSlug: m['badge_slug'] as String,
                isEarned: m['is_earned'] as bool? ?? false,
              ),
            )
            .toList() ??
        const [],
  );

  final int currentStreak;
  final int bestStreak;
  final List<bool> weekDays; // 7 bools, Mon-Sun
  final List<StreakMilestone> milestones;
  final DateTime? lastActivityDate;

  bool get isAtRisk {
    if (lastActivityDate == null) return false;
    return DateTime.now().difference(lastActivityDate!).inHours > 20;
  }
}
