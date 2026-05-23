import 'package:flutter/material.dart';
import 'package:silklens/core/theme/app_fonts.dart';

class AppTextStyles {
  // Display — Playfair Display (headings)
  static TextStyle displayLg(Color color) =>
      AppFonts.playfair(fontSize: 34, weight: FontWeight.w800, color: color);
  static TextStyle displayMd(Color color) =>
      AppFonts.playfair(fontSize: 28, weight: FontWeight.w700, color: color);

  // Heading — Inter
  static TextStyle headingLg(Color color) =>
      AppFonts.inter(fontSize: 22, weight: FontWeight.w700, color: color);
  static TextStyle headingMd(Color color) =>
      AppFonts.inter(fontSize: 18, weight: FontWeight.w600, color: color);

  // Body — Inter
  static TextStyle bodyLg(Color color) => AppFonts.inter(fontSize: 16, color: color);
  static TextStyle bodyMd(Color color) => AppFonts.inter(color: color);

  // Label — Inter
  static TextStyle label(Color color) => AppFonts.inter(
        fontSize: 13,
        weight: FontWeight.w500,
        color: color,
      );

  // Mono — JetBrains Mono
  static TextStyle mono(Color color) => AppFonts.mono(color: color);
}
