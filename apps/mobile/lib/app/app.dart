// Composition root for SilkLens.
//
// `SilkLensApp` wires together:
//   - GoRouter (presentation/router/app_router.dart)
//   - dynamic ThemeData (presentation/theme/theme_provider.dart)
//   - dynamic Locale (presentation/providers/locale_provider.dart)
//   - generated AppLocalizations (lib/l10n)
//
// Anything that hard-codes a string, color, or route belongs in `presentation/`
// — never here. This file is intentionally short.

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/l10n/app_localizations.dart';
import 'package:silklens/presentation/providers/locale_provider.dart';
import 'package:silklens/presentation/router/app_router.dart';
import 'package:silklens/presentation/theme/theme_provider.dart';
import 'package:silklens/presentation/widgets/offline_banner.dart';

class SilkLensApp extends ConsumerWidget {
  const SilkLensApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(appRouterProvider);
    final themePack = ref.watch(activeThemePackProvider);
    final locale = ref.watch(activeLocaleProvider);

    return MaterialApp.router(
      // The visible name is read from AppLocalizations at runtime via
      // splash / branding widgets. The string below is only ever surfaced
      // in OS-level task switchers before the first frame paints, so we
      // keep it as the canonical product name. Per Project-Decisions §1
      // anything user-facing must come from localization / remote config.
      onGenerateTitle: (BuildContext context) => AppLocalizations.of(context).appName,
      debugShowCheckedModeBanner: false,
      theme: themePack.light,
      darkTheme: themePack.dark,
      themeMode: themePack.mode,
      locale: locale,
      supportedLocales: AppLocalizations.supportedLocales,
      localizationsDelegates: const <LocalizationsDelegate<Object?>>[
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ],
      builder: (context, child) => OfflineBanner(child: child!),
      routerConfig: router,
    );
  }
}
