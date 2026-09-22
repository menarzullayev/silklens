import 'package:flutter/material.dart';
import 'package:flutter_hooks/flutter_hooks.dart';
import 'package:go_router/go_router.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/domain/heritage/entities/heritage.dart';
import 'package:silklens/presentation/providers/heritage_list_provider.dart';
import 'package:silklens/presentation/providers/locale_provider.dart';
import 'package:silklens/presentation/widgets/shimmer_loading.dart';

class HeritageListPage extends HookConsumerWidget {
  const HeritageListPage({super.key});

  // Category label keys map to kindSlug filter values.
  // Index 0 = all (null), 1 = UNESCO (special flag handled in UI only),
  // 2..n = kind slugs.
  static const _categoryKeys = [
    'heritage_cat_all',
    'heritage_cat_mosque',
    'heritage_cat_palace',
    'heritage_cat_museum',
    'heritage_cat_city',
    'heritage_cat_arch',
  ];

  static const _categoryIcons = [
    Icons.grid_view_rounded,
    Icons.mosque_rounded,
    Icons.account_balance_rounded,
    Icons.museum_rounded,
    Icons.location_city_rounded,
    Icons.terrain_rounded,
  ];

  // Maps category index → kindSlug (null means "all").
  static const _kindSlugs = <String?>[
    null,
    'mosque',
    'palace',
    'museum',
    'historical_centre',
    'archaeological_site',
  ];

  static const _toneGradients = [
    [Color(0xFF8B3A2A), Color(0xFFD2691E)],
    [Color(0xFF1A3A5C), Color(0xFF2E6B9E)],
    [Color(0xFFF5E6C8), Color(0xFFD4A853)],
    [Color(0xFF2D5A1B), Color(0xFF4A7C3F)],
  ];

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final activeCategory = useState(0);
    final scrollCtrl = useScrollController();
    final appBarBlur = useState<double>(0);

    final listState = ref.watch(heritageListProvider);
    final notifier = ref.read(heritageListProvider.notifier);
    final locale = ref.watch(activeLocaleProvider);
    final lang = locale.languageCode;

    String s(String key) => AppStrings.get(lang, key);

