import 'package:hooks_riverpod/hooks_riverpod.dart';

final vocabProvider = FutureProvider.family<List<Map<String, String>>, String>(
  (ref, slug) async => [],
);
final heritageKindsVocabProvider =
    Provider<List<Map<String, String>>>((ref) => []);
final languagesVocabProvider = Provider<List<Map<String, String>>>((ref) => []);
