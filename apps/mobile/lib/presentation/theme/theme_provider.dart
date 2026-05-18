// Dynamic theme provider (Project-Decisions §21).
//
// `activeThemePackProvider` exposes `(light, dark, mode)` so MaterialApp can
// consume all three at once. The pack is rebuilt whenever:
//   * the user picks a different variant via the profile sheet, or
//   * the branding fetch resolves with a fresh palette.

import "package:flutter/material.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:meta/meta.dart";
import "package:silklens/domain/branding/entities/branding.dart";
import "package:silklens/presentation/providers/branding_provider.dart";
import "package:silklens/presentation/theme/theme_tokens.dart";

@immutable
class ThemePack {
  const ThemePack({
    required this.light,
    required this.dark,
    required this.mode,
  });

  final ThemeData light;
  final ThemeData dark;
  final ThemeMode mode;
}

enum ThemeVariant { light, dark, milliy, highContrast, system }

class ThemeController extends Notifier<ThemeVariant> {
  @override
  ThemeVariant build() => ThemeVariant.system;

  void setVariant(ThemeVariant variant) => state = variant;
}

final NotifierProvider<ThemeController, ThemeVariant> themeControllerProvider =
    NotifierProvider<ThemeController, ThemeVariant>(
  ThemeController.new,
  name: "themeControllerProvider",
);

/// Tokens come from the active branding (admin remote config). If the user
/// picks the "milliy" theme variant explicitly, that always wins.
final Provider<ThemeTokens> themeTokensProvider = Provider<ThemeTokens>(
  (Ref ref) {
    final variant = ref.watch(themeControllerProvider);
    if (variant == ThemeVariant.milliy) return ThemeTokens.milliy;
    final branding = ref.watch(brandingValueProvider);
    return ThemeTokens.fromBranding(branding);
  },
  name: "themeTokensProvider",
);

final Provider<ThemePack> activeThemePackProvider = Provider<ThemePack>(
  (Ref ref) {
    final variant = ref.watch(themeControllerProvider);
    final tokens = ref.watch(themeTokensProvider);
    final branding = ref.watch(brandingValueProvider);

    final light = _buildTheme(tokens, brightness: Brightness.light, highContrast: false);
    final dark = _buildTheme(tokens, brightness: Brightness.dark, highContrast: false);

    final mode = switch (variant) {
      ThemeVariant.light => ThemeMode.light,
      ThemeVariant.dark => ThemeMode.dark,
      ThemeVariant.milliy => ThemeMode.light,
      ThemeVariant.highContrast => ThemeMode.light,
      ThemeVariant.system => _modeFromBranding(branding),
    };

    if (variant == ThemeVariant.highContrast) {
      final hc = _buildTheme(tokens, brightness: Brightness.light, highContrast: true);
      return ThemePack(light: hc, dark: hc, mode: ThemeMode.light);
    }

    return ThemePack(light: light, dark: dark, mode: mode);
  },
  name: "activeThemePackProvider",
);

ThemeMode _modeFromBranding(Branding b) {
  switch (b.themeModeDefault) {
    case "light":
      return ThemeMode.light;
    case "dark":
      return ThemeMode.dark;
    default:
      return ThemeMode.system;
  }
}

ThemeData _buildTheme(
  ThemeTokens tokens, {
  required Brightness brightness,
  required bool highContrast,
}) {
  final scheme = ColorScheme.fromSeed(
    seedColor: tokens.primary,
    brightness: brightness,
    primary: tokens.primary,
    secondary: tokens.secondary,
    tertiary: tokens.accent,
  );

  final base = ThemeData(
    colorScheme: scheme,
    useMaterial3: true,
    fontFamily: tokens.fontFamily,
    visualDensity: VisualDensity.adaptivePlatformDensity,
    extensions: <ThemeExtension<dynamic>>[
      SilkLensThemeExt(tokens: tokens),
    ],
  );

  if (!highContrast) return base;

  // Boost contrast: pump text onto pure-black, primary onto pure-white BG.
  return base.copyWith(
    colorScheme: scheme.copyWith(
      surface: Colors.white,
      onSurface: Colors.black,
      primary: Colors.black,
      onPrimary: Colors.white,
    ),
    textTheme:
        base.textTheme.apply(bodyColor: Colors.black, displayColor: Colors.black),
  );
}
