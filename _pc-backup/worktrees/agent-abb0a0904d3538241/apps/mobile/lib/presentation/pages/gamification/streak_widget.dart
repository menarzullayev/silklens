import 'package:flutter/material.dart';

class StreakPage extends StatelessWidget {
  const StreakPage({super.key});

  static const _gold = Color(0xFFB78628);
  static const _week = [true, true, true, false, true, true, true];
  static const _days = ['Du', 'Se', 'Ch', 'Pa', 'Ju', 'Sh', 'Ya'];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0D2337),
      appBar: AppBar(
        backgroundColor: const Color(0xFF0D2337),
        title: const Text(
          'Kunlik Streak',
          style: TextStyle(color: Colors.white),
        ),
        leading: GestureDetector(
          onTap: () => Navigator.pop(context),
          child: const Icon(
            Icons.arrow_back_ios_new,
            color: Colors.white,
            size: 20,
          ),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            // Streak count
            Container(
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.07),
                borderRadius: BorderRadius.circular(24),
                border: Border.all(
                  color: Colors.white.withValues(alpha: 0.12),
                ),
              ),
              child: Row(
                children: [
                  const Icon(
                    Icons.local_fire_department_rounded,
                    color: Color(0xFFFF6B35),
                    size: 48,
                  ),
                  const SizedBox(width: 16),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        '23',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 42,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      Text(
                        'kun uzluksiz!',
                        style: TextStyle(
                          color: Colors.white.withValues(alpha: 0.6),
                          fontSize: 14,
                        ),
                      ),
                    ],
                  ),
                  const Spacer(),
                  Column(
                    children: [
                      Text(
                        'Eng yaxshi',
                        style: TextStyle(
                          color: Colors.white.withValues(alpha: 0.5),
                          fontSize: 11,
                        ),
                      ),
                      const Text(
                        '42 kun',
                        style: TextStyle(
                          color: Color(0xFFB78628),
                          fontSize: 16,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            // Week calendar
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.07),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: Colors.white.withValues(alpha: 0.12),
                ),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: List.generate(7, (i) {
                  return Column(
                    children: [
                      Text(
                        _days[i],
                        style: TextStyle(
                          color: Colors.white.withValues(alpha: 0.5),
                          fontSize: 11,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Container(
                        width: 36,
                        height: 36,
                        decoration: BoxDecoration(
                          color: _week[i]
                              ? _gold
                              : Colors.white.withValues(alpha: 0.08),
                          shape: BoxShape.circle,
                          border: i == 6
                              ? Border.all(color: Colors.white, width: 2)
                              : null,
                          boxShadow: _week[i]
                              ? [
                                  BoxShadow(
                                    color: _gold.withValues(alpha: 0.4),
                                    blurRadius: 8,
                                  ),
                                ]
                              : null,
                        ),
                        child: _week[i]
                            ? const Icon(
                                Icons.check_rounded,
                                color: Color(0xFF1A1200),
                                size: 18,
                              )
                            : null,
                      ),
                    ],
                  );
                }),
              ),
            ),
            const SizedBox(height: 16),
            // Milestones
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.07),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: Colors.white.withValues(alpha: 0.12),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Muhim belgilar',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 12),
                  ...[7, 14, 30, 42, 60, 100].map((milestone) {
                    final reached = 23 >= milestone;
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: Row(
                        children: [
                          Container(
                            width: 32,
                            height: 32,
                            decoration: BoxDecoration(
                              color: reached
                                  ? _gold
                                  : Colors.white.withValues(alpha: 0.08),
                              shape: BoxShape.circle,
                            ),
                            child: Icon(
                              reached
                                  ? Icons.check_rounded
                                  : Icons.lock_outline_rounded,
                              color: reached
                                  ? const Color(0xFF1A1200)
                                  : Colors.white.withValues(alpha: 0.4),
                              size: 16,
                            ),
                          ),
                          const SizedBox(width: 12),
                          Text(
                            '$milestone kun streak',
                            style: TextStyle(
                              color: reached
                                  ? Colors.white
                                  : Colors.white.withValues(alpha: 0.4),
                              fontSize: 13,
                              fontWeight:
                                  reached ? FontWeight.w600 : FontWeight.w400,
                            ),
                          ),
                          const Spacer(),
                          Text(
                            '+${milestone * 10} XP',
                            style: TextStyle(
                              color: reached
                                  ? _gold
                                  : Colors.white.withValues(alpha: 0.3),
                              fontSize: 12,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ],
                      ),
                    );
                  }),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
