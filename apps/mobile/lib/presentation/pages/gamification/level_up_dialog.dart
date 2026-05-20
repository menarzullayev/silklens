import 'package:flutter/material.dart';

class LevelUpDialog extends StatelessWidget {
  const LevelUpDialog({
    required this.newLevel, required this.levelName, super.key,
  });
  final int newLevel;
  final String levelName;

  static Future<void> show(
    BuildContext context, {
    required int level,
    required String name,
  }) {
    return showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => LevelUpDialog(newLevel: level, levelName: name),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: Colors.transparent,
      child: Container(
        padding: const EdgeInsets.all(32),
        decoration: BoxDecoration(
          color: const Color(0xFF102844),
          borderRadius: BorderRadius.circular(28),
          border: Border.all(
            color: const Color(0xFFB78628).withValues(alpha: 0.5),
            width: 2,
          ),
          boxShadow: [
            BoxShadow(
              color: const Color(0xFFB78628).withValues(alpha: 0.3),
              blurRadius: 40,
            ),
          ],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              '🎉 Yangi daraja!',
              style: TextStyle(
                color: Colors.white,
                fontSize: 22,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 24),
            Container(
              width: 80,
              height: 80,
              decoration: const BoxDecoration(
                gradient: LinearGradient(
                  colors: [Color(0xFFB78628), Color(0xFFE5C97A)],
                ),
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: Color(0x40B78628),
                    blurRadius: 24,
                  ),
                ],
              ),
              child: Center(
                child: Text(
                  '$newLevel',
                  style: const TextStyle(
                    color: Color(0xFF1A1200),
                    fontSize: 32,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
            ),
            const SizedBox(height: 12),
            Text(
              levelName,
              style: const TextStyle(
                color: Color(0xFFB78628),
                fontSize: 18,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              "Tabriklaymiz! Siz yangi darajaga\nko'tarildingiz.",
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.6),
                fontSize: 13,
              ),
            ),
            const SizedBox(height: 24),
            GestureDetector(
              onTap: () => Navigator.pop(context),
              child: Container(
                width: double.infinity,
                height: 48,
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [Color(0xFFB78628), Color(0xFFE5C97A)],
                  ),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: const Center(
                  child: Text(
                    'Davom etish',
                    style: TextStyle(
                      color: Color(0xFF1A1200),
                      fontSize: 15,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