    useEffect(
      () {
        void onScroll() {
          appBarBlur.value = (scrollCtrl.offset / 80).clamp(0.0, 1.0);
          if (scrollCtrl.hasClients &&
              scrollCtrl.position.pixels >=
                  scrollCtrl.position.maxScrollExtent - 200) {
            notifier.loadMore();
          }
        }

        scrollCtrl.addListener(onScroll);
        return () => scrollCtrl.removeListener(onScroll);
      },
      [scrollCtrl],
    );

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
          RefreshIndicator(
            onRefresh: notifier.refresh,
            color: const Color(0xFFB78628),
            backgroundColor: const Color(0xFF1A3A5C),
            child: CustomScrollView(
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
                          horizontal: 16,
                          vertical: 8,
                        ),
                        child: Row(
                          children: [
                            const Icon(
                              Icons.explore_rounded,
                              color: Color(0xFFB78628),
                              size: 28,
                            ),
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
                            Container(
                              width: 40,
                              height: 40,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                color: Colors.white.withValues(alpha: 0.08),
                                border: Border.all(
                                  color: Colors.white.withValues(alpha: 0.15),
                                ),
                              ),
                              child: const Icon(
                                Icons.notifications_outlined,
                                color: Colors.white,
                                size: 20,
                              ),
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
                      child: GestureDetector(
                        onTap: () => context.push('/search'),
                        child: Container(
                          height: 44,
                          decoration: BoxDecoration(
                            color: Colors.white.withValues(alpha: 0.08),
                            borderRadius: BorderRadius.circular(22),
                            border: Border.all(
                              color: Colors.white.withValues(alpha: 0.12),
                            ),
                          ),
                          child: Row(
                            children: [
                              const SizedBox(width: 12),
                              Icon(
                                Icons.search,
                                color: Colors.white.withValues(alpha: 0.5),
                                size: 18,
                              ),
                              const SizedBox(width: 8),
                              Text(
                                s('heritage_search_hint'),
                                style: TextStyle(
                                  color: Colors.white.withValues(alpha: 0.4),
                                  fontSize: 14,
                                ),
                              ),
                            ],
                          ),
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
                      itemCount: _categoryKeys.length,
                      separatorBuilder: (_, __) => const SizedBox(width: 8),
                      itemBuilder: (_, i) {
                        final active = activeCategory.value == i;
                        return GestureDetector(
                          onTap: () {
                            activeCategory.value = i;
                            notifier.updateFilter(
                              listState.filters
                                  .copyWith(kindSlug: _kindSlugs[i]),
                            );
                          },
                          child: AnimatedContainer(
                            duration: const Duration(milliseconds: 200),
                            padding: const EdgeInsets.symmetric(
                              horizontal: 14,
                              vertical: 10,
                            ),
                            decoration: BoxDecoration(
                              color: active
                                  ? const Color(0xFFB78628)
                                  : Colors.white.withValues(alpha: 0.08),
                              borderRadius: BorderRadius.circular(22),
                              border: Border.all(
                                color: active
                                    ? const Color(0xFFB78628)
                                    : Colors.white.withValues(alpha: 0.15),
                              ),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(
                                  _categoryIcons[i],
                                  size: 13,
                                  color: active
                                      ? const Color(0xFF1A1200)
                                      : Colors.white,
                                ),
                                const SizedBox(width: 4),
                                Text(
                                  s(_categoryKeys[i]),
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
                              ],
                            ),
                          ),
                        );
                      },
                    ),
                  ),
                ),

                const SliverToBoxAdapter(child: SizedBox(height: 16)),

                // Error state
                if (listState.error != null && listState.items.isEmpty)
                  SliverToBoxAdapter(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 24,
                        vertical: 40,
                      ),
                      child: Column(
                        children: [
                          Icon(
                            Icons.wifi_off_rounded,
                            color: Colors.white.withValues(alpha: 0.4),
                            size: 48,
                          ),
                          const SizedBox(height: 12),
                          Text(
                            s('heritage_err_load'),
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              color: Colors.white.withValues(alpha: 0.6),
                              fontSize: 14,
                            ),
                          ),
                          const SizedBox(height: 16),
                          GestureDetector(
                            onTap: notifier.refresh,
                            child: Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 20,
                                vertical: 10,
                              ),
                              decoration: BoxDecoration(
                                color: const Color(0xFFB78628),
                                borderRadius: BorderRadius.circular(20),
                              ),
                              child: Text(
                                s('heritage_retry'),
                                style: const TextStyle(
                                  color: Color(0xFF1A1200),
                                  fontWeight: FontWeight.w600,
                                  fontSize: 13,
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  )
                // Loading skeleton grid
                else if (listState.isLoading && listState.items.isEmpty)
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
                        (_, __) => const _HeritageCardSkeleton(),
                        childCount: 6,
                      ),
                    ),
                  )
                // Empty state
                else if (!listState.isLoading && listState.items.isEmpty)
                  SliverToBoxAdapter(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 24,
                        vertical: 60,
                      ),
                      child: Column(
                        children: [
                          Icon(
                            Icons.search_off_rounded,
                            color: Colors.white.withValues(alpha: 0.3),
                            size: 56,
                          ),
                          const SizedBox(height: 12),
                          Text(
                            s('heritage_empty'),
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              color: Colors.white.withValues(alpha: 0.5),
                              fontSize: 15,
                            ),
                          ),
                        ],
                      ),
                    ),
                  )
                // Heritage grid
                else
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
                        (_, i) => _HeritageCard(
                          heritage: listState.items[i],
                          lang: lang,
                          toneIndex: i,
                          gradients: _toneGradients,
                        ),
                        childCount: listState.items.length,
                      ),
                    ),
                  ),

                // Pagination loading indicator
                if (listState.isLoading && listState.items.isNotEmpty)
                  const SliverToBoxAdapter(
                    child: Padding(
                      padding: EdgeInsets.symmetric(vertical: 16),
                      child: Center(
                        child: SizedBox(
                          width: 24,
                          height: 24,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Color(0xFFB78628),
                          ),
                        ),
                      ),
                    ),
                  ),

                // Bottom padding so content clears the floating nav
                const SliverToBoxAdapter(child: SizedBox(height: 100)),
              ],
            ),
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
                      color: Colors.white.withValues(alpha: 0.15),
                    ),
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
                        label: AppStrings.get(lang, 'nav_home'),
                        active: true,
                        onTap: () {},
                      ),
                      _NavIcon(
                        icon: Icons.map_outlined,
                        label: AppStrings.get(lang, 'nav_map'),
                        onTap: () => context.go('/map'),
                      ),
                      _NavIcon(
                        icon: Icons.camera_alt_outlined,
                        label: AppStrings.get(lang, 'nav_camera'),
                        onTap: () => context.go('/camera'),
                      ),
                      _NavIcon(
                        icon: Icons.people_outline,
                        label: AppStrings.get(lang, 'nav_social'),
                        onTap: () {},
                      ),
                      _NavIcon(
                        icon: Icons.person_outline,
                        label: AppStrings.get(lang, 'nav_profile'),
                        onTap: () {},
                      ),
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
// Heritage card — driven by real Heritage entity
// ---------------------------------------------------------------------------

