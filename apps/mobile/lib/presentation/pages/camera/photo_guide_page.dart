// SILK-0100 — PhotoGuidePage
//
// AI-powered photography angle suggestions and historical overlays for a
// heritage site. Three tabs: Angle (compass + azimuth), Historical
// (photo overlay), Compare (side-by-side). API: POST /v1/ai/photo-guide.
// Calls go through SilkLensApiClient via silkLensApiClientProvider —
// never Dio directly from the widget.

import 'dart:math' show sin, cos, pi;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/core/l10n/locale_service.dart';
import 'package:silklens/data/api/clients/api_client_provider.dart';

class PhotoGuidePage extends ConsumerStatefulWidget {
  const PhotoGuidePage({
    super.key,
    required this.heritagePubId,
    this.heritageName,
  });

  final String heritagePubId;
  final String? heritageName;

  @override
  ConsumerState<PhotoGuidePage> createState() => _PhotoGuidePageState();
}

class _PhotoGuidePageState extends ConsumerState<PhotoGuidePage>
    with SingleTickerProviderStateMixin {
  late final TabController _tabController;

  Map<String, dynamic>? _angleData;
  Map<String, dynamic>? _overlayData;

  bool _isLoadingAngle = true;
  bool _isLoadingOverlay = false;

  static const _gold = Color(0xFFB78628);
  static const _bg = Color(0xFF0D2337);

  // ---- helpers ----

  String _s(String key) =>
      AppStrings.get(LocaleService.instance.locale, key);

  // ---- lifecycle ----

  @override
  void initState() {
    super.initState();
    SystemChrome.setSystemUIOverlayStyle(
      const SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.light,
        systemNavigationBarColor: _bg,
        systemNavigationBarIconBrightness: Brightness.light,
      ),
    );
    _tabController = TabController(length: 3, vsync: this)
      ..addListener(_onTabChanged);
    _loadAngle();
  }

  @override
  void dispose() {
    _tabController
      ..removeListener(_onTabChanged)
      ..dispose();
    super.dispose();
  }

  void _onTabChanged() {
    if (!_tabController.indexIsChanging) return;
    final idx = _tabController.index;
    if (idx == 1 && _overlayData == null && !_isLoadingOverlay) {
      _loadOverlay('overlay');
    }
    if (idx == 2 && _overlayData == null && !_isLoadingOverlay) {
      _loadOverlay('compare');
    }
  }

  // ---- data loading ----

  Future<void> _loadAngle() async {
    if (!mounted) return;
    setState(() => _isLoadingAngle = true);
    try {
      final client = ref.read(silkLensApiClientProvider);
      final lang = LocaleService.instance.locale;
      final data = await client.getPhotoGuide(
        heritagePubId: widget.heritagePubId,
        mode: 'angle',
        language: lang,
      );
      if (!mounted) return;
      setState(() {
        _angleData = data;
        _isLoadingAngle = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _isLoadingAngle = false);
    }
  }

  Future<void> _loadOverlay(String mode) async {
    if (!mounted) return;
    setState(() => _isLoadingOverlay = true);
    try {
      final client = ref.read(silkLensApiClientProvider);
      final lang = LocaleService.instance.locale;
      final data = await client.getPhotoGuide(
        heritagePubId: widget.heritagePubId,
        mode: mode,
        language: lang,
      );
      if (!mounted) return;
      setState(() {
        _overlayData = data;
        _isLoadingOverlay = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _isLoadingOverlay = false);
    }
  }

  // ---- build ----

  @override
  Widget build(BuildContext context) {
    final title = widget.heritageName != null
        ? '${widget.heritageName} — ${_s('photo_guide_title')}'
        : _s('photo_guide_title');

    return Scaffold(
      backgroundColor: _bg,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: Text(
          title,
          style: const TextStyle(
            color: Colors.white,
            fontWeight: FontWeight.w600,
            fontSize: 16,
          ),
          overflow: TextOverflow.ellipsis,
        ),
        leading: Material(
          color: Colors.white.withAlpha(20),
          borderRadius: BorderRadius.circular(24),
          child: InkWell(
            borderRadius: BorderRadius.circular(24),
            onTap: () => context.pop(),
            child: const Padding(
              padding: EdgeInsets.all(10),
              child: Icon(
                Icons.arrow_back_ios_new,
                color: Colors.white,
                size: 20,
              ),
            ),
          ),
        ),
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: _gold,
          labelColor: _gold,
          unselectedLabelColor: Colors.white60,
          tabs: [
            Tab(
              icon: const Icon(Icons.explore, size: 18),
              text: _s('photo_guide_tab_angle'),
            ),
            Tab(
              icon: const Icon(Icons.history, size: 18),
              text: _s('photo_guide_tab_historical'),
            ),
            Tab(
              icon: const Icon(Icons.compare, size: 18),
              text: _s('photo_guide_tab_compare'),
            ),
          ],
        ),
      ),
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [_bg, Color(0xFF1A3A5C), _bg],
            stops: [0.0, 0.5, 1.0],
          ),
        ),
        child: TabBarView(
          controller: _tabController,
          children: [
            _AngleTab(
              isLoading: _isLoadingAngle,
              data: _angleData,
              gold: _gold,
              emptyLabel: _s('photo_guide_loading'),
              errorLabel: _s('photo_guide_angle_error'),
              bestTimeLabel: _s('photo_guide_best_time'),
              elevationLabel: _s('photo_guide_elevation'),
              tipLabel: _s('photo_guide_tip'),
            ),
            _OverlayTab(
              isLoading: _isLoadingOverlay,
              data: _overlayData,
              gold: _gold,
              errorLabel: _s('photo_guide_overlay_error'),
              yearSuffix: _s('photo_guide_year_suffix'),
            ),
            _OverlayTab(
              isLoading: _isLoadingOverlay,
              data: _overlayData,
              gold: _gold,
              errorLabel: _s('photo_guide_overlay_error'),
              yearSuffix: _s('photo_guide_year_suffix'),
            ),
          ],
        ),
      ),
    );
  }
}

