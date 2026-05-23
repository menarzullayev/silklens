// SILK-0095 — SearchPage wired to real /v1/search API.
// Converts from StatefulWidget to HookConsumerWidget, pulls recentSearches
// from SharedPreferences-backed provider, and navigates to SearchResultsPage.

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_hooks/flutter_hooks.dart';
import 'package:go_router/go_router.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/core/l10n/locale_service.dart';
import 'package:silklens/data/api/clients/api_client_provider.dart';
import 'package:silklens/presentation/providers/recent_searches_provider.dart';

class SearchPage extends HookConsumerWidget {
  const SearchPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final locale = LocaleService.instance.locale;
    String s(String key) => AppStrings.get(locale, key);

    final ctrl = useTextEditingController();
    final isSearching = useState(false);
    final errorMsg = useState<String?>(null);
    final activeCountry = useState(-1);
    final activeType = useState(-1);

    // Locale-aware country + type labels
    final countries = [
      ('uz', s('search_country_uz')),
      ('kz', s('search_country_kz')),
      ('tj', s('search_country_tj')),
      ('tm', s('search_country_tm')),
    ];
    final types = [
      ('mosque', s('search_type_mosque')),
      ('palace', s('search_type_palace')),
      ('museum', s('search_type_museum')),
      ('tomb', s('search_type_tomb')),
      ('nature', s('search_type_nature')),
    ];

    // Recent searches (async)
    final recentAsync = ref.watch(recentSearchesProvider);
    final recentList = recentAsync.valueOrNull ?? const <String>[];

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

    Future<void> doSearch(String q) async {
      final trimmed = q.trim();
      if (trimmed.isEmpty) return;
      isSearching.value = true;
      errorMsg.value = null;
      try {
        final client = ref.read(silkLensApiClientProvider);
        final country = activeCountry.value >= 0 ? countries[activeCountry.value].$1 : null;
        final kind = activeType.value >= 0 ? types[activeType.value].$1 : null;
        await client.searchHeritage(
          query: trimmed,
          lang: locale,
          country: country,
          kind: kind,
        );
        await ref.read(recentSearchesProvider.notifier).add(trimmed);
        if (!context.mounted) return;
        // ignore: unawaited_futures
        context.push('/search/results?q=${Uri.encodeComponent(trimmed)}');
      } catch (_) {
        if (!context.mounted) return;
        errorMsg.value = s('search_error');
      } finally {
        isSearching.value = false;
      }
    }

