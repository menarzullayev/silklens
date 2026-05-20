import 'dart:ui';
import 'package:flutter/material.dart';

/// Frosted glass panel. Use real blur only when aurora/photo is behind it.
/// Pass `useRealBlur: false` on plain dark backgrounds (zero GPU cost).
class GlassSurface extends StatelessWidget {
  const GlassSurface({
    required this.child,
    super.key,
    this.blur = 24,
    this.opacity = 0.08,
    this.borderRadius = 28,
    this.borderOpacity = 0.20,
    this.useRealBlur = true,
  });

  final Widget child;
  final double blur;
  final double opacity;
  final double borderRadius;
  final double borderOpacity;
  final bool useRealBlur;

  @override
  Widget build(BuildContext context) {
    final decoration = BoxDecoration(
      color: Colors.white.withValues(alpha: opacity),
      borderRadius: BorderRadius.circular(borderRadius),
      border: Border.all(
        color: Colors.white.withValues(alpha: borderOpacity),
      ),
      boxShadow: const [
        BoxShadow(
          color: Color(0x59000000),
          blurRadius: 32,
          offset: Offset(0, 8),
        ),
        BoxShadow(
          color: Color(0x0DFFFFFF),
          offset: Offset(0, 1),
        ),
      ],
    );

    if (!useRealBlur) {
      return Container(decoration: decoration, child: child);
    }

    return ClipRRect(
      borderRadius: BorderRadius.circular(borderRadius),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: blur, sigmaY: blur),
        child: Container(decoration: decoration, child: child),
      ),
    );
  }
}
