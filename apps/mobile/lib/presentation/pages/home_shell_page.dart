// HomeShellPage hosts the bottom-nav tabs. Project-Decisions §23 keeps
// the camera FAB in the visual center (Shazam-style), with Discover +
// Saved on the left and Map + Profile on the right.
//
// Layout:
//   Discover   |   Map   | [Camera FAB] |   Saved   |   Profile
//
// Tabs are computed off the active GoRouter location so deep-links land
// on the correct highlight.

import "package:flutter/material.dart";
import "package:go_router/go_router.dart";
import "package:silklens/l10n/app_localizations.dart";
import "package:silklens/presentation/router/app_router.dart";

class HomeShellPage extends StatelessWidget {
  const HomeShellPage({required this.child, super.key});

  final Widget child;

  int _resolveIndex(BuildContext context) {
    final location = GoRouterState.of(context).matchedLocation;
    if (location.startsWith(AppRoutes.homeDiscover)) return 0;
    if (location.startsWith(AppRoutes.homeMap)) return 1;
    if (location.startsWith(AppRoutes.homeCamera)) return 2;
    if (location.startsWith(AppRoutes.homeSaved)) return 3;
    if (location.startsWith(AppRoutes.homeProfile)) return 4;
    return 0;
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final currentIndex = _resolveIndex(context);

    return Scaffold(
      body: child,
      floatingActionButtonLocation: FloatingActionButtonLocation.centerDocked,
      floatingActionButton: FloatingActionButton.large(
        key: const Key("nav.camera_fab"),
        onPressed: () => context.go(AppRoutes.homeCamera),
        backgroundColor: theme.colorScheme.primary,
        foregroundColor: theme.colorScheme.onPrimary,
        elevation: 4,
        shape: const CircleBorder(),
        child: const Icon(Icons.camera_alt, size: 36),
      ),
      bottomNavigationBar: BottomAppBar(
        shape: const CircularNotchedRectangle(),
        notchMargin: 8,
        child: SizedBox(
          height: 64,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: <Widget>[
              _NavButton(
                buttonKey: const Key("nav.discover"),
                icon: Icons.explore_outlined,
                selected: currentIndex == 0,
                label: l10n?.navDiscover ?? "Discover",
                onPressed: () => context.go(AppRoutes.homeDiscover),
              ),
              _NavButton(
                buttonKey: const Key("nav.map"),
                icon: Icons.map_outlined,
                selected: currentIndex == 1,
                label: l10n?.navMap ?? "Map",
                onPressed: () => context.go(AppRoutes.homeMap),
              ),
              const SizedBox(width: 64), // gap for the camera FAB
              _NavButton(
                buttonKey: const Key("nav.saved"),
                icon: Icons.bookmark_outline,
                selected: currentIndex == 3,
                label: l10n?.navSaved ?? "Saved",
                onPressed: () => context.go(AppRoutes.homeSaved),
              ),
              _NavButton(
                buttonKey: const Key("nav.profile"),
                icon: Icons.person_outline,
                selected: currentIndex == 4,
                label: l10n?.navProfile ?? "Profile",
                onPressed: () => context.go(AppRoutes.homeProfile),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _NavButton extends StatelessWidget {
  const _NavButton({
    required this.buttonKey,
    required this.icon,
    required this.selected,
    required this.label,
    required this.onPressed,
  });

  final Key buttonKey;
  final IconData icon;
  final bool selected;
  final String label;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    final color = selected
        ? Theme.of(context).colorScheme.primary
        : Theme.of(context).colorScheme.onSurfaceVariant;
    return InkWell(
      key: buttonKey,
      onTap: onPressed,
      borderRadius: BorderRadius.circular(12),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Icon(icon, color: color, size: 22),
            const SizedBox(height: 2),
            Text(
              label,
              style: TextStyle(color: color, fontSize: 10),
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
      ),
    );
  }
}
