import 'package:flutter/material.dart';

class ActivityFeedPage extends StatelessWidget {
  const ActivityFeedPage({super.key});

  static const _stories = ['Siz', 'Aziz', 'Dilnoza', 'Jasur', 'Malika'];
  static const _feed = [
    (
      'Aziz Karimov',
      'Registon ga tashrif buyurdi',
      '2 soat oldin',
      true,
    ),
    (
      'Dilnoza Yusupova',
      "Bibi-Xonim da yangi foto qo'shdi",
      '4 soat oldin',
      false,
    ),
    (
      'Jasur Rahimov',
      'Itchan Kala da AI tanish ishlatdi',
      '6 soat oldin',
      true,
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0D2337),
      appBar: AppBar(
        backgroundColor: const Color(0xFF0D2337),
        title: const Text(
          'Jamiyat',
          style: TextStyle(
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
          // Stories
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
          // Feed
          SliverList(
            delegate: SliverChildBuilderDelegate(
              (_, i) => _FeedCard(
                author: _feed[i].$1,
                action: _feed[i].$2,
                time: _feed[i].$3,
                hasPhoto: _feed[i].$4,
              ),
              childCount: _feed.length,
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

class _FeedCard extends StatefulWidget {
  const _FeedCard({
    required this.author,
    required this.action,
    required this.time,
    required this.hasPhoto,
  });
  final String author;
  final String action;
  final String time;
  final bool hasPhoto;

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
                    widget.author[0],
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
                      '24',
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
                    '5',
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
