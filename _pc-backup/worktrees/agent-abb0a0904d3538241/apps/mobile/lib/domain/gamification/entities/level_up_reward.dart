class LevelUpReward {
  const LevelUpReward({
    required this.title,
    required this.iconSlug,
    required this.description,
    this.xpBonus = 0,
  });

  factory LevelUpReward.fromJson(Map<String, dynamic> j) => LevelUpReward(
    title: j['title'] as String,
    iconSlug: j['icon_slug'] as String,
    description: j['description'] as String,
    xpBonus: j['xp_bonus'] as int? ?? 0,
  );

  final String title;
  final String iconSlug;
  final String description;
  final int xpBonus;
}
