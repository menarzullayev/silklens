// Discover (heritage list) page — the main FAZA 1 Hafta 2 deliverable.
//
//   * Search bar at the top with 300ms debounce.
//   * Filter chips: kind (from /vocab/heritage_kinds) + country.
//   * Masonry-style ListView of cards (hero image + title + period).
//   * Infinite scroll via [HeritageListNotifier.loadMore].
//   * Empty / loading / error states all localized.

import "dart:async";

import "package:flutter/material.dart";
import "package:flutter_hooks/flutter_hooks.dart";
import "package:go_router/go_router.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/domain/vocab/entities/vocab_term.dart";
import "package:silklens/l10n/app_localizations.dart";
import "package:silklens/presentation/providers/heritage_list_provider.dart";
import "package:silklens/presentation/providers/recent_searches_provider.dart";
import "package:silklens/presentation/providers/vocab_provider.dart";
import "package:silklens/presentation/router/app_router.dart";
import "package:silklens/presentation/widgets/heritage_card.dart";

class HeritageListPage extends HookConsumerWidget {
  const HeritageListPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final scrollController = useScrollController();
    final searchController = useTextEditingController();
    final debounceTimer = useRef<Timer?>(null);

    useEffect(
      () {
        void onScroll() {
          if (scrollController.position.pixels >=
              scrollController.position.maxScrollExtent - 240) {
            ref.read(heritageListProvider.notifier).loadMore();
          }
        }

        scrollController.addListener(onScroll);
        return () => scrollController.removeListener(onScroll);
      },
      <Object?>[scrollController],
    );

    useEffect(
      () => () => debounceTimer.value?.cancel(),
      const <Object?>[],
    );

    final state = ref.watch(heritageListProvider);
    final kindsAsync = ref.watch(heritageKindsProvider);
    final notifier = ref.read(heritageListProvider.notifier);

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n?.heritageListTitle ?? ""),
        actions: <Widget>[
          IconButton(
            key: const Key("heritage_list.search_icon"),
            icon: const Icon(Icons.search),
            onPressed: () => context.go(AppRoutes.heritageSearch),
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: <Widget>[
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
              child: TextField(
                key: const Key("heritage_list.search_field"),
                controller: searchController,
                decoration: InputDecoration(
                  hintText: l10n?.heritageSearchHint ?? "",
                  prefixIcon: const Icon(Icons.search),
                  suffixIcon: searchController.text.isEmpty
                      ? null
                      : IconButton(
                          icon: const Icon(Icons.clear),
                          onPressed: () {
                            searchController.clear();
                            notifier.setSearch(null);
                          },
                        ),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                onChanged: (String value) {
                  debounceTimer.value?.cancel();
                  debounceTimer.value = Timer(
                    const Duration(milliseconds: 300),
                    () {
                      notifier.setSearch(value.trim().isEmpty ? null : value);
                      if (value.trim().isNotEmpty) {
                        ref
                            .read(recentSearchesProvider.notifier)
                            .add(value.trim());
                      }
                    },
                  );
                },
                onSubmitted: (String value) {
                  if (value.trim().isNotEmpty) {
                    ref
                        .read(recentSearchesProvider.notifier)
                        .add(value.trim());
                  }
                },
              ),
            ),
            _FilterChipsRow(kindsAsync: kindsAsync),
            Expanded(
              child: _HeritageListBody(
                state: state,
                scrollController: scrollController,
                onRetry: notifier.refresh,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _FilterChipsRow extends ConsumerWidget {
  const _FilterChipsRow({required this.kindsAsync});

  final AsyncValue<List<VocabTerm>> kindsAsync;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final state = ref.watch(heritageListProvider);
    final notifier = ref.read(heritageListProvider.notifier);
    final locale = Localizations.localeOf(context).languageCode;
    final kinds = kindsAsync.maybeWhen(
      data: (List<VocabTerm> v) => v,
      orElse: () => const <VocabTerm>[],
    );

    return SizedBox(
      key: const Key("heritage_list.filter_chips"),
      height: 48,
      child: ListView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 12),
        children: <Widget>[
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4),
            child: ChoiceChip(
              key: const Key("heritage_list.chip_all"),
              selected: state.filters.kindSlug == null,
              label: Text(l10n?.heritageFilterAll ?? ""),
              onSelected: (_) => notifier.setKind(null),
            ),
          ),
          for (final VocabTerm term in kinds)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 4),
              child: ChoiceChip(
                key: Key("heritage_list.chip_${term.slug}"),
                selected: state.filters.kindSlug == term.slug,
                label: Text(term.localizedName(locale)),
                onSelected: (bool selected) =>
                    notifier.setKind(selected ? term.slug : null),
              ),
            ),
        ],
      ),
    );
  }
}

class _HeritageListBody extends StatelessWidget {
  const _HeritageListBody({
    required this.state,
    required this.scrollController,
    required this.onRetry,
  });

  final HeritageListState state;
  final ScrollController scrollController;
  final Future<void> Function() onRetry;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    if (state.isLoading && state.items.isEmpty) {
      return const Center(
        key: Key("heritage_list.loading"),
        child: CircularProgressIndicator(),
      );
    }

    if (state.failure != null && state.items.isEmpty) {
      return _ErrorView(
        message: state.failure!.message,
        onRetry: onRetry,
      );
    }

    if (state.items.isEmpty) {
      return Center(
        key: const Key("heritage_list.empty"),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              const Icon(Icons.travel_explore, size: 80),
              const SizedBox(height: 12),
              Text(
                l10n?.heritageEmpty ?? "",
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyLarge,
              ),
            ],
          ),
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: onRetry,
      child: ListView.builder(
        key: const Key("heritage_list.list_view"),
        controller: scrollController,
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(12, 8, 12, 16),
        itemCount: state.items.length + (state.isLoadingMore ? 1 : 0),
        itemBuilder: (BuildContext context, int index) {
          if (index >= state.items.length) {
            return const Padding(
              padding: EdgeInsets.symmetric(vertical: 16),
              child: Center(child: CircularProgressIndicator()),
            );
          }
          final heritage = state.items[index];
          return Padding(
            padding: const EdgeInsets.symmetric(vertical: 6),
            child: HeritageCard(
              heritage: heritage,
              onTap: () => context.go(
                AppRoutes.heritageDetail(heritage.pubId),
              ),
            ),
          );
        },
      ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  const _ErrorView({required this.message, required this.onRetry});

  final String message;
  final Future<void> Function() onRetry;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Center(
      key: const Key("heritage_list.error"),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            const Icon(Icons.error_outline, size: 64),
            const SizedBox(height: 12),
            Text(message, textAlign: TextAlign.center),
            const SizedBox(height: 12),
            FilledButton.tonal(
              key: const Key("heritage_list.retry"),
              onPressed: onRetry,
              child: Text(l10n?.commonRetry ?? "Retry"),
            ),
          ],
        ),
      ),
    );
  }
}
