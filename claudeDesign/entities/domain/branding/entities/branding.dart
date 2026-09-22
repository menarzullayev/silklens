class Branding {
  const Branding({
    required this.tenantSlug,
    required this.appName,
    this.logoUrl,
    this.logoDarkUrl,
    this.primaryColor = '#1A3A5C',
    this.accentColor,
    this.splashUrl,
    this.fontFamily,
    this.themeModeDefault = 'system',
    this.extra = const {},
  });

  factory Branding.fromJson(Map<String, dynamic> j) => Branding(
        tenantSlug: j['tenant_slug'] as String? ?? 'silklens',
        appName: (j['app_name'] as Map?)?.cast<String, String>() ?? {'en': 'SilkLens'},
        logoUrl: j['logo_url'] as String?,
        logoDarkUrl: j['logo_dark_url'] as String?,
        primaryColor: j['primary_color'] as String? ?? '#1A3A5C',
        accentColor: j['accent_color'] as String?,
        splashUrl: j['splash_url'] as String?,
        fontFamily: j['font_family'] as String?,
        themeModeDefault: j['theme_mode_default'] as String? ?? 'system',
        extra: (j['extra'] as Map?)?.cast<String, dynamic>() ?? {},
      );

  final String tenantSlug;
  final Map<String, String> appName;
  final String? logoUrl;
  final String? logoDarkUrl;
  final String primaryColor;
  final String? accentColor;
  final String? splashUrl;
  final String? fontFamily;
  final String themeModeDefault;
  final Map<String, dynamic> extra;

  static const Branding defaults = Branding(
    tenantSlug: 'silklens',
    appName: {'en': 'SilkLens', 'uz': 'SilkLens', 'ru': 'SilkLens', 'zh': 'SilkLens'},
  );


  String get primaryColorHex => primaryColor;
  String get accentColorHex => accentColor ?? primaryColor;
  String localizedAppName(String languageCode) {
    if (appName.isEmpty) return 'SilkLens';
    return appName[languageCode] ?? appName['en'] ?? appName['uz'] ?? appName.values.first;
  }
}
