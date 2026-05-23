// SilkLens mobile entry point.
//
// Boot order:
//   1. Bind Flutter widgets.
//   2. Load .env (assets/.env, copied from .env.example by the developer).
//   3. Initialize local DB stub (offline full persistence in FAZA 6+).
//   4. Initialize Sentry (Project-Decisions §40 — crash reporting).
//   5. Wrap the app in ProviderScope.
//
// FCM Push Notifications (SILK-0139):
//   Once firebase_core + firebase_messaging are added to pubspec.yaml and the
//   google-services.json / GoogleService-Info.plist files are placed, wire FCM
//   after step 3 above by adding:
//
//     import 'package:firebase_core/firebase_core.dart';
//     import 'package:silklens/core/push/fcm_service.dart';
//
//     await Firebase.initializeApp();
//     await FcmService().init(
//       onTokenReceived: (token) async {
//         // Register token with backend — container is available here because
//         // runAppWithProviders has not been called yet; use a temporary
//         // ProviderContainer or pass the client directly.
//         await FcmService.registerToken(
//           token: token,
//           apiClient: SilkLensApiClient(Dio()),  // replace with DI
//         );
//       },
//     );
//     FcmService().handleForegroundMessages();
//
//   See lib/core/push/fcm_service.dart for the full setup checklist.

import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
// import 'package:flutter_stripe/flutter_stripe.dart'; // SLK-041
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:sentry_flutter/sentry_flutter.dart';
import 'package:silklens/app/app.dart';
import 'package:silklens/core/env/app_environment.dart';
import 'package:silklens/core/logging/app_logger.dart';
import 'package:silklens/data/local/isar_database.dart';

Future<void> main() async {
  await runZonedGuarded<Future<void>>(
    () async {
      WidgetsFlutterBinding.ensureInitialized();

      // SLK-041: Stripe initialization.
      // Uncomment when STRIPE_PK env var is configured:
      // Stripe.publishableKey =
      //     const String.fromEnvironment('STRIPE_PK', defaultValue: '');

      try {
        await dotenv.load(fileName: 'assets/.env');
      } on Exception catch (error, stackTrace) {
        AppLogger.instance.w(
          'assets/.env not found; falling back to defaults.',
          error: error,
          stackTrace: stackTrace,
        );
      }
      final env = AppEnvironment.fromDotEnv(dotenv.env);

      // Initialize in-memory local DB stub.
      final db = LocalDatabase.instance;
      await db.init();

      FlutterError.onError = (FlutterErrorDetails details) {
        AppLogger.instance.e(
          'FlutterError',
          error: details.exception,
          stackTrace: details.stack,
        );
        if (env.sentryDsn.isNotEmpty) {
          unawaited(Sentry.captureException(details.exception, stackTrace: details.stack));
        }
      };

      Future<void> runApp() async {
        runAppWithProviders(environment: env, localDb: db);
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
      AppLogger.instance.e('Uncaught zone error', error: error, stackTrace: stackTrace);
      unawaited(Sentry.captureException(error, stackTrace: stackTrace));
    },
  );
}

void runAppWithProviders({
  required AppEnvironment environment,
  required LocalDatabase localDb,
}) {
  runApp(
    ProviderScope(
      overrides: <Override>[
        appEnvironmentProvider.overrideWithValue(environment),
      ],
      child: const _FcmInitWrapper(child: SilkLensApp()),
    ),
  );
}

/// Thin ConsumerStatefulWidget wrapper that initialises FCM after the first
/// frame so it never blocks app startup and has access to Riverpod providers.
class _FcmInitWrapper extends ConsumerStatefulWidget {
  const _FcmInitWrapper({required this.child});
  final Widget child;

  @override
  ConsumerState<_FcmInitWrapper> createState() => _FcmInitWrapperState();
}

class _FcmInitWrapperState extends ConsumerState<_FcmInitWrapper> {
  @override
  void initState() {
    super.initState();
    // Run after the first frame so the widget tree is fully mounted.
    // Errors are caught — a failed FCM init must not crash the app.
    Future.microtask(() async {
      try {
        await ref
            .read(fcmServiceProvider)
            .init();
      } catch (e) {
        AppLogger.instance.w('FCM init failed', error: e);
      }
    });
  }

  @override
  Widget build(BuildContext context) => widget.child;
}
