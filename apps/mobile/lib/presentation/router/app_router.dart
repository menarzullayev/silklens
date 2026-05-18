// SilkLens navigation map (go_router 14).
//
// Top-level routes:
//   /                       → SplashPage (decides where to land)
//   /onboarding             → 3-slide intro (anonymous)
//   /auth/sign-in           → email+password sign-in
//   /auth/sign-up           → register (auto-login on 201)
//   /auth/forgot-password   → recovery stub
//   /heritage/search        → dedicated search page
//   /heritage/:pubId        → detail page (deep-linkable)
//   /home/...               → bottom-nav shell:
//      ├─ /home/discover    → heritage list (default landing)
//      ├─ /home/map         → map (Agent B)
//      ├─ /home/camera      → camera (Agent B)
//      ├─ /home/saved       → Isar-backed saved list
//      └─ /home/profile     → profile + theme/locale
//
// Stack routes (no bottom-nav shell): chat, user profile, badges,
// leaderboard, billing — surface on top of /home/.
//
// Auth redirect: anonymous users hitting the /home/... shell are routed
// to /auth/sign-in. The splash page handles the initial bootstrap so we
// don't redirect away from it.

import "package:flutter/widgets.dart";
import "package:go_router/go_router.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/presentation/pages/auth/forgot_password_page.dart";
import "package:silklens/presentation/pages/auth/onboarding_page.dart"
    as auth_onboarding;
import "package:silklens/presentation/pages/auth/sign_in_page.dart";
import "package:silklens/presentation/pages/auth/sign_up_page.dart";
import "package:silklens/presentation/pages/auth/splash_page.dart"
    as auth_splash;
import "package:silklens/presentation/pages/billing/checkout_page.dart";
import "package:silklens/presentation/pages/billing/invoices_page.dart";
import "package:silklens/presentation/pages/billing/manage_subscription_page.dart";
import "package:silklens/presentation/pages/billing/plans_page.dart";
import "package:silklens/presentation/pages/camera/camera_page.dart";
import "package:silklens/presentation/pages/chat/chat_page.dart";
import "package:silklens/presentation/pages/gamification/badges_page.dart";
import "package:silklens/presentation/pages/gamification/leaderboard_page.dart";
import "package:silklens/presentation/pages/heritage/heritage_detail_page.dart";
import "package:silklens/presentation/pages/heritage/heritage_list_page.dart";
import "package:silklens/presentation/pages/heritage/heritage_search_page.dart";
import "package:silklens/presentation/pages/heritage/saved_heritage_page.dart";
import "package:silklens/presentation/pages/home_shell_page.dart";
import "package:silklens/presentation/pages/map/map_page.dart";
import "package:silklens/presentation/pages/profile/profile_page.dart";
import "package:silklens/presentation/pages/profile/user_profile_page.dart";
import "package:silklens/presentation/providers/auth_provider.dart";

abstract final class AppRoutes {
  static const String splash = "/";
  static const String onboarding = "/onboarding";

  static const String authSignIn = "/auth/sign-in";
  static const String authSignUp = "/auth/sign-up";
  static const String authForgotPassword = "/auth/forgot-password";

  static const String home = "/home";
  static const String homeDiscover = "/home/discover";
  static const String homeMap = "/home/map";
  static const String homeCamera = "/home/camera";
  static const String homeSaved = "/home/saved";
  static const String homeProfile = "/home/profile";

  static const String heritageSearch = "/heritage/search";

  /// Build the canonical detail-page path for a heritage object.
  static String heritageDetail(String pubId) => "/heritage/$pubId";

  // Stack routes (no bottom-nav shell).
  static const String heritageDetailPattern = "/heritage/:pubId";

  static const String chat = "/chat";
  static const String chatWithContextPattern = "/chat/:heritage_id";
  static const String userProfilePattern = "/users/:pub_id";
  static String userProfile(String pubId) => "/users/$pubId";

  static const String badges = "/gamification/badges";
  static const String leaderboard = "/gamification/leaderboard";

  static const String billingPlans = "/billing/plans";
  static const String billingCheckoutPattern = "/billing/checkout/:plan_slug";
  static const String billingManage = "/billing/manage";
  static const String billingInvoices = "/billing/invoices";

  // ── Legacy aliases (kept so older imports keep compiling). ──
  static const String camera = homeCamera;
  static const String map = homeMap;
  static const String profile = homeProfile;
}

