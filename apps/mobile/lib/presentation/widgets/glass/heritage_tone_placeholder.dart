import 'package:flutter/material.dart';

enum HeritageTone { registan, bukhara, khiva, shahi, gur, warm }

class HeritageTonePlaceholder extends StatelessWidget {
  const HeritageTonePlaceholder({
    super.key,
    this.tone = HeritageTone.registan,
    this.width,
    this.height,
    this.borderRadius = 12,
    this.label,
  });

  final HeritageTone tone;
  final double? width;
  final double? height;
  final double borderRadius;
  final String? label;

  static const _gradients = {
    HeritageTone.registan: [
      Color(0xFF8B3A2A),
      Color(0xFFD2691E),
      Color(0xFF8B6914),
    ],
    HeritageTone.bukhara: [
      Color(0xFF1A3A5C),
      Color(0xFF2E6B9E),
      Color(0xFFB78628),
    ],
    HeritageTone.khiva: [
      Color(0xFFF5E6C8),
      Color(0xFFD4A853),
      Color(0xFF8B6914),
    ],
    HeritageTone.shahi: [
      Color(0xFF2D5A1B),
      Color(0xFF4A7C3F),
      Color(0xFFB78628),
    ],
    HeritageTone.gur: [
      Color(0xFF3A3070),
      Color(0xFF6B5A9E),
      Color(0xFFB78628),
    ],
    HeritageTone.warm: [
      Color(0xFFA07850),
      Color(0xFF7A5030),
      Color(0xFF503818),
    ],
  };

  @override
  Widget build(BuildContext context) {
    final colors = _gradients[tone]!;
    return Container(
      width: width,
      height: height,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: colors,
        ),
        borderRadius: BorderRadius.circular(borderRadius),
      ),
      child: label != null
          ? Padding(
              padding: const EdgeInsets.all(8),
              child: Align(
                alignment: Alignment.bottomLeft,
                child: Text(
                  label!,
                  style: const TextStyle(
                    color: Colors.white70,
                    fontSize: 9,
                    fontFamily: 'monospace',
                    letterSpacing: 1.5,
                  ),
                ),
              ),
            )
          : null,
    );
  }
}
