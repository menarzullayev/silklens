import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppFonts {
  static TextStyle playfair({
    double fontSize = 16,
    FontWeight weight = FontWeight.w400,
    Color color = Colors.white,
  }) =>
      GoogleFonts.playfairDisplay(
        fontSize: fontSize,
        fontWeight: weight,
        color: color,
      );

  static TextStyle inter({
    double fontSize = 14,
    FontWeight weight = FontWeight.w400,
    Color color = Colors.white,
  }) =>
      GoogleFonts.inter(
        fontSize: fontSize,
        fontWeight: weight,
        color: color,
      );

  static TextStyle mono({
    double fontSize = 11,
    FontWeight weight = FontWeight.w400,
    Color color = Colors.white,
  }) =>
      GoogleFonts.jetBrainsMono(
        fontSize: fontSize,
        fontWeight: weight,
        color: color,
      );
}
