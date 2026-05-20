import 'dart:math';
import 'package:flutter/material.dart';

/// Custom SVG-style icons for onboarding screens.
/// Drawn with CustomPainter — no assets needed.

// ──────────────────────────────────────────────
// Icon 1: Compass Rose — Discover Heritage
// ──────────────────────────────────────────────
class CompassRoseIcon extends StatelessWidget {
  const CompassRoseIcon({super.key, this.size = 120});
  final double size;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: CustomPaint(painter: _CompassRosePainter()),
    );
  }
}

class _CompassRosePainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final cx = size.width / 2;
    final cy = size.height / 2;
    final r = size.width / 2;
    final s = r / 60; // scale unit

    // Gold outer ring
    canvas.drawCircle(
      Offset(cx, cy),
      r * 0.90,
      Paint()
        ..color = const Color(0xFFB78628)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.5 * s,
    );

    // Dashed inner ring
    _drawDashedCircle(canvas, cx, cy, r * 0.72, 24, const Color(0x66B78628), 1.5 * s);

    // N needle (white, large)
    final nLen = r * 0.62;
    final nW = r * 0.10;
    canvas.drawPath(
      Path()
        ..moveTo(cx, cy - nLen)
        ..lineTo(cx + nW, cy - r * 0.08)
        ..lineTo(cx, cy)
        ..lineTo(cx - nW, cy - r * 0.08)
        ..close(),
      Paint()..color = Colors.white,
    );

    // S needle (gold, shorter)
    final sLen = r * 0.45;
    canvas.drawPath(
      Path()
        ..moveTo(cx, cy + sLen)
        ..lineTo(cx + nW, cy + r * 0.06)
        ..lineTo(cx, cy)
        ..lineTo(cx - nW, cy + r * 0.06)
        ..close(),
      Paint()..color = const Color(0xFFB78628),
    );

    // E/W needles (white, small)
    final ewLen = r * 0.30;
    final ewW = r * 0.06;
    for (final dx in [-1.0, 1.0]) {
      canvas.drawPath(
        Path()
          ..moveTo(cx + dx * ewLen, cy)
          ..lineTo(cx + dx * r * 0.04, cy - ewW)
          ..lineTo(cx, cy)
          ..lineTo(cx + dx * r * 0.04, cy + ewW)
          ..close(),
        Paint()..color = Colors.white.withValues(alpha: 0.60),
      );
    }

    // Center glow + dot
    canvas.drawCircle(
      Offset(cx, cy),
      r * 0.10,
      Paint()
        ..color = const Color(0x44E5C97A)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 6),
    );
    canvas.drawCircle(
      Offset(cx, cy),
      r * 0.06,
      Paint()..color = const Color(0xFFFFF3CC),
    );
  }

  void _drawDashedCircle(Canvas c, double cx, double cy, double r,
      int n, Color color, double width,) {
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = width
      ..strokeCap = StrokeCap.round;
    for (var i = 0; i < n; i++) {
      final a1 = 2 * pi * i / n;
      final a2 = 2 * pi * (i + 0.45) / n;
      c.drawArc(
        Rect.fromCircle(center: Offset(cx, cy), radius: r),
        a1, a2 - a1, false, paint,
      );
    }
  }

  @override
  bool shouldRepaint(_CompassRosePainter _) => false;
}

// ──────────────────────────────────────────────
// Icon 2: AI Camera — Recognition
// ──────────────────────────────────────────────
class AICameraIcon extends StatelessWidget {
  const AICameraIcon({super.key, this.size = 120});
  final double size;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: CustomPaint(painter: _AICameraPainter()),
    );
  }
}

