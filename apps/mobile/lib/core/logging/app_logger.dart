// Single Logger instance for the app.
//
// Keep the API tiny so swapping the underlying package later (e.g. a
// custom Sentry-aware sink) is a one-file change.

import 'package:flutter/foundation.dart';
import 'package:logger/logger.dart';

class AppLogger {
  AppLogger._();

  static final Logger instance = Logger(
    filter: kDebugMode ? DevelopmentFilter() : ProductionFilter(),
    printer: PrettyPrinter(
      methodCount: 0,
      lineLength: 100,
      printEmojis: false,
      dateTimeFormat: DateTimeFormat.onlyTimeAndSinceStart,
    ),
  );
}
