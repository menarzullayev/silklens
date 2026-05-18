// Splash — first frame the user sees.
//
// Per Project-Decisions §1 the app name MUST be read from localization /
// remote tenant branding, not hard-coded. We pull `appName` from the
// generated AppLocalizations.

import "dart:async";

import "package:flutter/material.dart";
import "package:flutter_hooks/flutter_hooks.dart";
import "package:go_router/go_router.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/l10n/app_localizations.dart";
import "package:silklens/presentation/router/app_router.dart";

class SplashPage extends HookConsumerWidget {
  const SplashPage({super.key});

  static const Duration _minVisibleDuration = Duration(milliseconds: 1200);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    useEffect(
      () {
        final timer = Timer(_minVisibleDuration, () {
          if (!context.mounted) return;
          // FAZA 2 will check `has_seen_onboarding` here; for now always
          // run the onboarding flow on cold start.
          context.go(AppRoutes.onboarding);
        });
        return timer.cancel;
      },
      const <Object?>[],
    );

    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Scaffold(
      backgroundColor: colorScheme.primary,
      body: SafeArea(
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: <Widget>[
              Icon(
                Icons.travel_explore,
                key: const Key("splash.logo"),
                size: 96,
                color: colorScheme.onPrimary,
              ),
              const SizedBox(height: 24),
              Text(
                l10n?.appName ?? "SilkLens",
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
            ],
          ),
        ),
      ),
    );
  }
}
