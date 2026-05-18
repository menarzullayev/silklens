// Another user's public profile.
//
// Shows the follow button + bio + a public activity teaser. The full
// public-activity feed endpoint is on the FAZA 3 backend roadmap; until then
// we render the same shared feed filtered client-side.

import "package:flutter/material.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/l10n/app_localizations.dart";
import "package:silklens/presentation/pages/profile/follow_button.dart";
import "package:silklens/presentation/providers/social_provider.dart";

class UserProfilePage extends ConsumerWidget {
  const UserProfilePage({required this.pubId, super.key});

  final String pubId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final asyncUser = ref.watch(followControllerProvider(pubId));

    return Scaffold(
      appBar: AppBar(title: Text(l10n?.profileTitle ?? "Profile")),
      body: asyncUser.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (Object e, _) => Center(child: Text(e.toString())),
        data: (user) {
          if (user == null) {
            return Center(
              key: const Key("user_profile.not_found"),
              child: Text(l10n?.profileUserNotFound ?? "User not found"),
            );
          }
          return ListView(
            key: const Key("user_profile.body"),
            padding: const EdgeInsets.all(20),
            children: <Widget>[
              Center(
                child: CircleAvatar(
                  radius: 56,
                  backgroundImage: user.avatarUrl != null
                      ? NetworkImage(user.avatarUrl!)
                      : null,
                  child: user.avatarUrl == null
                      ? Text(user.displayName.isNotEmpty
                          ? user.displayName.characters.first
                          : "?")
                      : null,
                ),
              ),
              const SizedBox(height: 12),
              Center(
                child: Text(
                  user.displayName,
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
              ),
              if (user.handle != null)
                Center(
                  child: Text(
                    "@${user.handle}",
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: Theme.of(context).colorScheme.outline,
                        ),
                  ),
                ),
              const SizedBox(height: 16),
              if (user.bio != null) Text(user.bio!),
              const SizedBox(height: 16),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: <Widget>[
                  _StatColumn(
                    label: l10n?.profileFollowers ?? "Followers",
                    value: user.followersCount,
                  ),
                  _StatColumn(
                    label: l10n?.profileFollowing ?? "Following",
                    value: user.followingCount,
                  ),
                ],
              ),
              const SizedBox(height: 16),
              Center(child: FollowButton(userPubId: pubId)),
            ],
          );
        },
      ),
    );
  }
}

class _StatColumn extends StatelessWidget {
  const _StatColumn({required this.label, required this.value});
  final String label;
  final int value;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        Text("$value", style: Theme.of(context).textTheme.titleLarge),
        Text(label, style: Theme.of(context).textTheme.bodySmall),
      ],
    );
  }
}
