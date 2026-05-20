import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/domain/heritage/entities/heritage.dart';

final heritageDetailProvider =
    FutureProvider.family<Heritage?, String>((ref, pubId) async => null);

final heritageSavedProvider =
    StateNotifierProvider.family<HeritageSavedNotifier, bool, String>(
  (ref, pubId) => HeritageSavedNotifier(),
);

class HeritageSavedNotifier extends StateNotifier<bool> {
  HeritageSavedNotifier() : super(false);
  void toggle() => state = !state;
}
