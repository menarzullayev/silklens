class XpGainEvent {
  const XpGainEvent({
    required this.amount,
    required this.reason,
    this.missionCompleted,
    this.badgeUnlocked,
  });

  final int amount;
  final String reason;
  final String? missionCompleted;
  final String? badgeUnlocked;
}
