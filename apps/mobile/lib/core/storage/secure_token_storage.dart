// Wraps flutter_secure_storage so the rest of the app sees a tiny,
// substitutable interface. Tests pass an in-memory fake.

import "package:flutter_secure_storage/flutter_secure_storage.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";

abstract class SecureTokenStorage {
  Future<void> writeAccessToken(String token);
  Future<String?> readAccessToken();
  Future<void> writeRefreshToken(String token);
  Future<String?> readRefreshToken();
  Future<void> clear();
}

class FlutterSecureTokenStorage implements SecureTokenStorage {
  FlutterSecureTokenStorage(this._storage);

  static const _accessKey = "sl.auth.access_token";
  static const _refreshKey = "sl.auth.refresh_token";

  final FlutterSecureStorage _storage;

  @override
  Future<String?> readAccessToken() => _storage.read(key: _accessKey);

  @override
  Future<String?> readRefreshToken() => _storage.read(key: _refreshKey);

  @override
  Future<void> writeAccessToken(String token) =>
      _storage.write(key: _accessKey, value: token);

  @override
  Future<void> writeRefreshToken(String token) =>
      _storage.write(key: _refreshKey, value: token);

  @override
  Future<void> clear() async {
    await _storage.delete(key: _accessKey);
    await _storage.delete(key: _refreshKey);
  }
}

final Provider<SecureTokenStorage> secureTokenStorageProvider =
    Provider<SecureTokenStorage>(
  (Ref ref) => FlutterSecureTokenStorage(
    const FlutterSecureStorage(
      aOptions: AndroidOptions(encryptedSharedPreferences: true),
    ),
  ),
  name: "secureTokenStorageProvider",
);
