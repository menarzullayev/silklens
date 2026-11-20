import 'package:flutter/material.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/core/l10n/locale_service.dart';
import 'package:silklens/domain/gamification/entities/streak_entity.dart';
import 'package:silklens/presentation/providers/gamification_provider.dart';

class StreakPage extends ConsumerWidget {
  const StreakPage({super.key});

  static const _gold = Color(0xFFB78628);

  String _s(String key) => AppStrings.get(LocaleService.instance.locale, key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final streakAsync = ref.watch(streakProvider);

    return Scaffold(
      backgroundColor: const Color(0xFF0D2337),
      appBar: AppBar(
        backgroundColor: const Color(0xFF0D2337),
        title: Text(
          _s('streak_page_title'),
          style: const TextStyle(color: Colors.white),
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
      body: streakAsync.when(
        loading: () => const Center(
          child: CircularProgressIndicator(color: _gold),
        ),
        error: (e, _) => Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.wifi_off_rounded,
                color: Colors.white.withValues(alpha: 0.4),
                size: 40,
              ),
              const SizedBox(height: 12),
              Text(
                _s('streak_load_error'),
                style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.6),
                  fontSize: 13,
                ),
              ),
              const SizedBox(height: 16),
              GestureDetector(
                onTap: () => ref.invalidate(streakProvider),
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 20,
                    vertical: 8,
                  ),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [_gold, Color(0xFFE5C97A)],
                    ),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    _s('xp_retry'),
                    style: const TextStyle(
                      color: Color(0xFF1A1200),
                      fontWeight: FontWeight.w700,
                      fontSize: 13,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
        data: (streak) => _StreakContent(streak: streak, s: _s),
      ),
    );
  }
}

class _StreakContent extends StatelessWidget {
  const _StreakContent({required this.streak, required this.s});

  final StreakEntity streak;
  final String Function(String) s;

  static const _gold = Color(0xFFB78628);
  static const _days = ['Du', 'Se', 'Ch', 'Pa', 'Ju', 'Sh', 'Ya'];

  @override
  Widget build(BuildContext context) {
    // Ensure weekDays always has 7 entries, padding with false if needed.
    final weekDays = streak.weekDays;
    final week = List<bool>.generate(
      7,
      (i) => i < weekDays.length && weekDays[i],
    );

    // Build milestone day targets from data, or fall back to static list.
    final milestoneDays = streak.milestones.isNotEmpty
        ? streak.milestones.map((m) => m.days).toList()
        : [7, 14, 30, 42, 60, 100];

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          // Streak count card
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
                    Text(
                      '${streak.currentStreak}',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 42,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    Text(
                      s('streak_days_label'),
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
                      s('streak_best_label'),
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.5),
                        fontSize: 11,
                      ),
                    ),
                    Text(
                      '${streak.bestStreak} ${s('streak_days_unit')}',
                      style: const TextStyle(
                        color: _gold,
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
                final active = week[i];
                final isToday = i == DateTime.now().weekday - 1;
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
                        color: active ? _gold : Colors.white.withValues(alpha: 0.08),
                        shape: BoxShape.circle,
                        border: isToday ? Border.all(color: Colors.white, width: 2) : null,
                        boxShadow: active
                            ? [
                                BoxShadow(
                                  color: _gold.withValues(alpha: 0.4),
                                  blurRadius: 8,
                                ),
                              ]
                            : null,
                      ),
                      child: active
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
                Text(
                  s('streak_milestones_title'),
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 12),
                ...milestoneDays.map((days) {
                  final reached = streak.currentStreak >= days;
                  // Find XP reward from milestone data if available.
                  final milestone = streak.milestones.where((m) => m.days == days).firstOrNull;
                  final xpReward = milestone?.xpReward ?? days * 10;
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: Row(
                      children: [
                        Container(
                          width: 32,
                          height: 32,
                          decoration: BoxDecoration(
                            color: reached ? _gold : Colors.white.withValues(alpha: 0.08),
                            shape: BoxShape.circle,
                          ),
                          child: Icon(
                            reached ? Icons.check_rounded : Icons.lock_outline_rounded,
                            color: reached
                                ? const Color(0xFF1A1200)
                                : Colors.white.withValues(alpha: 0.4),
                            size: 16,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Text(
                          '$days ${s('streak_milestone_suffix')}',
                          style: TextStyle(
                            color: reached ? Colors.white : Colors.white.withValues(alpha: 0.4),
                            fontSize: 13,
                            fontWeight: reached ? FontWeight.w600 : FontWeight.w400,
                          ),
                        ),
                        const Spacer(),
                        Text(
                          '+$xpReward XP',
                          style: TextStyle(
                            color: reached ? _gold : Colors.white.withValues(alpha: 0.3),
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
    );
  }
}
