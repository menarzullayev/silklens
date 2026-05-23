import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/presentation/pages/auth/auth_choice_page.dart';
import 'package:silklens/presentation/pages/auth/email_verify_page.dart';
import 'package:silklens/presentation/pages/auth/forgot_password_page.dart';
import 'package:silklens/presentation/pages/auth/language_selection_page.dart';
import 'package:silklens/presentation/pages/auth/onboarding_page.dart';
import 'package:silklens/presentation/pages/auth/sign_in_page.dart';
import 'package:silklens/presentation/pages/auth/sign_up_page.dart';
import 'package:silklens/presentation/pages/auth/splash_page.dart';
import 'package:silklens/presentation/pages/billing/checkout_page.dart';
import 'package:silklens/presentation/pages/billing/invoices_page.dart';
import 'package:silklens/presentation/pages/billing/manage_subscription_page.dart';
import 'package:silklens/presentation/pages/billing/plans_page.dart';
import 'package:silklens/presentation/pages/billing/tickets_page.dart';
import 'package:silklens/presentation/pages/camera/camera_page.dart';
import 'package:silklens/presentation/pages/camera/photo_guide_page.dart';
import 'package:silklens/presentation/pages/camera/voice_assistant_page.dart';
import 'package:silklens/presentation/pages/gamification/badges_page.dart';
import 'package:silklens/presentation/pages/gamification/leaderboard_page.dart';
import 'package:silklens/presentation/pages/gamification/missions_page.dart';
import 'package:silklens/presentation/pages/gamification/streak_widget.dart';
import 'package:silklens/presentation/pages/gamification/xp_card.dart';
import 'package:silklens/presentation/pages/heritage/audio_guide_page.dart';
import 'package:silklens/presentation/pages/heritage/heritage_detail_page.dart';
import 'package:silklens/presentation/pages/heritage/heritage_list_page.dart';
import 'package:silklens/presentation/pages/heritage/offline_mode_page.dart';
import 'package:silklens/presentation/pages/heritage/search_page.dart';
import 'package:silklens/presentation/pages/heritage/search_results_page.dart';
import 'package:silklens/presentation/pages/map/map_page.dart';
import 'package:silklens/presentation/pages/map/weather_guide_page.dart';
import 'package:silklens/presentation/pages/profile/user_profile_page.dart';
import 'package:silklens/presentation/pages/settings/about_page.dart';
import 'package:silklens/presentation/pages/settings/delete_account_page.dart';
import 'package:silklens/presentation/pages/settings/emergency_page.dart';
import 'package:silklens/presentation/pages/settings/language_settings_page.dart';
import 'package:silklens/presentation/pages/settings/notification_prefs_page.dart';
import 'package:silklens/presentation/pages/settings/privacy_gdpr_page.dart';
import 'package:silklens/presentation/pages/settings/settings_home_page.dart';
import 'package:silklens/presentation/pages/social/activity_feed_page.dart';
import 'package:silklens/presentation/pages/social/following_list_page.dart';
import 'package:silklens/presentation/pages/social/friend_invite_page.dart';
import 'package:silklens/presentation/pages/social/notifications_page.dart';
import 'package:silklens/presentation/providers/auth_provider.dart';

// Shell page with bottom navigation
class HomeShellPage extends StatelessWidget {
  const HomeShellPage({required this.child, super.key});
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Scaffold(body: child);
  }
}

// ─── Transition helpers ──────────────────────────────────────────────────────

CustomTransitionPage<void> _noTransitionPage(
  BuildContext ctx,
  GoRouterState state,
  Widget child,
) =>
    CustomTransitionPage<void>(
      key: state.pageKey,
      child: child,
      transitionDuration: Duration.zero,
      reverseTransitionDuration: Duration.zero,
      transitionsBuilder: (_, __, ___, child) => child,
    );

CustomTransitionPage<void> _fadePage(
  BuildContext ctx,
  GoRouterState state,
  Widget child, {
  Duration duration = const Duration(milliseconds: 300),
}) =>
    CustomTransitionPage<void>(
      key: state.pageKey,
      child: child,
      transitionDuration: duration,
      transitionsBuilder: (_, anim, __, child) =>
          FadeTransition(opacity: anim, child: child),
    );

CustomTransitionPage<void> _slideUpPage(
  BuildContext ctx,
  GoRouterState state,
  Widget child,
) =>
    CustomTransitionPage<void>(
      key: state.pageKey,
      child: child,
      transitionsBuilder: (_, anim, __, child) => SlideTransition(
        position: anim.drive(
          Tween(begin: const Offset(0, 0.08), end: Offset.zero)
              .chain(CurveTween(curve: Curves.easeOutCubic)),
        ),
        child: FadeTransition(opacity: anim, child: child),
      ),
    );

CustomTransitionPage<void> _slideRightPage(
  BuildContext ctx,
  GoRouterState state,
  Widget child, {
  Duration duration = const Duration(milliseconds: 250),
}) =>
    CustomTransitionPage<void>(
      key: state.pageKey,
      child: child,
      transitionDuration: duration,
      transitionsBuilder: (_, anim, __, child) => SlideTransition(
        position: anim.drive(
          Tween(begin: const Offset(1, 0), end: Offset.zero)
              .chain(CurveTween(curve: Curves.easeOutCubic)),
        ),
        child: child,
      ),
    );

