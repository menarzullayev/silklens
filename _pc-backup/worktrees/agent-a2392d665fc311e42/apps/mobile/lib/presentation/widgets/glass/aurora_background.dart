import 'dart:math';
import 'package:flutter/material.dart';

class AuroraBackground extends StatefulWidget {
  const AuroraBackground({
    super.key,
    this.color1 = const Color(0xFF1F3A93),
    this.color2 = const Color(0xFFC2501F),
    this.colorGold = const Color(0x59B78628),
    this.baseColor = const Color(0xFF0D2337),
    this.child,
  });

  final Color color1;
  final Color color2;
  final Color colorGold;
  final Color baseColor;
  final Widget? child;

  @override
  State<AuroraBackground> createState() => _AuroraBackgroundState();
}

class _AuroraBackgroundState extends State<AuroraBackground> with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late Animation<double> _phase;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 22),
    )..repeat(reverse: true);
    _phase = _ctrl;
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return RepaintBoundary(
      child: AnimatedBuilder(
        animation: _phase,
        builder: (_, child) => CustomPaint(
          painter: _AuroraPainter(
            phase: _phase.value,
            color1: widget.color1,
            color2: widget.color2,
            colorGold: widget.colorGold,
            baseColor: widget.baseColor,
          ),
          child: child,
        ),
        child: widget.child,
      ),
    );
  }
}

class _AuroraPainter extends CustomPainter {
  const _AuroraPainter({
    required this.phase,
    required this.color1,
    required this.color2,
    required this.colorGold,
    required this.baseColor,
  });

  final double phase;
  final Color color1;
  final Color color2;
  final Color colorGold;
  final Color baseColor;

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Offset.zero & size;

    // Base fill + blobs as a single canvas cascade
    canvas
      ..drawRect(rect, Paint()..color = baseColor)

      // Blob 1: deep blue (top-left, moves slightly)
      ..drawRect(
        rect,
        Paint()
          ..shader = RadialGradient(
            center: Alignment(-0.6 + 0.1 * sin(phase * 2 * pi), 0),
            radius: 0.7,
            colors: [color1.withValues(alpha: 0.7), Colors.transparent],
          ).createShader(rect),
      )

      // Blob 2: terracotta (top-right, blendMode additive)
      ..drawRect(
        rect,
        Paint()
          ..blendMode = BlendMode.plus
          ..shader = RadialGradient(
            center: Alignment(0.6, -0.2 + 0.08 * cos(phase * pi)),
            radius: 0.6,
            colors: [color2.withValues(alpha: 0.5), Colors.transparent],
          ).createShader(rect),
      )

      // Blob 3: gold (bottom center)
      ..drawRect(
        rect,
        Paint()
          ..blendMode = BlendMode.screen
          ..shader = RadialGradient(
            center: Alignment(0, 0.6 + 0.05 * sin(phase * 3 * pi)),
            radius: 0.45,
            colors: [colorGold, Colors.transparent],
          ).createShader(rect),
      );
  }

  @override
  bool shouldRepaint(_AuroraPainter old) => old.phase != phase;
}
