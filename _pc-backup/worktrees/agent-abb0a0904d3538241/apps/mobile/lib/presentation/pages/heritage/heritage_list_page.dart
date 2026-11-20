import 'package:flutter/material.dart';
import 'package:flutter_hooks/flutter_hooks.dart';
import 'package:go_router/go_router.dart';

class HeritageListPage extends HookWidget {
  const HeritageListPage({super.key});

  static const _categories = [
    ('Barchasi', Icons.grid_view_rounded),
    ('UNESCO 🏅', Icons.workspace_premium_rounded),
    ('Masjid', Icons.mosque_rounded),
    ('Saroy', Icons.account_balance_rounded),
    ('Muzey', Icons.museum_rounded),
    ('Shahar', Icons.location_city_rounded),
  ];

  // Heritage tone color gradients (inline since widget may not exist yet)
  static const _toneGradients = [
    [Color(0xFF8B3A2A), Color(0xFFD2691E)], // registan
    [Color(0xFF1A3A5C), Color(0xFF2E6B9E)], // bukhara
    [Color(0xFFF5E6C8), Color(0xFFD4A853)], // khiva
    [Color(0xFF2D5A1B), Color(0xFF4A7C3F)], // shahi
  ];

  static const _demoData = [
    ('Registon', 'Samarqand', 0, '4.9', true),
    ('Bibi-Xonim', 'Samarqand', 1, '4.7', true),
    ("Ark Qal'asi", 'Buxoro', 2, '4.8', false),
    ("Po'lon Khan Minorasi", 'Buxoro', 1, '4.6', false),
    ('Itchan Kala', 'Xiva', 3, '4.9', true),
    ('Shoh-i-Zinda', 'Samarqand', 0, '4.8', true),
  ];

