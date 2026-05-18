// XP / level / progress card. Drop-in widget for profile header.

import "package:flutter/material.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/l10n/app_localizations.dart";
import "package:silklens/presentation/providers/gamification_provider.dart";

class XpCard extends ConsumerWidget {
  const XpCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final asyncSummary = ref.watch(xpSummaryProvider);
    final theme = Theme.of(context);

    return Card(
      key: const Key("gamification.xp_card"),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: asyncSummary.when(
          loading: () => const SizedBox(
            height: 80,
            child: Center(child: CircularProgressIndicator()),
          ),
          error: (Object e, _) => Text(e.toString()),
          data: (summary) {
            if (summary == null) {
              return Text(l10n?.gamificationNoData ?? "No data");
            }
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                Row(
                  children: <Widget>[
                    Expanded(
                      child: Text(
                        "${l10n?.gamificationLevel ?? "Level"} ${summary.level}",
                        style: theme.textTheme.titleMedium,
                      ),
                    ),
                    Text(
                      "${summary.totalXp} XP",
                      style: theme.textTheme.titleMedium?.copyWith(
                        color: theme.colorScheme.primary,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                ClipRRect(
                  borderRadius: BorderRadius.circular(6),
                  child: LinearProgressIndicator(
                    value: summary.levelProgress,
                    minHeight: 10,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  "${summary.xpIntoCurrentLevel} / ${summary.xpForNextLevel} XP",
                  style: theme.textTheme.bodySmall,
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}
