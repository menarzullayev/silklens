// Onboarding — placeholder.
//
// Project-Decisions §22 prescribes "Shazam onboarding" (camera-first WOW
// moment). FAZA 2 ships the real flow; today this page is a single
// continue button that drops the user into camera.

import "package:flutter/material.dart";
import "package:go_router/go_router.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/l10n/app_localizations.dart";
import "package:silklens/presentation/router/app_router.dart";

class OnboardingPage extends ConsumerWidget {
  const OnboardingPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);

    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              const Spacer(),
              Icon(
                Icons.camera_alt_outlined,
                size: 96,
                color: theme.colorScheme.primary,
              ),
              const SizedBox(height: 24),
              Text(
                l10n?.onboardingTitle ?? "Discover heritage with your camera",
                textAlign: TextAlign.center,
                style: theme.textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 12),
              Text(
                l10n?.onboardingSubtitle ??
                    "Point at any monument to instantly learn its story.",
                textAlign: TextAlign.center,
                style: theme.textTheme.bodyLarge?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
              const Spacer(),
              FilledButton(
                onPressed: () => context.go(AppRoutes.camera),
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  child: Text(l10n?.onboardingCta ?? "Start exploring"),
                ),
              ),
              const SizedBox(height: 12),
              TextButton(
                onPressed: () => context.go(AppRoutes.camera),
                child: Text(l10n?.onboardingSkip ?? "Skip"),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
