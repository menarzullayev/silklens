import 'package:flutter/material.dart';

class HexClipper extends CustomClipper<Path> {
  @override
  Path getClip(Size size) {
    final w = size.width;
    final h = size.height;
    return Path()
      ..moveTo(w * 0.5, 0)
      ..lineTo(w, h * 0.25)
      ..lineTo(w, h * 0.75)
      ..lineTo(w * 0.5, h)
      ..lineTo(0, h * 0.75)
      ..lineTo(0, h * 0.25)
      ..close();
  }

  @override
  bool shouldReclip(HexClipper _) => false;
}

class HexBadge extends StatelessWidget {
  const HexBadge({
    required this.child,
    super.key,
    this.size = 60,
    this.color = const Color(0xFFB78628),
    this.glowColor,
    this.isLocked = false,
  });

  final Widget child;
  final double size;
  final Color color;
  final Color? glowColor;
  final bool isLocked;

  @override
  Widget build(BuildContext context) {
    final ratio = size / 60;
    return Container(
      width: size,
      height: size * 1.15,
      decoration: glowColor != null
          ? BoxDecoration(
              boxShadow: [
                BoxShadow(
                  color: glowColor!.withValues(alpha: 0.5),
                  blurRadius: 12 * ratio,
                ),
              ],
            )
          : null,
      child: ClipPath(
        clipper: HexClipper(),
        child: Opacity(
          opacity: isLocked ? 0.35 : 1.0,
          child: Container(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: isLocked
                    ? [Colors.white24, Colors.white10]
                    : [color, color.withValues(alpha: 0.7)],
              ),
            ),
            child: child,
          ),
        ),
      ),
    );
  }
}
