import 'dart:ui' show lerpDouble;

import 'package:flutter/material.dart';

/// Glass extension for ThemeData
class SilkGlassTokens extends ThemeExtension<SilkGlassTokens> {
  const SilkGlassTokens({
    required this.glassBg,
    required this.glassBgStrong,
    required this.glassBorder,
    required this.glassBorderStrong,
    required this.glassBlur,
    required this.glassBlurStrong,
    required this.navBg,
    required this.gold,
    required this.goldLight,
    required this.goldDeep,
    required this.aurora1,
    required this.aurora2,
    required this.auroraGold,
  });

  final Color glassBg;
  final Color glassBgStrong;
  final Color glassBorder;
  final Color glassBorderStrong;
  final double glassBlur;
  final double glassBlurStrong;
  final Color navBg;
  final Color gold;
  final Color goldLight;
  final Color goldDeep;
  final Color aurora1;
  final Color aurora2;
  final Color auroraGold;

  /// Variant A — Premium Dark (default)
  static const variantA = SilkGlassTokens(
    glassBg: Color(0x14FFFFFF), // rgba(255,255,255,0.08)
    glassBgStrong: Color(0x21FFFFFF), // rgba(255,255,255,0.13)
    glassBorder: Color(0x33FFFFFF), // rgba(255,255,255,0.20)
    glassBorderStrong: Color(0x4DFFFFFF),
    glassBlur: 24,
    glassBlurStrong: 28,
    navBg: Color(0xBF0D2337),
    gold: Color(0xFFB78628),
    goldLight: Color(0xFFE5C97A),
    goldDeep: Color(0xFF8C6418),
    aurora1: Color(0xFF1F3A93),
    aurora2: Color(0xFFC2501F),
    auroraGold: Color(0x59B78628),
  );

  /// Variant B — Cultural Earthy
  static const variantB = SilkGlassTokens(
    glassBg: Color(0x14FAF6F0),
    glassBgStrong: Color(0x21FAF6F0),
    glassBorder: Color(0x33FAF6F0),
    glassBorderStrong: Color(0x4DFAF6F0),
    glassBlur: 22,
    glassBlurStrong: 28,
    navBg: Color(0xBF1A0F0A),
    gold: Color(0xFFB78628),
    goldLight: Color(0xFFE5C97A),
    goldDeep: Color(0xFF8C6418),
    aurora1: Color(0xFF1F3A93),
    aurora2: Color(0xFFC2501F),
    auroraGold: Color(0x59B78628),
  );

  /// Variant D — Immersive Glass (max blur)
  static const variantD = SilkGlassTokens(
    glassBg: Color(0x0FFFFFFF),
    glassBgStrong: Color(0x1AFFFFFF),
    glassBorder: Color(0x52FFFFFF),
    glassBorderStrong: Color(0x66FFFFFF),
    glassBlur: 36,
    glassBlurStrong: 48,
    navBg: Color(0x990D2337),
    gold: Color(0xFFB78628),
    goldLight: Color(0xFFFFD976),
    goldDeep: Color(0xFF8C6418),
    aurora1: Color(0xFF1F3A93),
    aurora2: Color(0xFFC2501F),
    auroraGold: Color(0x59B78628),
  );

  @override
  SilkGlassTokens copyWith({
    Color? glassBg,
    Color? glassBgStrong,
    Color? glassBorder,
    Color? glassBorderStrong,
    double? glassBlur,
    double? glassBlurStrong,
    Color? navBg,
    Color? gold,
    Color? goldLight,
    Color? goldDeep,
    Color? aurora1,
    Color? aurora2,
    Color? auroraGold,
  }) =>
      SilkGlassTokens(
        glassBg: glassBg ?? this.glassBg,
        glassBgStrong: glassBgStrong ?? this.glassBgStrong,
        glassBorder: glassBorder ?? this.glassBorder,
        glassBorderStrong: glassBorderStrong ?? this.glassBorderStrong,
        glassBlur: glassBlur ?? this.glassBlur,
        glassBlurStrong: glassBlurStrong ?? this.glassBlurStrong,
        navBg: navBg ?? this.navBg,
        gold: gold ?? this.gold,
        goldLight: goldLight ?? this.goldLight,
        goldDeep: goldDeep ?? this.goldDeep,
        aurora1: aurora1 ?? this.aurora1,
        aurora2: aurora2 ?? this.aurora2,
        auroraGold: auroraGold ?? this.auroraGold,
      );

  @override
  SilkGlassTokens lerp(SilkGlassTokens? other, double t) {
    if (other == null) return this;
    return SilkGlassTokens(
      glassBg: Color.lerp(glassBg, other.glassBg, t)!,
      glassBgStrong: Color.lerp(glassBgStrong, other.glassBgStrong, t)!,
      glassBorder: Color.lerp(glassBorder, other.glassBorder, t)!,
      glassBorderStrong:
          Color.lerp(glassBorderStrong, other.glassBorderStrong, t)!,
      glassBlur: lerpDouble(glassBlur, other.glassBlur, t)!,
      glassBlurStrong: lerpDouble(glassBlurStrong, other.glassBlurStrong, t)!,
      navBg: Color.lerp(navBg, other.navBg, t)!,
      gold: Color.lerp(gold, other.gold, t)!,
      goldLight: Color.lerp(goldLight, other.goldLight, t)!,
      goldDeep: Color.lerp(goldDeep, other.goldDeep, t)!,
      aurora1: Color.lerp(aurora1, other.aurora1, t)!,
      aurora2: Color.lerp(aurora2, other.aurora2, t)!,
      auroraGold: Color.lerp(auroraGold, other.auroraGold, t)!,
    );
  }
}
