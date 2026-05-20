enum InboxItemKind {
  like,
  follow,
  badgeUnlock,
  mission,
  streak,
  leaderboard,
  newHeritage,
  systemAnnouncement,
}

class InboxItem {
  const InboxItem({
    required this.id,
    required this.kind,
    required this.text,
    required this.timestamp,
    this.actorName,
    this.isRead = false,
    this.thumbnailUrl,
    this.deepLinkPath,
  });

  factory InboxItem.fromJson(Map<String, dynamic> j) => InboxItem(
    id: j['id'] as String,
    kind: InboxItemKind.values.firstWhere(
      (k) => k.name == j['kind'],
      orElse: () => InboxItemKind.systemAnnouncement,
    ),
    text: j['text'] as String,
    timestamp: DateTime.parse(j['timestamp'] as String),
    actorName: j['actor_name'] as String?,
    isRead: j['is_read'] as bool? ?? false,
    thumbnailUrl: j['thumbnail_url'] as String?,
    deepLinkPath: j['deep_link_path'] as String?,
  );

  final String id;
  final InboxItemKind kind;
  final String text;
  final DateTime timestamp;
  final String? actorName;
  final bool isRead;
  final String? thumbnailUrl;
  final String? deepLinkPath;
}
