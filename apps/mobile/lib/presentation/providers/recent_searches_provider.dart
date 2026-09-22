// Tiny SharedPreferences-backed list of recent heritage search queries.
// Shown on the dedicated search page so users can re-issue their last
// query in one tap.

import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:silklens/core/logging/app_logger.dart';

const String _prefsKey = 'sl.heritage.recent_searches';
const int _maxEntries = 8;

class RecentSearchesNotifier extends AsyncNotifier<List<String>> {
  @override
  Future<List<String>> build() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      return prefs.getStringList(_prefsKey) ?? const <String>[];
    } on Exception catch (error, stackTrace) {
      AppLogger.instance.w(
        'Recent-searches read failed',
        error: error,
        stackTrace: stackTrace,
      );
      return const <String>[];
    }
  }

  Future<void> add(String query) async {
    final trimmed = query.trim();
    if (trimmed.isEmpty) return;
    final current = state.valueOrNull ?? <String>[];
    final next = <String>[
      trimmed,
      ...current.where(
        (String q) => q.toLowerCase() != trimmed.toLowerCase(),
      ),
    ].take(_maxEntries).toList();
    state = AsyncValue<List<String>>.data(next);
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setStringList(_prefsKey, next);
    } on Exception catch (error, stackTrace) {
      AppLogger.instance.w(
        'Recent-searches write failed',
        error: error,
        stackTrace: stackTrace,
      );
    }
  }

  Future<void> clear() async {
    state = const AsyncValue<List<String>>.data(<String>[]);
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(_prefsKey);
    } on Exception catch (error, stackTrace) {
      AppLogger.instance.w(
        'Recent-searches clear failed',
        error: error,
        stackTrace: stackTrace,
      );
    }
  }
}

final AsyncNotifierProvider<RecentSearchesNotifier, List<String>>
    recentSearchesProvider =
    AsyncNotifierProvider<RecentSearchesNotifier, List<String>>(
  RecentSearchesNotifier.new,
  name: 'recentSearchesProvider',
);
