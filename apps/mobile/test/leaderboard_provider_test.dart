import 'package:flutter_test/flutter_test.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/domain/gamification/entities/leaderboard_entry.dart';
import 'package:silklens/presentation/providers/gamification_provider.dart';

void main() {
  group('leaderboardEntriesProvider', () {
    test('family key uses (slug, period) tuple', () {
      final container = ProviderContainer(
        overrides: [
          leaderboardEntriesProvider.overrideWith(
            (ref, arg) async => <LeaderboardEntry>[],
          ),
        ],
      );
      addTearDown(container.dispose);

      final weekly = container.read(
        leaderboardEntriesProvider(('heritage', 'weekly')),
      );
      final monthly = container.read(
        leaderboardEntriesProvider(('heritage', 'monthly')),
      );

      expect(weekly, isA<AsyncValue<List<LeaderboardEntry>>>());
      expect(monthly, isA<AsyncValue<List<LeaderboardEntry>>>());
    });
  });
}
