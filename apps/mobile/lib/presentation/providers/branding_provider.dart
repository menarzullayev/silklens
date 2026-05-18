// Riverpod provider for the tenant branding.
//
// Splash + theme provider both read this. The implementation lives in
// `data/`; this file consumes only the [BrandingRepository] interface.

import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/data/repositories/branding_repository_impl.dart"
    show brandingRepositoryProvider;
import "package:silklens/domain/branding/entities/branding.dart";
import "package:silklens/domain/branding/repositories/branding_repository.dart";

class BrandingNotifier extends AsyncNotifier<Branding> {
  @override
  Future<Branding> build() async {
    final repo = ref.read(brandingRepositoryProvider);
    // Fast path: paint the cached value while a fresh fetch is in flight.
    final cached = await repo.cached();
    if (cached != null) {
      // Refresh in the background — non-awaited so we don't block the
      // first frame.
      _refreshInBackground(repo);
      return cached;
    }
    final result = await repo.fetch();
    return result.fold<Branding>(
      onSuccess: (Branding b) => b,
      onFailure: (_) => Branding.defaults,
    );
  }

  Future<void> refresh() async {
    state = const AsyncValue<Branding>.loading();
    final repo = ref.read(brandingRepositoryProvider);
    final result = await repo.fetch();
    state = result.fold<AsyncValue<Branding>>(
      onSuccess: (Branding b) => AsyncValue<Branding>.data(b),
      onFailure: (_) => const AsyncValue<Branding>.data(Branding.defaults),
    );
  }

  Future<void> _refreshInBackground(BrandingRepository repo) async {
    final result = await repo.fetch();
    result.fold<void>(
      onSuccess: (Branding b) => state = AsyncValue<Branding>.data(b),
      onFailure: (_) {
        // Keep showing the cached value; the user doesn't care.
      },
    );
  }
}

final AsyncNotifierProvider<BrandingNotifier, Branding> brandingProvider =
    AsyncNotifierProvider<BrandingNotifier, Branding>(
  BrandingNotifier.new,
  name: "brandingProvider",
);

/// Synchronous selector — used by widgets that want a non-AsyncValue read
/// after the first paint. Falls back to defaults until the first fetch
/// resolves.
final Provider<Branding> brandingValueProvider = Provider<Branding>(
  (Ref ref) {
    final async = ref.watch(brandingProvider);
    return async.maybeWhen(
      data: (Branding b) => b,
      orElse: () => Branding.defaults,
    );
  },
  name: "brandingValueProvider",
);
