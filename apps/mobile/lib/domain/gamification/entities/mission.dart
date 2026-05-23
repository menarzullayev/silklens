enum MissionKind { daily, weekly, special }

class Mission {
  const Mission({
    required this.id,
    required this.title,
    required this.kind,
    required this.progress,
    required this.maxProgress,
    required this.xpReward,
    this.iconSlug = 'compass',
    this.description,
    this.deadlineHours,
    this.isCompleted = false,
  });

  factory Mission.fromJson(Map<String, dynamic> j) => Mission(
        id: j['id'] as String,
        title: j['title'] as String,
        kind: MissionKind.values.firstWhere(
          (k) => k.name == (j['kind'] as String),
          orElse: () => MissionKind.daily,
        ),
        progress: j['progress'] as int? ?? 0,
        maxProgress: j['max_progress'] as int,
        xpReward: j['xp_reward'] as int,
        iconSlug: j['icon_slug'] as String? ?? 'compass',
        description: j['description'] as String?,
        deadlineHours: j['deadline_hours'] as int?,
        isCompleted: j['is_completed'] as bool? ?? false,
      );

  final String id;
  final String title;
  final MissionKind kind;
  final int progress;
  final int maxProgress;
  final int xpReward;
  final String iconSlug;
  final String? description;
  final int? deadlineHours;
  final bool isCompleted;

  double get progressFraction => maxProgress > 0 ? progress / maxProgress : 0;
}
