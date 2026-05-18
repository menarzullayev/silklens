// Heritage detail provider. One AsyncNotifier instance per `pubId`.

import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/core/error/failures.dart";
import "package:silklens/core/utils/result.dart";
import "package:silklens/data/repositories/heritage_repository_impl.dart"
    show heritageRepositoryProvider;
import "package:silklens/domain/heritage/entities/heritage.dart";

class HeritageDetailNotifier
    extends FamilyAsyncNotifier<Heritage, String> {
  @override
  Future<Heritage> build(String pubId) async {
    final result =
        await ref.read(heritageRepositoryProvider).getByPubId(pubId);
    return result.fold<Heritage>(
      onSuccess: (Heritage h) => h,
      onFailure: (Failure f) => throw _DetailError(f),
    );
  }

  Future<void> refresh() async {
    state = const AsyncValue<Heritage>.loading();
    final result =
        await ref.read(heritageRepositoryProvider).getByPubId(arg);
    state = result.fold<AsyncValue<Heritage>>(
      onSuccess: (Heritage h) => AsyncValue<Heritage>.data(h),
      onFailure: (Failure f) => AsyncValue<Heritage>.error(
        _DetailError(f),
        StackTrace.current,
      ),
    );
  }
}

class _DetailError implements Exception {
  _DetailError(this.failure);
  final Failure failure;
  @override
  String toString() => failure.message;
}

final AsyncNotifierProviderFamily<HeritageDetailNotifier, Heritage, String>
    heritageDetailProvider =
    AsyncNotifierProvider.family<HeritageDetailNotifier, Heritage, String>(
  HeritageDetailNotifier.new,
  name: "heritageDetailProvider",
);

/// Tracks the "is this heritage saved locally?" boolean for the detail page
/// CTA. Re-emitted whenever [saveLocally] / [removeLocally] is called.
class HeritageSavedNotifier extends FamilyAsyncNotifier<bool, String> {
  @override
  Future<bool> build(String pubId) =>
      ref.read(heritageRepositoryProvider).isSaved(pubId);

  Future<void> toggle(Heritage heritage) async {
    final repo = ref.read(heritageRepositoryProvider);
    final currentlySaved = await repo.isSaved(heritage.pubId);
    final result = currentlySaved
        ? await repo.removeLocally(heritage.pubId)
        : await repo.saveLocally(heritage);
    result.fold<void>(
      onSuccess: (_) => state = AsyncValue<bool>.data(!currentlySaved),
      onFailure: (Failure f) {},
    );
    ref.invalidate(savedHeritageStreamProvider);
  }
}

final AsyncNotifierProviderFamily<HeritageSavedNotifier, bool, String>
    heritageSavedProvider =
    AsyncNotifierProvider.family<HeritageSavedNotifier, bool, String>(
  HeritageSavedNotifier.new,
  name: "heritageSavedProvider",
);

/// Stream of locally-saved heritage objects. The Saved tab + the offline-
/// only flows watch this.
final StreamProvider<List<Heritage>> savedHeritageStreamProvider =
    StreamProvider<List<Heritage>>(
  (Ref ref) => ref.read(heritageRepositoryProvider).watchSaved(),
  name: "savedHeritageStreamProvider",
);
