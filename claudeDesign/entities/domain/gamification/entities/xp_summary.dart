class XpSummary {
  const XpSummary({required this.currentXp, required this.lifetimeXp, required this.levelName, required this.levelNumber, required this.xpToNextLevel});
  final int currentXp;
  final int lifetimeXp;
  final String levelName;
  final int levelNumber;
  final int xpToNextLevel;
  double get progressToNextLevel => xpToNextLevel > 0 ? (currentXp % xpToNextLevel) / xpToNextLevel : 1.0;
}
