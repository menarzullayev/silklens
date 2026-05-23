import 'package:flutter/material.dart';

class GoldButton extends StatelessWidget {
  const GoldButton({
    required this.label,
    super.key,
    this.onPressed,
    this.loading = false,
    this.height = 54,
    this.borderRadius = 14,
    this.fontSize = 16,
  });

  final String label;
  final VoidCallback? onPressed;
  final bool loading;
  final double height;
  final double borderRadius;
  final double fontSize;

  static const _gold1 = Color(0xFFB78628);
  static const _gold2 = Color(0xFFE5C97A);
  static const _goldDark = Color(0xFF1A1200);

  @override
  Widget build(BuildContext context) {
    final enabled = onPressed != null && !loading;
    return AnimatedOpacity(
      opacity: enabled ? 1.0 : 0.5,
      duration: const Duration(milliseconds: 200),
      child: GestureDetector(
        onTap: enabled ? onPressed : null,
        child: Container(
          height: height,
          decoration: BoxDecoration(
            gradient:
                enabled ? const LinearGradient(colors: [_gold1, _gold2]) : null,
            color: enabled ? null : Colors.white.withValues(alpha: 0.3),
            borderRadius: BorderRadius.circular(borderRadius),
            boxShadow: enabled
                ? [
                    BoxShadow(
                      color: _gold1.withValues(alpha: 0.35),
                      blurRadius: 16,
                      offset: const Offset(0, 4),
                    ),
                  ]
                : null,
          ),
          child: Center(
            child: loading
                ? const SizedBox(
                    width: 22,
                    height: 22,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      valueColor: AlwaysStoppedAnimation(_goldDark),
                    ),
                  )
                : Text(
                    label,
                    style: TextStyle(
                      color: _goldDark,
                      fontSize: fontSize,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
          ),
        ),
      ),
    );
  }
}
