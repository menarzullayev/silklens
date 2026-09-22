import 'package:flutter/material.dart';

class SilkDurations {
  static const instant = Duration.zero;
  static const fast = Duration(milliseconds: 150);
  static const normal = Duration(milliseconds: 300);
  static const slow = Duration(milliseconds: 500);
  static const aurora = Duration(seconds: 22);
  static const pageSlide = Duration(milliseconds: 350);
  static const sheetSlide = Duration(milliseconds: 400);
  static const xpFill = Duration(milliseconds: 1200);
  static const scanPulse = Duration(milliseconds: 1500);
}

class SilkCurves {
  static const springSlide = Cubic(0.16, 1, 0.30, 1);
  static const modalOvershoot = Cubic(0.34, 1.56, 0.64, 1);
  static const sheetSpring = Cubic(0.22, 1, 0.36, 1);
  static const goldEase = Curves.easeOutCubic;
}
