import 'package:flutter_test/flutter_test.dart';
import 'package:silklens/domain/heritage/entities/heritage.dart';
import 'package:silklens/presentation/providers/heritage_list_provider.dart';

void main() {
  group('HeritageListState', () {
    test('default state is not loading', () {
      const s = HeritageListState();
      expect(s.isLoading, isFalse);
      expect(s.items, isEmpty);
    });

    test('initial loading state is loading', () {
      const s = HeritageListState(isLoading: true);
      expect(s.isLoading, isTrue);
      expect(s.items, isEmpty);
    });

    test('isEmpty returns true when no items and not loading', () {
      const empty = HeritageListState();
      expect(empty.isEmpty, isTrue);
    });

    test('hasMore is false when items count equals total', () {
      const s = HeritageListState(items: [], total: 0);
      expect(s.hasMore, isFalse);
    });

    test('copyWith replaces only specified fields', () {
      const s = HeritageListState(isLoading: true, total: 5);
      final updated = s.copyWith(isLoading: false);
      expect(updated.isLoading, isFalse);
      expect(updated.total, equals(5));
    });

    test('copyWith clearError removes error', () {
      const s = HeritageListState(error: 'network_error');
      final cleared = s.copyWith(clearError: true);
      expect(cleared.error, isNull);
    });
  });

  group('HeritageFilters', () {
    test('default filters have no constraints', () {
      const f = HeritageFilters();
      expect(f.kindSlug, isNull);
      expect(f.countryCode, isNull);
      expect(f.search, isNull);
    });

    test('copyWith updates only the specified field', () {
      const f = HeritageFilters(countryCode: 'UZ');
      final updated = f.copyWith(kindSlug: 'mosque');
      expect(updated.kindSlug, equals('mosque'));
      expect(updated.countryCode, equals('UZ'));
    });
  });
}
