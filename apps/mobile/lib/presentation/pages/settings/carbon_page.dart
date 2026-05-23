// SILK-0134 — Carbon Footprint: calculate and grade your travel emissions.

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_hooks/flutter_hooks.dart';
import 'package:go_router/go_router.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/core/l10n/locale_service.dart';
import 'package:silklens/data/api/clients/api_client_provider.dart';
import 'package:silklens/presentation/providers/locale_provider.dart';

class CarbonPage extends HookConsumerWidget {
  const CarbonPage({super.key});

  String _s(String key) =>
      AppStrings.get(LocaleService.instance.locale, key);

  static const _transports = <(String, String, IconData)>[
    ('car_petrol', 'carbon_transport_car', Icons.directions_car),
    ('bus', 'carbon_transport_bus', Icons.directions_bus),
    ('train', 'carbon_transport_train', Icons.train),
    ('bicycle', 'carbon_transport_bicycle', Icons.pedal_bike),
    ('walk', 'carbon_transport_walk', Icons.directions_walk),
    ('flight_domestic', 'carbon_transport_flight', Icons.flight),
  ];

  Color _gradeColor(String grade) => switch (grade) {
        'A' => const Color(0xFF4CAF50),
        'B' => const Color(0xFF8BC34A),
        'C' => const Color(0xFFFF9800),
        _ => const Color(0xFFF44336),
      };

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    useEffect(() {
      SystemChrome.setSystemUIOverlayStyle(
        const SystemUiOverlayStyle(
          statusBarColor: Colors.transparent,
          statusBarIconBrightness: Brightness.light,
          systemNavigationBarColor: Color(0xFF0D2337),
          systemNavigationBarIconBrightness: Brightness.light,
        ),
      );
      return null;
    }, const []);

    final locale = ref.watch(activeLocaleProvider);
    final legs =
        useState<List<Map<String, dynamic>>>([]);
    final selectedTransport = useState('car_petrol');
    final distCtrl = useTextEditingController();
    final result = useState<Map<String, dynamic>?>(null);
    final isLoading = useState(false);

    Future<void> calculate() async {
      if (legs.value.isEmpty) return;
      isLoading.value = true;
      try {
        final client = ref.read(silkLensApiClientProvider);
        result.value = await client.calculateCarbonFootprint(
          journeyLegs: legs.value,
          language: locale.languageCode,
        );
      } catch (_) {}
      isLoading.value = false;
    }

    void addLeg() {
      final d = double.tryParse(distCtrl.text);
      if (d == null || d <= 0) return;
      legs.value = [
        ...legs.value,
        {
          'transport_type': selectedTransport.value,
          'distance_km': d,
        },
      ];
      distCtrl.clear();
    }

    void removeLeg(int index) {
      final updated = List<Map<String, dynamic>>.from(legs.value);
      updated.removeAt(index);
      legs.value = updated;
    }

    final totalCo2 = (result.value?['total_co2_kg'] as num?)?.toDouble() ?? 0;
    final grade = result.value?['grade'] as String? ?? '';
    final tip = result.value?['tip'] as String?;
    final gradeColor = grade.isEmpty ? Colors.white24 : _gradeColor(grade);

