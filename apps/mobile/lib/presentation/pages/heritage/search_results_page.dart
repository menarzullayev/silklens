import 'dart:async';

// SILK-0095 — SearchResultsPage wired to real /v1/search API.
// Replaces hardcoded list with live results from the backend.
// Tapping a card navigates to /home/heritage/:pubId.

import 'package:flutter/material.dart';
import 'package:flutter_hooks/flutter_hooks.dart';
import 'package:go_router/go_router.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/core/l10n/locale_service.dart';
import 'package:silklens/data/api/clients/api_client_provider.dart';

class SearchResultsPage extends HookConsumerWidget {
  const SearchResultsPage({super.key, this.query = ''});
  final String query;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final locale = LocaleService.instance.locale;
    String s(String key) => AppStrings.get(locale, key);

    final results = useState<List<Map<String, dynamic>>>([]);
    final isLoading = useState(true);
    final errorMsg = useState<String?>(null);
    final gridView = useState(true);

    const gradients = [
      [Color(0xFF8B3A2A), Color(0xFFD2691E)],
      [Color(0xFF1A3A5C), Color(0xFF2E6B9E)],
      [Color(0xFFF5E6C8), Color(0xFFD4A853)],
      [Color(0xFF2D5A1B), Color(0xFF4A7C3F)],
    ];

    useEffect(() {
      Future<void> load() async {
        if (query.trim().isEmpty) {
          isLoading.value = false;
          return;
        }
        try {
          final client = ref.read(silkLensApiClientProvider);
          final data = await client.searchHeritage(
            query: query.trim(),
            lang: locale,
          );
          final hits = (data['hits'] as List?) ?? [];
          results.value = hits
              .whereType<Map<String, dynamic>>()
              .toList();
        } catch (_) {
          errorMsg.value = s('search_error');
        } finally {
          isLoading.value = false;
        }
      }

      unawaited(load());
      return null;
    }, [query]);

    final count = results.value.length;
    final title = count == 0 && !isLoading.value
        ? s('search_empty')
        : s('search_results_title').replaceFirst('{n}', '$count');

    return Scaffold(
      backgroundColor: const Color(0xFF0D2337),
      appBar: AppBar(
        backgroundColor: const Color(0xFF0D2337),
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
          isLoading.value ? s('search_loading') : title,
          style: const TextStyle(color: Colors.white, fontSize: 16),
        ),
        actions: [
          if (!isLoading.value && results.value.isNotEmpty)
            IconButton(
              icon: Icon(
                gridView.value
                    ? Icons.view_list_rounded
                    : Icons.grid_view_rounded,
                color: Colors.white,
              ),
              onPressed: () => gridView.value = !gridView.value,
            ),
        ],
      ),
      body: _buildBody(
        context: context,
        isLoading: isLoading.value,
        error: errorMsg.value,
        items: results.value,
        gridView: gridView.value,
        gradients: gradients,
        locale: locale,
        s: s,
      ),
    );
  }

  Widget _buildBody({
    required BuildContext context,
    required bool isLoading,
    required String? error,
    required List<Map<String, dynamic>> items,
    required bool gridView,
    required List<List<Color>> gradients,
    required String locale,
    required String Function(String) s,
  }) {
    if (isLoading) {
      return const Center(
        child: CircularProgressIndicator(color: Color(0xFFB78628)),
      );
    }
    if (error != null) {
      return Center(
        child: Text(
          error,
          style: const TextStyle(color: Colors.white70, fontSize: 14),
          textAlign: TextAlign.center,
        ),
      );
    }
    if (items.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.search_off_rounded,
              color: Colors.white.withValues(alpha: 0.3),
              size: 56,
            ),
            const SizedBox(height: 12),
            Text(
              s('search_empty'),
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.5),
                fontSize: 15,
              ),
            ),
          ],
        ),
      );
    }
    if (gridView) {
      return GridView.builder(
        padding: const EdgeInsets.all(16),
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 2,
          crossAxisSpacing: 12,
          mainAxisSpacing: 12,
          childAspectRatio: 0.8,
        ),
        itemCount: items.length,
        itemBuilder: (_, i) => _ResultCard(
          hit: items[i],
          colors: gradients[i % 4],
          isGrid: true,
          locale: locale,
          onTap: (pubId) => context.push('/home/heritage/$pubId'),
        ),
      );
    }
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: items.length,
      itemBuilder: (_, i) => Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: _ResultCard(
          hit: items[i],
          colors: gradients[i % 4],
          isGrid: false,
          locale: locale,
          onTap: (pubId) => context.push('/home/heritage/$pubId'),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Internal card widget
// ---------------------------------------------------------------------------

class _ResultCard extends StatelessWidget {
  const _ResultCard({
    required this.hit,
    required this.colors,
    required this.isGrid,
    required this.locale,
    required this.onTap,
  });

  final Map<String, dynamic> hit;
  final List<Color> colors;
  final bool isGrid;
  final String locale;
  final void Function(String pubId) onTap;

  String get _name {
    final nameMap = hit['name'];
    if (nameMap is Map) {
      return (nameMap[locale] ?? nameMap['en'] ?? nameMap.values.firstOrNull)
              ?.toString() ??
          hit['pub_id']?.toString() ??
          '';
    }
    return hit['name']?.toString() ?? hit['pub_id']?.toString() ?? '';
  }

  String get _pubId => hit['heritage_pub_id']?.toString() ?? hit['pub_id']?.toString() ?? '';

  String get _kindSlug => hit['kind_slug']?.toString() ?? '';

  String get _countryCode => hit['country_code']?.toString() ?? '';

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () {
        if (_pubId.isNotEmpty) onTap(_pubId);
      },
      child: Container(
        height: isGrid ? null : 80,
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.06),
          borderRadius: BorderRadius.circular(16),
          border:
              Border.all(color: Colors.white.withValues(alpha: 0.10)),
        ),
        child: isGrid
            ? Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Container(
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          colors: colors,
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                        ),
                        borderRadius: const BorderRadius.vertical(
                          top: Radius.circular(16),
                        ),
                      ),
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.all(10),
                    child: Text(
                      _name,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              )
            : Row(
                children: [
                  Container(
                    width: 80,
                    height: 80,
                    decoration: BoxDecoration(
                      gradient: LinearGradient(colors: colors),
                      borderRadius: const BorderRadius.horizontal(
                        left: Radius.circular(16),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          _name,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: 4),
                        Row(
                          children: [
                            if (_kindSlug.isNotEmpty) ...[
                              const Icon(
                                Icons.place_rounded,
                                color: Color(0xFFB78628),
                                size: 12,
                              ),
                              const SizedBox(width: 2),
                              Text(
                                _kindSlug,
                                style: const TextStyle(
                                  color: Color(0xFFB78628),
                                  fontSize: 11,
                                ),
                              ),
                              const SizedBox(width: 8),
                            ],
                            if (_countryCode.isNotEmpty)
                              Text(
                                _countryCode.toUpperCase(),
                                style: TextStyle(
                                  color: Colors.white.withValues(alpha: 0.5),
                                  fontSize: 11,
                                ),
                              ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ],
              ),
      ),
    );
  }
}
