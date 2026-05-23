import 'package:flutter/material.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/core/l10n/locale_service.dart';
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

  String _s(String key) =>
      AppStrings.get(LocaleService.instance.locale, key);

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

  List<Map<String, dynamic>> _applySearch(
    List<Map<String, dynamic>> users,
  ) {
    final q = _searchController.text.trim().toLowerCase();
    if (q.isEmpty) return users;
    return users.where((u) {
      final name =
          (u['display_name'] as String? ?? '').toLowerCase();
      final handle =
          (u['username'] as String? ?? '').toLowerCase();
      return name.contains(q) || handle.contains(q);
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    final pubId = _userPubId;
    final state = ref.watch(followingListProvider(pubId));
    final notifier =
        ref.read(followingListProvider(pubId).notifier);

    // Merge following + followers for "All" tab, deduped by pub_id
    final allUsers = <String, Map<String, dynamic>>{};
    for (final u in [...state.following, ...state.followers]) {
      final id = u['pub_id'] as String? ?? '';
      if (id.isNotEmpty) allUsers[id] = u;
    }

    final rawList = switch (_activeFilter) {
      1 => state.followers,
      2 => state.following,
      _ => allUsers.values.toList(),
    };

    final displayed =
        _applySearch(rawList.where((u) => u.isNotEmpty).toList());

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
                style:
                    const TextStyle(color: Colors.white, fontSize: 14),
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
                  contentPadding:
                      const EdgeInsets.symmetric(vertical: 12),
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
          // User list / loading / empty
          Expanded(
            child: state.isLoading
                ? const Center(
                    child: CircularProgressIndicator(
                      color: _gold,
                      strokeWidth: 2,
                    ),
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
                          final id =
                              user['pub_id'] as String? ?? '';
                          final name =
                              user['display_name'] as String? ??
                                  user['username'] as String? ??
                                  '?';
                          final handle =
                              user['username'] as String? ?? id;
                          final levelNum =
                              (user['level_number'] as num?)
                                  ?.toInt() ??
                                  1;
                          final levelLabel =
                              user['level_name'] as String? ??
                                  'Level $levelNum';
                          final isFollowing =
                              user['is_following'] as bool? ?? false;

                          return _UserRow(
                            pubId: id,
                            name: name,
                            handle: '@$handle',
                            levelLabel: levelLabel,
                            isFollowing: isFollowing,
                            onFollow: () => notifier.follow(id),
                            onUnfollow: () => notifier.unfollow(id),
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
      padding:
          const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
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
                widget.name.isNotEmpty
                    ? widget.name[0].toUpperCase()
                    : '?',
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
                color: _following
                    ? Colors.white.withValues(alpha: 0.08)
                    : _gold,
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
                  color: _following
                      ? Colors.white
                      : const Color(0xFF1A1200),
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
