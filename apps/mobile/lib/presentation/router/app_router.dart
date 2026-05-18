// SilkLens navigation map.
//
// Project-Decisions §23 — Shazam-style camera-centered nav. Three roots
// (Map, Camera, Profile); the camera tab sits in the visual center and is
// the default landing after onboarding.
//
// Splash → (first run) Onboarding → Home (camera focused).
// `redirect` here is conservative — onboarding state lives in
// SharedPreferences in FAZA 2; for now we always show the splash for ≤1.5s
// and then route to camera.

import "package:flutter/widgets.dart";
import "package:go_router/go_router.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/presentation/pages/camera_page.dart";
import "package:silklens/presentation/pages/home_shell_page.dart";
import "package:silklens/presentation/pages/map_page.dart";
import "package:silklens/presentation/pages/onboarding_page.dart";
import "package:silklens/presentation/pages/profile_page.dart";
import "package:silklens/presentation/pages/splash_page.dart";

abstract final class AppRoutes {
  static const String splash = "/";
  static const String onboarding = "/onboarding";
  static const String home = "/home";
  static const String camera = "/home/camera";
  static const String map = "/home/map";
  static const String profile = "/home/profile";
}

final Provider<GoRouter> appRouterProvider = Provider<GoRouter>((Ref ref) {
  final shellNavKey = GlobalKey<NavigatorState>(debugLabel: "sl-shell");

  return GoRouter(
    initialLocation: AppRoutes.splash,
    debugLogDiagnostics: false,
    routes: <RouteBase>[
      GoRoute(
        path: AppRoutes.splash,
        name: "splash",
        builder: (BuildContext context, GoRouterState state) => const SplashPage(),
      ),
      GoRoute(
        path: AppRoutes.onboarding,
        name: "onboarding",
        builder: (BuildContext context, GoRouterState state) => const OnboardingPage(),
      ),
      ShellRoute(
        navigatorKey: shellNavKey,
        builder: (BuildContext context, GoRouterState state, Widget child) =>
            HomeShellPage(child: child),
        routes: <RouteBase>[
          GoRoute(
            path: AppRoutes.map,
            name: "map",
            pageBuilder: (BuildContext context, GoRouterState state) =>
                const NoTransitionPage<void>(child: MapPage()),
          ),
          GoRoute(
            path: AppRoutes.camera,
            name: "camera",
            pageBuilder: (BuildContext context, GoRouterState state) =>
                const NoTransitionPage<void>(child: CameraPage()),
          ),
          GoRoute(
            path: AppRoutes.profile,
            name: "profile",
            pageBuilder: (BuildContext context, GoRouterState state) =>
                const NoTransitionPage<void>(child: ProfilePage()),
          ),
        ],
      ),
    ],
  );
}, name: "appRouterProvider");
