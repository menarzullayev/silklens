import 'package:flutter_test/flutter_test.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/domain/branding/entities/branding.dart';
import 'package:silklens/presentation/providers/branding_provider.dart';

void main() {
  group('BrandingProvider', () {
    test('defaults branding has tenantSlug silklens', () {
      expect(Branding.defaults.tenantSlug, equals('silklens'));
    });

    test('defaults branding appName contains en key', () {
      expect(Branding.defaults.appName['en'], equals('SilkLens'));
    });

    test('localizedAppName returns en fallback', () {
      const b = Branding.defaults;
      expect(b.localizedAppName('en'), equals('SilkLens'));
      expect(b.localizedAppName('uz'), equals('SilkLens'));
    });

    test('brandingValueProvider returns defaults on initial load', () {
      final container = ProviderContainer(
        overrides: [
          brandingProvider.overrideWith(_StubBrandingNotifier.new),
        ],
      );
      addTearDown(container.dispose);
      final value = container.read(brandingValueProvider);
      expect(value.tenantSlug, equals('silklens'));
    });
  });
}

class _StubBrandingNotifier extends BrandingNotifier {
  @override
  Future<Branding> build() async => Branding.defaults;
}
