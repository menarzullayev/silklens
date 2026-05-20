// Design tokens — Project-Decisions §21 design-token architecture.
//
// The mobile app receives tokens from the admin panel via `/v1/branding`
// (jsonb i18n app_name + primary_color + accent_color + theme_mode_default
// + font_family + extra). `ThemeTokens` is the in-memory shape;
// [fromBranding] builds it from a [Branding] entity, falling back to the
// hardcoded SilkLens defaults if a field is null.

import 'package:flutter/material.dart';
import 'package:silklens/domain/branding/entities/branding.dart';

@immutable
class ThemeTokens {
  const ThemeTokens({
    required this.primary,
    required this.secondary,
    required this.accent,
    required this.fontFamily,
    required this.nationalAccents,
  });

  /// Build tokens from the [Branding] payload. Fields that are null on the
  /// payload retain their defaults from [silkLensDefault].
  factory ThemeTokens.fromBranding(Branding branding) {
    Color parse(String? hex, Color fallback) {
      if (hex == null || hex.isEmpty) return fallback;
      var clean = hex.replaceFirst('#', '');
      if (clean.length == 6) clean = 'FF$clean';
      final value = int.tryParse(clean, radix: 16);
      if (value == null) return fallback;
      return Color(value);
    }

    final extraAccents = branding.extra['national_accents'];
    final accents = extraAccents is bool && extraAccents;

    return ThemeTokens(
      primary: parse(branding.primaryColorHex, silkLensDefault.primary),
      // Use the same color twice when no explicit secondary is provided —
      // the seed-based ColorScheme will derive a reasonable harmonized hue.
      secondary: parse(branding.primaryColorHex, silkLensDefault.secondary),
      accent: parse(branding.accentColorHex, silkLensDefault.accent),
      fontFamily: branding.fontFamily ?? silkLensDefault.fontFamily,
      nationalAccents: accents,
    );
  }

  /// Default SilkLens palette — `Silk Road` warm gold + lapis lazuli blue.
  static const ThemeTokens silkLensDefault = ThemeTokens(
    primary: Color(0xFFB78628), // gold
    secondary: Color(0xFF1F3A93), // lapis
    accent: Color(0xFFD96C2C), // terracotta
    fontFamily: 'Roboto',
    nationalAccents: false,
  );

  /// "Milliy" preset — national accents on, deeper saturation.
  static const ThemeTokens milliy = ThemeTokens(
    primary: Color(0xFF0E4D92),
    secondary: Color(0xFFC9A227),
    accent: Color(0xFF7D0A0A),
    fontFamily: 'Roboto',
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