    return Scaffold(
      backgroundColor: const Color(0xFF0D2337),
      body: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // --- Search bar ---------------------------------------------------
            Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  GestureDetector(
                    onTap: () => context.pop(),
                    child: const Icon(
                      Icons.arrow_back_ios_new,
                      color: Colors.white,
                      size: 20,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Container(
                      height: 48,
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.08),
                        borderRadius: BorderRadius.circular(24),
                        border: Border.all(
                          color: Colors.white.withValues(alpha: 0.20),
                        ),
                      ),
                      child: TextField(
                        controller: ctrl,
                        autofocus: true,
                        style: const TextStyle(color: Colors.white),
                        onSubmitted: doSearch,
                        decoration: InputDecoration(
                          hintText: s('search_hint'),
                          hintStyle: TextStyle(
                            color: Colors.white.withValues(alpha: 0.4),
                          ),
                          prefixIcon: isSearching.value
                              ? const Padding(
                                  padding: EdgeInsets.all(12),
                                  child: SizedBox(
                                    width: 18,
                                    height: 18,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                      color: Colors.white70,
                                    ),
                                  ),
                                )
                              : Icon(
                                  Icons.search,
                                  color: Colors.white.withValues(alpha: 0.5),
                                  size: 18,
                                ),
                          border: InputBorder.none,
                          contentPadding: const EdgeInsets.symmetric(vertical: 14),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),

            // --- Error message ------------------------------------------------
            if (errorMsg.value != null)
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
                child: Text(
                  errorMsg.value!,
                  style: const TextStyle(color: Color(0xFFE57373), fontSize: 12),
                ),
              ),

            // --- Recent searches ----------------------------------------------
            if (recentList.isNotEmpty) ...[
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 4, 16, 4),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      s('search_recent_label'),
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.5),
                        fontSize: 12,
                        letterSpacing: 0.8,
                      ),
                    ),
                    GestureDetector(
                      onTap: () => ref.read(recentSearchesProvider.notifier).clear(),
                      child: Text(
                        s('search_recent_clear'),
                        style: const TextStyle(
                          color: Color(0xFFB78628),
                          fontSize: 12,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              SizedBox(
                height: 32,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  itemCount: recentList.length,
                  separatorBuilder: (_, __) => const SizedBox(width: 6),
                  itemBuilder: (_, i) => GestureDetector(
                    onTap: () {
                      ctrl
                        ..text = recentList[i]
                        ..selection = TextSelection.collapsed(
                          offset: recentList[i].length,
                        );
                      // ignore: discarded_futures
                      doSearch(recentList[i]);
                    },
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 6,
                      ),
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.07),
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(
                          color: Colors.white.withValues(alpha: 0.12),
                        ),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.history,
                            color: Colors.white.withValues(alpha: 0.4),
                            size: 12,
                          ),
                          const SizedBox(width: 4),
                          Text(
                            recentList[i],
                            style: TextStyle(
                              color: Colors.white.withValues(alpha: 0.7),
                              fontSize: 12,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 8),
            ],

            // --- Country filter -----------------------------------------------
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 0, 8),
              child: Text(
                s('search_filter_country'),
                style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.5),
                  fontSize: 12,
                  letterSpacing: 1,
                ),
              ),
            ),
            SizedBox(
              height: 36,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 16),
                itemCount: countries.length,
                separatorBuilder: (_, __) => const SizedBox(width: 8),
                itemBuilder: (_, i) => GestureDetector(
                  onTap: () => activeCountry.value = activeCountry.value == i ? -1 : i,
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 8,
                    ),
                    decoration: BoxDecoration(
                      color: activeCountry.value == i
                          ? const Color(0xFFB78628)
                          : Colors.white.withValues(alpha: 0.08),
                      borderRadius: BorderRadius.circular(18),
                      border: Border.all(
                        color: activeCountry.value == i
                            ? const Color(0xFFB78628)
                            : Colors.white.withValues(alpha: 0.15),
                      ),
                    ),
                    child: Text(
                      countries[i].$2,
                      style: TextStyle(
                        color: activeCountry.value == i ? const Color(0xFF1A1200) : Colors.white,
                        fontSize: 12,
                      ),
                    ),
                  ),
                ),
              ),
            ),

            // --- Type filter --------------------------------------------------
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 0, 8),
              child: Text(
                s('search_filter_type'),
                style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.5),
                  fontSize: 12,
                  letterSpacing: 1,
                ),
              ),
            ),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: List.generate(
                types.length,
                (i) => GestureDetector(
                  onTap: () => activeType.value = activeType.value == i ? -1 : i,
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 14,
                      vertical: 8,
                    ),
                    margin: const EdgeInsets.only(left: 16),
                    decoration: BoxDecoration(
                      color: activeType.value == i
                          ? const Color(0xFFB78628)
                          : Colors.white.withValues(alpha: 0.08),
                      borderRadius: BorderRadius.circular(18),
                      border: Border.all(
                        color: activeType.value == i
                            ? const Color(0xFFB78628)
                            : Colors.white.withValues(alpha: 0.15),
                      ),
                    ),
                    child: Text(
                      types[i].$2,
                      style: TextStyle(
                        color: activeType.value == i ? const Color(0xFF1A1200) : Colors.white,
                        fontSize: 12,
                      ),
                    ),
                  ),
                ),
              ),
            ),

            const Spacer(),

            // --- Apply button -------------------------------------------------
            Padding(
              padding: const EdgeInsets.all(16),
              child: GestureDetector(
                // ignore: discarded_futures
                onTap: isSearching.value ? null : () => doSearch(ctrl.text),
                child: Container(
                  height: 54,
                  width: double.infinity,
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [Color(0xFFB78628), Color(0xFFE5C97A)],
                    ),
                    borderRadius: BorderRadius.circular(14),
                    boxShadow: [
                      BoxShadow(
                        color: const Color(0xFFB78628).withValues(alpha: 0.3),
                        blurRadius: 12,
                        offset: const Offset(0, 4),
                      ),
                    ],
                  ),
                  child: Center(
                    child: isSearching.value
                        ? const SizedBox(
                            width: 22,
                            height: 22,
                            child: CircularProgressIndicator(
                              strokeWidth: 2.5,
                              color: Color(0xFF1A1200),
                            ),
                          )
                        : Text(
                            s('search_apply'),
                            style: const TextStyle(
                              color: Color(0xFF1A1200),
                              fontSize: 16,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
