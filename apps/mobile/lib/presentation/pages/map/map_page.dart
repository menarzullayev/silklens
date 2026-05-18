// Map screen.
//
// Tile provider strategy:
//   - Mapbox preferred (`MAPBOX_PUBLIC_TOKEN` in .env). When token exists we
//     pass it to the URL template; when it doesn't we silently fall back to
//     the OpenStreetMap tile server. The same `flutter_map` widget renders
//     both — we just swap the URL template. This keeps the swap to a single
//     point of indirection per Project-Decisions §23.
//
// Bottom sheet preview opens via [showModalBottomSheet] from a marker tap;
// "Open" routes to /heritage/{pub_id}.

import "package:flutter/material.dart";
import "package:flutter_map/flutter_map.dart";
import "package:geolocator/geolocator.dart";
import "package:go_router/go_router.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:latlong2/latlong.dart";
import "package:silklens/core/env/app_environment.dart";
import "package:silklens/core/logging/app_logger.dart";
import "package:silklens/domain/heritage/entities/heritage.dart";
import "package:silklens/l10n/app_localizations.dart";
import "package:silklens/presentation/providers/map_provider.dart";

class MapPage extends ConsumerStatefulWidget {
  const MapPage({super.key});

  @override
  ConsumerState<MapPage> createState() => _MapPageState();
}

class _MapPageState extends ConsumerState<MapPage> {
  final MapController _mapController = MapController();
  bool _loadedInitial = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      if (_loadedInitial) return;
      _loadedInitial = true;
      await ref.read(mapControllerProvider.notifier).reload();
    });
  }

  Future<void> _locateMe() async {
    try {
      final permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.denied ||
          permission == LocationPermission.deniedForever) {
        return;
      }
      final pos = await Geolocator.getCurrentPosition();
      _mapController.move(LatLng(pos.latitude, pos.longitude), 12);
    } on Exception catch (e, st) {
      AppLogger.instance.w("Geolocator failed", error: e, stackTrace: st);
    }
  }

  void _onMarkerTapped(Heritage h) {
    final l10n = AppLocalizations.of(context);
    showModalBottomSheet<void>(
      context: context,
      builder: (BuildContext ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(h.name, style: Theme.of(ctx).textTheme.titleLarge),
              const SizedBox(height: 8),
              if (h.description != null)
                Text(
                  h.description!,
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                ),
              const SizedBox(height: 16),
              FilledButton.icon(
                key: const Key("map.bottom_sheet.open"),
                onPressed: () {
                  Navigator.of(ctx).pop();
                  ctx.go("/heritage/${h.id}");
                },
                icon: const Icon(Icons.open_in_new),
                label: Text(l10n?.mapOpen ?? "Open"),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final state = ref.watch(mapControllerProvider);
    final tileProvider = ref.watch(mapTileProviderProvider);
    final env = ref.watch(appEnvironmentProvider);
    final ThemeData theme = Theme.of(context);

    final urlTemplate = tileProvider == MapTileProvider.mapbox
        ? "https://api.mapbox.com/styles/v1/mapbox/streets-v12/tiles/256/{z}/{x}/{y}?access_token=${env.mapboxPublicToken}"
        : "https://tile.openstreetmap.org/{z}/{x}/{y}.png";

    return Scaffold(
      body: Stack(
        children: <Widget>[
          FlutterMap(
            key: const Key("map.flutter_map"),
            mapController: _mapController,
            options: MapOptions(
              initialCenter: LatLng(
                state.viewport.centerLat,
                state.viewport.centerLng,
              ),
              initialZoom: state.viewport.zoom,
              onPositionChanged: (MapCamera camera, bool _) {
                ref.read(mapControllerProvider.notifier).setViewport(
                      MapViewport(
                        centerLat: camera.center.latitude,
                        centerLng: camera.center.longitude,
                        zoom: camera.zoom,
                      ),
                    );
              },
            ),
            children: <Widget>[
              TileLayer(
                urlTemplate: urlTemplate,
                userAgentPackageName: "com.silklens.app",
                maxZoom: 19,
              ),
              MarkerLayer(
                markers: state.markers
                    .where((Heritage h) => h.hasGeolocation)
                    .map(
                      (Heritage h) => Marker(
                        point: LatLng(h.latitude!, h.longitude!),
                        width: 40,
                        height: 40,
                        child: GestureDetector(
                          onTap: () => _onMarkerTapped(h),
                          child: Icon(
                            Icons.location_on,
                            size: 36,
                            color: theme.colorScheme.primary,
                          ),
                        ),
                      ),
                    )
                    .toList(growable: false),
              ),
            ],
          ),
          Positioned(
            top: MediaQuery.of(context).padding.top + 12,
            left: 16,
            right: 16,
            child: _LayerToggleBar(
              current: state.filters.layer,
              onChanged: (MapLayer layer) {
                ref.read(mapControllerProvider.notifier).setLayer(layer);
                ref.read(mapControllerProvider.notifier).reload();
              },
            ),
          ),
          if (state.isLoading)
            const Positioned(
              top: 80,
              right: 16,
              child: SizedBox(
                width: 24,
                height: 24,
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
            ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        key: const Key("map.locate_me"),
        onPressed: _locateMe,
        tooltip: l10n?.mapLocateMe ?? "Locate me",
        child: const Icon(Icons.my_location),
      ),
    );
  }
}

class _LayerToggleBar extends StatelessWidget {
  const _LayerToggleBar({required this.current, required this.onChanged});

  final MapLayer current;
  final ValueChanged<MapLayer> onChanged;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    return Container(
      decoration: BoxDecoration(
        color: theme.colorScheme.surface.withValues(alpha: 0.9),
        borderRadius: BorderRadius.circular(12),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.1),
            blurRadius: 8,
          ),
        ],
      ),
      child: SegmentedButton<MapLayer>(
        showSelectedIcon: false,
        segments: <ButtonSegment<MapLayer>>[
          ButtonSegment<MapLayer>(
            value: MapLayer.allHeritage,
            label: Text(l10n?.mapLayerHeritage ?? "Heritage"),
          ),
          ButtonSegment<MapLayer>(
            value: MapLayer.unescoOnly,
            label: Text(l10n?.mapLayerUnesco ?? "UNESCO"),
          ),
          ButtonSegment<MapLayer>(
            value: MapLayer.cities,
            label: Text(l10n?.mapLayerCities ?? "Cities"),
          ),
        ],
        selected: <MapLayer>{current},
        onSelectionChanged: (Set<MapLayer> sel) => onChanged(sel.first),
      ),
    );
  }
}
