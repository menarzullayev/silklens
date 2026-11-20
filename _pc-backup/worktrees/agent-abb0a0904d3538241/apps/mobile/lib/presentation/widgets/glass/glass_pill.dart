import 'package:flutter/material.dart';

class GlassPill extends StatelessWidget {
  const GlassPill({
    required this.label,
    super.key,
    this.isActive = false,
    this.onTap,
    this.icon,
  });

  final String label;
  final bool isActive;
  final VoidCallback? onTap;
  final IconData? icon;

  static const _gold = Color(0xFFB78628);
  static const _ink = Color(0xFF1A1200);

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(
          color: isActive
              ? _gold
              : Colors.white.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(100),
          border: Border.all(
            color: isActive
                ? _gold
                : Colors.white.withValues(alpha: 0.18),
          ),
          boxShadow: isActive
              ? [
                  BoxShadow(
                    color: _gold.withValues(alpha: 0.3),
                    blurRadius: 8,
                  ),
                ]
              : null,
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (icon != null) ...[
              Icon(
                icon,
                size: 14,
                color: isActive ? _ink : Colors.white,
              ),
              const SizedBox(width: 4),
            ],
            Text(
              label,
              style: TextStyle(
                color: isActive ? _ink : Colors.white,
                fontSize: 13,
                fontWeight: isActive ? FontWeight.w600 : FontWeight.w400,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
