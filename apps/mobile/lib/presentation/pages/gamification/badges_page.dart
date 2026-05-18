// Grid of badges. Unlocked badges full-colour; locked badges silhouetted
// with the criterion hint as the tooltip + a one-line subtitle.
//
// When a new badge unlocks the [newlyUnlockedBadgeProvider] listener fires
// and we play a brief scale-in highlight via the AnimatedSwitcher.

import "package:flutter/material.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/domain/gamification/entities/badge.dart" as gam;
import "package:silklens/l10n/app_localizations.dart";
import "package:silklens/presentation/providers/gamification_provider.dart";

class BadgesPage extends ConsumerWidget {
  const BadgesPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final asyncBadges = ref.watch(badgesProvider);
    final newlyUnlocked = ref.watch(newlyUnlockedBadgeProvider);

    return Scaffold(
      appBar: AppBar(title: Text(l10n?.gamificationBadgesTitle ?? "Badges")),
      body: asyncBadges.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (Object e, _) => Center(child: Text(e.toString())),
        data: (badges) {
          if (badges.isEmpty) {
            return Center(
              key: const Key("gamification.badges.empty"),
              child: Text(l10n?.gamificationBadgesEmpty ?? "No badges yet"),
            );
          }
          return GridView.builder(
            key: const Key("gamification.badges.grid"),
            padding: const EdgeInsets.all(12),
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 3,
              childAspectRatio: 0.85,
              crossAxisSpacing: 12,
              mainAxisSpacing: 12,
            ),
            itemCount: badges.length,
            itemBuilder: (BuildContext ctx, int i) {
              final b = badges[i];
              return _BadgeTile(badge: b, isNewlyUnlocked: b.slug == newlyUnlocked);
            },
          );
        },
      ),
    );
  }
}

class _BadgeTile extends StatelessWidget {
  const _BadgeTile({required this.badge, required this.isNewlyUnlocked});

  final gam.Badge badge;
  final bool isNewlyUnlocked;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isLocked = !badge.isUnlocked;
    final body = Card(
      child: Padding(
        padding: const EdgeInsets.all(8),
        child: Column(
          children: <Widget>[
            Expanded(
              child: Center(
                child: Icon(
                  Icons.emoji_events,
                  size: 48,
                  color: isLocked
                      ? theme.colorScheme.outline
                      : Colors.amber,
                ),
              ),
            ),
            const SizedBox(height: 4),
            Text(
              badge.name,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: theme.textTheme.bodySmall,
            ),
            if (isLocked && badge.criterionHint != null)
              Text(
                badge.criterionHint!,
                maxLines: 2,
                textAlign: TextAlign.center,
                overflow: TextOverflow.ellipsis,
                style: theme.textTheme.labelSmall?.copyWith(
                  color: theme.colorScheme.outline,
                ),
              ),
          ],
        ),
      ),
    );
    // Lightweight unlock animation — wraps in TweenAnimationBuilder rather
    // than pulling in Lottie / Rive for the FAZA 1 deliverable.
    if (!isNewlyUnlocked) return body;
    return TweenAnimationBuilder<double>(
      key: ValueKey<String>("anim.${badge.slug}"),
      tween: Tween<double>(begin: 0.7, end: 1),
      duration: const Duration(milliseconds: 700),
      curve: Curves.elasticOut,
      builder: (BuildContext _, double scale, Widget? child) =>
          Transform.scale(scale: scale, child: child),
      child: body,
    );
  }
}
