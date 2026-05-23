// Firebase Cloud Messaging service for SilkLens push notifications.
//
// Setup checklist (SILK-0139):
//
// 1. Add to pubspec.yaml dependencies:
//      firebase_core: ^3.0.0
//      firebase_messaging: ^15.0.0
//      flutter_local_notifications: ^17.0.0
//    Then run: flutter pub get
//
// 2. Android: Download google-services.json from Firebase Console
//    (Project Settings > Your Apps > Android) and place it at:
//      android/app/google-services.json   (already in .gitignore)
//    Add to android/build.gradle (project-level):
//      classpath 'com.google.gms:google-services:4.4.2'
//    Add to android/app/build.gradle (app-level) plugins block:
//      id 'com.google.gms.google-services'
//
// 3. iOS: Download GoogleService-Info.plist from Firebase Console and place at:
//      ios/Runner/GoogleService-Info.plist  (already in .gitignore)
//    Add to ios/Runner/Info.plist:
//      <key>FirebaseAppDelegateProxyEnabled</key><string>NO</string>
//
// 4. Initialize Firebase in main.dart before runApp:
//      await Firebase.initializeApp();
//    Then call:
//      await FcmService().init(onTokenReceived: (token) async {
//        await FcmService.registerToken(
//          token: token,
//          apiClient: container.read(silkLensApiClientProvider),
//        );
//      });
//
// 5. Register background handler (top-level function, not inside a class):
//    @pragma('vm:entry-point')
//    Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage msg) async {
//      await Firebase.initializeApp();
//      // handle message
//    }
//    Call in main.dart: FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);
//
// SILK-0139

// ignore_for_file: avoid_print

import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/data/api/clients/silklens_api_client.dart';

// ignore: avoid_classes_with_only_static_members
class FcmService {
  const FcmService();

  // ---------------------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------------------

  /// Initialize Firebase Messaging and request notification permission.
  ///
  /// Call this from main.dart after [Firebase.initializeApp()].
  /// The [onTokenReceived] callback fires immediately with the current token
  /// and again whenever FCM rotates the token.
  Future<void> init({
    required void Function(String token) onTokenReceived,
  }) async {
    // TODO(SILK-0139): Uncomment when firebase_messaging is added to pubspec.
    //
    // final messaging = FirebaseMessaging.instance;
    //
    // final settings = await messaging.requestPermission(
    //   alert: true,
    //   badge: true,
    //   sound: true,
    // );
    // debugPrint('[FCM] Permission status: ${settings.authorizationStatus}');
    //
    // final token = await messaging.getToken();
    // if (token != null) onTokenReceived(token);
    //
    // messaging.onTokenRefresh.listen(onTokenReceived);

    if (kDebugMode) {
      debugPrint(
        '[FCM] Firebase not configured. '
        'Follow the checklist in lib/core/push/fcm_service.dart (SILK-0139).',
      );
    }
  }

  // ---------------------------------------------------------------------------
  // Foreground message handling
  // ---------------------------------------------------------------------------

  /// Subscribe to messages that arrive while the app is in the foreground.
  ///
  /// Typically you want to display a local notification here so the user
  /// sees it even though the app is open.
  void handleForegroundMessages() {
    // TODO(SILK-0139): Uncomment when firebase_messaging is added.
    //
    // FirebaseMessaging.onMessage.listen((RemoteMessage message) {
    //   final notification = message.notification;
    //   if (notification != null) {
    //     _showLocalNotification(
    //       title: notification.title ?? '',
    //       body:  notification.body  ?? '',
    //       data:  message.data,
    //     );
    //   }
    // });
  }

  // ---------------------------------------------------------------------------
  // Token registration
  // ---------------------------------------------------------------------------

  /// Register the FCM [token] with the SilkLens backend so the server can
  /// address push notifications to this installation.
  ///
  /// Errors are swallowed and logged — a failed registration must not crash
  /// the boot sequence.
  static Future<void> registerToken({
    required String token,
    required SilkLensApiClient apiClient,
  }) async {
    try {
      await apiClient.registerPushDevice(
        platform: _platformSlug,
        installationId: token,
        fcmToken: token,
      );
      if (kDebugMode) {
        debugPrint('[FCM] Token registered with backend.');
      }
    } on Exception catch (e) {
      // Non-fatal: push will simply not work until the next token refresh.
      debugPrint('[FCM] Token registration failed: $e');
    }
  }

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  static String get _platformSlug {
    if (Platform.isIOS) return 'ios';
    if (Platform.isAndroid) return 'android';
    return 'unknown';
  }
}

// ---------------------------------------------------------------------------
// Riverpod provider
// ---------------------------------------------------------------------------

/// Provides the singleton [FcmService] instance.
///
/// Consume via `ref.read(fcmServiceProvider)` — typically called once from
/// a startup provider, not from Widget build methods.
final fcmServiceProvider = Provider<FcmService>((_) => const FcmService());
