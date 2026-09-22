class XpSummary {
  const XpSummary({
    required this.currentXp,
    required this.lifetimeXp,
    required this.levelName,
    required this.levelNumber,
    required this.xpToNextLevel,
    this.todayXp = 0,
  });

  factory XpSummary.fromJson(Map<String, dynamic> j) => XpSummary(
        currentXp: j['current_xp'] as int,
        lifetimeXp: j['lifetime_xp'] as int,
        levelName: j['level_name'] as String,
        levelNumber: j['level_number'] as int,
        xpToNextLevel: j['xp_to_next_level'] as int,
        todayXp: j['today_xp'] as int? ?? 0,
      );

  final int currentXp;
  final int lifetimeXp;
  final String levelName;
  final int levelNumber;
  final int xpToNextLevel;
  final int todayXp;

  double get progressToNextLevel =>
      xpToNextLevel > 0 ? (currentXp % xpToNextLevel) / xpToNextLevel : 1.0;
}