class _HeritageCard extends StatelessWidget {
  const _HeritageCard({
    required this.heritage,
    required this.lang,
    required this.toneIndex,
    required this.gradients,
  });

  final Heritage heritage;
  final String lang;
  final int toneIndex;
  final List<List<Color>> gradients;

  @override
  Widget build(BuildContext context) {
    final colors = gradients[toneIndex % gradients.length];
    final title = heritage.localizedName(lang);
    final location = heritage.countryCode ?? '';

    return GestureDetector(
      onTap: () => context.push('/home/heritage/${heritage.pubId}'),
      child: Container(
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.06),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: Colors.white.withValues(alpha: 0.10)),
        ),
        clipBehavior: Clip.hardEdge,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Photo area — gradient tone placeholder until media service lands
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
                  // Kind icon overlay
                  Positioned(
                    bottom: 8,
                    left: 8,
                    child: Icon(
                      _iconForKind(heritage.kindSlug),
                      color: Colors.white.withValues(alpha: 0.6),
                      size: 20,
                    ),
                  ),
                  if (heritage.isUnescoListed)
                    Positioned(
                      top: 8,
                      right: 8,
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 6,
                          vertical: 2,
                        ),
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
                      title,
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
                        const Icon(
                          Icons.location_on,
                          color: Color(0xFFB78628),
                          size: 12,
                        ),
                        const SizedBox(width: 2),
                        Expanded(
                          child: Text(
                            location,
                            style: TextStyle(
                              color: Colors.white.withValues(alpha: 0.6),
                              fontSize: 11,
                            ),
                            overflow: TextOverflow.ellipsis,
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

  IconData _iconForKind(String slug) {
    switch (slug) {
      case 'mosque':
        return Icons.mosque_rounded;
      case 'palace':
      case 'castle':
        return Icons.account_balance_rounded;
      case 'museum':
        return Icons.museum_rounded;
      case 'historical_centre':
        return Icons.location_city_rounded;
      case 'archaeological_site':
        return Icons.terrain_rounded;
      default:
        return Icons.place_rounded;
    }
  }
}

// ---------------------------------------------------------------------------
// Skeleton card shown while loading
// ---------------------------------------------------------------------------

class _HeritageCardSkeleton extends StatelessWidget {
  const _HeritageCardSkeleton();

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white.withValues(alpha: 0.10)),
      ),
      clipBehavior: Clip.hardEdge,
      child: const Column(
        children: [
          Expanded(
            flex: 3,
            child: ShimmerBox(
              width: double.infinity,
              height: double.infinity,
              borderRadius: 0,
            ),
          ),
          Expanded(
            flex: 2,
            child: Padding(
              padding: EdgeInsets.all(10),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  ShimmerBox(
                    width: double.infinity,
                    height: 13,
                    borderRadius: 4,
                  ),
                  SizedBox(height: 6),
                  ShimmerBox(width: 80, height: 11, borderRadius: 4),
                ],
              ),
            ),
          ),
        ],
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
