// SILK-0097 — OfflineModePage wired to real /v1/offline/bundles API.
// Falls back to 5 hardcoded Uzbek heritage bundles when API is unavailable.
// Converted to ConsumerStatefulWidget with download-in-progress tracking.

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/core/l10n/locale_service.dart';
import 'package:silklens/data/api/clients/api_client_provider.dart';

// ─── Fallback bundles used when API is unreachable ───────────────────────────

const _fallbackBundles = [
  {
    'id': 'registon',
    'name': 'Registon',
    'status': 'available',
    'size_mb': 12,
  },
  {
    'id': 'bibi_xonim',
    'name': 'Bibi-Xonim',
    'status': 'available',
    'size_mb': 9,
  },
  {
    'id': 'itchan_kala',
    'name': 'Itchan Kala',
    'status': 'available',
    'size_mb': 15,
  },
  {
    'id': 'ark_qalasi',
    'name': "Ark Qal'asi",
    'status': 'unavailable',
    'size_mb': 8,
  },
  {
    'id': 'kalon',
    'name': 'Kalon',
    'status': 'unavailable',
    'size_mb': 7,
  },
];

class OfflineModePage extends ConsumerStatefulWidget {
  const OfflineModePage({super.key});

  @override
  ConsumerState<OfflineModePage> createState() => _OfflineModePageState();
}

class _OfflineModePageState extends ConsumerState<OfflineModePage> {
  List<Map<String, dynamic>> _bundles = [];
  bool _isLoadingBundles = true;

  // Tracks bundle IDs currently being downloaded.
  final Set<String> _downloading = {};

  // Tracks bundle IDs already downloaded (persisted only in memory for now;
  // full local storage arrives when Hive integration lands in FAZA 3).
  final Set<String> _downloaded = {};

  @override
  void initState() {
    super.initState();
    SystemChrome.setSystemUIOverlayStyle(
      const SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.light,
        systemNavigationBarColor: Color(0xFF0D2337),
        systemNavigationBarIconBrightness: Brightness.light,
      ),
    );
    _loadBundles();
  }

  String _s(String key) => AppStrings.get(LocaleService.instance.locale, key);

  Future<void> _loadBundles() async {
    setState(() => _isLoadingBundles = true);
    try {
      final client = ref.read(silkLensApiClientProvider);
      final locale = LocaleService.instance.locale;
      final data = await client.getOfflineBundles(language: locale);
      final items = (data['items'] as List?) ?? [];
      final parsed =
          items.map((e) => Map<String, dynamic>.from(e as Map)).toList();
      if (mounted) {
        setState(() {
          _bundles = parsed.isNotEmpty ? parsed : _buildFallback();
          _isLoadingBundles = false;
        });
      }
    } catch (_) {
      // API unavailable — use static fallback so offline UX still works.
      if (mounted) {
        setState(() {
          _bundles = _buildFallback();
          _isLoadingBundles = false;
        });
      }
    }
  }

  List<Map<String, dynamic>> _buildFallback() =>
      List<Map<String, dynamic>>.from(_fallbackBundles);

  Future<void> _download(String bundleId) async {
    if (_downloading.contains(bundleId)) return;
    setState(() => _downloading.add(bundleId));
    try {
      final client = ref.read(silkLensApiClientProvider);
      await client.getOfflineBundleManifest(bundleId: bundleId);
      // In production each file in the manifest is downloaded individually
      // and stored via PathProvider. For now we simulate the download delay.
      await Future<void>.delayed(const Duration(seconds: 2));
      if (mounted) {
        setState(() {
          _downloading.remove(bundleId);
          _downloaded.add(bundleId);
          // Mark bundle status in list.
          final idx = _bundles.indexWhere((b) => b['id'] == bundleId);
          if (idx != -1) {
            _bundles[idx] = Map.from(_bundles[idx])..['status'] = 'available';
          }
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() => _downloading.remove(bundleId));
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(_s('offline_download_error')),
            backgroundColor: const Color(0xFFE53935),
          ),
        );
      }
    }
  }

  bool _isAvailable(Map<String, dynamic> bundle) {
    final id = bundle['id'] as String? ?? '';
    if (_downloaded.contains(id)) return true;
    return (bundle['status'] as String?) == 'available';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0D2337),
      body: Column(
        children: [
          // ── Red offline banner ─────────────────────────────────────────
          Container(
            width: double.infinity,
            color: const Color(0xFFE53935),
            padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 16),
            child: SafeArea(
              bottom: false,
              child: Row(
                children: [
                  const Icon(Icons.wifi_off, color: Colors.white, size: 16),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      _s('offline_banner_text'),
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 13,
                      ),
                    ),
                  ),
                  GestureDetector(
                    onTap: _isLoadingBundles ? null : _loadBundles,
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        color: Colors.white24,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        _s('offline_refresh_btn'),
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 11,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),

          // ── Bundle list ────────────────────────────────────────────────
          Expanded(
            child: _isLoadingBundles
                ? const Center(
                    child: CircularProgressIndicator(
                      color: Color(0xFFB78628),
                      strokeWidth: 2,
                    ),
                  )
                : _bundles.isEmpty
                    ? Center(
                        child: Text(
                          _s('offline_empty'),
                          style: TextStyle(
                            color: Colors.white.withValues(alpha: 0.5),
                            fontSize: 14,
                          ),
                        ),
                      )
                    : ListView.builder(
                        padding: const EdgeInsets.all(16),
                        itemCount: _bundles.length,
                        itemBuilder: (_, i) => _BundleTile(
                          bundle: _bundles[i],
                          isAvailable: _isAvailable(_bundles[i]),
                          isDownloading: _downloading
                              .contains(_bundles[i]['id'] as String? ?? ''),
                          onDownload: () =>
                              _download(_bundles[i]['id'] as String? ?? ''),
                          sAvailable: _s('offline_status_available'),
                          sNeedsNet: _s('offline_status_needs_internet'),
                          sDownload: _s('offline_download_btn'),
                          sDownloading: _s('offline_downloading'),
                        ),
                      ),
          ),
        ],
      ),
    );
  }
}

