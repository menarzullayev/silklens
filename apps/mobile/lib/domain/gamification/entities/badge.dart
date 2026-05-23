class Badge {
  const Badge({
    required this.slug,
    required this.name,
    required this.description,
    this.iconUrl,
    this.earnedAt,
    this.category = '',
    this.stepsRemaining,
    this.accentHex,
  });

  factory Badge.fromJson(Map<String, dynamic> j) => Badge(
        slug: j['slug'] as String,
        name: j['name'] as String,
        description: j['description'] as String,
        iconUrl: j['icon_url'] as String?,
        earnedAt: j['earned_at'] != null
            ? DateTime.parse(j['earned_at'] as String)
            : null,
        category: j['category'] as String? ?? '',
        stepsRemaining: j['steps_remaining'] as int?,
        accentHex: j['accent_hex'] as String?,
      );

  final String slug;
  final String name;
  final String description;
  final String? iconUrl;
  final DateTime? earnedAt;
  final String category;
  final int? stepsRemaining;
  final String? accentHex;

  bool get isEarned => earnedAt != null;
}
