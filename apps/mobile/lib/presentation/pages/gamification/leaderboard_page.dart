import 'package:flutter/material.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/core/l10n/locale_service.dart';
import 'package:silklens/domain/gamification/entities/leaderboard_entry.dart';
import 'package:silklens/presentation/providers/gamification_provider.dart';

class LeaderboardPage extends ConsumerStatefulWidget {
  const LeaderboardPage({super.key});

  @override
  ConsumerState<LeaderboardPage> createState() => _LeaderboardPageState();
}

class _LeaderboardPageState extends ConsumerState<LeaderboardPage> {
  int _periodIndex = 0;
  static const _gold = Color(0xFFB78628);
  static const _goldLight = Color(0xFFE5C97A);

  String _s(String key) => AppStrings.get(LocaleService.instance.locale, key);

  List<String> get _periods => [
        _s('lb_period_weekly'),
        _s('lb_period_monthly'),
        _s('lb_period_all'),
      ];

  static const _periodSlugs = ['weekly', 'monthly', 'all_time'];

  Color _medalColor(int rank) {
    if (rank == 1) return const Color(0xFFFFD700);
    if (rank == 2) return const Color(0xFFC0C0C0);
    if (rank == 3) return const Color(0xFFCD7F32);
    return Colors.white.withValues(alpha: 0.2);
  }

  @override
  Widget build(BuildContext context) {
    const slug = 'global';
    final period = _periodSlugs[_periodIndex];
    final entriesAsync = ref.watch(leaderboardEntriesProvider((slug, period)));

    return Scaffold(
      backgroundColor: const Color(0xFF0D2337),
      appBar: AppBar(
        backgroundColor: const Color(0xFF0D2337),
        title: Text(
          _s('lb_page_title'),
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
      body: Column(
        children: [
          // Period tab bar
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Container(
              height: 44,
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.07),
                borderRadius: BorderRadius.circular(22),
                border: Border.all(
                  color: Colors.white.withValues(alpha: 0.12),
                ),
              ),
              child: Row(
                children: List.generate(_periods.length, (i) {
                  final active = _periodIndex == i;
                  return Expanded(
                    child: GestureDetector(
                      onTap: () => setState(() => _periodIndex = i),
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 200),
                        margin: const EdgeInsets.all(4),
                        decoration: BoxDecoration(
                          gradient: active
                              ? const LinearGradient(
                                  colors: [_gold, _goldLight],
                                )
                              : null,
                          borderRadius: BorderRadius.circular(18),
                        ),
                        child: Center(
                          child: Text(
                            _periods[i],
                            style: TextStyle(
                              color: active
                                  ? const Color(0xFF1A1200)
                                  : Colors.white.withValues(alpha: 0.6),
                              fontSize: 13,
                              fontWeight:
                                  active ? FontWeight.w700 : FontWeight.w400,
                            ),
                          ),
                        ),
                      ),
                    ),
                  );
                }),
              ),
            ),
          ),
          const SizedBox(height: 16),
          // Content
          Expanded(
            child: entriesAsync.when(
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
                      _s('lb_load_error'),
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.6),
                        fontSize: 13,
                      ),
                    ),
                    const SizedBox(height: 16),
                    GestureDetector(
                      onTap: () => ref.invalidate(
                        leaderboardEntriesProvider((slug, period)),
                      ),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 20,
                          vertical: 8,
                        ),
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(
                            colors: [_gold, _goldLight],
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
              data: (entries) {
                if (entries.isEmpty) {
                  return Center(
                    child: Text(
                      _s('lb_empty'),
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.4),
                        fontSize: 14,
                      ),
                    ),
                  );
                }
                return ListView.separated(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  itemCount: entries.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (_, i) => _LeaderboardRow(
                    entry: entries[i],
                    medalColor: _medalColor(entries[i].rank),
                    levelPrefix: _s('lb_level_prefix'),
                  ),
                );
              },
            ),
          ),
          const SizedBox(height: 16),
        ],
      ),
    );
  }
}

class _LeaderboardRow extends StatelessWidget {
  const _LeaderboardRow({
    required this.entry,
    required this.medalColor,
    required this.levelPrefix,
  });

  final LeaderboardEntry entry;
  final Color medalColor;
  final String levelPrefix;

  static const _gold = Color(0xFFB78628);

  @override
  Widget build(BuildContext context) {
    final isTop3 = entry.rank <= 3;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: entry.isCurrentUser
            ? _gold.withValues(alpha: 0.12)
            : Colors.white.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: entry.isCurrentUser
              ? _gold.withValues(alpha: 0.6)
              : isTop3
                  ? medalColor.withValues(alpha: 0.4)
                  : Colors.white.withValues(alpha: 0.08),
          width: entry.isCurrentUser ? 1.5 : 1,
        ),
        boxShadow: entry.isCurrentUser
            ? [
                BoxShadow(
                  color: _gold.withValues(alpha: 0.15),
                  blurRadius: 12,
                ),
              ]
            : null,
      ),
      child: Row(
        children: [
          // Rank circle
          Container(
            width: 32,
            height: 32,
            decoration: BoxDecoration(
              color: isTop3 ? medalColor : Colors.white.withValues(alpha: 0.1),
              shape: BoxShape.circle,
            ),
            child: Center(
              child: Text(
                '${entry.rank}',
                style: TextStyle(
                  color: isTop3
                      ? const Color(0xFF1A1200)
                      : Colors.white.withValues(alpha: 0.7),
                  fontSize: 13,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
          ),
          const SizedBox(width: 10),
          // Avatar placeholder
          Container(
            width: 38,
            height: 38,
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.12),
              shape: BoxShape.circle,
              border: Border.all(
                color: entry.isCurrentUser ? _gold : Colors.transparent,
                width: 1.5,
              ),
            ),
            child: Center(
              child: Text(
                entry.displayName.isNotEmpty
                    ? entry.displayName.substring(0, 1).toUpperCase()
                    : '?',
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ),
          const SizedBox(width: 10),
          // Name + level name
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  entry.displayName,
                  style: TextStyle(
                    color: entry.isCurrentUser ? _gold : Colors.white,
                    fontSize: 13,
                    fontWeight:
                        entry.isCurrentUser ? FontWeight.w700 : FontWeight.w500,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
                if (entry.levelName != null && entry.levelName!.isNotEmpty)
                  Text(
                    entry.levelName!,
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.45),
                      fontSize: 11,
                    ),
                  ),
              ],
            ),
          ),
          // XP + rank delta
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '${entry.xp} XP',
                style: TextStyle(
                  color: entry.isCurrentUser ? _gold : Colors.white,
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                ),
              ),
              Row(
                children: [
                  Icon(
                    entry.delta >= 0
                        ? Icons.arrow_drop_up_rounded
                        : Icons.arrow_drop_down_rounded,
                    color: entry.delta >= 0
                        ? Colors.greenAccent
                        : Colors.redAccent,
                    size: 16,
                  ),
                  Text(
                    '${entry.delta.abs()}',
                    style: TextStyle(
                      color: entry.delta >= 0
                          ? Colors.greenAccent
                          : Colors.redAccent,
                      fontSize: 11,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }
}
