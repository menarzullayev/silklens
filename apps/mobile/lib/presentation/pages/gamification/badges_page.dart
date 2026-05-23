// Hide Flutter's Badge widget to avoid name clash with domain Badge entity.
import 'package:flutter/material.dart' hide Badge;
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/core/l10n/locale_service.dart';
import 'package:silklens/domain/gamification/entities/badge.dart';
import 'package:silklens/presentation/providers/gamification_provider.dart';

class BadgesPage extends ConsumerStatefulWidget {
  const BadgesPage({super.key});

  @override
  ConsumerState<BadgesPage> createState() => _BadgesPageState();
}

class _BadgesPageState extends ConsumerState<BadgesPage> {
  int _activeFilter = 0;
  static const _gold = Color(0xFFB78628);

  String _s(String key) => AppStrings.get(LocaleService.instance.locale, key);

  List<String> get _filters => [
        _s('badge_filter_all'),
        _s('badge_filter_heritage'),
        _s('badge_filter_ai'),
        _s('badge_filter_social'),
        _s('badge_filter_explorer'),
      ];

  /// Category slug → filter index mapping.
  static const _categoryToIndex = <String, int>{
    'heritage': 1,
    'ai': 2,
    'social': 3,
    'explorer': 4,
  };

  List<Badge> _applyFilter(List<Badge> badges) {
    if (_activeFilter == 0) return badges;
    final targetCategory = _categoryToIndex.entries
        .firstWhere(
          (e) => e.value == _activeFilter,
          orElse: () => const MapEntry('', -1),
        )
        .key;
    if (targetCategory.isEmpty) return badges;
    return badges.where((b) => b.category.toLowerCase() == targetCategory).toList();
  }

  @override
  Widget build(BuildContext context) {
    final badgesAsync = ref.watch(badgesProvider);

    return Scaffold(
      backgroundColor: const Color(0xFF0D2337),
      appBar: AppBar(
        backgroundColor: const Color(0xFF0D2337),
        title: Text(
          _s('badge_page_title'),
          style: const TextStyle(color: Colors.white),
        ),
        leading: GestureDetector(
          onTap: () => Navigator.pop(context),
          child: const Icon(
            Icons.arrow_back_ios_new,
            color: Colors.white,
            size: 20,
          ),
        ),
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
                    horizontal: 14,
                    vertical: 10,
                  ),
                  decoration: BoxDecoration(
                    color: _activeFilter == i ? _gold : Colors.white.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(22),
                    border: Border.all(
                      color: _activeFilter == i ? _gold : Colors.white.withValues(alpha: 0.15),
                    ),
                  ),
                  child: Text(
                    _filters[i],
                    style: TextStyle(
                      color: _activeFilter == i ? const Color(0xFF1A1200) : Colors.white,
                      fontSize: 13,
                    ),
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: 8),

          // Content area
          Expanded(
            child: badgesAsync.when(
              loading: () => const Center(
                child: CircularProgressIndicator(color: _gold),
              ),
              error: (e, _) => Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      Icons.wifi_off_rounded,
                      color: Colors.white.withValues(alpha: 0.4),
                      size: 40,
                    ),
                    const SizedBox(height: 12),
                    Text(
                      _s('badge_load_error'),
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.6),
                        fontSize: 13,
                      ),
                    ),
                    const SizedBox(height: 16),
                    GestureDetector(
                      onTap: () => ref.invalidate(badgesProvider),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 20,
                          vertical: 8,
                        ),
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(
                            colors: [_gold, Color(0xFFE5C97A)],
                          ),
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Text(
                          _s('xp_retry'),
                          style: const TextStyle(
                            color: Color(0xFF1A1200),
                            fontWeight: FontWeight.w700,
                            fontSize: 13,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              data: (badges) {
                final filtered = _applyFilter(badges);
                final earned = badges.where((b) => b.isEarned).length;
                return Column(
                  children: [
                    // Progress row
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      child: Row(
                        children: [
                          Text(
                            '$earned / ${badges.length} '
                            '${_s('badge_progress_suffix')}',
                            style: TextStyle(
                              color: Colors.white.withValues(alpha: 0.6),
                              fontSize: 13,
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Container(
                              height: 4,
                              decoration: BoxDecoration(
                                color: Colors.white.withValues(alpha: 0.12),
                                borderRadius: BorderRadius.circular(2),
                              ),
                              child: FractionallySizedBox(
                                widthFactor: badges.isEmpty ? 0 : earned / badges.length,
                                alignment: Alignment.centerLeft,
                                child: Container(
                                  decoration: BoxDecoration(
                                    color: _gold,
                                    borderRadius: BorderRadius.circular(2),
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 16),
                    // Badge grid
                    Expanded(
                      child: filtered.isEmpty
                          ? Center(
                              child: Text(
                                _s('badge_empty'),
                                style: TextStyle(
                                  color: Colors.white.withValues(alpha: 0.4),
                                  fontSize: 14,
                                ),
                              ),
                            )
                          : GridView.builder(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 16,
                              ),
                              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                                crossAxisCount: 3,
                                crossAxisSpacing: 12,
                                mainAxisSpacing: 12,
                              ),
                              itemCount: filtered.length,
                              itemBuilder: (_, i) => _BadgeTile(badge: filtered[i]),
                            ),
                    ),
                  ],
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _BadgeTile extends StatelessWidget {
  const _BadgeTile({required this.badge});
  final Badge badge;

  @override
  Widget build(BuildContext context) {
    final earned = badge.isEarned;
    return Opacity(
      opacity: earned ? 1.0 : 0.4,
      child: Container(
        decoration: BoxDecoration(
          gradient: earned
              ? const LinearGradient(
                  colors: [Color(0xFF8C6418), Color(0xFFB78628)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                )
              : null,
          color: earned ? null : Colors.white.withValues(alpha: 0.06),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: earned ? const Color(0xFFB78628) : Colors.white.withValues(alpha: 0.12),
          ),
          boxShadow: earned
              ? const [
                  BoxShadow(color: Color(0x40B78628), blurRadius: 12),
                ]
              : null,
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              earned ? Icons.workspace_premium_rounded : Icons.lock_outline_rounded,
              color: earned ? const Color(0xFF1A1200) : Colors.white.withValues(alpha: 0.4),
              size: 28,
            ),
            const SizedBox(height: 6),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 4),
              child: Text(
                badge.name,
                style: TextStyle(
                  color: earned ? const Color(0xFF1A1200) : Colors.white.withValues(alpha: 0.4),
                  fontSize: 10,
                  fontWeight: FontWeight.w600,
                ),
                textAlign: TextAlign.center,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
