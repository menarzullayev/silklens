// Fire icon + day count. Sits next to the avatar in the home shell or
// embeds inside the profile header.

import "package:flutter/material.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/l10n/app_localizations.dart";
import "package:silklens/presentation/providers/gamification_provider.dart";

class StreakWidget extends ConsumerWidget {
  const StreakWidget({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final summary = ref.watch(xpSummaryProvider).valueOrNull;
    final days = summary?.streakDays ?? 0;
    return Container(
      key: const Key("gamification.streak"),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.orange.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          const Icon(Icons.local_fire_department, color: Colors.deepOrange),
          const SizedBox(width: 4),
          Text(
            "$days ${l10n?.gamificationStreakDays ?? "day streak"}",
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
        ],
      ),
    );
  }
}
