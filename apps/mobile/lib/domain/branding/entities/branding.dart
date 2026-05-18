// Pure-Dart branding entity. Mirrors the `BrandingPublicOut` payload from
// `services/api/src/api/routers/public_meta.py` — the response of
// `GET /v1/branding`.
//
// We surface app_name as a jsonb i18n map (BCP-47 → display), so the
// presentation layer can pick the right translation given the active
// locale. `themeModeDefault` matches Flutter's [ThemeMode] enum strings.

import "package:freezed_annotation/freezed_annotation.dart";

part "branding.freezed.dart";

@freezed
class Branding with _$Branding {
  const factory Branding({
    required String tenantSlug,
    @Default(<String, String>{}) Map<String, String> appName,
    String? logoUrl,
    String? logoDarkUrl,
    String? primaryColorHex,
    String? accentColorHex,
    String? splashUrl,
    String? fontFamily,
    @Default("system") String themeModeDefault,
    @Default(<String, Object?>{}) Map<String, Object?> extra,
  }) = _Branding;

  const Branding._();

  /// Default branding when the API is unreachable on first run. Mirrors the
  /// platform default seeded in migration 0002 (silklens tenant).
  static const Branding defaults = Branding(
    tenantSlug: "silklens",
    appName: <String, String>{
      "en": "SilkLens",
      "uz": "SilkLens",
      "ru": "SilkLens",
      "zh": "SilkLens",
    },
    themeModeDefault: "system",
  );

  String localizedAppName(String languageCode) {
    if (appName.isEmpty) return "SilkLens";
    return appName[languageCode] ??
        appName["en"] ??
        appName["uz"] ??
        appName.values.first;
  }
}