CustomTransitionPage<void> _fadeScalePage(
  BuildContext ctx,
  GoRouterState state,
  Widget child,
) =>
    CustomTransitionPage<void>(
      key: state.pageKey,
      child: child,
      transitionDuration: const Duration(milliseconds: 400),
      transitionsBuilder: (_, anim, __, child) {
        final curved = CurvedAnimation(
          parent: anim,
          curve: Curves.easeOutCubic,
        );
        return FadeTransition(
          opacity: curved,
          child: ScaleTransition(
            scale: Tween<double>(begin: 0.96, end: 1).animate(curved),
            child: child,
          ),
        );
      },
    );

// ─── Auth router notifier ────────────────────────────────────────────────────

// Bridges Riverpod auth state into GoRouter's refreshListenable so the
// router re-evaluates its redirect callback whenever auth state changes.
class _AuthRouterNotifier extends ChangeNotifier {
  _AuthRouterNotifier(Ref ref) {
    ref.listen<AuthState>(authProvider, (_, __) => notifyListeners());
  }
}

// Routes that are only for unauthenticated users.
const _guestOnlyPaths = {
  '/',
  '/language',
  '/onboarding',
  '/auth/choice',
  '/auth/sign-in',
  '/auth/sign-up',
  '/auth/forgot-password',
};

// ─── Router ──────────────────────────────────────────────────────────────────