  @override
  Widget build(BuildContext context) {
    final activeCategory = useState(0);
    final scrollCtrl = useScrollController();
    final appBarBlur = useState<double>(0);

    useEffect(() {
      void onScroll() {
        appBarBlur.value = (scrollCtrl.offset / 80).clamp(0.0, 1.0);
      }
      scrollCtrl.addListener(onScroll);
      return () => scrollCtrl.removeListener(onScroll);
    }, [scrollCtrl],);

    return Scaffold(
      backgroundColor: const Color(0xFF0D2337),
      body: Stack(
        children: [
          // Aurora background — blue pulse
          Container(
            decoration: BoxDecoration(
              gradient: RadialGradient(
                center: const Alignment(-0.3, -0.5),
                radius: 1.5,
                colors: [
                  const Color(0xFF1F3A93).withValues(alpha: 0.5),
                  Colors.transparent,
                ],
              ),
            ),
          ),
          // Aurora background — amber pulse
          Container(
            decoration: BoxDecoration(
              gradient: RadialGradient(
                center: const Alignment(0.7, 0.3),
                radius: 1,
                colors: [
                  const Color(0xFFC2501F).withValues(alpha: 0.3),
                  Colors.transparent,
                ],
              ),
            ),
          ),

          // Main scrollable content
          CustomScrollView(
            controller: scrollCtrl,
            slivers: [
              // Glass AppBar (transparent → frosted on scroll)
              SliverAppBar(
                backgroundColor: Colors.transparent,
                elevation: 0,
                floating: true,
                expandedHeight: 0,
                flexibleSpace: AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  decoration: BoxDecoration(
                    color: Colors.white
                        .withValues(alpha: 0.08 * appBarBlur.value),
                    border: Border(
                      bottom: BorderSide(
                        color: Colors.white
                            .withValues(alpha: 0.10 * appBarBlur.value),
                      ),
                    ),
                  ),
                  child: SafeArea(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 16, vertical: 8,),
                      child: Row(
                        children: [
                          const Icon(Icons.explore_rounded,
                              color: Color(0xFFB78628), size: 28,),
                          const SizedBox(width: 8),
                          const Text(
                            'SilkLens',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 20,
                              fontWeight: FontWeight.w800,
                              letterSpacing: 1,
                            ),
                          ),
                          const Spacer(),
                          // Notification bell
                          Container(
                            width: 40,
                            height: 40,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color:
                                  Colors.white.withValues(alpha: 0.08),
                              border: Border.all(
                                  color: Colors.white
                                      .withValues(alpha: 0.15),),
                            ),
                            child: const Icon(
                                Icons.notifications_outlined,
                                color: Colors.white,
                                size: 20,),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
                bottom: PreferredSize(
                  preferredSize: const Size.fromHeight(52),
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
                    child: Container(
                      height: 44,
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.08),
                        borderRadius: BorderRadius.circular(22),
                        border: Border.all(
                            color:
                                Colors.white.withValues(alpha: 0.12),),
                      ),
                      child: Row(
                        children: [
                          const SizedBox(width: 12),
                          Icon(Icons.search,
                              color:
                                  Colors.white.withValues(alpha: 0.5),
                              size: 18,),
                          const SizedBox(width: 8),
                          Text(
                            'Meros joylarini qidiring...',
                            style: TextStyle(
                                color:
                                    Colors.white.withValues(alpha: 0.4),
                                fontSize: 14,),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),

              // Category chips row
              SliverToBoxAdapter(
                child: SizedBox(
                  height: 44,
                  child: ListView.separated(
                    scrollDirection: Axis.horizontal,
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    itemCount: _categories.length,
                    separatorBuilder: (_, __) =>
                        const SizedBox(width: 8),
                    itemBuilder: (_, i) {
                      final active = activeCategory.value == i;
                      return GestureDetector(
                        onTap: () => activeCategory.value = i,
                        child: AnimatedContainer(
                          duration: const Duration(milliseconds: 200),
                          padding: const EdgeInsets.symmetric(
                              horizontal: 14, vertical: 10,),
                          decoration: BoxDecoration(
                            color: active
                                ? const Color(0xFFB78628)
                                : Colors.white.withValues(alpha: 0.08),
                            borderRadius: BorderRadius.circular(22),
                            border: Border.all(
                              color: active
                                  ? const Color(0xFFB78628)
                                  : Colors.white
                                      .withValues(alpha: 0.15),
                            ),
                          ),
                          child: Text(
                            _categories[i].$1,
                            style: TextStyle(
                              color: active
                                  ? const Color(0xFF1A1200)
                                  : Colors.white,
                              fontSize: 13,
                              fontWeight: active
                                  ? FontWeight.w600
                                  : FontWeight.w400,
                            ),
                          ),
                        ),
                      );
                    },
                  ),
                ),
              ),

              const SliverToBoxAdapter(child: SizedBox(height: 16)),

              // Heritage grid
              SliverPadding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                sliver: SliverGrid(
                  gridDelegate:
                      const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 2,
                    crossAxisSpacing: 12,
                    mainAxisSpacing: 12,
                    childAspectRatio: 0.80,
                  ),
                  delegate: SliverChildBuilderDelegate(
                    (ctx, i) => _HeritageCard(
                      name: _demoData[i].$1,
                      city: _demoData[i].$2,
                      toneIndex: _demoData[i].$3,
                      rating: _demoData[i].$4,
                      isUnesco: _demoData[i].$5,
                      gradients: _toneGradients,
                      onTap: () =>
                          ctx.go('/home/heritage/demo-$i'),
                    ),
                    childCount: _demoData.length,
                  ),
                ),
              ),

              // Bottom padding so content clears the floating nav
              const SliverToBoxAdapter(child: SizedBox(height: 100)),
            ],
          ),

          // Floating glass bottom nav pill
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            child: SafeArea(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(24, 0, 24, 8),
                child: Container(
                  height: 64,
                  decoration: BoxDecoration(
                    color: const Color(0xBF0D2337),
                    borderRadius: BorderRadius.circular(32),
                    border: Border.all(
                        color: Colors.white.withValues(alpha: 0.15),),
                    boxShadow: const [
                      BoxShadow(
                        color: Color(0x40000000),
                        blurRadius: 24,
                        offset: Offset(0, 8),
                      ),
                    ],
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                    children: [
                      _NavIcon(
                          icon: Icons.explore_rounded,
                          label: 'Asosiy',
                          active: true,
                          onTap: () {},),
                      _NavIcon(
                          icon: Icons.map_outlined,
                          label: 'Xarita',
                          onTap: () => context.go('/map'),),
                      _NavIcon(
                          icon: Icons.camera_alt_outlined,
                          label: 'Kamera',
                          onTap: () => context.go('/camera'),),
                      _NavIcon(
                          icon: Icons.people_outline,
                          label: 'Ijtimoiy',
                          onTap: () {},),
                      _NavIcon(
                          icon: Icons.person_outline,
                          label: 'Profil',
                          onTap: () {},),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Heritage card with gradient tone placeholder
// ---------------------------------------------------------------------------

class _HeritageCard extends StatelessWidget {
  const _HeritageCard({
    required this.name,
    required this.city,
    required this.toneIndex,
    required this.rating,
    required this.isUnesco,
    required this.gradients,
    required this.onTap,
  });

  final String name;
  final String city;
  final int toneIndex;
  final String rating;
  final bool isUnesco;
  final List<List<Color>> gradients;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colors = gradients[toneIndex % gradients.length];
    return GestureDetector(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.06),
          borderRadius: BorderRadius.circular(20),
          border:
              Border.all(color: Colors.white.withValues(alpha: 0.10)),
        ),
        clipBehavior: Clip.hardEdge,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Photo area — gradient tone placeholder
            Expanded(
              flex: 3,
              child: Stack(
                children: [
                  Container(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                        colors: colors,
                      ),
                    ),
                  ),
                  if (isUnesco)
                    Positioned(
                      top: 8,
                      right: 8,
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 6, vertical: 2,),
                        decoration: BoxDecoration(
                          color: const Color(0xFFB78628),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: const Text(
                          'UNESCO',
                          style: TextStyle(
                            color: Color(0xFF1A1200),
                            fontSize: 9,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                    ),
                ],
              ),
            ),
            // Info area
            Expanded(
              flex: 2,
              child: Padding(
                padding: const EdgeInsets.all(10),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      name,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        const Icon(Icons.location_on,
                            color: Color(0xFFB78628), size: 12,),
                        const SizedBox(width: 2),
                        Expanded(
                          child: Text(
                            city,
                            style: TextStyle(
                                color:
                                    Colors.white.withValues(alpha: 0.6),
                                fontSize: 11,),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        const Icon(Icons.star_rounded,
                            color: Color(0xFFB78628), size: 12,),
                        const SizedBox(width: 2),
                        Text(
                          rating,
                          style: const TextStyle(
                            color: Color(0xFFB78628),
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ],
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
// Bottom nav icon item
// ---------------------------------------------------------------------------

class _NavIcon extends StatelessWidget {
  const _NavIcon({
    required this.icon,
    required this.label,
    required this.onTap,
    this.active = false,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;
  final bool active;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            icon,
            color: active
                ? const Color(0xFFB78628)
                : Colors.white.withValues(alpha: 0.45),
            size: 24,
          ),
          if (active)
            Container(
              margin: const EdgeInsets.only(top: 3),
              width: 4,
              height: 4,
              decoration: const BoxDecoration(
                color: Color(0xFFB78628),
                shape: BoxShape.circle,
              ),
            ),
        ],
      ),
    );
  }
}
