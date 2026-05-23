// GamificationProvider — Riverpod state layer for XP, badges, streaks and
// leaderboards. Pages watch these providers; no direct repo access from UI.
//
// SILK-0108..0112: wired to real GamificationRepositoryImpl.

import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/data/repositories/gamification_repository_impl.dart';
import 'package:silklens/domain/gamification/entities/badge.dart';
import 'package:silklens/domain/gamification/entities/leaderboard_entry.dart';
import 'package:silklens/domain/gamification/entities/streak_entity.dart';

// ---------------------------------------------------------------------------
// XP + Streak state
// ---------------------------------------------------------------------------

class XpState {
  const XpState({
    this.currentXp = 0,
    this.lifetimeXp = 0,
    this.level = 1,
    this.nextLevel = 2,
    this.xpToNextLevel = 1000,
    this.progressPct = 0.0,
    this.todayXp = 0,
    this.weeklyXp = 0,
    this.monthlyXp = 0,
    this.levelName = '',
    this.currentStreak = 0,
    this.longestStreak = 0,
    this.isLoading = false,
    this.error,
  });

  final int currentXp;
  final int lifetimeXp;
  final int level;
  final int nextLevel;
  final int xpToNextLevel;
  final double progressPct;
  final int todayXp;
  final int weeklyXp;
  final int monthlyXp;
  final String levelName;
  final int currentStreak;
  final int longestStreak;
  final bool isLoading;
  final String? error;

  XpState copyWith({
    int? currentXp,
    int? lifetimeXp,
    int? level,
    int? nextLevel,
    int? xpToNextLevel,
    double? progressPct,
    int? todayXp,
    int? weeklyXp,
    int? monthlyXp,
    String? levelName,
    int? currentStreak,
    int? longestStreak,
    bool? isLoading,
    String? error,
  }) =>
      XpState(
        currentXp: currentXp ?? this.currentXp,
        lifetimeXp: lifetimeXp ?? this.lifetimeXp,
        level: level ?? this.level,
        nextLevel: nextLevel ?? this.nextLevel,
        xpToNextLevel: xpToNextLevel ?? this.xpToNextLevel,
        progressPct: progressPct ?? this.progressPct,
        todayXp: todayXp ?? this.todayXp,
        weeklyXp: weeklyXp ?? this.weeklyXp,
        monthlyXp: monthlyXp ?? this.monthlyXp,
        levelName: levelName ?? this.levelName,
        currentStreak: currentStreak ?? this.currentStreak,
        longestStreak: longestStreak ?? this.longestStreak,
        isLoading: isLoading ?? this.isLoading,
        error: error,
      );
}

// ---------------------------------------------------------------------------
// Notifier
// ---------------------------------------------------------------------------

class GamificationNotifier extends Notifier<XpState> {
  @override
  XpState build() {
    Future.microtask(refresh);
    return const XpState(isLoading: true);
  }

  Future<void> refresh() async {
    state = state.copyWith(isLoading: true);
    try {
      final repo = ref.read(gamificationRepositoryProvider);
      final results = await Future.wait([
        repo.getXpRaw(),
        repo.getStreakRaw(),
      ]);
      final xp = results[0];
      final streak = results[1];

      // XP fields — tolerate partial payloads from backend.
      final currentXp = (xp['current_xp'] as num?)?.toInt() ?? 0;
      final xpToNext = (xp['xp_to_next_level'] as num?)?.toInt() ?? 1000;
      final rawPct = (xp['progress_pct'] as num?)?.toDouble();
      final computedPct =
          rawPct ?? (xpToNext > 0 ? (currentXp % xpToNext) / xpToNext : 0.0);
      final levelNum = (xp['level_number'] as num?)?.toInt() ??
          (xp['level'] as num?)?.toInt() ??
          1;

      state = state.copyWith(
        currentXp: currentXp,
        lifetimeXp: (xp['lifetime_xp'] as num?)?.toInt() ?? 0,
        todayXp: (xp['today_xp'] as num?)?.toInt() ?? 0,
        weeklyXp: (xp['weekly_xp'] as num?)?.toInt() ?? 0,
        monthlyXp: (xp['monthly_xp'] as num?)?.toInt() ?? 0,
        level: levelNum,
        nextLevel: levelNum + 1,
        xpToNextLevel: xpToNext,
        progressPct: computedPct.clamp(0.0, 1.0),
        levelName: (xp['level_name'] as String?) ?? '',
        currentStreak: (streak['current_streak'] as num?)?.toInt() ?? 0,
        longestStreak: (streak['best_streak'] as num?)?.toInt() ??
            (streak['longest_streak'] as num?)?.toInt() ??
            0,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<void> tickStreak() async {
    try {
      final repo = ref.read(gamificationRepositoryProvider);
      final streak = await repo.tickStreakRaw();
      state = state.copyWith(
        currentStreak:
            (streak['current_streak'] as num?)?.toInt() ?? state.currentStreak,
      );
    } catch (_) {
      // Silent — streak tick is best-effort.
    }
  }
}

final gamificationProvider = NotifierProvider<GamificationNotifier, XpState>(
  GamificationNotifier.new,
);

// ---------------------------------------------------------------------------
// Badges — FutureProvider
// ---------------------------------------------------------------------------

final badgesProvider = FutureProvider<List<Badge>>((ref) async {
  final repo = ref.watch(gamificationRepositoryProvider);
  final result = await repo.badges();
  return result.fold(
    onSuccess: (badges) => badges,
    onFailure: (f) => throw Exception(f.message),
  );
});

// ---------------------------------------------------------------------------
// Streak — FutureProvider exposing the full StreakEntity (week days +
// milestones) for the StreakPage.
// ---------------------------------------------------------------------------

final streakProvider = FutureProvider<StreakEntity>((ref) async {
  final repo = ref.watch(gamificationRepositoryProvider);
  return repo.getStreak();
});

// ---------------------------------------------------------------------------
// Leaderboard entries — FutureProvider.family keyed by (slug, period)
// ---------------------------------------------------------------------------

final leaderboardEntriesProvider =
    FutureProvider.family<List<LeaderboardEntry>, (String, String)>(
  (ref, args) async {
    final (slug, period) = args;
    final repo = ref.watch(gamificationRepositoryProvider);
    final data = await repo.getLeaderboardRaw(slug, period: period);
    final entries = ((data['entries'] as List?) ?? [])
        .cast<Map<String, dynamic>>()
        .map(LeaderboardEntry.fromJson)
        .toList();
    return entries;
  },
);
