// Map state.
//
// Two layers of indirection:
//   1. `MapTileProvider` interface — Mapbox or OSM, swappable at runtime.
//      Mapbox is preferred but requires a public token; we fall back to OSM
//      (`flutter_map`) automatically when the token isn't configured.
//   2. `MapController` — owns the visible heritage markers + viewport state,
//      and translates viewport changes into filter params (country / kind /
//      unesco_only) for the backend `GET /v1/heritage` call.

import "package:flutter/foundation.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/core/env/app_environment.dart";
import "package:silklens/domain/heritage/entities/heritage.dart";
import "package:silklens/domain/heritage/repositories/heritage_repository.dart";
import "package:silklens/data/repositories/heritage_repository_impl.dart";

/// Map tile providers — swap at runtime based on environment config.
enum MapTileProvider { mapbox, osm }

/// Layer toggles in the map UI.
enum MapLayer { allHeritage, unescoOnly, cities }

@immutable
class MapViewport {
  const MapViewport({
    required this.centerLat,
    required this.centerLng,
    required this.zoom,
    this.minLat,
    this.minLng,
    this.maxLat,
    this.maxLng,
  });

  final double centerLat;
  final double centerLng;
  final double zoom;
  final double? minLat;
  final double? minLng;
  final double? maxLat;
  final double? maxLng;

  /// Default viewport — Samarkand at zoom 10.
  static const MapViewport silkRoadDefault = MapViewport(
    centerLat: 39.6542,
    centerLng: 66.9597,
    zoom: 6,
  );

  MapViewport copyWith({
    double? centerLat,
    double? centerLng,
    double? zoom,
    double? minLat,
    double? minLng,
    double? maxLat,
    double? maxLng,
  }) =>
      MapViewport(
        centerLat: centerLat ?? this.centerLat,
        centerLng: centerLng ?? this.centerLng,
        zoom: zoom ?? this.zoom,
        minLat: minLat ?? this.minLat,
        minLng: minLng ?? this.minLng,
        maxLat: maxLat ?? this.maxLat,
        maxLng: maxLng ?? this.maxLng,
      );
}

@immutable
class MapFilters {
  const MapFilters({
    this.country = "UZ",
    this.layer = MapLayer.allHeritage,
    this.pageSize = 200,
  });

  final String country;
  final MapLayer layer;
  final int pageSize;

  Map<String, dynamic> toQuery() => <String, dynamic>{
        "country": country,
        if (layer == MapLayer.unescoOnly) "unesco": true,
        if (layer == MapLayer.cities) "kind": "city",
        "page_size": pageSize,
      };

  MapFilters copyWith({String? country, MapLayer? layer, int? pageSize}) =>
      MapFilters(
        country: country ?? this.country,
        layer: layer ?? this.layer,
        pageSize: pageSize ?? this.pageSize,
      );
}

@immutable
class MapState {
  const MapState({
    required this.viewport,
    required this.filters,
    required this.markers,
    this.isLoading = false,
  });

  final MapViewport viewport;
  final MapFilters filters;
  final List<Heritage> markers;
  final bool isLoading;

  MapState copyWith({
    MapViewport? viewport,
    MapFilters? filters,
    List<Heritage>? markers,
    bool? isLoading,
  }) =>
      MapState(
        viewport: viewport ?? this.viewport,
        filters: filters ?? this.filters,
        markers: markers ?? this.markers,
        isLoading: isLoading ?? this.isLoading,
      );
}

/// Resolves which tile provider to use given the runtime environment.
final Provider<MapTileProvider> mapTileProviderProvider =
    Provider<MapTileProvider>(
  (Ref ref) {
    final token = ref.watch(appEnvironmentProvider).mapboxPublicToken;
    return token.isNotEmpty ? MapTileProvider.mapbox : MapTileProvider.osm;
  },
  name: "mapTileProviderProvider",
);

class MapController extends Notifier<MapState> {
  @override
  MapState build() => const MapState(
        viewport: MapViewport.silkRoadDefault,
        filters: MapFilters(),
        markers: <Heritage>[],
      );

  void setViewport(MapViewport viewport) {
    state = state.copyWith(viewport: viewport);
  }

  void setLayer(MapLayer layer) {
    state = state.copyWith(filters: state.filters.copyWith(layer: layer));
  }

  void setCountry(String country) {
    state = state.copyWith(filters: state.filters.copyWith(country: country));
  }

  /// Reloads markers for the current viewport. For FAZA 1 we ignore the
  /// bbox and send country + paging; the backend will grow bbox query support
  /// later — see HeritageRepository.search.
  Future<void> reload() async {
    state = state.copyWith(isLoading: true);
    final HeritageRepository repo = ref.read(heritageRepositoryProvider);
    final result = await repo.search(pageSize: state.filters.pageSize);
    state = state.copyWith(
      isLoading: false,
      markers: result.successOrNull ?? state.markers,
    );
  }

  @visibleForTesting
  Map<String, dynamic> filtersAsQueryForTest() => state.filters.toQuery();
}

final NotifierProvider<MapController, MapState> mapControllerProvider =
    NotifierProvider<MapController, MapState>(
  MapController.new,
  name: "mapControllerProvider",
);
