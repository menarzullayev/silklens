// Shared scaffolding for widget tests.
//
// Wraps the widget under test in a MaterialApp with our localisation
// delegates so AppLocalizations.of(context) works inside test pumps.

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/l10n/app_localizations.dart';

Widget wrapForWidgetTest(
  Widget child, {
  List<Override> overrides = const <Override>[],
  Locale locale = const Locale('en'),
}) {
  return ProviderScope(
    overrides: overrides,
    child: MaterialApp(
      locale: locale,
      supportedLocales: AppLocalizations.supportedLocales,
      localizationsDelegates: const <LocalizationsDelegate<Object?>>[
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ],
      home: Scaffold(body: child),
    ),
  );
}
