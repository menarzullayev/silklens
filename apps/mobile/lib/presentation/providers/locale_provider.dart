// Active app locale.
//
// Project-Decisions §8 ships four ARB files: uz, en, ru, zh — and new
// languages drop in via admin remote config (NLLB-200 auto-translates the
// missing keys). The chosen language is persisted in SharedPreferences so
// it survives app restarts.
//
// Resolution order on cold-start:
//   1. SharedPreferences (user-overridden)
//   2. Device locale (if supported)
//   3. `.env` DEFAULT_LOCALE
//   4. "en"

import 'package:flutter/widgets.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:silklens/core/env/app_environment.dart';
import 'package:silklens/core/logging/app_logger.dart';

const Set<String> kSupportedLanguageCodes = <String>{'en', 'uz', 'ru', 'zh'};
const String _prefsKey = 'sl.locale.language_code';

class LocaleController extends Notifier<Locale> {
  @override
  Locale build() {
    final env = ref.watch(appEnvironmentProvider);
    // Synchronously return the .env default; an async bootstrap below may
    // overwrite it once prefs and the device locale are resolved.
    Future<void>.microtask(_bootstrap);
    return _parse(env.defaultLocale);
  }

  Future<void> _bootstrap() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final stored = prefs.getString(_prefsKey);
      if (stored != null && kSupportedLanguageCodes.contains(stored)) {
        state = Locale(stored);
        return;
      }
      final platform = WidgetsBinding.instance.platformDispatcher.locale;
      if (kSupportedLanguageCodes.contains(platform.languageCode)) {
        state = Locale(platform.languageCode);
      }
    } on Exception catch (error, stackTrace) {
      AppLogger.instance.w(
        'Locale bootstrap failed',
        error: error,
        stackTrace: stackTrace,
      );
    }
  }

  Future<void> set(Locale locale) async {
    state = locale;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_prefsKey, locale.languageCode);
  }

  Future<void> setLanguageCode(String code) async {
    if (!kSupportedLanguageCodes.contains(code)) return;
    await set(Locale(code));
  }

  Locale _parse(String code) {
    final normalized = code.toLowerCase();
    final parts = normalized.split(RegExp('[_-]'));
    final language = parts.first;
    if (!kSupportedLanguageCodes.contains(language)) return const Locale('en');
    return parts.length >= 2 ? Locale(language, parts[1]) : Locale(language);
  }
}

final NotifierProvider<LocaleController, Locale> activeLocaleProvider =
    NotifierProvider<LocaleController, Locale>(
  LocaleController.new,
  name: 'activeLocaleProvider',
);
