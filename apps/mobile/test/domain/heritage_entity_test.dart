import 'package:flutter_test/flutter_test.dart';
import 'package:silklens/domain/heritage/entities/heritage.dart';

void main() {
  group('Heritage', () {
    test('fromJson parses required fields', () {
      final h = Heritage.fromJson({
        'id': 'uuid-1',
        'pub_id': 'pub-1',
        'kind_slug': 'mosque',
        'name': {'en': 'Registan', 'uz': 'Registon'},
        'summary_md': {'en': 'Famous square'},
        'description_md': {'en': 'Long description'},
        'tags': ['silk_road', 'unesco'],
        'status': 'published',
        'country_code': 'UZ',
        'latitude': 39.6542,
        'longitude': 66.9758,
      });

      expect(h.id, equals('uuid-1'));
      expect(h.pubId, equals('pub-1'));
      expect(h.kindSlug, equals('mosque'));
      expect(h.name['en'], equals('Registan'));
      expect(h.tags, containsAll(['silk_road', 'unesco']));
      expect(h.status, equals('published'));
      expect(h.countryCode, equals('UZ'));
      expect(h.latitude, closeTo(39.6542, 0.0001));
    });

    test('fromJson uses defaults for missing optional fields', () {
      final h = Heritage.fromJson({
        'id': 'x',
        'pub_id': 'y',
        'kind_slug': 'fort',
        'name': <String, String>{},
        'summary_md': <String, String>{},
        'description_md': <String, String>{},
        'tags': <String>[],
        'status': null,
      });

      expect(h.status, equals('published'));
      expect(h.confidenceScore, equals(0));
      expect(h.revision, equals(1));
      expect(h.isSaved, isFalse);
    });

    test('isSaved defaults to false', () {
      final h = Heritage.fromJson({
        'id': 'a',
        'pub_id': 'b',
        'kind_slug': 'temple',
        'name': <String, String>{},
        'summary_md': <String, String>{},
        'description_md': <String, String>{},
        'tags': <String>[],
      });
      expect(h.isSaved, isFalse);
    });

    test('copyWith preserves fields not updated', () {
      final h = Heritage.fromJson({
        'id': 'a',
        'pub_id': 'b',
        'kind_slug': 'temple',
        'name': {'en': 'Test'},
        'summary_md': <String, String>{},
        'description_md': <String, String>{},
        'tags': <String>[],
        'status': 'published',
      });
      final updated = h.copyWith(isSaved: true);
      expect(updated.isSaved, isTrue);
      expect(updated.id, equals('a'));
      expect(updated.kindSlug, equals('temple'));
    });

    test('hasGeolocation returns true when lat+lon present', () {
      final h = Heritage.fromJson({
        'id': 'a',
        'pub_id': 'b',
        'kind_slug': 'fort',
        'name': <String, String>{},
        'summary_md': <String, String>{},
        'description_md': <String, String>{},
        'tags': <String>[],
        'latitude': 41.3,
        'longitude': 69.2,
      });
      expect(h.hasGeolocation, isTrue);
    });

    test('hasGeolocation returns false when missing', () {
      final h = Heritage.fromJson({
        'id': 'a',
        'pub_id': 'b',
        'kind_slug': 'fort',
        'name': <String, String>{},
        'summary_md': <String, String>{},
        'description_md': <String, String>{},
        'tags': <String>[],
      });
      expect(h.hasGeolocation, isFalse);
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