// ─── Angle tab ────────────────────────────────────────────────────────────────

class _AngleTab extends StatelessWidget {
  const _AngleTab({
    required this.isLoading,
    required this.data,
    required this.gold,
    required this.emptyLabel,
    required this.errorLabel,
    required this.bestTimeLabel,
    required this.elevationLabel,
    required this.tipLabel,
  });

  final bool isLoading;
  final Map<String, dynamic>? data;
  final Color gold;
  final String emptyLabel;
  final String errorLabel;
  final String bestTimeLabel;
  final String elevationLabel;
  final String tipLabel;

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return Center(
        child: CircularProgressIndicator(color: gold),
      );
    }
    if (data == null) {
      return Center(
        child: Text(
          errorLabel,
          style: const TextStyle(color: Colors.white60),
          textAlign: TextAlign.center,
        ),
      );
    }

    final azimuth =
        (data!['suggested_azimuth_deg'] as num? ?? 315).toDouble();
    final elevation =
        (data!['suggested_elevation_deg'] as num? ?? 10).toDouble();
    final tip = data!['tip'] as String? ?? '';
    final bestTime = data!['best_time'] as String? ?? '07:00–09:00';
    final direction = data!['compass_direction'] as String? ?? 'NW';

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // Compass card
        Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [
                const Color(0xFF1F3A93).withAlpha(200),
                const Color(0xFF0D2337),
              ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(20),
          ),
          child: Column(
            children: [
              SizedBox(
                width: 120,
                height: 120,
                child: CustomPaint(
                  painter: _CompassPainter(azimuth: azimuth, gold: gold),
                ),
              ),
              const SizedBox(height: 16),
              Text(
                direction,
                style: TextStyle(
                  color: gold,
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                ),
              ),
              Text(
                '${azimuth.round()}°',
                style: const TextStyle(color: Colors.white70),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // Info cards
        _InfoCard(
          icon: Icons.schedule,
          label: bestTimeLabel,
          value: bestTime,
          gold: gold,
        ),
        const SizedBox(height: 8),
        _InfoCard(
          icon: Icons.height,
          label: elevationLabel,
          value: '${elevation.round()}°',
          gold: gold,
        ),
        const SizedBox(height: 16),

        // Tip box
        if (tip.isNotEmpty)
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: gold.withAlpha(38),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: gold.withAlpha(76)),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(Icons.lightbulb_outline, color: gold, size: 20),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    tip,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 14,
                      height: 1.5,
                    ),
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

// ─── Overlay / Compare tab ────────────────────────────────────────────────────

class _OverlayTab extends StatelessWidget {
  const _OverlayTab({
    required this.isLoading,
    required this.data,
    required this.gold,
    required this.errorLabel,
    required this.yearSuffix,
  });

  final bool isLoading;
  final Map<String, dynamic>? data;
  final Color gold;
  final String errorLabel;
  final String yearSuffix;

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return Center(child: CircularProgressIndicator(color: gold));
    }
    if (data == null) {
      return Center(
        child: Text(
          errorLabel,
          style: const TextStyle(color: Colors.white60),
          textAlign: TextAlign.center,
        ),
      );
    }

    final available = data!['overlay_available'] as bool? ?? false;
    final tip = data!['tip'] as String? ?? '';
    final histPhoto = data!['historical_photo'] as Map<String, dynamic>?;

    if (!available) {
      return Padding(
        padding: const EdgeInsets.all(24),
        child: Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: Colors.white.withAlpha(20),
            borderRadius: BorderRadius.circular(16),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.photo_library_outlined,
                color: Colors.white.withAlpha(97),
                size: 48,
              ),
              const SizedBox(height: 12),
              Text(
                tip.isNotEmpty ? tip : errorLabel,
                style: const TextStyle(color: Colors.white70),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      );
    }

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        if (histPhoto != null)
          Container(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16),
              color: Colors.white.withAlpha(20),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                ClipRRect(
                  borderRadius:
                      const BorderRadius.vertical(top: Radius.circular(16)),
                  child: histPhoto['url'] != null
                      ? Image.network(
                          histPhoto['url'] as String,
                          fit: BoxFit.cover,
                          height: 200,
                          width: double.infinity,
                          errorBuilder: (_, __, ___) => SizedBox(
                            height: 200,
                            child: Center(
                              child: Icon(
                                Icons.broken_image,
                                color: Colors.white.withAlpha(97),
                                size: 48,
                              ),
                            ),
                          ),
                        )
                      : SizedBox(
                          height: 200,
                          child: Center(
                            child: Icon(
                              Icons.photo,
                              color: Colors.white.withAlpha(97),
                              size: 48,
                            ),
                          ),
                        ),
                ),
                Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (histPhoto['year'] != null)
                        Text(
                          '${histPhoto['year']}$yearSuffix',
                          style: TextStyle(
                            color: gold,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      if (histPhoto['description'] != null) ...[
                        const SizedBox(height: 4),
                        Text(
                          histPhoto['description'] as String,
                          style: const TextStyle(
                            color: Colors.white70,
                            fontSize: 13,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ],
            ),
          ),
        if (tip.isNotEmpty) ...[
          const SizedBox(height: 12),
          Text(
            tip,
            style: const TextStyle(color: Colors.white70, fontSize: 14),
          ),
        ],
      ],
    );
  }
}

