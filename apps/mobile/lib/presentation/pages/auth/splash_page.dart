// SplashPage — first frame the user sees on cold start.
//
// The splash sits on screen for at most [_maxWait] milliseconds while:
//   1. [brandingProvider] resolves (so the logo/app-name from the active
//      tenant paint correctly).
//   2. [authNotifierProvider] bootstraps and either confirms an
//      authenticated session (silent refresh) or settles on anonymous.
//
// Routing decision after both have settled:
//   * authenticated → /home/discover (Discover tab is the new default
//     landing per WAVE-3 spec).
//   * anonymous → /onboarding.

import "dart:async";

import "package:flutter/material.dart";
import "package:flutter_hooks/flutter_hooks.dart";
import "package:go_router/go_router.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/l10n/app_localizations.dart";
import "package:silklens/presentation/providers/auth_provider.dart";
import "package:silklens/presentation/providers/branding_provider.dart";
import "package:silklens/presentation/router/app_router.dart";

class SplashPage extends HookConsumerWidget {
  const SplashPage({super.key});

  static const Duration _minVisible = Duration(milliseconds: 1200);
  static const Duration _maxWait = Duration(seconds: 6);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final didNavigate = useRef(false);

    ref.listen<AuthState>(authNotifierProvider, (AuthState? prev, AuthState next) {
      _maybeNavigate(context, next, didNavigate);
    });

    useEffect(
      () {
        final startedAt = DateTime.now();
        final timer = Timer(_maxWait, () {
          if (!context.mounted || didNavigate.value) return;
          // Hard-cap — assume anonymous if nothing has resolved.
          _navigate(context, isAuthenticated: false, didNavigate: didNavigate);
        });

        // Force the splash to remain visible for at least _minVisible even
        // if everything resolves instantly.
        Future<void>.delayed(_minVisible, () {
          if (!context.mounted || didNavigate.value) return;
          final state = ref.read(authNotifierProvider);
          if (state is! AuthLoading) {
            final elapsed = DateTime.now().difference(startedAt);
            if (elapsed >= _minVisible) {
              _maybeNavigate(context, state, didNavigate);
            }
          }
        });
        return timer.cancel;
      },
      const <Object?>[],
    );

    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final branding = ref.watch(brandingValueProvider);
    final locale = Localizations.localeOf(context);

    return Scaffold(
      backgroundColor: colorScheme.primary,
      body: SafeArea(
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: <Widget>[
              if (branding.logoUrl != null && branding.logoUrl!.isNotEmpty)
                _Logo(url: branding.logoUrl!, color: colorScheme.onPrimary)
              else
                Icon(
                  Icons.travel_explore,
                  key: const Key("splash.logo"),
                  size: 96,
                  color: colorScheme.onPrimary,
                ),
              const SizedBox(height: 24),
              Text(
                branding.localizedAppName(locale.languageCode),
                key: const Key("splash.app_name"),
                style: theme.textTheme.headlineMedium?.copyWith(
                  color: colorScheme.onPrimary,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1.2,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                l10n?.appTagline ?? "",
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: colorScheme.onPrimary.withValues(alpha: 0.8),
                ),
              ),
              const SizedBox(height: 32),
              SizedBox(
                width: 24,
                height: 24,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  valueColor: AlwaysStoppedAnimation<Color>(
                    colorScheme.onPrimary.withValues(alpha: 0.7),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _maybeNavigate(
    BuildContext context,
    AuthState state,
    ObjectRef<bool> didNavigate,
  ) {
    if (didNavigate.value) return;
    if (state is AuthLoading) return;
    _navigate(
      context,
      isAuthenticated: state.isAuthenticated,
      didNavigate: didNavigate,
    );
  }

  void _navigate(
    BuildContext context, {
    required bool isAuthenticated,
    required ObjectRef<bool> didNavigate,
  }) {
    if (didNavigate.value) return;
    didNavigate.value = true;
    if (!context.mounted) return;
    context.go(
      isAuthenticated ? AppRoutes.homeDiscover : AppRoutes.onboarding,
    );
  }
}

class _Logo extends StatelessWidget {
  const _Logo({required this.url, required this.color});

  final String url;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Image.network(
      url,
      key: const Key("splash.logo"),
      width: 96,
      height: 96,
      errorBuilder: (BuildContext context, Object _, StackTrace? __) => Icon(
        Icons.travel_explore,
        size: 96,
        color: color,
      ),
    );
  }
}