    return Scaffold(
      backgroundColor: const Color(0xFF0D2337),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: GestureDetector(
          onTap: () => context.pop(),
          child: const Icon(
            Icons.arrow_back_ios_new,
            color: Colors.white,
            size: 20,
          ),
        ),
        title: Text(
          _s('carbon_title'),
          style: const TextStyle(
            color: Colors.white,
            fontSize: 20,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // ── Result card ───────────────────────────────────────────────────
          if (result.value != null)
            Container(
              margin: const EdgeInsets.only(bottom: 20),
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: gradeColor.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: gradeColor.withValues(alpha: 0.4),
                ),
              ),
              child: Column(
                children: [
                  if (grade.isNotEmpty)
                    Container(
                      width: 56,
                      height: 56,
                      decoration: BoxDecoration(
                        color: gradeColor,
                        shape: BoxShape.circle,
                      ),
                      child: Center(
                        child: Text(
                          grade,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 24,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ),
                  const SizedBox(height: 8),
                  Text(
                    '${totalCo2.toStringAsFixed(1)} kg CO₂',
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 22,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  if (tip != null) ...[
                    const SizedBox(height: 8),
                    Text(
                      tip,
                      style: const TextStyle(
                        color: Colors.white70,
                        fontSize: 13,
                        height: 1.4,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ],
                ],
              ),
            ),

          // ── Add journey leg ───────────────────────────────────────────────
          Text(
            _s('carbon_add_leg'),
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.bold,
              fontSize: 16,
            ),
          ),
          const SizedBox(height: 12),
          // Transport selector
          SizedBox(
            height: 52,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              itemCount: _transports.length,
              separatorBuilder: (_, __) => const SizedBox(width: 8),
              itemBuilder: (_, i) {
                final (id, labelKey, icon) = _transports[i];
                final isSelected = selectedTransport.value == id;
                return GestureDetector(
                  onTap: () => selectedTransport.value = id,
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 180),
                    padding: const EdgeInsets.symmetric(
                      horizontal: 14,
                      vertical: 10,
                    ),
                    decoration: BoxDecoration(
                      color: isSelected
                          ? const Color(0xFFB78628)
                          : Colors.white.withValues(alpha: 0.08),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: isSelected
                            ? const Color(0xFFB78628)
                            : Colors.white12,
                      ),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          icon,
                          size: 18,
                          color: isSelected
                              ? Colors.white
                              : Colors.white60,
                        ),
                        const SizedBox(width: 6),
                        Text(
                          _s(labelKey),
                          style: TextStyle(
                            color: isSelected
                                ? Colors.white
                                : Colors.white60,
                            fontSize: 12,
                            fontWeight: isSelected
                                ? FontWeight.bold
                                : FontWeight.normal,
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
          const SizedBox(height: 12),
          // Distance input
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: distCtrl,
                  keyboardType:
                      const TextInputType.numberWithOptions(decimal: true),
                  style: const TextStyle(color: Colors.white),
                  decoration: InputDecoration(
                    hintText: _s('carbon_distance_hint'),
                    hintStyle: const TextStyle(color: Colors.white38),
                    filled: true,
                    fillColor: Colors.white.withValues(alpha: 0.08),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                      borderSide: BorderSide.none,
                    ),
                    contentPadding: const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 14,
                    ),
                    suffixText: 'km',
                    suffixStyle:
                        const TextStyle(color: Colors.white38),
                  ),
                  onSubmitted: (_) => addLeg(),
                ),
              ),
              const SizedBox(width: 8),
              ElevatedButton(
                onPressed: addLeg,
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFFB78628),
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 16,
                  ),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                child: Text(
                  _s('carbon_add_btn'),
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),

          // ── Legs list ─────────────────────────────────────────────────────
          if (legs.value.isNotEmpty) ...[
            const SizedBox(height: 16),
            Text(
              _s('carbon_legs_label'),
              style: const TextStyle(
                color: Colors.white70,
                fontWeight: FontWeight.bold,
                fontSize: 13,
                letterSpacing: 1.1,
              ),
            ),
            const SizedBox(height: 8),
            ...legs.value.asMap().entries.map((entry) {
              final i = entry.key;
              final leg = entry.value;
              final transportId =
                  leg['transport_type'] as String? ?? '';
              final dist = leg['distance_km'];
              final transportEntry = _transports.firstWhere(
                (t) => t.$1 == transportId,
                orElse: () =>
                    ('', 'carbon_transport_car', Icons.directions_car),
              );
              return Container(
                margin: const EdgeInsets.only(bottom: 6),
                padding: const EdgeInsets.symmetric(
                  horizontal: 14,
                  vertical: 10,
                ),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.06),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: Colors.white12),
                ),
                child: Row(
                  children: [
                    Icon(
                      transportEntry.$3,
                      color: const Color(0xFFB78628),
                      size: 18,
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        '${_s(transportEntry.$2)} · $dist km',
                        style: const TextStyle(color: Colors.white70),
                      ),
                    ),
                    GestureDetector(
                      onTap: () => removeLeg(i),
                      child: const Icon(
                        Icons.close,
                        size: 16,
                        color: Colors.white38,
                      ),
                    ),
                  ],
                ),
              );
            }),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: isLoading.value ? null : calculate,
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF4CAF50),
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                child: isLoading.value
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(
                          color: Colors.white,
                          strokeWidth: 2,
                        ),
                      )
                    : Text(
                        _s('carbon_calculate_btn'),
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.bold,
                          fontSize: 15,
                        ),
                      ),
              ),
            ),
          ],
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}