final Provider<GoRouter> appRouterProvider = Provider<GoRouter>((Ref ref) {
  final shellNavKey = GlobalKey<NavigatorState>(debugLabel: "sl-shell");
  final authListenable = _AuthChangeNotifier(ref);
  ref.onDispose(authListenable.dispose);

  return GoRouter(
    initialLocation: AppRoutes.splash,
    debugLogDiagnostics: false,
    refreshListenable: authListenable,
    redirect: (BuildContext context, GoRouterState state) {
      final auth = ref.read(authNotifierProvider);
      final location = state.matchedLocation;
      final isProtected = location.startsWith("/home");
      final isAuthLoc = location.startsWith("/auth/");

      if (auth.isLoading) return null;
      if (auth.isAnonymous && isProtected) return AppRoutes.authSignIn;
      if (auth.isAuthenticated && isAuthLoc) return AppRoutes.homeDiscover;
      return null;
    },
    routes: <RouteBase>[
      GoRoute(
        path: AppRoutes.splash,
        name: "splash",
        builder: (BuildContext context, GoRouterState state) =>
            const auth_splash.SplashPage(),
      ),
      GoRoute(
        path: AppRoutes.onboarding,
        name: "onboarding",
        builder: (BuildContext context, GoRouterState state) =>
            const auth_onboarding.OnboardingPage(),
      ),
      GoRoute(
        path: AppRoutes.authSignIn,
        name: "sign-in",
        builder: (BuildContext context, GoRouterState state) =>
            const SignInPage(),
      ),
      GoRoute(
        path: AppRoutes.authSignUp,
        name: "sign-up",
        builder: (BuildContext context, GoRouterState state) =>
            const SignUpPage(),
      ),
      GoRoute(
        path: AppRoutes.authForgotPassword,
        name: "forgot-password",
        builder: (BuildContext context, GoRouterState state) =>
            const ForgotPasswordPage(),
      ),
      GoRoute(
        path: AppRoutes.heritageSearch,
        name: "heritage-search",
        builder: (BuildContext context, GoRouterState state) =>
            const HeritageSearchPage(),
      ),
      GoRoute(
        path: AppRoutes.heritageDetailPattern,
        name: "heritage-detail",
        builder: (BuildContext context, GoRouterState state) =>
            HeritageDetailPage(
          pubId: state.pathParameters["pubId"] ?? "",
        ),
      ),
      ShellRoute(
        navigatorKey: shellNavKey,
        builder: (BuildContext context, GoRouterState state, Widget child) =>
            HomeShellPage(child: child),
        routes: <RouteBase>[
          GoRoute(
            path: AppRoutes.homeDiscover,
            name: "discover",
            pageBuilder: (BuildContext context, GoRouterState state) =>
                const NoTransitionPage<void>(child: HeritageListPage()),
          ),
          GoRoute(
            path: AppRoutes.homeMap,
            name: "map",
            pageBuilder: (BuildContext context, GoRouterState state) =>
                const NoTransitionPage<void>(child: MapPage()),
          ),
          GoRoute(
            path: AppRoutes.homeCamera,
            name: "camera",
            pageBuilder: (BuildContext context, GoRouterState state) =>
                const NoTransitionPage<void>(child: CameraPage()),
          ),
          GoRoute(
            path: AppRoutes.homeSaved,
            name: "saved",
            pageBuilder: (BuildContext context, GoRouterState state) =>
                const NoTransitionPage<void>(child: SavedHeritagePage()),
          ),
          GoRoute(
            path: AppRoutes.homeProfile,
            name: "profile",
            pageBuilder: (BuildContext context, GoRouterState state) =>
                const NoTransitionPage<void>(child: ProfilePage()),
          ),
        ],
      ),
      GoRoute(
        path: AppRoutes.chat,
        name: "chat",
        builder: (BuildContext context, GoRouterState state) =>
            const ChatPage(),
      ),
      GoRoute(
        path: AppRoutes.chatWithContextPattern,
        name: "chat_context",
        builder: (BuildContext context, GoRouterState state) => ChatPage(
          heritagePubIdContext: state.pathParameters["heritage_id"],
        ),
      ),
      GoRoute(
        path: AppRoutes.userProfilePattern,
        name: "user_profile",
        builder: (BuildContext context, GoRouterState state) =>
            UserProfilePage(
          pubId: state.pathParameters["pub_id"] ?? "",
        ),
      ),
      GoRoute(
        path: AppRoutes.badges,
        name: "badges",
        builder: (BuildContext context, GoRouterState state) =>
            const BadgesPage(),
      ),
      GoRoute(
        path: AppRoutes.leaderboard,
        name: "leaderboard",
        builder: (BuildContext context, GoRouterState state) =>
            const LeaderboardPage(),
      ),
      GoRoute(
        path: AppRoutes.billingPlans,
        name: "billing_plans",
        builder: (BuildContext context, GoRouterState state) =>
            const PlansPage(),
      ),
      GoRoute(
        path: AppRoutes.billingCheckoutPattern,
        name: "billing_checkout",
        builder: (BuildContext context, GoRouterState state) => CheckoutPage(
          planSlug: state.pathParameters["plan_slug"] ?? "",
        ),
      ),
      GoRoute(
        path: AppRoutes.billingManage,
        name: "billing_manage",
        builder: (BuildContext context, GoRouterState state) =>
            const ManageSubscriptionPage(),
      ),
      GoRoute(
        path: AppRoutes.billingInvoices,
        name: "billing_invoices",
        builder: (BuildContext context, GoRouterState state) =>
            const InvoicesPage(),
      ),
    ],
  );
}, name: "appRouterProvider");

/// Bridges Riverpod's [authNotifierProvider] into a [Listenable] so
/// go_router knows to re-evaluate redirects whenever the auth state
/// transitions.
class _AuthChangeNotifier extends ChangeNotifier {
  _AuthChangeNotifier(this._ref) {
    _sub = _ref.listen<AuthState>(
      authNotifierProvider,
      (AuthState? _, AuthState __) => notifyListeners(),
      fireImmediately: false,
    );
  }

  final Ref _ref;
  late final ProviderSubscription<AuthState> _sub;

  @override
  void dispose() {
    _sub.close();
    super.dispose();
  }
}
