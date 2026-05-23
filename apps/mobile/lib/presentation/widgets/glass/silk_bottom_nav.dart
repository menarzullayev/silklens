import 'package:flutter/material.dart';
import 'package:silklens/presentation/widgets/glass/glass_surface.dart';

enum SilkNavTab { home, map, camera, social, profile }

class SilkBottomNav extends StatelessWidget {
  const SilkBottomNav({
    required this.activeTab,
    required this.onTabChanged,
    super.key,
  });

  final SilkNavTab activeTab;
  final ValueChanged<SilkNavTab> onTabChanged;

  static const _tabs = [
    (
      SilkNavTab.home,
      Icons.explore_outlined,
      Icons.explore_rounded,
      'Asosiy',
    ),
    (
      SilkNavTab.map,
      Icons.map_outlined,
      Icons.map_rounded,
      'Xarita',
    ),
    (
      SilkNavTab.camera,
      Icons.camera_alt_outlined,
      Icons.camera_alt_rounded,
      'Kamera',
    ),
    (
      SilkNavTab.social,
      Icons.people_outline,
      Icons.people_rounded,
      'Ijtimoiy',
    ),
    (
      SilkNavTab.profile,
      Icons.person_outline_rounded,
      Icons.person_rounded,
      'Profil',
    ),
  ];

  static const _gold = Color(0xFFB78628);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16, left: 24, right: 24),
      child: GlassSurface(
        borderRadius: 32,
        opacity: 0.75,
        blur: 32,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 10),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: _tabs
                .map(
                  (tab) => _NavItem(
                    tab: tab.$1,
                    inactiveIcon: tab.$2,
                    activeIcon: tab.$3,
                    label: tab.$4,
                    isActive: activeTab == tab.$1,
                    onTap: () => onTabChanged(tab.$1),
                    gold: _gold,
                  ),
                )
                .toList(),
          ),
        ),
      ),
    );
  }
}

class _NavItem extends StatelessWidget {
  const _NavItem({
    required this.tab,
    required this.inactiveIcon,
    required this.activeIcon,
    required this.label,
    required this.isActive,
    required this.onTap,
    required this.gold,
  });

  final SilkNavTab tab;
  final IconData inactiveIcon;
  final IconData activeIcon;
  final String label;
  final bool isActive;
  final VoidCallback onTap;
  final Color gold;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: SizedBox(
        width: 52,
        height: 48,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              width: isActive ? 40 : 28,
              height: isActive ? 32 : 28,
              decoration: isActive
                  ? BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(12),
                    )
                  : null,
              child: Icon(
                isActive ? activeIcon : inactiveIcon,
                color: isActive ? gold : Colors.white.withValues(alpha: 0.45),
                size: 22,
              ),
            ),
            if (isActive)
              Container(
                margin: const EdgeInsets.only(top: 3),
                width: 4,
                height: 4,
                decoration: BoxDecoration(
                  color: gold,
                  shape: BoxShape.circle,
                ),
              ),
          ],
        ),
      ),
    );
  }
}
