import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_hooks/flutter_hooks.dart';
import 'package:go_router/go_router.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/core/l10n/locale_service.dart';
import 'package:silklens/data/api/clients/api_client_provider.dart';
import 'package:silklens/presentation/providers/locale_provider.dart';

class MoodTravelPage extends HookConsumerWidget {
  const MoodTravelPage({super.key});

  String _s(String key) => AppStrings.get(LocaleService.instance.locale, key);

  static const _moods = <(String, String, String)>[
    ('tired', '😴', 'mood_tired'),
    ('adventurous', '🏃', 'mood_adventurous'),
    ('romantic', '❤️', 'mood_romantic'),
    ('curious', '🔍', 'mood_curious'),
    ('family', '👨‍👩‍👧', 'mood_family'),
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
    final selectedMood = useState<String?>(null);
    final result = useState<Map<String, dynamic>?>(null);
    final isLoading = useState(false);

    Future<void> fetchRecs(String mood) async {
      selectedMood.value = mood;
      isLoading.value = true;
      result.value = null;
      try {
        result.value =
            await ref.read(silkLensApiClientProvider).getMoodRecommendations(
                  mood: mood,
                  availableHours: 3,
                  language: locale.languageCode,
                );
      } catch (_) {}
      isLoading.value = false;
    }

    final recommendations =
        (result.value?['recommended_heritage'] as List?) ?? [];

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
          _s('mood_title'),
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
          Text(
            _s('mood_question'),
            style: const TextStyle(
              color: Colors.white,
              fontSize: 22,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 20),
          // Mood chips
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: _moods.map((m) {
              final (id, emoji, labelKey) = m;
              final isSelected = selectedMood.value == id;
              return GestureDetector(
                onTap: () => fetchRecs(id),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 12,
                  ),
                  decoration: BoxDecoration(
                    color: isSelected
                        ? const Color(0xFFB78628)
                        : Colors.white.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(
                      color:
                          isSelected ? const Color(0xFFB78628) : Colors.white12,
                    ),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(emoji, style: const TextStyle(fontSize: 20)),
                      const SizedBox(width: 8),
                      Text(
                        _s(labelKey),
                        style: TextStyle(
                          color: isSelected ? Colors.white : Colors.white70,
                          fontWeight:
                              isSelected ? FontWeight.bold : FontWeight.normal,
                        ),
                      ),
                    ],
                  ),
                ),
              );
            }).toList(),
          ),
          const SizedBox(height: 28),
          if (isLoading.value)
            const Center(
              child: CircularProgressIndicator(color: Color(0xFFB78628)),
            ),
          if (result.value != null) ...[
            // AI message
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.06),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: Colors.white12),
              ),
              child: Text(
                result.value!['message'] as String? ?? '',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 15,
                  height: 1.5,
                ),
              ),
            ),
            const SizedBox(height: 20),
            if (recommendations.isNotEmpty) ...[
              Text(
                _s('mood_recommended'),
                style: const TextStyle(
                  color: Colors.white70,
                  fontWeight: FontWeight.bold,
                  fontSize: 13,
                  letterSpacing: 1.1,
                ),
              ),
              const SizedBox(height: 10),
              ...recommendations.map((h) {
                final heritage = h as Map<String, dynamic>;
                final name = heritage['name'] as String? ?? '';
                final dist = heritage['distance_km'];
                final pubId = heritage['pub_id'] as String?;
                return Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.06),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: Colors.white12),
                  ),
                  child: ListTile(
                    leading: const Icon(
                      Icons.place,
                      color: Color(0xFFB78628),
                    ),
                    title: Text(
                      name,
                      style: const TextStyle(color: Colors.white),
                    ),
                    subtitle: dist != null
                        ? Text(
                            '$dist km',
                            style: const TextStyle(
                              color: Colors.white60,
                              fontSize: 12,
                            ),
                          )
                        : null,
                    trailing: const Icon(
                      Icons.chevron_right,
                      color: Colors.white38,
                    ),
                    onTap: pubId != null
                        ? () => context.push('/home/heritage/$pubId')
                        : null,
                  ),
                );
              }),
            ],
          ],
        ],
      ),
    );
  }
}
