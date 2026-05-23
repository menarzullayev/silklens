import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:go_router/go_router.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:latlong2/latlong.dart';
import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/domain/heritage/entities/heritage.dart';
import 'package:silklens/presentation/providers/heritage_list_provider.dart';
import 'package:silklens/presentation/providers/locale_provider.dart';

class MapPage extends ConsumerStatefulWidget {
  const MapPage({super.key});

  @override
  ConsumerState<MapPage> createState() => _MapPageState();
}

class _MapPageState extends ConsumerState<MapPage> {
  final _mapCtrl = MapController();
  static const _center = LatLng(39.6542, 66.9597); // Samarqand
  static const _gold = Color(0xFFB78628);

  String _s(String key) {
    final locale = ref.read(activeLocaleProvider).languageCode;
    return AppStrings.get(locale, key);
  }

  @override
  Widget build(BuildContext context) {
    final heritageState = ref.watch(heritageListProvider);
    final lang = ref.watch(activeLocaleProvider).languageCode;

    final geoItems =
        heritageState.items.where((h) => h.hasGeolocation).toList();

    return Scaffold(
      backgroundColor: const Color(0xFF0D2337),
      body: Stack(
        children: [
          FlutterMap(
            mapController: _mapCtrl,
            options: const MapOptions(
              initialCenter: _center,
              initialZoom: 6,
            ),
            children: [
              TileLayer(
                urlTemplate:
                    'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                userAgentPackageName: 'com.silklens.app',
              ),
              MarkerLayer(
                markers: geoItems
                    .map(
                      (h) => Marker(
                        point: LatLng(h.latitude!, h.longitude!),
                        width: 40,
                        height: 40,
                        child: GestureDetector(
                          onTap: () => _showHeritageSheet(h, lang),
                          child: Container(
                            decoration: BoxDecoration(
                              color: _gold,
                              shape: BoxShape.circle,
                              border: Border.all(
                                color: Colors.white,
                                width: 2,
                              ),
                              boxShadow: [
                                BoxShadow(
                                  color: Colors.black.withValues(alpha: 0.3),
                                  blurRadius: 8,
                                ),
                              ],
                            ),
                            child: const Icon(
                              Icons.explore_rounded,
                              color: Colors.white,
                              size: 20,
                            ),
                          ),
                        ),
                      ),
                    )
                    .toList(),
              ),
            ],
          ),

          // Glass search bar top
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            child: SafeArea(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Container(
                  height: 48,
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.92),
                    borderRadius: BorderRadius.circular(24),
                    boxShadow: const [
                      BoxShadow(
                        color: Color(0x30000000),
                        blurRadius: 12,
                      ),
                    ],
                  ),
                  child: Row(
                    children: [
                      const SizedBox(width: 12),
                      Icon(Icons.search, color: Colors.grey.shade600),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          _s('map_search_hint'),
                          style: TextStyle(
                            color: Colors.grey.shade500,
                            fontSize: 14,
                          ),
                        ),
                      ),
                      if (heritageState.isLoading)
                        Padding(
                          padding: const EdgeInsets.only(right: 12),
                          child: SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: Colors.grey.shade400,
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
              ),
            ),
          ),

          // Location FAB
          Positioned(
            bottom: 100,
            right: 16,
            child: FloatingActionButton.small(
              onPressed: () => _mapCtrl.move(_center, 10),
              backgroundColor: Colors.white,
              child: const Icon(
                Icons.my_location_rounded,
                color: Color(0xFF0D2337),
              ),
            ),
          ),
        ],
      ),
    );
  }

  void _showHeritageSheet(Heritage h, String lang) {
    showModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (_) => Container(
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          color: const Color(0xFF102844),
          borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
          border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Center(
              child: Container(
                width: 36,
                height: 4,
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.3),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: 16),
            Text(
              h.localizedName(lang),
              style: const TextStyle(
                color: Colors.white,
                fontSize: 22,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              [
                AppStrings.get(lang, 'map_heritage_type'),
                if (h.countryCode != null) h.countryCode!,
              ].join(' · '),
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.6),
                fontSize: 14,
              ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                const Icon(
                  Icons.star_rounded,
                  color: Color(0xFFB78628),
                  size: 16,
                ),
                const SizedBox(width: 4),
                Text(
                  h.kindSlug,
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.7),
                    fontSize: 12,
                  ),
                ),
                const Spacer(),
                GestureDetector(
                  onTap: () {
                    Navigator.pop(context);
                    context.push('/home/heritage/${h.pubId}');
                  },
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 20,
                      vertical: 10,
                    ),
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [Color(0xFFB78628), Color(0xFFE5C97A)],
                      ),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      AppStrings.get(lang, 'map_view_detail'),
                      style: const TextStyle(
                        color: Color(0xFF1A1200),
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
          ],
        ),
      ),
    );
  }
}
