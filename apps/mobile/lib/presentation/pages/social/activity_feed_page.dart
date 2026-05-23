import 'package:flutter/material.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/core/l10n/locale_service.dart';
import 'package:silklens/presentation/providers/social_provider.dart';

class ActivityFeedPage extends ConsumerWidget {
  const ActivityFeedPage({super.key});

  static const _stories = ['Siz', 'Aziz', 'Dilnoza', 'Jasur', 'Malika'];

  String _s(String key) =>
      AppStrings.get(LocaleService.instance.locale, key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final feedAsync = ref.watch(feedProvider);

    return Scaffold(
      backgroundColor: const Color(0xFF0D2337),
      appBar: AppBar(
        backgroundColor: const Color(0xFF0D2337),
        title: Text(
          _s('social_title'),
          style: const TextStyle(
            color: Colors.white,
            fontSize: 20,
            fontWeight: FontWeight.w700,
          ),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.search, color: Colors.white),
            onPressed: () {},
          ),
        ],
      ),
      body: CustomScrollView(
        slivers: [
          // Stories row — no API yet, kept static
          SliverToBoxAdapter(
            child: SizedBox(
              height: 88,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 16),
                itemCount: _stories.length,
                separatorBuilder: (_, __) => const SizedBox(width: 12),
                itemBuilder: (_, i) => Column(
                  children: [
                    Container(
                      width: 56,
                      height: 56,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        gradient: i == 0
                            ? null
                            : const LinearGradient(
                                colors: [
                                  Color(0xFFB78628),
                                  Color(0xFF1F3A93),
                                ],
                              ),
                        color: i == 0
                            ? Colors.white.withValues(alpha: 0.12)
                            : null,
                        border: Border.all(
                          color: i == 0
                              ? Colors.white.withValues(alpha: 0.3)
                              : const Color(0xFFB78628),
                          width: 2,
                        ),
                      ),
                      child: i == 0
                          ? const Icon(
                              Icons.add_rounded,
                              color: Colors.white,
                              size: 24,
                            )
                          : Center(
                              child: Text(
                                _stories[i][0],
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 20,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      _stories[i],
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 10,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
            ),
          ),

          // Feed — real data
          feedAsync.when(
            loading: () => SliverList(
              delegate: SliverChildBuilderDelegate(
                (_, i) => const _FeedSkeleton(),
                childCount: 3,
              ),
            ),
            error: (e, _) => SliverToBoxAdapter(
              child: _ErrorCard(
                message: _s('social_feed_error'),
                retryLabel: _s('social_feed_retry'),
                onRetry: () => ref.invalidate(feedProvider),
              ),
            ),
            data: (items) => items.isEmpty
                ? SliverToBoxAdapter(
                    child: Padding(
                      padding: const EdgeInsets.only(top: 60),
                      child: Center(
                        child: Text(
                          _s('social_feed_empty'),
                          style: TextStyle(
                            color: Colors.white.withValues(alpha: 0.4),
                            fontSize: 15,
                          ),
                        ),
                      ),
                    ),
                  )
                : SliverList(
                    delegate: SliverChildBuilderDelegate(
                      (_, i) => _FeedCard.fromItem(items[i]),
                      childCount: items.length,
                    ),
                  ),
          ),

          const SliverToBoxAdapter(child: SizedBox(height: 80)),
        ],
      ),
      floatingActionButton: Container(
        width: 52,
        height: 52,
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: [Color(0xFFB78628), Color(0xFFE5C97A)],
          ),
          shape: BoxShape.circle,
        ),
        child: const Icon(Icons.add_rounded, color: Color(0xFF1A1200)),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Feed card built from API item
// ---------------------------------------------------------------------------

class _FeedCard extends StatefulWidget {
  const _FeedCard({
    required this.author,
    required this.action,
    required this.time,
    required this.hasPhoto,
    required this.likeCount,
    required this.commentCount,
  });

  factory _FeedCard.fromItem(Map<String, dynamic> item) {
    final verb = item['verb'] as String? ?? '';
    final locale = LocaleService.instance.locale;
    final verbLabel = switch (verb) {
      'visit' => AppStrings.get(locale, 'social_verb_visit'),
      'review' => AppStrings.get(locale, 'social_verb_review'),
      'badge' => AppStrings.get(locale, 'social_verb_badge'),
      'follow' => AppStrings.get(locale, 'social_verb_follow'),
      _ => verb,
    };
    final targetName = item['target_name'] as String?
        ?? item['target_kind'] as String?
        ?? '';
    final action = targetName.isNotEmpty ? '$verbLabel $targetName' : verbLabel;
    final actorName = item['actor_display_name'] as String?
        ?? item['actor_pub_id'] as String?
        ?? '?';
    final createdAt = item['created_at'] as String? ?? '';
    final likeCount = (item['like_count'] as num?)?.toInt() ?? 0;
    final commentCount = (item['comment_count'] as num?)?.toInt() ?? 0;
    final hasMedia = item['media_url'] != null;

    return _FeedCard(
      author: actorName,
      action: action,
      time: createdAt,
      hasPhoto: hasMedia,
      likeCount: likeCount,
      commentCount: commentCount,
    );
  }

  final String author;
  final String action;
  final String time;
  final bool hasPhoto;
  final int likeCount;
  final int commentCount;

  @override
  State<_FeedCard> createState() => _FeedCardState();
}

class _FeedCardState extends State<_FeedCard> {
  bool _liked = false;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 0, 16, 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white.withValues(alpha: 0.10)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: const Color(0xFF1F3A93),
                  border: Border.all(
                    color: Colors.white.withValues(alpha: 0.2),
                  ),
                ),
                child: Center(
                  child: Text(
                    widget.author.isNotEmpty
                        ? widget.author[0].toUpperCase()
                        : '?',
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      widget.author,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    Text(
                      widget.time,
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.45),
                        fontSize: 11,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            widget.action,
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.85),
              fontSize: 14,
            ),
          ),
          if (widget.hasPhoto) ...[
            const SizedBox(height: 10),
            Container(
              height: 160,
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFF8B3A2A), Color(0xFFD2691E)],
                ),
                borderRadius: BorderRadius.circular(12),
              ),
            ),
          ],
          const SizedBox(height: 10),
          Row(
            children: [
              GestureDetector(
                onTap: () => setState(() => _liked = !_liked),
                child: Row(
                  children: [
                    Icon(
                      _liked
                          ? Icons.favorite_rounded
                          : Icons.favorite_outline_rounded,
                      color: _liked
                          ? Colors.red
                          : Colors.white.withValues(alpha: 0.5),
                      size: 20,
                    ),
                    const SizedBox(width: 4),
                    Text(
                      '${_liked ? widget.likeCount + 1 : widget.likeCount}',
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.5),
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 16),
              Row(
                children: [
                  Icon(
                    Icons.chat_bubble_outline_rounded,
                    color: Colors.white.withValues(alpha: 0.5),
                    size: 18,
                  ),
                  const SizedBox(width: 4),
                  Text(
                    '${widget.commentCount}',
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.5),
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
              const Spacer(),
              Icon(
                Icons.share_outlined,
                color: Colors.white.withValues(alpha: 0.5),
                size: 18,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Skeleton shimmer card
// ---------------------------------------------------------------------------

class _FeedSkeleton extends StatelessWidget {
  const _FeedSkeleton();

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 0, 16, 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.04),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white.withValues(alpha: 0.06)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _shimmer(40, 40, circular: true),
              const SizedBox(width: 10),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _shimmer(120, 12),
                  const SizedBox(height: 4),
                  _shimmer(80, 10),
                ],
              ),
            ],
          ),
          const SizedBox(height: 10),
          _shimmer(double.infinity, 14),
          const SizedBox(height: 6),
          _shimmer(200, 14),
        ],
      ),
    );
  }

  Widget _shimmer(double w, double h, {bool circular = false}) {
    return Container(
      width: w,
      height: h,
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.08),
        borderRadius: circular
            ? BorderRadius.circular(h / 2)
            : BorderRadius.circular(6),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Error card
// ---------------------------------------------------------------------------

class _ErrorCard extends StatelessWidget {
  const _ErrorCard({
    required this.message,
    required this.retryLabel,
    required this.onRetry,
  });

  final String message;
  final String retryLabel;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
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
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 10),
              decoration: BoxDecoration(
                color: const Color(0xFFB78628).withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: const Color(0xFFB78628).withValues(alpha: 0.4),
                ),
              ),
              child: Text(
                retryLabel,
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
    );
  }
}
