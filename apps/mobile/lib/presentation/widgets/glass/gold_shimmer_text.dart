import 'package:flutter/material.dart';

class GoldShimmerText extends StatefulWidget {
  const GoldShimmerText(
    this.text, {
    super.key,
    this.fontSize = 42,
    this.fontWeight = FontWeight.w800,
    this.letterSpacing = 3,
  });

  final String text;
  final double fontSize;
  final FontWeight fontWeight;
  final double letterSpacing;

  @override
  State<GoldShimmerText> createState() => _GoldShimmerTextState();
}

class _GoldShimmerTextState extends State<GoldShimmerText>
    with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 3),
    )..repeat();
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _ctrl,
      builder: (_, __) => ShaderMask(
        shaderCallback: (bounds) => LinearGradient(
          begin: Alignment(-1.5 + _ctrl.value * 3, 0),
          end: Alignment(-0.5 + _ctrl.value * 3, 0),
          colors: const [
            Color(0xFFB78628),
            Color(0xFFE5C97A),
            Color(0xFFFFF3CC),
            Color(0xFFE5C97A),
            Color(0xFFB78628),
          ],
        ).createShader(bounds),
        child: Text(
          widget.text,
          style: TextStyle(
            color: Colors.white,
            fontSize: widget.fontSize,
            fontWeight: widget.fontWeight,
            letterSpacing: widget.letterSpacing,
          ),
        ),
      ),
    );
  }
}
