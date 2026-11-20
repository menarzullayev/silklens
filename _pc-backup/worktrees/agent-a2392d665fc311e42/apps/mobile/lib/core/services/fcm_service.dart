// FCM push notification service.
// Registers FCM token with backend on init.
//
// Prerequisites (SILK-0139):
//   - firebase_core, firebase_messaging, flutter_local_notifications in
//     pubspec.yaml.
//   - android/app/google-services.json placed (gitignored) from Firebase Console
//   - ios/Runner/GoogleService-Info.plist placed (gitignored) from Firebase Console
//   - Google Services plugin applied in android/app/build.gradle and
//     android/build.gradle (project-level)
//
// Wiring: see lib/core/push/fcm_service.dart for setup steps. This file is
// the production-ready Riverpod-integrated implementation.

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/data/api/clients/api_client_provider.dart';

/// Background message handler — must be a top-level function.
/// Called when a FCM message arrives while the app is in background/terminated.
@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  // Firebase must be initialized again in the background isolate.
  await Firebase.initializeApp();
  debugPrint('[FCM] Background message: ${message.messageId}');
}

class FcmService {
  FcmService(this._ref);
  final Ref _ref;

  final FlutterLocalNotificationsPlugin _localNotifications = FlutterLocalNotificationsPlugin();

  static const _androidChannel = AndroidNotificationChannel(
    'silklens_default',
    'SilkLens Notifications',
    description: 'General notifications from SilkLens',
    importance: Importance.high,
  );

  /// Initializes Firebase, requests permission, configures local notifications,
  /// registers the FCM token with the backend, and wires up refresh listeners.
  ///
  /// Returns the FCM token string, or null if permission was denied or
  /// Firebase initialization failed (e.g., google-services.json missing).
  Future<String?> init() async {
    try {
      await Firebase.initializeApp();
    } catch (e) {
      debugPrint('[FCM] Firebase initialization failed: $e');
      debugPrint(
        '[FCM] Ensure google-services.json (Android) / GoogleService-Info.plist '
        '(iOS) are placed in the correct directories. See SILK-0139.',
      );
      return null;
    }

    // Register background message handler.
    FirebaseMessaging.onBackgroundMessage(firebaseMessagingBackgroundHandler);

    final messaging = FirebaseMessaging.instance;

    // Request permission (iOS requires explicit prompt; Android 13+ also does).
    final settings = await messaging.requestPermission();
    if (settings.authorizationStatus == AuthorizationStatus.denied) {
      debugPrint('[FCM] Permission denied by user.');
      return null;
    }

    // Initialize flutter_local_notifications for foreground display.
    const initSettings = InitializationSettings(
      android: AndroidInitializationSettings('@mipmap/ic_launcher'),
      iOS: DarwinInitializationSettings(),
    );
    await _localNotifications.initialize(initSettings);

    // Create the Android notification channel.
    await _localNotifications
        .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(_androidChannel);

    // Listen for messages arriving while the app is in the foreground.
    FirebaseMessaging.onMessage.listen(_handleForegroundMessage);

    // Retrieve the current FCM token and register it with the backend.
    final token = await messaging.getToken();
    if (token != null) {
      await _registerToken(token);
    }

    // Re-register whenever FCM rotates the token.
    messaging.onTokenRefresh.listen(_registerToken);

    debugPrint('[FCM] Initialized. Token: ${token?.substring(0, 12)}...');
    return token;
  }

  Future<void> _registerToken(String token) async {
    try {
      final platform = defaultTargetPlatform == TargetPlatform.iOS ? 'ios' : 'android';
      // Use the token itself as a stable installation ID — it is unique per
      // app install and rotates with the token, keeping the backend in sync.
      await _ref.read(silkLensApiClientProvider).registerPushDevice(
            platform: platform,
            installationId: token,
            fcmToken: token,
          );
      debugPrint('[FCM] Token registered with backend.');
    } catch (e) {
      // Non-fatal: push will simply not work until the next token refresh.
      debugPrint('[FCM] Failed to register token with backend: $e');
    }
  }

  Future<void> _handleForegroundMessage(RemoteMessage message) async {
    final notification = message.notification;
    if (notification == null) return;

    await _localNotifications.show(
      // Use remainder to stay within the int32 range for notification IDs.
      DateTime.now().millisecondsSinceEpoch.remainder(100000),
      notification.title,
      notification.body,
      NotificationDetails(
        android: AndroidNotificationDetails(
          _androidChannel.id,
          _androidChannel.name,
          channelDescription: _androidChannel.description,
          importance: Importance.high,
          priority: Priority.high,
        ),
        iOS: const DarwinNotificationDetails(),
      ),
      payload: message.data['action_url']?.toString(),
    );
  }
}

/// Riverpod provider for [FcmService].
///
/// Consume via `ref.read(fcmServiceProvider)` in initState of the root widget
/// or in a startup provider. Do not call [FcmService.init] from widget builds.
final fcmServiceProvider = Provider<FcmService>(
  FcmService.new,
  name: 'fcmServiceProvider',
);