// ─── Shared sub-widgets ───────────────────────────────────────────────────────

class _InfoCard extends StatelessWidget {
  const _InfoCard({
    required this.icon,
    required this.label,
    required this.value,
    required this.gold,
  });

  final IconData icon;
  final String label;
  final String value;
  final Color gold;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white.withAlpha(20),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          Icon(icon, color: gold, size: 20),
          const SizedBox(width: 12),
          Text(label, style: const TextStyle(color: Colors.white60)),
          const Spacer(),
          Text(
            value,
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

// ─── Compass painter ──────────────────────────────────────────────────────────

class _CompassPainter extends CustomPainter {
  const _CompassPainter({required this.azimuth, required this.gold});

  final double azimuth;
  final Color gold;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2 - 8;

    // Outer circle
    canvas.drawCircle(
      center,
      radius,
      Paint()
        ..color = Colors.white.withAlpha(51)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2,
    );

    // Inner tick marks at cardinal directions
    for (var i = 0; i < 4; i++) {
      final angle = i * pi / 2;
      final outerPt = Offset(
        center.dx + radius * cos(angle),
        center.dy + radius * sin(angle),
      );
      final innerPt = Offset(
        center.dx + (radius - 8) * cos(angle),
        center.dy + (radius - 8) * sin(angle),
      );
      canvas.drawLine(
        outerPt,
        innerPt,
        Paint()
          ..color = Colors.white.withAlpha(128)
          ..strokeWidth = 2,
      );
    }

    // Compass needle pointing at azimuth
    // azimuth: 0 = North (top), 90 = East (right), etc.
    // Canvas 0° = East, so subtract 90° to map North to top.
    final needleAngle = (azimuth - 90) * pi / 180;
    final needleTip = Offset(
      center.dx + radius * 0.7 * cos(needleAngle),
      center.dy + radius * 0.7 * sin(needleAngle),
    );
    final tailAngle = needleAngle + pi;
    final needleTail = Offset(
      center.dx + radius * 0.3 * cos(tailAngle),
      center.dy + radius * 0.3 * sin(tailAngle),
    );

    canvas.drawLine(
      needleTail,
      needleTip,
      Paint()
        ..color = gold
        ..strokeWidth = 3
        ..strokeCap = StrokeCap.round,
    );

    // Centre dot
    canvas.drawCircle(center, 5, Paint()..color = gold);
  }

  @override
  bool shouldRepaint(_CompassPainter old) => old.azimuth != azimuth;
}
