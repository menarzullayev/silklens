import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_hooks/flutter_hooks.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/core/l10n/locale_service.dart';
import 'package:silklens/data/api/clients/api_client_provider.dart';
import 'package:silklens/presentation/providers/locale_provider.dart';

class TripPlannerPage extends HookConsumerWidget {
  const TripPlannerPage({super.key});

  String _s(String key) => AppStrings.get(LocaleService.instance.locale, key);

  static const _cities = <String>[
    'Samarqand',
    'Buxoro',
    'Xiva',
    'Toshkent',
    'Shahrisabz',
    'Termiz',
  ];

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
    final selectedCities = useState<Set<String>>({});
    final days = useState<int>(3);
    final budget = useState<double>(300);
    final isLoading = useState(false);
    final result = useState<Map<String, dynamic>?>(null);
    final errorMsg = useState<String?>(null);

    Future<void> submit() async {
      if (selectedCities.value.isEmpty) return;
      isLoading.value = true;
      errorMsg.value = null;
      result.value = null;
      try {
        result.value = await ref.read(silkLensApiClientProvider).createTrip(
              cities: selectedCities.value.toList(),
              budgetUsd: budget.value,
              language: locale.languageCode,
            );
      } catch (_) {
        errorMsg.value = _s('trip_error');
      }
      isLoading.value = false;
    }

    final dayPlan = (result.value?['day_plan'] as List?) ?? [];

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
          _s('trip_title'),
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
          // ── City selection ─────────────────────────────────────────────
          _Label(text: _s('trip_select_cities')),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: _cities.map((city) {
              final isSelected = selectedCities.value.contains(city);
              return FilterChip(
                label: Text(city),
                selected: isSelected,
                onSelected: (v) {
                  final next = Set<String>.from(selectedCities.value);
                  if (v) {
                    next.add(city);
                  } else {
                    next.remove(city);
                  }
                  selectedCities.value = next;
                },
                selectedColor: const Color(0xFFB78628),
                backgroundColor: Colors.white.withValues(alpha: 0.1),
                checkmarkColor: Colors.white,
                labelStyle: TextStyle(
                  color: isSelected ? Colors.white : Colors.white70,
                  fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                ),
                side: BorderSide(
                  color: isSelected ? const Color(0xFFB78628) : Colors.white24,
                ),
              );
            }).toList(),
          ),
          const SizedBox(height: 24),

          // ── Days slider ────────────────────────────────────────────────
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _Label(text: _s('trip_days')),
              Text(
                '$days ${_s("trip_days_unit")}',
                style: const TextStyle(
                  color: Color(0xFFB78628),
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          Slider(
            value: days.value.toDouble(),
            min: 1,
            max: 14,
            divisions: 13,
            activeColor: const Color(0xFFB78628),
            inactiveColor: Colors.white24,
            onChanged: (v) => days.value = v.round(),
          ),
          const SizedBox(height: 16),

          // ── Budget slider ──────────────────────────────────────────────
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _Label(text: _s('trip_budget')),
              Text(
                '\$${budget.value.toStringAsFixed(0)}',
                style: const TextStyle(
                  color: Color(0xFFB78628),
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          Slider(
            value: budget.value,
            min: 50,
            max: 5000,
            divisions: 99,
            activeColor: const Color(0xFFB78628),
            inactiveColor: Colors.white24,
            onChanged: (v) => budget.value = v,
          ),
          const SizedBox(height: 28),

          // ── Submit ─────────────────────────────────────────────────────
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFFB78628),
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                ),
                disabledBackgroundColor:
                    const Color(0xFFB78628).withValues(alpha: 0.4),
              ),
              onPressed: (isLoading.value || selectedCities.value.isEmpty)
                  ? null
                  : submit,
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
                      _s('trip_generate_btn'),
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
            ),
          ),
          const SizedBox(height: 24),

          // ── Error ──────────────────────────────────────────────────────
          if (errorMsg.value != null)
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: Colors.red.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: Colors.red.withValues(alpha: 0.3),
                ),
              ),
              child: Text(
                errorMsg.value!,
                style: const TextStyle(color: Colors.redAccent),
              ),
            ),

          // ── Results ────────────────────────────────────────────────────
          if (result.value != null && dayPlan.isNotEmpty) ...[
            _Label(text: _s('trip_plan_label')),
            const SizedBox(height: 12),
            ...dayPlan.asMap().entries.map((entry) {
              final dayIndex = entry.key + 1;
              final day = entry.value as Map<String, dynamic>;
              final activities = (day['activities'] as List?) ?? [];
              return _DayCard(
                dayIndex: dayIndex,
                day: day,
                activities: activities,
                s: _s,
              );
            }),
          ],
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------

class _Label extends StatelessWidget {
  const _Label({required this.text});
  final String text;

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      style: const TextStyle(
        color: Colors.white70,
        fontWeight: FontWeight.bold,
        fontSize: 13,
        letterSpacing: 1.1,
      ),
    );
  }
}

// ---------------------------------------------------------------------------

class _DayCard extends StatelessWidget {
  const _DayCard({
    required this.dayIndex,
    required this.day,
    required this.activities,
    required this.s,
  });

  final int dayIndex;
  final Map<String, dynamic> day;
  final List<dynamic> activities;
  final String Function(String) s;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Day header
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: 16,
              vertical: 12,
            ),
            decoration: BoxDecoration(
              color: const Color(0xFFB78628).withValues(alpha: 0.15),
              borderRadius: const BorderRadius.vertical(
                top: Radius.circular(16),
              ),
            ),
            child: Row(
              children: [
                Container(
                  width: 32,
                  height: 32,
                  decoration: const BoxDecoration(
                    color: Color(0xFFB78628),
                    shape: BoxShape.circle,
                  ),
                  child: Center(
                    child: Text(
                      '$dayIndex',
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Text(
                  '${s("trip_day")} $dayIndex',
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                    fontSize: 15,
                  ),
                ),
                if (day['city'] != null) ...[
                  const SizedBox(width: 8),
                  Text(
                    '· ${day["city"]}',
                    style: const TextStyle(
                      color: Colors.white60,
                      fontSize: 13,
                    ),
                  ),
                ],
              ],
            ),
          ),
          // Activities
          Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              children: activities.map((a) {
                final activity = a as Map<String, dynamic>;
                final time = activity['time'] as String? ?? '';
                final name = activity['name'] as String? ?? '';
                final desc = activity['description'] as String? ?? '';
                return Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (time.isNotEmpty)
                        SizedBox(
                          width: 52,
                          child: Text(
                            time,
                            style: const TextStyle(
                              color: Color(0xFFB78628),
                              fontSize: 12,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              name,
                              style: const TextStyle(
                                color: Colors.white,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            if (desc.isNotEmpty)
                              Text(
                                desc,
                                style: const TextStyle(
                                  color: Colors.white60,
                                  fontSize: 12,
                                ),
                              ),
                          ],
                        ),
                      ),
                    ],
                  ),
                );
              }).toList(),
            ),
          ),
        ],
      ),
    );
  }
}
