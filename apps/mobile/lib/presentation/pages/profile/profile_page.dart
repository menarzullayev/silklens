// User profile screen — five tabs: Activity / Saved / Reviews / Friends /
// Settings.
//
// Settings hosts language picker, theme picker, notification preferences
// (calls /v1/notifications/preferences) and logout.

import "package:flutter/material.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/data/repositories/identity_repository_impl.dart";
import "package:silklens/domain/social/entities/feed_item.dart";
import "package:silklens/l10n/app_localizations.dart";
import "package:silklens/presentation/pages/profile/review_composer_sheet.dart";
import "package:silklens/presentation/providers/locale_provider.dart";
import "package:silklens/presentation/providers/social_provider.dart";
import "package:silklens/presentation/theme/theme_provider.dart";

class ProfilePage extends ConsumerStatefulWidget {
  const ProfilePage({super.key});

  @override
  ConsumerState<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends ConsumerState<ProfilePage>
    with SingleTickerProviderStateMixin {
  late final TabController _tabs = TabController(length: 5, vsync: this);

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n?.profileTitle ?? "Profile"),
        bottom: TabBar(
          controller: _tabs,
          isScrollable: true,
          tabs: <Widget>[
            Tab(text: l10n?.profileTabActivity ?? "Activity"),
            Tab(text: l10n?.profileTabSaved ?? "Saved"),
            Tab(text: l10n?.profileTabReviews ?? "Reviews"),
            Tab(text: l10n?.profileTabFriends ?? "Friends"),
            Tab(text: l10n?.profileTabSettings ?? "Settings"),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabs,
        children: const <Widget>[
          _ActivityTab(),
          _SavedTab(),
          _ReviewsTab(),
          _FriendsTab(),
          _SettingsTab(),
        ],
      ),
    );
  }
}

class _ActivityTab extends ConsumerStatefulWidget {
  const _ActivityTab();

  @override
  ConsumerState<_ActivityTab> createState() => _ActivityTabState();
}

class _ActivityTabState extends ConsumerState<_ActivityTab> {
  final ScrollController _ctrl = ScrollController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(feedControllerProvider.notifier).refresh();
    });
    _ctrl.addListener(() {
      if (_ctrl.position.pixels >= _ctrl.position.maxScrollExtent - 200) {
        ref.read(feedControllerProvider.notifier).loadMore();
      }
    });
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(feedControllerProvider);
    final l10n = AppLocalizations.of(context);
    if (state.items.isEmpty && state.isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (state.items.isEmpty) {
      return Center(
        key: const Key("profile.activity.empty"),
        child: Text(l10n?.profileActivityEmpty ?? "No activity yet"),
      );
    }
    return RefreshIndicator(
      onRefresh: () => ref.read(feedControllerProvider.notifier).refresh(),
      child: ListView.separated(
        key: const Key("profile.activity.list"),
        controller: _ctrl,
        padding: const EdgeInsets.all(12),
        itemCount: state.items.length,
        separatorBuilder: (_, __) => const SizedBox(height: 8),
        itemBuilder: (BuildContext ctx, int i) => _FeedItemCard(item: state.items[i]),
      ),
    );
  }
}

class _FeedItemCard extends StatelessWidget {
  const _FeedItemCard({required this.item});
  final FeedItem item;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final icon = switch (item.kind) {
      FeedItemKind.review => Icons.rate_review_outlined,
      FeedItemKind.checkIn => Icons.location_on_outlined,
      FeedItemKind.badgeUnlock => Icons.emoji_events_outlined,
      FeedItemKind.follow => Icons.person_add_outlined,
      FeedItemKind.comment => Icons.comment_outlined,
    };
    final title = switch (item.kind) {
      FeedItemKind.review =>
        "${item.actor.displayName} reviewed ${item.heritageName ?? "a place"}",
      FeedItemKind.checkIn =>
        "${item.actor.displayName} checked in at ${item.heritageName ?? "a place"}",
      FeedItemKind.badgeUnlock =>
        "${item.actor.displayName} unlocked ${item.badgeName ?? "a badge"}",
      FeedItemKind.follow => "${item.actor.displayName} followed someone",
      FeedItemKind.comment => "${item.actor.displayName} commented",
    };

