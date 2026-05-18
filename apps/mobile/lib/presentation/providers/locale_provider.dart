// Active app locale.
//
// Project-Decisions §8 ships four ARB files: uz, en, ru, zh — and new
// languages drop in via admin remote config (NLLB-200 auto-translates the
// missing keys). For now the locale is user-controlled with the .env
// default as the initial value.

import "package:flutter/widgets.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/core/env/app_environment.dart";

class LocaleController extends Notifier<Locale> {
  @override
  Locale build() {
    final env = ref.watch(appEnvironmentProvider);
    return _parse(env.defaultLocale);
  }

  void set(Locale locale) => state = locale;

  void setLanguageCode(String code) => state = _parse(code);

  Locale _parse(String code) {
    final parts = code.split(RegExp("[_-]"));
    return parts.length >= 2 ? Locale(parts[0], parts[1]) : Locale(parts[0]);
  }
}

final NotifierProvider<LocaleController, Locale> activeLocaleProvider =
    NotifierProvider<LocaleController, Locale>(
  LocaleController.new,
  name: "activeLocaleProvider",
);