final appRouterProvider = Provider<GoRouter>((ref) {
  final notifier = _AuthRouterNotifier(ref);

  return GoRouter(
    initialLocation: '/',
    refreshListenable: notifier,
    redirect: (context, state) {
      final auth = ref.read(authProvider);
      final loc = state.matchedLocation;

      // Still loading — keep showing splash, don't redirect anything else.
      if (auth is AuthInitial) {
        return loc == '/' ? null : '/';
      }

      if (auth is AuthAuthenticated) {
        // Send authenticated users away from auth/splash pages.
        if (_guestOnlyPaths.contains(loc)) return '/home';
        return null;
      }

      // Unauthenticated — block protected routes.
      if (!_guestOnlyPaths.contains(loc)) return '/onboarding';
      return null;
    },
    routes: [
      GoRoute(
        path: '/',
        pageBuilder: (ctx, state) =>
            _noTransitionPage(ctx, state, const SplashPage()),
      ),
      GoRoute(
        path: '/language',
        pageBuilder: (ctx, state) =>
            _fadePage(ctx, state, const LanguageSelectionPage()),
      ),
      GoRoute(
        path: '/onboarding',
        pageBuilder: (ctx, state) => _fadePage(
          ctx,
          state,
          const OnboardingPage(),
          duration: const Duration(milliseconds: 350),
        ),
      ),
      GoRoute(
        path: '/auth/choice',
        pageBuilder: (ctx, state) =>
            _slideUpPage(ctx, state, const AuthChoicePage()),
      ),
      GoRoute(
        path: '/auth/sign-in',
        pageBuilder: (ctx, state) =>
            _slideUpPage(ctx, state, const SignInPage()),
      ),
      GoRoute(
        path: '/auth/sign-up',
        pageBuilder: (ctx, state) =>
            _slideUpPage(ctx, state, const SignUpPage()),
      ),
      GoRoute(
        path: '/auth/forgot-password',
        pageBuilder: (ctx, state) =>
            _slideRightPage(ctx, state, const ForgotPasswordPage()),
      ),
      GoRoute(
        path: '/settings',
        pageBuilder: (ctx, state) =>
            _fadePage(ctx, state, const SettingsHomePage()),
      ),
      GoRoute(
        path: '/settings/notifications',
        pageBuilder: (ctx, state) =>
            _slideRightPage(ctx, state, const NotificationPrefsPage()),
      ),
      GoRoute(
        path: '/settings/privacy',
        pageBuilder: (ctx, state) =>
            _slideRightPage(ctx, state, const PrivacyGDPRPage()),
      ),
      GoRoute(
        path: '/settings/about',
        pageBuilder: (ctx, state) =>
            _slideRightPage(ctx, state, const AboutPage()),
      ),
      GoRoute(
        path: '/settings/delete-account',
        pageBuilder: (ctx, state) =>
            _slideRightPage(ctx, state, const DeleteAccountPage()),
      ),
      GoRoute(
        path: '/settings/language',
        pageBuilder: (ctx, state) =>
            _slideRightPage(ctx, state, const LanguageSettingsPage()),
      ),
      GoRoute(
        path: '/social/feed',
        pageBuilder: (ctx, state) =>
            _fadePage(ctx, state, const ActivityFeedPage()),
      ),
      GoRoute(
        path: '/social/notifications',
        pageBuilder: (ctx, state) =>
            _slideRightPage(ctx, state, const NotificationsPage()),
      ),
      GoRoute(
        path: '/auth/email-verify',
        pageBuilder: (ctx, state) => _slideRightPage(
          ctx,
          state,
          EmailVerifyPage(
            email: state.uri.queryParameters['email'] ?? '',
          ),
        ),
      ),
      GoRoute(
        path: '/home',
        pageBuilder: (ctx, state) =>
            _fadeScalePage(ctx, state, const HeritageListPage()),
        routes: [
          GoRoute(
            path: 'heritage/:pubId',
            pageBuilder: (ctx, state) => _slideRightPage(
              ctx,
              state,
              HeritageDetailPage(pubId: state.pathParameters['pubId']!),
            ),
          ),
        ],
      ),
      GoRoute(
        path: '/map',
        pageBuilder: (ctx, state) =>
            _slideRightPage(ctx, state, const MapPage()),
      ),
      GoRoute(
        path: '/camera',
        pageBuilder: (ctx, state) =>
            _slideUpPage(ctx, state, const CameraPage()),
      ),
      GoRoute(
        path: '/voice-assistant',
        pageBuilder: (ctx, state) =>
            _slideUpPage(ctx, state, const VoiceAssistantPage()),
      ),
      // SILK-0100 — AI Photo Guide (angle suggestions + historical overlays)
      GoRoute(
        path: '/photo-guide/:pubId',
        pageBuilder: (ctx, state) => _slideRightPage(
          ctx,
          state,
          PhotoGuidePage(
            heritagePubId: state.pathParameters['pubId']!,
            heritageName: state.uri.queryParameters['name'],
          ),
        ),
      ),
      GoRoute(
        path: '/search',
        pageBuilder: (ctx, state) =>
            _slideUpPage(ctx, state, const SearchPage()),
      ),
      GoRoute(
        path: '/search/results',
        pageBuilder: (ctx, state) => _slideRightPage(
          ctx,
          state,
          SearchResultsPage(query: state.uri.queryParameters['q'] ?? ''),
        ),
      ),
      GoRoute(
        path: '/offline',
        pageBuilder: (ctx, state) =>
            _slideRightPage(ctx, state, const OfflineModePage()),
      ),
      GoRoute(
        path: '/audio-guide',
        pageBuilder: (ctx, state) => _slideUpPage(
          ctx,
          state,
          AudioGuidePage(
            heritagePubId: state.uri.queryParameters['pubId'],
            heritageText: state.uri.queryParameters['text'],
          ),
        ),
      ),
      GoRoute(
        path: '/billing',
        pageBuilder: (ctx, state) =>
            _fadePage(ctx, state, const PlansPage()),
      ),
      GoRoute(
        path: '/billing/checkout',
        pageBuilder: (ctx, state) => _slideUpPage(
          ctx,
          state,
          CheckoutPage(
            planSlug: state.uri.queryParameters['plan'],
          ),
        ),
      ),
      GoRoute(
        path: '/billing/invoices',
        pageBuilder: (ctx, state) =>
            _slideRightPage(ctx, state, const InvoicesPage()),
      ),
      GoRoute(
        path: '/billing/manage',
        pageBuilder: (ctx, state) =>
            _slideRightPage(ctx, state, const ManageSubscriptionPage()),
      ),
      GoRoute(
        path: '/billing/tickets',
        pageBuilder: (ctx, state) =>
            _slideRightPage(ctx, state, const TicketsPage()),
      ),
      GoRoute(
        path: '/emergency',
        pageBuilder: (ctx, state) =>
            _slideRightPage(ctx, state, const EmergencyPage()),
      ),
      GoRoute(
        path: '/weather',
        pageBuilder: (ctx, state) =>
            _slideRightPage(ctx, state, const WeatherGuidePage()),
      ),
      GoRoute(
        path: '/social/profile',
        pageBuilder: (ctx, state) =>
            _slideRightPage(ctx, state, const UserProfilePage()),
      ),
      GoRoute(
        path: '/social/following',
        pageBuilder: (ctx, state) =>
            _slideRightPage(ctx, state, const FollowingListPage()),
      ),
      GoRoute(
        path: '/social/invite',
        pageBuilder: (ctx, state) =>
            _slideUpPage(ctx, state, const FriendInvitePage()),
      ),
      GoRoute(
        path: '/gamification/xp',
        pageBuilder: (ctx, state) =>
            _fadeScalePage(ctx, state, const XPDashboardPage()),
      ),
      GoRoute(
        path: '/gamification/badges',
        pageBuilder: (ctx, state) =>
            _slideRightPage(ctx, state, const BadgesPage()),
      ),
      GoRoute(
        path: '/gamification/leaderboard',
        pageBuilder: (ctx, state) =>
            _slideRightPage(ctx, state, const LeaderboardPage()),
      ),
      GoRoute(
        path: '/gamification/streak',
        pageBuilder: (ctx, state) =>
            _slideRightPage(ctx, state, const StreakPage()),
      ),
      GoRoute(
        path: '/gamification/missions',
        pageBuilder: (ctx, state) =>
            _slideRightPage(ctx, state, const MissionsPage()),
      ),
    ],
  );
});
