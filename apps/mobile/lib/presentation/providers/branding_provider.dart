import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/domain/branding/entities/branding.dart';

class BrandingNotifier extends AsyncNotifier<Branding> {
  @override
  Future<Branding> build() async => Branding.defaults;

  Future<void> refresh() async {}
}

final brandingProvider = AsyncNotifierProvider<BrandingNotifier, Branding>(
  BrandingNotifier.new,
);

final brandingValueProvider = Provider<Branding>((ref) {
  return ref.watch(brandingProvider).when(
    data: (b) => b,
    loading: () => Branding.defaults,
    error: (_, __) => Branding.defaults,
  );
});
