import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_hooks/flutter_hooks.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/core/l10n/locale_service.dart';
import 'package:silklens/data/api/clients/api_client_provider.dart';
import 'package:silklens/presentation/providers/locale_provider.dart';

class WeatherGuidePage extends HookConsumerWidget {
  const WeatherGuidePage({super.key});

  // Default coordinates: Samarqand city centre.
  static const double _defaultLat = 39.6270;
  static const double _defaultLng = 66.9750;

  String _s(String key) => AppStrings.get(LocaleService.instance.locale, key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    useEffect(
      () {
        SystemChrome.setSystemUIOverlayStyle(
          const SystemUiOverlayStyle(
            statusBarColor: Colors.transparent,
            statusBarIconBrightness: Brightness.light,
            systemNavigationBarColor: Color(0xFF0D2337),
            systemNavigationBarIconBrightness: Brightness.light,
          ),
        );
        return null;
      },
      const [],
    );

    final locale = ref.watch(activeLocaleProvider);
    final guide = useState<Map<String, dynamic>?>(null);
    final isLoading = useState(true);
    final hasError = useState(false);

    useEffect(
      () {
        isLoading.value = true;
        hasError.value = false;
        Future(() async {
          try {
            guide.value = await ref.read(silkLensApiClientProvider).getWeatherGuide(
                  lat: _defaultLat,
                  lng: _defaultLng,
                  language: locale.languageCode,
                );
          } catch (_) {
            hasError.value = true;
          }
          isLoading.value = false;
        });
        return null;
      },
      [locale.languageCode],
    );

    return Scaffold(
      backgroundColor: const Color(0xFF0D2337),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: GestureDetector(
          onTap: () => Navigator.of(context).pop(),
          child: const Icon(
            Icons.arrow_back_ios_new,
            color: Colors.white,
            size: 20,
          ),
        ),
        title: Text(
          _s('weather_title'),
          style: const TextStyle(
            color: Colors.white,
            fontSize: 20,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
      body: isLoading.value
          ? const Center(
              child: CircularProgressIndicator(color: Color(0xFFB78628)),
            )
          : hasError.value || guide.value == null
              ? _ErrorView(s: _s)
              : _GuideView(guide: guide.value!, s: _s),
    );
  }
}

// ---------------------------------------------------------------------------

class _ErrorView extends StatelessWidget {
  const _ErrorView({required this.s});
  final String Function(String) s;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.cloud_off, size: 64, color: Colors.white30),
            const SizedBox(height: 16),
            Text(
              s('weather_error'),
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.white60, fontSize: 16),
            ),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------

class _GuideView extends StatelessWidget {
  const _GuideView({required this.guide, required this.s});
  final Map<String, dynamic> guide;
  final String Function(String) s;

  @override
  Widget build(BuildContext context) {
    final condition = guide['condition'] as String? ?? '';
    final tempC = guide['temp_c'];
    final summary = guide['summary'] as String? ?? '';
    final venues = (guide['recommended_venues'] as List?) ?? [];
    final tips = (guide['tips'] as List?) ?? [];

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // Current weather card
        Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFF1A3A5C), Color(0xFF0D2337)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: Colors.white12),
          ),
          child: Row(
            children: [
              _WeatherIcon(condition: condition),
              const SizedBox(width: 20),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (tempC != null)
                      Text(
                        '$tempC°C',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 40,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    Text(
                      condition,
                      style: const TextStyle(
                        color: Colors.white70,
                        fontSize: 16,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        // AI summary
        if (summary.isNotEmpty) ...[
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.06),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: Colors.white12),
            ),
            child: Text(
              summary,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 15,
                height: 1.5,
              ),
            ),
          ),
          const SizedBox(height: 20),
        ],
        // Tips
        if (tips.isNotEmpty) ...[
          _SectionLabel(label: s('weather_tips')),
          const SizedBox(height: 8),
          ...tips.map((t) => _BulletRow(text: t as String)),
          const SizedBox(height: 20),
        ],
        // Recommended venues
        if (venues.isNotEmpty) ...[
          _SectionLabel(label: s('weather_venues')),
          const SizedBox(height: 8),
          ...venues.map((v) {
            final venue = v as Map<String, dynamic>;
            return Container(
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.symmetric(
                horizontal: 16,
                vertical: 12,
              ),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.06),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.white12),
              ),
              child: Row(
                children: [
                  const Icon(Icons.place, color: Color(0xFFB78628), size: 18),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      venue['name'] as String? ?? '',
                      style: const TextStyle(color: Colors.white),
                    ),
                  ),
                ],
              ),
            );
          }),
        ],
      ],
    );
  }
}

class _WeatherIcon extends StatelessWidget {
  const _WeatherIcon({required this.condition});
  final String condition;

  @override
  Widget build(BuildContext context) {
    final lower = condition.toLowerCase();
    final icon = lower.contains('rain')
        ? Icons.water_drop
        : lower.contains('cloud')
            ? Icons.cloud
            : lower.contains('snow')
                ? Icons.ac_unit
                : lower.contains('storm')
                    ? Icons.thunderstorm
                    : Icons.wb_sunny;
    return Icon(icon, color: const Color(0xFFB78628), size: 52);
  }
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel({required this.label});
  final String label;

  @override
  Widget build(BuildContext context) {
    return Text(
      label,
      style: const TextStyle(
        color: Colors.white70,
        fontWeight: FontWeight.bold,
        fontSize: 13,
        letterSpacing: 1.1,
      ),
    );
  }
}

class _BulletRow extends StatelessWidget {
  const _BulletRow({required this.text});
  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            '• ',
            style: TextStyle(color: Color(0xFFB78628), fontSize: 16),
          ),
          Expanded(
            child: Text(
              text,
              style: const TextStyle(color: Colors.white70, fontSize: 14),
            ),
          ),
        ],
      ),
    );
  }
}
