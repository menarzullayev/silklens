// Wraps flutter_secure_storage so the rest of the app sees a tiny,
// substitutable interface. Tests pass an in-memory fake.
//
// We persist three things:
//   * access_token — short-lived JWT (~15 min)
//   * refresh_token — long-lived rotating token
//   * user_snapshot — JSON dump of the AuthUser, so cold-boot can render
//     a logged-in shell before /auth/me has resolved.

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';

abstract class SecureTokenStorage {
  Future<void> writeAccessToken(String token);
  Future<String?> readAccessToken();
  Future<void> writeRefreshToken(String token);
  Future<String?> readRefreshToken();
  Future<void> writeUserSnapshot(String json);
  Future<String?> readUserSnapshot();
  Future<void> clear();
}

class FlutterSecureTokenStorage implements SecureTokenStorage {
  FlutterSecureTokenStorage(this._storage);

  static const _accessKey = 'sl.auth.access_token';
  static const _refreshKey = 'sl.auth.refresh_token';
  static const _userKey = 'sl.auth.user_snapshot';

  final FlutterSecureStorage _storage;

  @override
  Future<String?> readAccessToken() => _storage.read(key: _accessKey);

  @override
  Future<String?> readRefreshToken() => _storage.read(key: _refreshKey);

  @override
  Future<void> writeAccessToken(String token) => _storage.write(key: _accessKey, value: token);

  @override
  Future<void> writeRefreshToken(String token) => _storage.write(key: _refreshKey, value: token);

  @override
  Future<String?> readUserSnapshot() => _storage.read(key: _userKey);

  @override
  Future<void> writeUserSnapshot(String json) => _storage.write(key: _userKey, value: json);

  @override
  Future<void> clear() async {
    await _storage.delete(key: _accessKey);
    await _storage.delete(key: _refreshKey);
    await _storage.delete(key: _userKey);
  }
}

/// In-memory fake — for widget tests and the integration_test boot path
/// where Keychain / KeyStore aren't available.
class InMemorySecureTokenStorage implements SecureTokenStorage {
  String? _access;
  String? _refresh;
  String? _user;

  @override
  Future<String?> readAccessToken() async => _access;

  @override
  Future<String?> readRefreshToken() async => _refresh;

  @override
  Future<String?> readUserSnapshot() async => _user;

  @override
  Future<void> writeAccessToken(String token) async => _access = token;

  @override
  Future<void> writeRefreshToken(String token) async => _refresh = token;

  @override
  Future<void> writeUserSnapshot(String json) async => _user = json;

  @override
  Future<void> clear() async {
    _access = null;
    _refresh = null;
    _user = null;
  }
}

final Provider<SecureTokenStorage> secureTokenStorageProvider = Provider<SecureTokenStorage>(
  (Ref ref) => FlutterSecureTokenStorage(
    const FlutterSecureStorage(
      aOptions: AndroidOptions(encryptedSharedPreferences: true),
    ),
  ),
  name: 'secureTokenStorageProvider',
);
