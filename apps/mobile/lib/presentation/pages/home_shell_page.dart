// HomeShellPage hosts the three child tabs (map / camera / profile) and
// renders the camera-centered Shazam-style bottom bar (Project-Decisions §23).

import "package:flutter/material.dart";
import "package:go_router/go_router.dart";
import "package:silklens/l10n/app_localizations.dart";
import "package:silklens/presentation/router/app_router.dart";

class HomeShellPage extends StatelessWidget {
  const HomeShellPage({required this.child, super.key});

  final Widget child;

  static const _tabs = <_HomeTab>[
    _HomeTab(route: AppRoutes.map, icon: Icons.map_outlined, key: "nav.map"),
    _HomeTab(route: AppRoutes.camera, icon: Icons.camera_alt, key: "nav.camera"),
    _HomeTab(route: AppRoutes.profile, icon: Icons.person_outline, key: "nav.profile"),
  ];

  int _resolveIndex(BuildContext context) {
    final location = GoRouterState.of(context).matchedLocation;
    for (int i = 0; i < _tabs.length; i++) {
      if (location.startsWith(_tabs[i].route)) return i;
    }
    return 1; // default = camera (middle)
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
        onPressed: () => context.go(AppRoutes.camera),
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
                icon: Icons.map_outlined,
                selected: currentIndex == 0,
                label: l10n?.navMap ?? "Map",
                onPressed: () => context.go(AppRoutes.map),
              ),
              const SizedBox(width: 64), // gap for the camera FAB
              _NavButton(
                icon: Icons.person_outline,
                selected: currentIndex == 2,
                label: l10n?.navProfile ?? "Profile",
                onPressed: () => context.go(AppRoutes.profile),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _HomeTab {
  const _HomeTab({required this.route, required this.icon, required this.key});
  final String route;
  final IconData icon;
  final String key;
}

class _NavButton extends StatelessWidget {
  const _NavButton({
    required this.icon,
    required this.selected,
    required this.label,
    required this.onPressed,
  });

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
      onTap: onPressed,
      borderRadius: BorderRadius.circular(12),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Icon(icon, color: color),
            const SizedBox(height: 2),
            Text(
              label,
              style: TextStyle(color: color, fontSize: 11),
            ),
          ],
        ),
      ),
    );
  }
}
