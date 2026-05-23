// SILK-0133 — Food Guide: AI-powered restaurant and dish recommendations.

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_hooks/flutter_hooks.dart';
import 'package:go_router/go_router.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/core/l10n/locale_service.dart';
import 'package:silklens/data/api/clients/api_client_provider.dart';
import 'package:silklens/presentation/providers/locale_provider.dart';

class FoodGuidePage extends HookConsumerWidget {
  const FoodGuidePage({super.key});

  String _s(String key) =>
      AppStrings.get(LocaleService.instance.locale, key);

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
    final controller = useTextEditingController();
    final isLoading = useState(false);
    final aiReply = useState<String?>(null);
    final restaurants =
        useState<List<Map<String, dynamic>>>([]);
    final mustTry = useState<List<String>>([]);
    final dietaryTips = useState<List<String>>([]);
    final selectedDietary = useState<List<String>>([]);

    Future<void> search(String query) async {
      if (isLoading.value) return;
      isLoading.value = true;
      try {
        final client = ref.read(silkLensApiClientProvider);
        final result = await client.getFoodRecommendations(
          message: query.isEmpty ? _s('food_default_query') : query,
          language: locale.languageCode,
          dietaryPreferences: selectedDietary.value,
        );
        aiReply.value = result['reply'] as String?;
        restaurants.value =
            ((result['restaurant_recommendations'] as List?) ?? [])
                .map((e) => Map<String, dynamic>.from(e as Map))
                .toList();
        mustTry.value = ((result['must_try_dishes'] as List?) ?? [])
            .cast<String>();
        dietaryTips.value =
            ((result['dietary_tips'] as List?) ?? []).cast<String>();
      } catch (_) {}
      isLoading.value = false;
    }

    useEffect(() {
      Future(
        () => search(''),
      );
      return null;
    }, const []);

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
          _s('food_title'),
          style: const TextStyle(
            color: Colors.white,
            fontSize: 20,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
      body: Column(
        children: [
          // ── Search bar ────────────────────────────────────────────────────
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: controller,
                    style: const TextStyle(color: Colors.white),
                    decoration: InputDecoration(
                      hintText: _s('food_search_hint'),
                      hintStyle:
                          const TextStyle(color: Colors.white38),
                      filled: true,
                      fillColor:
                          Colors.white.withValues(alpha: 0.08),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(14),
                        borderSide: BorderSide.none,
                      ),
                      contentPadding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 14,
                      ),
                    ),
                    onSubmitted: search,
                    textInputAction: TextInputAction.search,
                  ),
                ),
                const SizedBox(width: 8),
                _SendButton(
                  isLoading: isLoading.value,
                  onTap: () => search(controller.text),
                ),
              ],
            ),
          ),
          // ── Results ───────────────────────────────────────────────────────
          Expanded(
            child: ListView(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              children: [
                if (aiReply.value != null && aiReply.value!.isNotEmpty)
                  _AiReplyCard(text: aiReply.value!),
                if (mustTry.value.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  _SectionLabel(text: _s('food_must_try')),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 4,
                    children: mustTry.value
                        .map(
                          (dish) => Chip(
                            label: Text(
                              dish,
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 12,
                              ),
                            ),
                            backgroundColor: const Color(0xFF1F3A93)
                                .withValues(alpha: 0.5),
                            side: BorderSide.none,
                          ),
                        )
                        .toList(),
                  ),
                ],
                if (restaurants.value.isNotEmpty) ...[
                  const SizedBox(height: 16),
                  _SectionLabel(text: _s('food_nearby_restaurants')),
                  const SizedBox(height: 8),
                  ...restaurants.value.map(
                    (r) => _RestaurantCard(restaurant: r),
                  ),
                ],
                if (dietaryTips.value.isNotEmpty) ...[
                  const SizedBox(height: 16),
                  _SectionLabel(text: _s('food_dietary_tips')),
                  const SizedBox(height: 8),
                  ...dietaryTips.value.map(
                    (tip) => Padding(
                      padding: const EdgeInsets.only(bottom: 6),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Icon(
                            Icons.info_outline,
                            color: Color(0xFFB78628),
                            size: 16,
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              tip,
                              style: const TextStyle(
                                color: Colors.white70,
                                fontSize: 13,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
                const SizedBox(height: 24),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ─── Sub-widgets ─────────────────────────────────────────────────────────────

class _SendButton extends StatelessWidget {
  const _SendButton({required this.isLoading, required this.onTap});

  final bool isLoading;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 48,
        height: 48,
        decoration: BoxDecoration(
          color: const Color(0xFFB78628),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Center(
          child: isLoading
              ? const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: Colors.white,
                  ),
                )
              : const Icon(Icons.send, color: Colors.white, size: 20),
        ),
      ),
    );
  }
}

class _AiReplyCard extends StatelessWidget {
  const _AiReplyCard({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      margin: const EdgeInsets.only(top: 4, bottom: 4),
      decoration: BoxDecoration(
        color: const Color(0xFFB78628).withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: const Color(0xFFB78628).withValues(alpha: 0.3),
        ),
      ),
      child: Text(
        text,
        style: const TextStyle(color: Colors.white, fontSize: 14, height: 1.5),
      ),
    );
  }
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel({required this.text});

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

class _RestaurantCard extends StatelessWidget {
  const _RestaurantCard({required this.restaurant});

  final Map<String, dynamic> restaurant;

  @override
  Widget build(BuildContext context) {
    final name = restaurant['name'] as String? ?? '';
    final priceRange = restaurant['price_range'] as String? ?? '\$\$';
    final distanceKm = restaurant['distance_km'];
    final cuisine = restaurant['cuisine'] as String? ?? '';

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.white12),
      ),
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: const Color(0xFFB78628).withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Icon(
              Icons.restaurant,
              color: Color(0xFFB78628),
              size: 20,
            ),
          ),
          const SizedBox(width: 12),
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
                const SizedBox(height: 2),
                Text(
                  [
                    if (cuisine.isNotEmpty) cuisine,
                    priceRange,
                    if (distanceKm != null) '$distanceKm km',
                  ].join(' · '),
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
  }
}
