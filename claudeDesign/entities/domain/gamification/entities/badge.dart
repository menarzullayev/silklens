class Badge {
  const Badge({required this.slug, required this.name, required this.description, this.iconUrl, this.earnedAt});
  final String slug;
  final String name;
  final String description;
  final String? iconUrl;
  final DateTime? earnedAt;
  bool get isEarned => earnedAt != null;
}
