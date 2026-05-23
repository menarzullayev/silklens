import 'package:flutter/material.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/core/l10n/locale_service.dart';
import 'package:silklens/data/repositories/social_repository_impl.dart';
import 'package:silklens/presentation/providers/social_provider.dart';

class NotificationsPage extends ConsumerStatefulWidget {
  const NotificationsPage({super.key});

  @override
  ConsumerState<NotificationsPage> createState() => _NotificationsPageState();
}

class _NotificationsPageState extends ConsumerState<NotificationsPage> {
  static const _gold = Color(0xFFB78628);
  static const _bg = Color(0xFF0D2337);

  int _activeFilter = 0;

  String _s(String key) => AppStrings.get(LocaleService.instance.locale, key);

  List<String> get _filters => [
        _s('notif_filter_all'),
        _s('notif_filter_unread'),
        _s('notif_filter_social'),
        _s('notif_filter_level'),
      ];

  @override
  void initState() {
    super.initState();
    Future.microtask(
      () => ref.read(notificationsProvider.notifier).refresh(),
    );
  }

  List<SocialNotificationItem> _filtered(
    List<SocialNotificationItem> notifications,
  ) {
    if (_activeFilter == 0) return notifications;
    if (_activeFilter == 1) {
      return notifications.where((n) => !n.isRead).toList();
    }
    const typeMap = {
      2: ['follow', 'like', 'comment'],
      3: ['badge', 'level', 'streak', 'leaderboard', 'mission'],
    };
    final types = typeMap[_activeFilter] ?? [];
    return notifications.where((n) {
      final kind = n.category.toLowerCase();
      return types.any(kind.contains);
    }).toList();
  }

  IconData _iconForKind(String kind) {
    return switch (kind.toLowerCase()) {
      'like' => Icons.favorite_rounded,
      'follow' => Icons.person_add_rounded,
      'badge' || 'badge_unlock' => Icons.workspace_premium_rounded,
      'comment' => Icons.chat_bubble_rounded,
      'streak' => Icons.local_fire_department_rounded,
      'leaderboard' || 'level' || 'level_up' => Icons.trending_up_rounded,
      'mission' => Icons.flag_rounded,
      _ => Icons.notifications_rounded,
    };
  }

  Color _colorForKind(String kind) {
    return switch (kind.toLowerCase()) {
      'like' => Colors.redAccent,
      'follow' => const Color(0xFF1F3A93),
      'badge' || 'badge_unlock' => _gold,
      'comment' => const Color(0xFF7B68EE),
      'streak' => Colors.orange,
      'leaderboard' || 'level' || 'level_up' => Colors.greenAccent,
      'mission' => const Color(0xFF00BCD4),
      _ => Colors.white60,
    };
  }

  String _relativeTime(String isoString) {
    if (isoString.isEmpty) return '';
    try {
      final dt = DateTime.parse(isoString).toLocal();
      final diff = DateTime.now().difference(dt);
      if (diff.inMinutes < 60) return '${diff.inMinutes} min';
      if (diff.inHours < 24) return '${diff.inHours}h';
      if (diff.inDays == 1) return '1d';
      return '${diff.inDays}d';
    } catch (_) {
      return isoString;
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = ref.watch(notificationsProvider);
    final filtered = _filtered(s.items);
    final unreadCount = s.items.where((n) => !n.isRead).length;

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
        title: Row(
          children: [
            Text(
              _s('notif_title'),
              style: const TextStyle(
                color: Colors.white,
                fontSize: 20,
                fontWeight: FontWeight.w700,
              ),
            ),
            if (unreadCount > 0) ...[
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 7,
                  vertical: 2,
                ),
                decoration: BoxDecoration(
                  color: _gold,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  '$unreadCount',
                  style: const TextStyle(
                    color: Color(0xFF1A1200),
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ],
        ),
        actions: [
          if (unreadCount > 0)
            TextButton(
              onPressed: () =>
                  ref.read(notificationsProvider.notifier).markAllRead(),
              child: Text(
                _s('notif_mark_all_read'),
                style: const TextStyle(color: _gold, fontSize: 12),
              ),
            ),
        ],
      ),
      body: Column(
        children: [
          // Filter chips
          SizedBox(
            height: 44,
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
                    vertical: 10,
                  ),
                  decoration: BoxDecoration(
                    color: _activeFilter == i
                        ? _gold
                        : Colors.white.withValues(alpha: 0.07),
                    borderRadius: BorderRadius.circular(22),
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
          // Body
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
                        message: s.error!,
                        onRetry: () =>
                            ref.read(notificationsProvider.notifier).refresh(),
                      )
                    : filtered.isEmpty
                        ? Center(
                            child: Text(
                              _s('notif_empty'),
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
                            itemCount: filtered.length,
                            separatorBuilder: (_, __) =>
                                const SizedBox(height: 8),
                            itemBuilder: (_, i) {
                              final n = filtered[i];
                              return _NotifCard(
                                icon: _iconForKind(n.category),
                                iconColor: _colorForKind(n.category),
                                title: n.title.isNotEmpty ? n.title : n.body,
                                time: _relativeTime(n.createdAt),
                                isRead: n.isRead,
                                onTap: n.isRead
                                    ? null
                                    : () => ref
                                        .read(notificationsProvider.notifier)
                                        .markRead(n.id),
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
// Error retry widget
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
                fontSize: 13,
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
// Notification card
// ---------------------------------------------------------------------------

class _NotifCard extends StatelessWidget {
  const _NotifCard({
    required this.icon,
    required this.iconColor,
    required this.title,
    required this.time,
    required this.isRead,
    this.onTap,
  });

  final IconData icon;
  final Color iconColor;
  final String title;
  final String time;
  final bool isRead;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: isRead ? 0.04 : 0.08),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: Colors.white.withValues(alpha: isRead ? 0.08 : 0.14),
          ),
        ),
        child: Row(
          children: [
            // Left gold bar for unread
            AnimatedContainer(
              duration: const Duration(milliseconds: 300),
              width: 4,
              height: 64,
              decoration: BoxDecoration(
                color: isRead ? Colors.transparent : const Color(0xFFB78628),
                borderRadius: const BorderRadius.horizontal(
                  left: Radius.circular(16),
                ),
              ),
            ),
            const SizedBox(width: 12),
            // Icon circle
            Container(
              width: 42,
              height: 42,
              decoration: BoxDecoration(
                color: iconColor.withValues(alpha: 0.15),
                shape: BoxShape.circle,
              ),
              child: Icon(icon, color: iconColor, size: 20),
            ),
            const SizedBox(width: 12),
            // Text
            Expanded(
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: TextStyle(
                        color:
                            Colors.white.withValues(alpha: isRead ? 0.65 : 1.0),
                        fontSize: 13,
                        fontWeight: isRead ? FontWeight.w400 : FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      time,
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.4),
                        fontSize: 11,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(width: 12),
          ],
        ),
      ),
    );
  }
}