// ─── Bundle tile ─────────────────────────────────────────────────────────────

class _BundleTile extends StatelessWidget {
  const _BundleTile({
    required this.bundle,
    required this.isAvailable,
    required this.isDownloading,
    required this.onDownload,
    required this.sAvailable,
    required this.sNeedsNet,
    required this.sDownload,
    required this.sDownloading,
  });

  final Map<String, dynamic> bundle;
  final bool isAvailable;
  final bool isDownloading;
  final VoidCallback onDownload;
  final String sAvailable;
  final String sNeedsNet;
  final String sDownload;
  final String sDownloading;

  @override
  Widget build(BuildContext context) {
    final name = bundle['name'] as String? ??
        bundle['title'] as String? ??
        (bundle['id'] as String? ?? '');
    final sizeMb = bundle['size_mb'] as int? ?? 0;

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Opacity(
        opacity: isAvailable ? 1.0 : 0.55,
        child: Container(
          height: 76,
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.07),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: Colors.white.withValues(alpha: 0.10),
            ),
          ),
          child: Row(
            children: [
              // ── Left icon block ────────────────────────────────────────
              Container(
                width: 76,
                height: 76,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      Colors.blueGrey.shade800,
                      Colors.blueGrey.shade600,
                    ],
                  ),
                  borderRadius: const BorderRadius.horizontal(
                    left: Radius.circular(16),
                  ),
                ),
                child: isDownloading
                    ? const Center(
                        child: SizedBox(
                          width: 22,
                          height: 22,
                          child: CircularProgressIndicator(
                            color: Color(0xFFB78628),
                            strokeWidth: 2,
                          ),
                        ),
                      )
                    : Icon(
                        isAvailable
                            ? Icons.check_circle
                            : Icons.signal_wifi_off,
                        color: isAvailable
                            ? const Color(0xFF4CAF50)
                            : Colors.white38,
                        size: 20,
                      ),
              ),
              const SizedBox(width: 12),

              // ── Name + status ──────────────────────────────────────────
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      name,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      isAvailable ? sAvailable : sNeedsNet,
                      style: TextStyle(
                        color: isAvailable
                            ? const Color(0xFF4CAF50)
                            : const Color(0xFFFF6B6B),
                        fontSize: 11,
                      ),
                    ),
                  ],
                ),
              ),

              // ── Download button (shown when not yet available) ─────────
              if (!isAvailable && !isDownloading)
                Padding(
                  padding: const EdgeInsets.only(right: 12),
                  child: GestureDetector(
                    onTap: onDownload,
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 5,
                      ),
                      decoration: BoxDecoration(
                        color: const Color(0xFFB78628),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(
                            Icons.download_rounded,
                            color: Color(0xFF1A1200),
                            size: 14,
                          ),
                          const SizedBox(width: 4),
                          Text(
                            sizeMb > 0 ? '${sizeMb}MB' : sDownload,
                            style: const TextStyle(
                              color: Color(0xFF1A1200),
                              fontSize: 11,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                )
              else if (isDownloading)
                Padding(
                  padding: const EdgeInsets.only(right: 12),
                  child: Text(
                    sDownloading,
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.5),
                      fontSize: 11,
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
