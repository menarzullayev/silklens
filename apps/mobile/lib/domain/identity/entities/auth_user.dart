class AuthUser {
  const AuthUser({
    required this.id,
    required this.pubId,
    required this.tenantId,
    required this.residencyRegion,
    this.trustTier = 'new',
    this.preferredLocale = 'en',
    this.isVerified = false,
    this.displayName,
    this.avatarUrl,
  });

  factory AuthUser.fromJson(Map<String, dynamic> j) => AuthUser(
        id: j['id'] as String,
        pubId: j['pub_id'] as String,
        tenantId: j['tenant_id'] as String,
        residencyRegion: j['residency_region'] as String? ?? 'global',
        trustTier: j['trust_tier'] as String? ?? 'new',
        preferredLocale: j['preferred_locale'] as String? ?? 'en',
        isVerified: j['is_verified'] as bool? ?? false,
        displayName: j['display_name'] as String?,
        avatarUrl: j['avatar_url'] as String?,
      );
  final String id;
  final String pubId;
  final String tenantId;
  final String residencyRegion;
  final String trustTier;
  final String preferredLocale;
  final bool isVerified;
  final String? displayName;
  final String? avatarUrl;

  Map<String, dynamic> toJson() => {
        'id': id,
        'pub_id': pubId,
        'tenant_id': tenantId,
        'residency_region': residencyRegion,
        'trust_tier': trustTier,
        'preferred_locale': preferredLocale,
        'is_verified': isVerified,
        if (displayName != null) 'display_name': displayName,
        if (avatarUrl != null) 'avatar_url': avatarUrl,
      };
}
