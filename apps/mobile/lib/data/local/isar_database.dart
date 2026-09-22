/// Stub local database — isar replaced with in-memory storage for FAZA 1
/// real-device testing. Full offline persistence lands in FAZA 6+ with
/// hive_flutter or isar v4.
library;

import 'dart:collection';

import 'package:flutter/foundation.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';

/// Singleton in-memory store used until a proper local DB is wired.
class LocalDatabase {
  LocalDatabase._();
  static final LocalDatabase _instance = LocalDatabase._();
  static LocalDatabase get instance => _instance;

  final Map<String, dynamic> _store = HashMap<String, dynamic>();

  void put(String key, dynamic value) => _store[key] = value;
  T? get<T>(String key) => _store[key] as T?;
  void delete(String key) => _store.remove(key);
  void clear() => _store.clear();

  Future<void> init() async {
    if (kDebugMode) debugPrint('LocalDatabase: using in-memory stub');
  }

  Future<void> close() async {}
}

/// Provider so repositories can access the stub DB via Riverpod DI.
final localDatabaseProvider = Provider<LocalDatabase>((ref) {
  return LocalDatabase.instance;
});
