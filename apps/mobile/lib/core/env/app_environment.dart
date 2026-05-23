// Resolved runtime environment for SilkLens mobile.
//
// Loaded from `assets/.env` at boot (see main.dart) and exposed to the rest
// of the app via [appEnvironmentProvider]. We never read from `dotenv` from
// the rest of the tree — pure boundaries.

import 'dart:io' show Platform;

import 'package:flutter/foundation.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';

@immutable
class AppEnvironment {
  const AppEnvironment({
    required this.appName,
    required this.appEnv,
    required this.apiBaseUrl,
    required this.sentryDsn,
    required this.mapboxPublicToken,
    required this.googleMapsApiKeyAndroid,
    required this.googleMapsApiKeyIos,
    required this.onboardingVariant,
    required this.defaultLocale,
  });

  /// Build from a `dotenv` map. Pure — easy to test.
  factory AppEnvironment.fromDotEnv(Map<String, String> env) {
    final override = env['API_BASE_URL_OVERRIDE'] ?? '';
    final apiBaseUrl =
        override.isNotEmpty ? override : _platformDefaultApiBaseUrl(env);

    return AppEnvironment(
      appName: env['APP_NAME'] ?? 'SilkLens',
      appEnv: env['APP_ENV'] ?? 'local',
      apiBaseUrl: apiBaseUrl,
      sentryDsn: env['SENTRY_DSN'] ?? '',
      mapboxPublicToken: env['MAPBOX_PUBLIC_TOKEN'] ?? '',
      googleMapsApiKeyAndroid: env['GOOGLE_MAPS_API_KEY_ANDROID'] ?? '',
      googleMapsApiKeyIos: env['GOOGLE_MAPS_API_KEY_IOS'] ?? '',
      onboardingVariant: env['ONBOARDING_VARIANT'] ?? 'C',
      defaultLocale: env['DEFAULT_LOCALE'] ?? 'uz',
    );
  }

  /// Fallback used when `.env` is missing entirely (e.g. widget tests).
  factory AppEnvironment.fallback() =>
      AppEnvironment.fromDotEnv(const <String, String>{});

  final String appName;
  final String appEnv;
  final String apiBaseUrl;
  final String sentryDsn;
  final String mapboxPublicToken;
  final String googleMapsApiKeyAndroid;
  final String googleMapsApiKeyIos;
  final String onboardingVariant;
  final String defaultLocale;

  bool get isProduction => appEnv == 'production';
  bool get isLocal => appEnv == 'local';

  static String _platformDefaultApiBaseUrl(Map<String, String> env) {
    if (kIsWeb) {
      return env['API_BASE_URL_IOS'] ?? 'http://localhost:8000';
    }
    if (Platform.isAndroid) {
      return env['API_BASE_URL_ANDROID'] ?? 'http://10.0.2.2:8000';
    }
    // iOS, macOS, Linux desktop, Windows desktop.
    return env['API_BASE_URL_IOS'] ?? 'http://localhost:8000';
  }
}

/// Always overridden in `main.dart`. The default keeps widget tests booting
/// without a real `.env` file.
final Provider<AppEnvironment> appEnvironmentProvider =
    Provider<AppEnvironment>(
  (Ref ref) => AppEnvironment.fallback(),
  name: 'appEnvironmentProvider',
);
