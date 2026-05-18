// Branding provider — verifies the cache-first then refresh flow.

import "package:flutter_test/flutter_test.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:mocktail/mocktail.dart";
import "package:silklens/core/error/failures.dart";
import "package:silklens/core/utils/result.dart";
import "package:silklens/data/repositories/branding_repository_impl.dart"
    show brandingRepositoryProvider;
import "package:silklens/domain/branding/entities/branding.dart";
import "package:silklens/domain/branding/repositories/branding_repository.dart";
import "package:silklens/presentation/providers/branding_provider.dart";

class _MockBrandingRepository extends Mock implements BrandingRepository {}

void main() {
  group("BrandingNotifier", () {
    late _MockBrandingRepository repo;
    late ProviderContainer container;

    setUp(() {
      repo = _MockBrandingRepository();
      container = ProviderContainer(
        overrides: <Override>[
          brandingRepositoryProvider.overrideWithValue(repo),
        ],
      );
      addTearDown(container.dispose);
    });

    test("cached value is surfaced immediately when available", () async {
      const cachedBranding = Branding(
        tenantSlug: "silklens",
        appName: <String, String>{"en": "Cached"},
        primaryColorHex: "#FF0000",
      );
      when(() => repo.cached(tenantSlug: any(named: "tenantSlug")))
          .thenAnswer((_) async => cachedBranding);
      when(() => repo.fetch(tenantSlug: any(named: "tenantSlug")))
          .thenAnswer(
        (_) async => const Success<Branding>(
          Branding(
            tenantSlug: "silklens",
            appName: <String, String>{"en": "Fresh"},
            primaryColorHex: "#00FF00",
          ),
        ),
      );

      final initial =
          await container.read(brandingProvider.future);
      expect(initial.localizedAppName("en"), "Cached");
    });

    test("falls back to defaults when fetch fails and nothing is cached",
        () async {
      when(() => repo.cached(tenantSlug: any(named: "tenantSlug")))
          .thenAnswer((_) async => null);
      when(() => repo.fetch(tenantSlug: any(named: "tenantSlug")))
          .thenAnswer(
        (_) async =>
            const FailureResult<Branding>(NetworkFailure("oops")),
      );

      final value = await container.read(brandingProvider.future);
      expect(value.tenantSlug, Branding.defaults.tenantSlug);
    });

    test("brandingValueProvider stays on defaults until first data lands",
        () async {
      when(() => repo.cached(tenantSlug: any(named: "tenantSlug")))
          .thenAnswer((_) async => null);
      when(() => repo.fetch(tenantSlug: any(named: "tenantSlug")))
          .thenAnswer(
        (_) async => const Success<Branding>(
          Branding(
            tenantSlug: "silklens",
            appName: <String, String>{"en": "Hello"},
          ),
        ),
      );
      final v1 = container.read(brandingValueProvider);
      expect(v1.tenantSlug, Branding.defaults.tenantSlug);

      await container.read(brandingProvider.future);

      final v2 = container.read(brandingValueProvider);
      expect(v2.localizedAppName("en"), "Hello");
    });
  });
}

