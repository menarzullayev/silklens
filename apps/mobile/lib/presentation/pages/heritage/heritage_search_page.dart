// Dedicated search page — autofocus search box, recent-searches list,
// zero-results suggestion.
//
// Mounts a sibling [HeritageListNotifier] state for one-shot queries; we
// reuse the same provider so the discover page sees the same filters when
// the user navigates back.

import "dart:async";

import "package:flutter/material.dart";
import "package:flutter_hooks/flutter_hooks.dart";
import "package:go_router/go_router.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/l10n/app_localizations.dart";
import "package:silklens/presentation/providers/heritage_list_provider.dart";
import "package:silklens/presentation/providers/recent_searches_provider.dart";
import "package:silklens/presentation/router/app_router.dart";
import "package:silklens/presentation/widgets/heritage_card.dart";

class HeritageSearchPage extends HookConsumerWidget {
  const HeritageSearchPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final controller = useTextEditingController();
    final debounce = useRef<Timer?>(null);
    final state = ref.watch(heritageListProvider);
    final notifier = ref.read(heritageListProvider.notifier);
    final recent = ref.watch(recentSearchesProvider);

    useEffect(
      () => () => debounce.value?.cancel(),
      const <Object?>[],
    );

    void runSearch(String value) {
      final q = value.trim();
      notifier.setSearch(q.isEmpty ? null : q);
      if (q.isNotEmpty) {
        ref.read(recentSearchesProvider.notifier).add(q);
      }
    }

    return Scaffold(
      appBar: AppBar(
        leading: BackButton(
          key: const Key("heritage_search.back"),
          onPressed: () => context.pop(),
        ),
        title: TextField(
          key: const Key("heritage_search.field"),
          controller: controller,
          autofocus: true,
          decoration: InputDecoration(
            hintText: l10n?.heritageSearchHint ?? "",
            border: InputBorder.none,
          ),
          onChanged: (String value) {
            debounce.value?.cancel();
            debounce.value = Timer(
              const Duration(milliseconds: 300),
              () => runSearch(value),
            );
          },
          onSubmitted: runSearch,
        ),
        actions: <Widget>[
          if (controller.text.isNotEmpty)
            IconButton(
              icon: const Icon(Icons.clear),
              onPressed: () {
                controller.clear();
                notifier.setSearch(null);
              },
            ),
        ],
      ),
      body: SafeArea(
        child: _SearchBody(
          query: state.filters.search,
          state: state,
          recent: recent,
          onRecentTapped: (String q) {
            controller.text = q;
            runSearch(q);
          },
        ),
      ),
    );
  }
}

class _SearchBody extends StatelessWidget {
  const _SearchBody({
    required this.query,
    required this.state,
    required this.recent,
    required this.onRecentTapped,
  });

  final String? query;
  final HeritageListState state;
  final AsyncValue<List<String>> recent;
  final void Function(String) onRecentTapped;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    if (query == null || query!.isEmpty) {
      return _RecentList(
        recent: recent,
        onTap: onRecentTapped,
      );
    }
    if (state.isLoading && state.items.isEmpty) {
      return const Center(
        key: Key("heritage_search.loading"),
        child: CircularProgressIndicator(),
      );
    }
    if (state.items.isEmpty) {
      return Center(
        key: const Key("heritage_search.empty"),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              const Icon(Icons.search_off, size: 80),
              const SizedBox(height: 12),
              Text(
                l10n?.heritageSearchEmptyTitle ?? "",
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 6),
              Text(
                l10n?.heritageSearchEmptyBody ?? "",
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ],
          ),
        ),
      );
    }
    return ListView.builder(
      key: const Key("heritage_search.results"),
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 16),
      itemCount: state.items.length,
      itemBuilder: (BuildContext context, int index) {
        final h = state.items[index];
        return Padding(
          padding: const EdgeInsets.symmetric(vertical: 6),
          child: HeritageCard(
            heritage: h,
            onTap: () => context.go(AppRoutes.heritageDetail(h.pubId)),
          ),
        );
      },
    );
  }
}

class _RecentList extends StatelessWidget {
  const _RecentList({required this.recent, required this.onTap});

  final AsyncValue<List<String>> recent;
  final void Function(String) onTap;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    return recent.maybeWhen(
      data: (List<String> items) {
        if (items.isEmpty) {
          return Center(
            key: const Key("heritage_search.recent_empty"),
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Text(
                l10n?.heritageSearchEmptyTitle ?? "",
                style: theme.textTheme.titleMedium,
              ),
            ),
          );
        }
        return ListView(
          key: const Key("heritage_search.recent_list"),
          padding: const EdgeInsets.symmetric(vertical: 8),
          children: <Widget>[
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
              child: Text(
                l10n?.heritageRecentSearches ?? "",
                style: theme.textTheme.labelMedium?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
            ),
            for (final String q in items)
              ListTile(
                key: Key("heritage_search.recent_$q"),
                leading: const Icon(Icons.history),
                title: Text(q),
                onTap: () => onTap(q),
              ),
          ],
        );
      },
      orElse: () => const SizedBox.shrink(),
    );
  }
}