    return Card(
      child: ListTile(
        leading: CircleAvatar(child: Icon(icon)),
        title: Text(title, style: theme.textTheme.bodyMedium),
        subtitle: item.text != null
            ? Text(item.text!, maxLines: 2, overflow: TextOverflow.ellipsis)
            : null,
      ),
    );
  }
}

class _SavedTab extends StatelessWidget {
  const _SavedTab();
  @override
  Widget build(BuildContext context) => Center(
        key: const Key("profile.saved.placeholder"),
        child: Text(
          AppLocalizations.of(context)?.profileSavedEmpty ??
              "No saved heritage yet",
        ),
      );
}

class _ReviewsTab extends ConsumerWidget {
  const _ReviewsTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      body: Center(
        key: const Key("profile.reviews.placeholder"),
        child: Text(l10n?.profileReviewsEmpty ?? "Your reviews will appear here"),
      ),
      floatingActionButton: FloatingActionButton.extended(
        key: const Key("profile.reviews.new"),
        onPressed: () => showModalBottomSheet<void>(
          context: context,
          isScrollControlled: true,
          builder: (_) => const ReviewComposerSheet(heritagePubId: "demo"),
        ),
        icon: const Icon(Icons.add),
        label: Text(l10n?.profileReviewsNew ?? "New review"),
      ),
    );
  }
}

class _FriendsTab extends StatelessWidget {
  const _FriendsTab();
  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Center(
      key: const Key("profile.friends.placeholder"),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Text(l10n?.profileFriendsEmpty ?? "Invite friends to join SilkLens"),
          const SizedBox(height: 16),
          FilledButton.icon(
            key: const Key("profile.friends.invite"),
            onPressed: () {},
            icon: const Icon(Icons.share),
            label: Text(l10n?.profileFriendsInvite ?? "Invite"),
          ),
        ],
      ),
    );
  }
}

class _SettingsTab extends ConsumerWidget {
  const _SettingsTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final locale = ref.watch(activeLocaleProvider);
    final variant = ref.watch(themeControllerProvider);

    return ListView(
      key: const Key("profile.settings.list"),
      padding: const EdgeInsets.all(8),
      children: <Widget>[
        ListTile(
          leading: const Icon(Icons.language),
          title: Text(l10n?.profileLanguage ?? "Language"),
          subtitle: Text(locale.languageCode.toUpperCase()),
          trailing: PopupMenuButton<String>(
            key: const Key("profile.settings.language"),
            onSelected: (String code) =>
                ref.read(activeLocaleProvider.notifier).setLanguageCode(code),
            itemBuilder: (BuildContext context) => const <PopupMenuEntry<String>>[
              PopupMenuItem<String>(value: "uz", child: Text("O'zbek")),
              PopupMenuItem<String>(value: "en", child: Text("English")),
              PopupMenuItem<String>(value: "ru", child: Text("Русский")),
              PopupMenuItem<String>(value: "zh", child: Text("中文")),
            ],
          ),
        ),
        ListTile(
          leading: const Icon(Icons.palette_outlined),
          title: Text(l10n?.profileTheme ?? "Theme"),
          subtitle: Text(variant.name),
          trailing: PopupMenuButton<ThemeVariant>(
            key: const Key("profile.settings.theme"),
            onSelected: (ThemeVariant v) =>
                ref.read(themeControllerProvider.notifier).setVariant(v),
            itemBuilder: (BuildContext context) => ThemeVariant.values
                .map(
                  (ThemeVariant v) =>
                      PopupMenuItem<ThemeVariant>(value: v, child: Text(v.name)),
                )
                .toList(),
          ),
        ),
        ListTile(
          leading: const Icon(Icons.notifications_outlined),
          title: Text(l10n?.profileNotifications ?? "Notifications"),
          subtitle:
              Text(l10n?.profileNotificationsHint ?? "Configure push & email"),
          onTap: () {},
        ),
        const Divider(),
        ListTile(
          leading: const Icon(Icons.logout),
          title: Text(l10n?.profileLogout ?? "Log out"),
          onTap: () async {
            await ref.read(identityRepositoryProvider).logout();
          },
        ),
      ],
    );
  }
}
