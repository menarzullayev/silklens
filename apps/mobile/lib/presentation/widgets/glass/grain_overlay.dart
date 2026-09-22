import 'package:flutter/material.dart';

/// Subtle noise grain overlay. Opacity 0.04 — nearly invisible but adds depth.
class GrainOverlay extends StatelessWidget {
  const GrainOverlay({super.key});

  @override
  Widget build(BuildContext context) {
    // Uses a repeating pattern of tiny dots to simulate grain
    return Positioned.fill(
      child: IgnorePointer(
        child: CustomPaint(painter: _GrainPainter()),
      ),
    );
  }
}

class _GrainPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.white.withValues(alpha: 0.03)
      ..style = PaintingStyle.fill;
    const step = 4.0;
    for (var x = 0.0; x < size.width; x += step) {
      for (var y = 0.0; y < size.height; y += step) {
        if ((x.toInt() + y.toInt()) % 8 == 0) {
          canvas.drawCircle(Offset(x, y), 0.5, paint);
        }
      }
    }
  }

  @override
  bool shouldRepaint(_GrainPainter _) => false;
}
