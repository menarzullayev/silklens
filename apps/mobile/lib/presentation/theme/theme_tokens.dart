// Design tokens — Project-Decisions §21 design-token architecture.
//
// At FAZA 1 these are hardcoded placeholders. The admin panel (FAZA 1
// Hafta 2) will push these via tenant_branding endpoint and they will
// be hydrated into [ThemeTokens] by `theme_provider.dart`.

import "package:flutter/material.dart";
import "package:meta/meta.dart";

@immutable
class ThemeTokens {
  const ThemeTokens({
    required this.primary,
    required this.secondary,
    required this.accent,
    required this.fontFamily,
    required this.nationalAccents,
  });

  /// Default SilkLens palette — `Silk Road` warm gold + lapis lazuli blue.
  static const ThemeTokens silkLensDefault = ThemeTokens(
    primary: Color(0xFFB78628), // gold
    secondary: Color(0xFF1F3A93), // lapis
    accent: Color(0xFFD96C2C), // terracotta
    fontFamily: "Roboto",
    nationalAccents: false,
  );

  /// "Milliy" preset — national accents on, deeper saturation.
  static const ThemeTokens milliy = ThemeTokens(
    primary: Color(0xFF0E4D92),
    secondary: Color(0xFFC9A227),
    accent: Color(0xFF7D0A0A),
    fontFamily: "Roboto",
    nationalAccents: true,
  );

  final Color primary;
  final Color secondary;
  final Color accent;
  final String fontFamily;

  /// When true, the UI may render extra ornamental motifs / borders.
  /// Pages opt in via `Theme.of(context).extension<SilkLensThemeExt>()`.
  final bool nationalAccents;
}

/// Extension that travels on the [ThemeData] so widgets can read tokens
/// without re-plumbing through providers.
class SilkLensThemeExt extends ThemeExtension<SilkLensThemeExt> {
  const SilkLensThemeExt({required this.tokens});

  final ThemeTokens tokens;

  @override
  SilkLensThemeExt copyWith({ThemeTokens? tokens}) =>
      SilkLensThemeExt(tokens: tokens ?? this.tokens);

  @override
  SilkLensThemeExt lerp(ThemeExtension<SilkLensThemeExt>? other, double t) {
    if (other is! SilkLensThemeExt) return this;
    // Tokens are discrete (admin-pushed); no interpolation between them.
    return t < 0.5 ? this : other;
  }
}
