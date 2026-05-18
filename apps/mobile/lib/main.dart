// SilkLens mobile entry point.
//
// Boot order:
//   1. Bind Flutter widgets.
//   2. Load .env (assets/.env, copied from .env.example by the developer).
//   3. Initialize Isar (offline DB — Master Architecture §8).
//   4. Initialize Sentry (Project-Decisions §40 — crash reporting).
//   5. Wrap the app in ProviderScope so every layer below can read providers.
//
// We intentionally keep this file thin. Anything beyond boot orchestration
// belongs in `app/` (composition root) or one of the layers under `lib/`.

import "dart:async";

import "package:flutter/foundation.dart";
import "package:flutter/widgets.dart";
import "package:flutter_dotenv/flutter_dotenv.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:sentry_flutter/sentry_flutter.dart";
import "package:silklens/app/app.dart";
import "package:silklens/core/env/app_environment.dart";
import "package:silklens/core/logging/app_logger.dart";
import "package:silklens/data/local/isar_database.dart";

Future<void> main() async {
  // `runZonedGuarded` makes sure any async error inside the app surfaces to
  // Sentry. We use it instead of a top-level try/catch because async work
  // initiated by the framework would otherwise escape.
  await runZonedGuarded<Future<void>>(
    () async {
      WidgetsFlutterBinding.ensureInitialized();

      // 1. Environment. Missing .env is non-fatal in debug builds.
      try {
        await dotenv.load(fileName: "assets/.env");
      } on Exception catch (error, stackTrace) {
        AppLogger.instance.w(
          "assets/.env not found; falling back to defaults.",
          error: error,
          stackTrace: stackTrace,
        );
      }
      final env = AppEnvironment.fromDotEnv(dotenv.env);

      // 2. Offline DB. Schemas are wired here so the rest of the tree can
      // resolve the Isar instance via DI.
      final isar = await IsarDatabase.open();

      // 3. Sentry — only initialize when we actually have a DSN.
      FlutterError.onError = (FlutterErrorDetails details) {
        AppLogger.instance.e(
          "FlutterError",
          error: details.exception,
          stackTrace: details.stack,
        );
        if (env.sentryDsn.isNotEmpty) {
          unawaited(Sentry.captureException(details.exception, stackTrace: details.stack));
        }
      };

      Future<void> runApp() async {
        runAppWithProviders(
          environment: env,
          isarDatabase: isar,
        );
      }

      if (env.sentryDsn.isEmpty) {
        await runApp();
      } else {
        await SentryFlutter.init(
          (SentryFlutterOptions options) {
            options
              ..dsn = env.sentryDsn
              ..environment = env.appEnv
              ..tracesSampleRate = kReleaseMode ? 0.1 : 1.0
              ..attachStacktrace = true
              ..debug = !kReleaseMode;
          },
          appRunner: runApp,
        );
      }
    },
    (Object error, StackTrace stackTrace) {
      AppLogger.instance.e(
        "Uncaught zone error",
        error: error,
        stackTrace: stackTrace,
      );
      unawaited(Sentry.captureException(error, stackTrace: stackTrace));
    },
  );
}

/// Mounts [SilkLensApp] inside a [ProviderScope] with the resolved
/// environment & DB overrides. Extracted for clarity and so widget tests can
/// reuse it with a stub environment.
void runAppWithProviders({
  required AppEnvironment environment,
  required IsarDatabase isarDatabase,
}) {
  runApp(
    ProviderScope(
      overrides: <Override>[
        appEnvironmentProvider.overrideWithValue(environment),
        isarDatabaseProvider.overrideWithValue(isarDatabase),
      ],
      child: const SilkLensApp(),
    ),
  );
}
