// Onboarding — 3-slide PageView. Project-Decisions §22 variant 'D'
// personalization: the third slide collects the user's preferred language
// and gives them a "Sign in" / "Skip" CTA.

import "package:flutter/material.dart";
import "package:flutter_hooks/flutter_hooks.dart";
import "package:go_router/go_router.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/l10n/app_localizations.dart";
import "package:silklens/presentation/providers/locale_provider.dart";
import "package:silklens/presentation/router/app_router.dart";

class OnboardingPage extends HookConsumerWidget {
  const OnboardingPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final pageController = usePageController();
    final pageIndex = useState<int>(0);

    final slides = <_OnboardingSlide>[
      _OnboardingSlide(
        icon: Icons.camera_alt_outlined,
        title: l10n?.onboardingSlide1Title ?? "",
        body: l10n?.onboardingSlide1Body ?? "",
      ),
      _OnboardingSlide(
        icon: Icons.record_voice_over_outlined,
        title: l10n?.onboardingSlide2Title ?? "",
        body: l10n?.onboardingSlide2Body ?? "",
      ),
      _OnboardingSlide(
        icon: Icons.travel_explore,
        title: l10n?.onboardingSlide3Title ?? "",
        body: l10n?.onboardingSlide3Body ?? "",
      ),
    ];

    final isLast = pageIndex.value == slides.length - 1;

    return Scaffold(
      body: SafeArea(
        child: Column(
          children: <Widget>[
            Align(
              alignment: Alignment.centerRight,
              child: TextButton(
                key: const Key("onboarding.skip"),
                onPressed: () => context.go(AppRoutes.homeDiscover),
                child: Text(l10n?.onboardingSkip ?? ""),
              ),
            ),
            Expanded(
              child: PageView.builder(
                key: const Key("onboarding.page_view"),
                controller: pageController,
                onPageChanged: (int idx) => pageIndex.value = idx,
                itemCount: slides.length,
                itemBuilder: (BuildContext context, int idx) =>
                    _SlideView(slide: slides[idx]),
              ),
            ),
            if (isLast)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 24),
                child: _LanguagePicker(
                  current: Localizations.localeOf(context).languageCode,
                  onChanged: (String code) async {
                    await ref
                        .read(activeLocaleProvider.notifier)
                        .setLanguageCode(code);
                  },
                ),
              ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: <Widget>[
                  for (int i = 0; i < slides.length; i++)
                    Container(
                      key: Key("onboarding.dot.$i"),
                      width: 8,
                      height: 8,
                      margin: const EdgeInsets.symmetric(horizontal: 4),
                      decoration: BoxDecoration(
                        color: i == pageIndex.value
                            ? theme.colorScheme.primary
                            : theme.colorScheme.onSurface.withValues(alpha: 0.2),
                        shape: BoxShape.circle,
                      ),
                    ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(24, 0, 24, 16),
              child: Column(
                children: <Widget>[
                  FilledButton(
                    key: const Key("onboarding.cta_primary"),
                    onPressed: () {
                      if (isLast) {
                        context.go(AppRoutes.authSignIn);
                      } else {
                        pageController.nextPage(
                          duration: const Duration(milliseconds: 320),
                          curve: Curves.easeInOut,
                        );
                      }
                    },
                    child: Padding(
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      child: Text(
                        isLast
                            ? (l10n?.onboardingSignIn ?? "")
                            : (l10n?.onboardingNext ?? ""),
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  TextButton(
                    key: const Key("onboarding.cta_skip"),
                    onPressed: () => context.go(AppRoutes.homeDiscover),
                    child: Text(l10n?.onboardingSkip ?? ""),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _OnboardingSlide {
  const _OnboardingSlide({
    required this.icon,
    required this.title,
    required this.body,
  });

  final IconData icon;
  final String title;
  final String body;
}

class _SlideView extends StatelessWidget {
  const _SlideView({required this.slide});

  final _OnboardingSlide slide;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: <Widget>[
          Icon(slide.icon, size: 120, color: theme.colorScheme.primary),
          const SizedBox(height: 32),
          Text(
            slide.title,
            textAlign: TextAlign.center,
            style: theme.textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 16),
          Text(
            slide.body,
            textAlign: TextAlign.center,
            style: theme.textTheme.bodyLarge?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ],
      ),
    );
  }
}

class _LanguagePicker extends StatelessWidget {
  const _LanguagePicker({required this.current, required this.onChanged});

  final String current;
  final Future<void> Function(String) onChanged;

  static const List<({String code, String label})> _options =
      <({String code, String label})>[
    (code: "en", label: "English"),
    (code: "uz", label: "O‘zbekcha"),
    (code: "ru", label: "Русский"),
    (code: "zh", label: "中文"),
  ];

  @override
  Widget build(BuildContext context) {
    return Wrap(
      key: const Key("onboarding.language_picker"),
      spacing: 8,
      alignment: WrapAlignment.center,
      children: <Widget>[
        for (final option in _options)
          ChoiceChip(
            key: Key("onboarding.lang.${option.code}"),
            selected: option.code == current,
            label: Text(option.label),
            onSelected: (bool selected) {
              if (selected) onChanged(option.code);
            },
          ),
      ],
    );
  }
}
