// Reusable Follow / Unfollow button. Optimistic — the underlying controller
// rolls back on failure (see [FollowController.toggle]).

import "package:flutter/material.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/l10n/app_localizations.dart";
import "package:silklens/presentation/providers/social_provider.dart";

class FollowButton extends ConsumerWidget {
  const FollowButton({required this.userPubId, super.key});

  final String userPubId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final asyncUser = ref.watch(followControllerProvider(userPubId));

    return asyncUser.when(
      data: (user) {
        if (user == null) {
          return const SizedBox.shrink();
        }
        return FilledButton.icon(
          key: Key("follow_button.$userPubId"),
          onPressed: () =>
              ref.read(followControllerProvider(userPubId).notifier).toggle(),
          icon: Icon(user.isFollowing ? Icons.check : Icons.person_add_alt_1),
          label: Text(
            user.isFollowing
                ? (l10n?.profileFollowing ?? "Following")
                : (l10n?.profileFollow ?? "Follow"),
          ),
        );
      },
      loading: () => const SizedBox(
        width: 24,
        height: 24,
        child: CircularProgressIndicator(strokeWidth: 2),
      ),
      error: (_, __) => const SizedBox.shrink(),
    );
  }
}
