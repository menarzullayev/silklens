// Unit tests for [MapController].
//
// We assert that:
//   1. The default viewport / filter is the Silk Road preset.
//   2. Layer toggles produce the correct backend query params.
//   3. Setting viewport doesn't mutate filters.

import "package:flutter_test/flutter_test.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/presentation/providers/map_provider.dart";

void main() {
  test("default viewport is the Silk Road preset", () {
    final container = ProviderContainer();
    final state = container.read(mapControllerProvider);
    expect(state.viewport.centerLat, closeTo(39.6542, 0.0001));
    expect(state.filters.country, equals("UZ"));
    expect(state.filters.layer, equals(MapLayer.allHeritage));
  });

  test("layer toggle produces expected query params", () {
    final container = ProviderContainer();
    final notifier = container.read(mapControllerProvider.notifier);

    final initial = notifier.filtersAsQueryForTest();
    expect(initial["country"], equals("UZ"));
    expect(initial.containsKey("unesco"), isFalse);

    notifier.setLayer(MapLayer.unescoOnly);
    final unesco = notifier.filtersAsQueryForTest();
    expect(unesco["unesco"], isTrue);

    notifier.setLayer(MapLayer.cities);
    final cities = notifier.filtersAsQueryForTest();
    expect(cities["kind"], equals("city"));
  });

  test("setViewport does not change filters", () {
    final container = ProviderContainer();
    final notifier = container.read(mapControllerProvider.notifier);
    notifier.setViewport(
      const MapViewport(centerLat: 41, centerLng: 69, zoom: 12),
    );
    final state = container.read(mapControllerProvider);
    expect(state.viewport.centerLat, equals(41));
    expect(state.filters.layer, equals(MapLayer.allHeritage));
  });

  test("country setter updates filter and serialises", () {
    final container = ProviderContainer();
    final notifier = container.read(mapControllerProvider.notifier);
    notifier.setCountry("KZ");
    expect(notifier.filtersAsQueryForTest()["country"], equals("KZ"));
  });
}
