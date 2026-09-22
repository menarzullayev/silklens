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
import 'package:silklens/presentation/pages/camera/camera_page.dart';
import 'package:silklens/presentation/pages/heritage/heritage_detail_page.dart';
import 'package:silklens/presentation/pages/heritage/heritage_list_page.dart';
import 'package:silklens/presentation/pages/map/map_page.dart';

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

// ─── Router ──────────────────────────────────────────────────────────────────

final appRouterProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/',
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
            _slideRightPage(ctx, state, const CameraPage()),
      ),
    ],
  );
});
