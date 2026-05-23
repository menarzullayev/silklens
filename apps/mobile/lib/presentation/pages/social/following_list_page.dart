import 'package:flutter/material.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/core/l10n/locale_service.dart';
import 'package:silklens/data/repositories/social_repository_impl.dart';
import 'package:silklens/presentation/providers/auth_provider.dart';
import 'package:silklens/presentation/providers/social_provider.dart';

class FollowingListPage extends ConsumerStatefulWidget {
  const FollowingListPage({super.key});

  @override
  ConsumerState<FollowingListPage> createState() => _FollowingListPageState();
}

class _FollowingListPageState extends ConsumerState<FollowingListPage> {
  static const _gold = Color(0xFFB78628);
  static const _bg = Color(0xFF0D2337);

  int _activeFilter = 0;
  final _searchController = TextEditingController();

  String _s(String key) => AppStrings.get(LocaleService.instance.locale, key);

  List<String> get _filters => [
        _s('following_filter_all'),
        _s('following_filter_followers'),
        _s('following_filter_following'),
      ];

  String get _userPubId => ref.read(currentUserProvider)?.pubId ?? '';

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  List<UserRef> _applySearch(List<UserRef> users) {
    final q = _searchController.text.trim().toLowerCase();
    if (q.isEmpty) return users;
    return users.where((u) {
      final name = (u.displayName ?? '').toLowerCase();
      final handle = (u.username ?? '').toLowerCase();
      return name.contains(q) || handle.contains(q);
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    final pubId = _userPubId;
    final s = ref.watch(followingListProvider(pubId));
    final notifier = ref.read(followingListProvider(pubId).notifier);

    // Merge following + followers for "All" tab, deduped by pub_id
    final allMap = <String, UserRef>{};
    for (final u in [...s.following, ...s.followers]) {
      if (u.pubId.isNotEmpty) allMap[u.pubId] = u;
    }

    final rawList = switch (_activeFilter) {
      1 => s.followers,
      2 => s.following,
      _ => allMap.values.toList(),
    };

    final displayed = _applySearch(
      rawList.where((u) => u.pubId.isNotEmpty).toList(),
    );

    return Scaffold(
      backgroundColor: _bg,
      appBar: AppBar(
        backgroundColor: _bg,
        leading: GestureDetector(
          onTap: () => Navigator.pop(context),
          child: const Icon(
            Icons.arrow_back_ios_new,
            color: Colors.white,
            size: 20,
          ),
        ),
        title: Text(
          _s('following_title'),
          style: const TextStyle(
            color: Colors.white,
            fontSize: 20,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
      body: Column(
        children: [
          // Search bar
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Container(
              height: 44,
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.07),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(
                  color: Colors.white.withValues(alpha: 0.12),
                ),
              ),
              child: TextField(
                controller: _searchController,
                style: const TextStyle(color: Colors.white, fontSize: 14),
                decoration: InputDecoration(
                  hintText: _s('following_search_hint'),
                  hintStyle: TextStyle(
                    color: Colors.white.withValues(alpha: 0.4),
                    fontSize: 14,
                  ),
                  prefixIcon: Icon(
                    Icons.search_rounded,
                    color: Colors.white.withValues(alpha: 0.4),
                    size: 20,
                  ),
                  border: InputBorder.none,
                  contentPadding: const EdgeInsets.symmetric(vertical: 12),
                ),
                onChanged: (_) => setState(() {}),
              ),
            ),
          ),
          const SizedBox(height: 12),
          // Filter chips
          SizedBox(
            height: 36,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16),
              itemCount: _filters.length,
              separatorBuilder: (_, __) => const SizedBox(width: 8),
              itemBuilder: (_, i) => GestureDetector(
                onTap: () => setState(() => _activeFilter = i),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 8,
                  ),
                  decoration: BoxDecoration(
                    color: _activeFilter == i
                        ? _gold
                        : Colors.white.withValues(alpha: 0.07),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(
                      color: _activeFilter == i
                          ? _gold
                          : Colors.white.withValues(alpha: 0.15),
                    ),
                  ),
                  child: Text(
                    _filters[i],
                    style: TextStyle(
                      color: _activeFilter == i
                          ? const Color(0xFF1A1200)
                          : Colors.white,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: 8),
          // User list / loading / error / empty
          Expanded(
            child: s.isLoading
                ? const Center(
                    child: CircularProgressIndicator(
                      color: _gold,
                      strokeWidth: 2,
                    ),
                  )
                : s.error != null
                    ? _ErrorRetry(
                        message: _s('following_error'),
                        onRetry: () => notifier.reload(pubId),
                      )
                    : displayed.isEmpty
                        ? Center(
                            child: Text(
                              _s('following_empty'),
                              style: TextStyle(
                                color: Colors.white.withValues(alpha: 0.4),
                                fontSize: 15,
                              ),
                            ),
                          )
                        : ListView.separated(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 16,
                              vertical: 8,
                            ),
                            itemCount: displayed.length,
                            separatorBuilder: (_, __) =>
                                const SizedBox(height: 8),
                            itemBuilder: (_, i) {
                              final user = displayed[i];
                              final levelNum = user.levelNumber ?? 1;
                              final levelLabel =
                                  user.levelName ?? 'Level $levelNum';
                              final handle = user.username ?? user.pubId;
                              final name =
                                  user.displayName ?? user.username ?? '?';
                              return _UserRow(
                                pubId: user.pubId,
                                name: name,
                                handle: '@$handle',
                                levelLabel: levelLabel,
                                isFollowing: user.isFollowing,
                                onFollow: () => notifier.follow(user.pubId),
                                onUnfollow: () => notifier.unfollow(user.pubId),
                              );
                            },
                          ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Error retry
// ---------------------------------------------------------------------------

class _ErrorRetry extends StatelessWidget {
  const _ErrorRetry({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.cloud_off_rounded,
              color: Colors.white.withValues(alpha: 0.35),
              size: 48,
            ),
            const SizedBox(height: 12),
            Text(
              message,
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.55),
                fontSize: 14,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            GestureDetector(
              onTap: onRetry,
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 24,
                  vertical: 10,
                ),
                decoration: BoxDecoration(
                  color: const Color(0xFFB78628).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: const Color(0xFFB78628).withValues(alpha: 0.4),
                  ),
                ),
                child: Text(
                  AppStrings.get(
                    LocaleService.instance.locale,
                    'social_feed_retry',
                  ),
                  style: const TextStyle(
                    color: Color(0xFFB78628),
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// User row — local optimistic toggle, syncs from provider via didUpdateWidget
// ---------------------------------------------------------------------------

class _UserRow extends StatefulWidget {
  const _UserRow({
    required this.pubId,
    required this.name,
    required this.handle,
    required this.levelLabel,
    required this.isFollowing,
    required this.onFollow,
    required this.onUnfollow,
  });

  final String pubId;
  final String name;
  final String handle;
  final String levelLabel;
  final bool isFollowing;
  final VoidCallback onFollow;
  final VoidCallback onUnfollow;

  @override
  State<_UserRow> createState() => _UserRowState();
}

class _UserRowState extends State<_UserRow> {
  static const _gold = Color(0xFFB78628);

  late bool _following;

  @override
  void initState() {
    super.initState();
    _following = widget.isFollowing;
  }

  @override
  void didUpdateWidget(_UserRow oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.isFollowing != widget.isFollowing) {
      _following = widget.isFollowing;
    }
  }

  void _toggle() {
    final willFollow = !_following;
    setState(() => _following = willFollow);
    if (willFollow) {
      widget.onFollow();
    } else {
      widget.onUnfollow();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: Colors.white.withValues(alpha: 0.10),
        ),
      ),
      child: Row(
        children: [
          // Avatar
          Container(
            width: 44,
            height: 44,
            decoration: const BoxDecoration(
              shape: BoxShape.circle,
              gradient: LinearGradient(
                colors: [Color(0xFF1F3A93), Color(0xFFB78628)],
              ),
            ),
            child: Center(
              child: Text(
                widget.name.isNotEmpty ? widget.name[0].toUpperCase() : '?',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ),
          const SizedBox(width: 12),
          // Name + handle
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  widget.name,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  widget.handle,
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.45),
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
          // Level badge
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: 8,
              vertical: 3,
            ),
            margin: const EdgeInsets.only(right: 10),
            decoration: BoxDecoration(
              color: _gold.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              widget.levelLabel,
              style: const TextStyle(
                color: _gold,
                fontSize: 10,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          // Follow / Unfollow button
          GestureDetector(
            onTap: _toggle,
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              padding: const EdgeInsets.symmetric(
                horizontal: 14,
                vertical: 7,
              ),
              decoration: BoxDecoration(
                color:
                    _following ? Colors.white.withValues(alpha: 0.08) : _gold,
                borderRadius: BorderRadius.circular(10),
                border: _following
                    ? Border.all(
                        color: Colors.white.withValues(alpha: 0.2),
                      )
                    : null,
              ),
              child: Text(
                _following
                    ? AppStrings.get(
                        LocaleService.instance.locale,
                        'following_action_following',
                      )
                    : AppStrings.get(
                        LocaleService.instance.locale,
                        'following_action_follow',
                      ),
                style: TextStyle(
                  color: _following ? Colors.white : const Color(0xFF1A1200),
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