class _AICameraPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final cx = size.width / 2;
    final cy = size.height / 2;
    final r = size.width / 2;
    final s = r / 60;

    final whitePaint = Paint()
      ..color = Colors.white
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2 * s
      ..strokeCap = StrokeCap.round;

    final goldPaint = Paint()
      ..color = const Color(0xFFB78628)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2 * s
      ..strokeCap = StrokeCap.round;

    // Camera body (white rounded rect)
    final bodyRect = RRect.fromRectAndRadius(
      Rect.fromCenter(center: Offset(cx, cy + r * 0.04),
          width: r * 1.5, height: r * 1.1,),
      Radius.circular(r * 0.18),
    );
    canvas.drawRRect(bodyRect, whitePaint);

    // Viewfinder notch top
    final notchW = r * 0.40;
    final notchH = r * 0.18;
    final notchTop = cy - r * 0.63;
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        Rect.fromCenter(center: Offset(cx, notchTop),
            width: notchW, height: notchH,),
        Radius.circular(r * 0.08),
      ),
      whitePaint,
    );

    // Lens circle (gold gradient simulation — two arcs)
    canvas.drawCircle(Offset(cx, cy + r * 0.06), r * 0.32, goldPaint);
    canvas.drawCircle(
      Offset(cx, cy + r * 0.06),
      r * 0.20,
      Paint()
        ..color = const Color(0x44B78628)
        ..style = PaintingStyle.fill,
    );
    canvas.drawCircle(Offset(cx, cy + r * 0.06), r * 0.20, goldPaint);

    // AI scan corner brackets (gold)
    final scanR = r * 0.80;
    final bl = r * 0.20; // bracket length
    final bx = cx;
    final by = cy + r * 0.04;
    final corners = [
      Offset(bx - scanR / 2, by - scanR / 2),
      Offset(bx + scanR / 2, by - scanR / 2),
      Offset(bx - scanR / 2, by + scanR / 2),
      Offset(bx + scanR / 2, by + scanR / 2),
    ];
    final dirs = [
      [1.0, 1.0],
      [-1.0, 1.0],
      [1.0, -1.0],
      [-1.0, -1.0],
    ];
    for (var i = 0; i < 4; i++) {
      final o = corners[i];
      final dx = dirs[i][0];
      final dy = dirs[i][1];
      canvas.drawLine(o, Offset(o.dx + dx * bl, o.dy), goldPaint);
      canvas.drawLine(o, Offset(o.dx, o.dy + dy * bl), goldPaint);
    }

    // Small gold dots (AI sparkles)
    final dotPaint = Paint()..color = const Color(0xFFE5C97A);
    for (final pos in [
      Offset(cx + r * 0.62, cy - r * 0.45),
      Offset(cx + r * 0.70, cy - r * 0.20),
      Offset(cx + r * 0.55, cy - r * 0.60),
    ]) {
      canvas.drawCircle(pos, 2.5 * s, dotPaint);
    }
  }

  @override
  bool shouldRepaint(_AICameraPainter _) => false;
}

// ──────────────────────────────────────────────
// Icon 3: Connected Community
// ──────────────────────────────────────────────
class CommunityIcon extends StatelessWidget {
  const CommunityIcon({super.key, this.size = 120});
  final double size;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: CustomPaint(painter: _CommunityPainter()),
    );
  }
}

class _CommunityPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final cx = size.width / 2;
    final cy = size.height / 2;
    final r = size.width / 2;
    final s = r / 60;

    final avatarR = r * 0.28;
    // 3 avatar positions (triangle)
    final positions = [
      Offset(cx, cy - r * 0.40),        // top center
      Offset(cx - r * 0.42, cy + r * 0.25), // bottom left
      Offset(cx + r * 0.42, cy + r * 0.25), // bottom right
    ];

    // Connection lines (gold, thin)
    final linePaint = Paint()
      ..color = const Color(0x88B78628)
      ..strokeWidth = 1.5 * s
      ..strokeCap = StrokeCap.round;
    for (var i = 0; i < 3; i++) {
      for (var j = i + 1; j < 3; j++) {
        canvas.drawLine(positions[i], positions[j], linePaint);
      }
    }

    // Avatar circles (glass effect)
    for (var i = 0; i < 3; i++) {
      final pos = positions[i];
      final isMain = i == 0;

      // Glow
      canvas.drawCircle(
        pos, avatarR + 4 * s,
        Paint()
          ..color = const Color(0x33B78628)
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 6),
      );

      // Background fill
      canvas.drawCircle(
        pos, avatarR,
        Paint()..color = const Color(0xFF1A2A3A),
      );

      // Gold border (main = thicker)
      canvas.drawCircle(
        pos, avatarR,
        Paint()
          ..color = isMain ? const Color(0xFFB78628) : const Color(0x88B78628)
          ..style = PaintingStyle.stroke
          ..strokeWidth = (isMain ? 2.5 : 1.5) * s,
      );

      // Person silhouette (white)
      final headR = avatarR * 0.36;
      final headY = pos.dy - avatarR * 0.15;
      canvas.drawCircle(
        Offset(pos.dx, headY), headR,
        Paint()..color = Colors.white,
      );
      // Body arc
      canvas.drawArc(
        Rect.fromCenter(
          center: Offset(pos.dx, pos.dy + avatarR * 0.52),
          width: avatarR * 1.3,
          height: avatarR * 1.0,
        ),
        pi, pi, false,
        Paint()
          ..color = Colors.white
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2.5 * s,
      );
    }

    // Small gold location pins
    final pinPaint = Paint()..color = const Color(0xFFE5C97A);
    for (final pos in positions) {
      final pinPos = Offset(pos.dx + r * 0.20, pos.dy - r * 0.22);
      canvas.drawCircle(pinPos, 3.5 * s, pinPaint);
      canvas.drawLine(
        pinPos,
        Offset(pinPos.dx, pinPos.dy + 7 * s),
        Paint()
          ..color = const Color(0xFFE5C97A)
          ..strokeWidth = 1.5 * s,
      );
    }
  }

  @override
  bool shouldRepaint(_CommunityPainter _) => false;
}
