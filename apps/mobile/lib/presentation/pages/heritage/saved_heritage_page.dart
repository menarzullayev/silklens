// "Saved" bottom-nav tab — backed by the local Isar saved set.
// No network calls; everything streams from [savedHeritageStreamProvider].

import "package:flutter/material.dart";
import "package:go_router/go_router.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/domain/heritage/entities/heritage.dart";
import "package:silklens/l10n/app_localizations.dart";
import "package:silklens/presentation/providers/heritage_detail_provider.dart";
import "package:silklens/presentation/router/app_router.dart";
import "package:silklens/presentation/widgets/heritage_card.dart";

class SavedHeritagePage extends ConsumerWidget {
  const SavedHeritagePage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final asyncList = ref.watch(savedHeritageStreamProvider);

    return Scaffold(
      appBar: AppBar(title: Text(l10n?.heritageSavedTitle ?? "")),
      body: asyncList.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (Object e, StackTrace _) => Center(child: Text(e.toString())),
        data: (List<Heritage> items) {
          if (items.isEmpty) {
            return Center(
              key: const Key("saved.empty"),
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    const Icon(Icons.bookmark_outline, size: 80),
                    const SizedBox(height: 12),
                    Text(
                      l10n?.heritageSavedEmpty ?? "",
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              ),
            );
          }
          return ListView.builder(
            key: const Key("saved.list_view"),
            padding: const EdgeInsets.fromLTRB(12, 8, 12, 16),
            itemCount: items.length,
            itemBuilder: (BuildContext context, int index) => Padding(
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: HeritageCard(
                heritage: items[index],
                onTap: () => context.go(
                  AppRoutes.heritageDetail(items[index].pubId),
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}
