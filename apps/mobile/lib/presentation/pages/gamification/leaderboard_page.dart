// Leaderboard with four tabs: Weekly / Monthly / All-time / Friends.

import "package:flutter/material.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/domain/gamification/entities/leaderboard_entry.dart";
import "package:silklens/l10n/app_localizations.dart";
import "package:silklens/presentation/providers/gamification_provider.dart";

class LeaderboardPage extends ConsumerStatefulWidget {
  const LeaderboardPage({super.key});

  @override
  ConsumerState<LeaderboardPage> createState() => _LeaderboardPageState();
}

class _LeaderboardPageState extends ConsumerState<LeaderboardPage>
    with SingleTickerProviderStateMixin {
  static const _scopes = <LeaderboardScope>[
    LeaderboardScope.weekly,
    LeaderboardScope.monthly,
    LeaderboardScope.allTime,
    LeaderboardScope.friends,
  ];

  late final TabController _tabs = TabController(length: _scopes.length, vsync: this);

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(leaderboardControllerProvider.notifier).setScope(_scopes.first);
    });
    _tabs.addListener(() {
      if (_tabs.indexIsChanging) return;
      ref
          .read(leaderboardControllerProvider.notifier)
          .setScope(_scopes[_tabs.index]);
    });
  }

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  String _scopeLabel(LeaderboardScope s) {
    final l10n = AppLocalizations.of(context);
    return switch (s) {
      LeaderboardScope.weekly => l10n?.leaderboardWeekly ?? "Weekly",
      LeaderboardScope.monthly => l10n?.leaderboardMonthly ?? "Monthly",
      LeaderboardScope.allTime => l10n?.leaderboardAllTime ?? "All-time",
      LeaderboardScope.friends => l10n?.leaderboardFriends ?? "Friends",
    };
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(leaderboardControllerProvider);
    return Scaffold(
      appBar: AppBar(
        title: Text(AppLocalizations.of(context)?.leaderboardTitle ?? "Leaderboard"),
        bottom: TabBar(
          controller: _tabs,
          tabs: _scopes
              .map((LeaderboardScope s) => Tab(text: _scopeLabel(s)))
              .toList(growable: false),
        ),
      ),
      body: RefreshIndicator(
        onRefresh: () =>
            ref.read(leaderboardControllerProvider.notifier).refresh(),
        child: state.isLoading && state.entries.isEmpty
            ? const Center(child: CircularProgressIndicator())
            : ListView.separated(
                key: const Key("leaderboard.list"),
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.symmetric(vertical: 8),
                itemCount: state.entries.length,
                separatorBuilder: (_, __) => const Divider(height: 1),
                itemBuilder: (BuildContext ctx, int i) {
                  final e = state.entries[i];
                  return ListTile(
                    leading: CircleAvatar(child: Text("${e.rank}")),
                    title: Text(e.displayName),
                    subtitle: e.country != null ? Text(e.country!) : null,
                    trailing: Text(
                      "${e.score} XP",
                      style: Theme.of(ctx).textTheme.bodyLarge?.copyWith(
                            fontWeight: e.isMe ? FontWeight.bold : null,
                          ),
                    ),
                    tileColor: e.isMe
                        ? Theme.of(ctx).colorScheme.primaryContainer
                        : null,
                  );
                },
              ),
      ),
    );
  }
}
