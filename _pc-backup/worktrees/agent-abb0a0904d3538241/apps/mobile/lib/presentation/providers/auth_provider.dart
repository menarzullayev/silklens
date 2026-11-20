import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/core/error/failures.dart';
import 'package:silklens/data/repositories/auth_repository_impl.dart'
    as auth_impl;
import 'package:silklens/domain/identity/entities/auth_session.dart';
import 'package:silklens/domain/identity/entities/auth_user.dart';
import 'package:silklens/domain/identity/repositories/auth_repository.dart';

// ---------------------------------------------------------------------------
// AuthState — sealed class hierarchy
// ---------------------------------------------------------------------------

sealed class AuthState {
  const AuthState();
}

class AuthInitial extends AuthState {
  const AuthInitial();
}

class AuthLoading extends AuthState {
  const AuthLoading();
}

class AuthAuthenticated extends AuthState {
  const AuthAuthenticated(this.session);
  final AuthSession session;
}

class AuthUnauthenticated extends AuthState {
  const AuthUnauthenticated();
}

/// Backwards-compat alias — existing code that used [AuthAnonymous] still
/// compiles without changes.
typedef AuthAnonymous = AuthUnauthenticated;

class AuthError extends AuthState {
  const AuthError(this.message);
  final String message;
}

// ---------------------------------------------------------------------------
// Repository provider
// ---------------------------------------------------------------------------

/// Real AuthRepositoryImpl — wired to SilkLens API + SecureTokenStorage.
final authRepositoryProvider = auth_impl.authRepositoryProvider;

// ---------------------------------------------------------------------------
// AuthNotifier
// ---------------------------------------------------------------------------

class AuthNotifier extends Notifier<AuthState> {
  @override
  AuthState build() {
    // Kick off the silent session-restore check immediately.
    _init();
    return const AuthInitial();
  }

  AuthRepository get _repo => ref.read(authRepositoryProvider);

  // -------------------------------------------------------------------------
  // Cold-boot: restore persisted session from secure storage
  // -------------------------------------------------------------------------

  Future<void> _init() async {
    final session = await _repo.currentSession();
    state = session != null
        ? AuthAuthenticated(session)
        : const AuthUnauthenticated();
  }

  // -------------------------------------------------------------------------
  // Public API
  // -------------------------------------------------------------------------

  Future<bool> login(String email, String password) async {
    state = const AuthLoading();
    final result = await _repo.signIn(email: email, password: password);
    return result.fold(
      onSuccess: (session) {
        state = AuthAuthenticated(session);
        return true;
      },
      onFailure: (failure) {
        state = AuthError(_failureMessage(failure));
        return false;
      },
    );
  }

  Future<bool> register(String email, String password) async {
    state = const AuthLoading();
    final result = await _repo.signUp(email: email, password: password);
    return result.fold(
      onSuccess: (session) {
        state = AuthAuthenticated(session);
        return true;
      },
      onFailure: (failure) {
        state = AuthError(_failureMessage(failure));
        return false;
      },
    );
  }

  /// Sign in with Google access token.
  /// Flutter obtains [accessToken] via `google_sign_in` package,
  /// then backend verifies it with Google tokeninfo API.
  Future<bool> loginWithGoogle(String accessToken) async {
    state = const AuthLoading();
    final result = await _repo.signInWithGoogle(accessToken);
    return result.fold(
      onSuccess: (session) {
        state = AuthAuthenticated(session);
        return true;
      },
      onFailure: (failure) {
        state = AuthError(_failureMessage(failure));
        return false;
      },
    );
  }

  Future<bool> verifyEmail({
    required String email,
    required String code,
  }) async {
    final result = await _repo.verifyEmail(email: email, code: code);
    return result.fold(
      onSuccess: (verified) => verified,
      onFailure: (_) => false,
    );
  }

  Future<bool> resendVerification({required String email}) async {
    final result = await _repo.resendVerification(email: email);
    return result.fold(
      onSuccess: (sent) => sent,
      onFailure: (_) => false,
    );
  }

  Future<void> logout() async {
    await _repo.signOut();
    state = const AuthUnauthenticated();
  }

  /// Dismiss an error and return to [AuthUnauthenticated] so the UI can
  /// re-enable the form without a full navigation reset.
  void clearError() {
    if (state is AuthError) {
      state = const AuthUnauthenticated();
    }
  }

  // -------------------------------------------------------------------------
  // Convenience getters
  // -------------------------------------------------------------------------

  bool get isAuthenticated => state is AuthAuthenticated;

  AuthSession? get session =>
      state is AuthAuthenticated ? (state as AuthAuthenticated).session : null;

  // -------------------------------------------------------------------------
  // Error message localisation (Uzbek)
  // -------------------------------------------------------------------------

  String _failureMessage(Failure failure) {
    if (failure is AuthFailure) {
      return failure.message.isNotEmpty
          ? failure.message
          : "Email yoki parol noto'g'ri";
    }
    if (failure is ValidationFailure) {
      final fields = failure.fieldErrors;
      if (fields.isNotEmpty) return fields.values.first;
      return "Noto'g'ri ma'lumot";
    }
    if (failure is ServerFailure) {
      return switch (failure.statusCode) {
        401 => "Email yoki parol noto'g'ri",
        403 => 'Kirish taqiqlangan',
        422 => "Noto'g'ri ma'lumot",
        423 => 'Hisob vaqtincha bloklangan',
        429 => "Juda ko'p urinish. Biroz kuting.",
        500 => 'Server xatosi',
        _ => failure.message.isNotEmpty ? failure.message : 'Server xatosi',
      };
    }
    if (failure is NetworkFailure) {
      return 'Ulanish xatosi. Internet aloqasini tekshiring.';
    }
    return failure.message.isNotEmpty ? failure.message : 'Xato yuz berdi';
  }
}

// ---------------------------------------------------------------------------
// Providers
// ---------------------------------------------------------------------------

final authProvider =
    NotifierProvider<AuthNotifier, AuthState>(AuthNotifier.new);

/// Convenience alias used by route guards and legacy call-sites.
final authNotifierProvider = authProvider;

final currentUserProvider = Provider<AuthUser?>((ref) {
  final s = ref.watch(authProvider);
  return s is AuthAuthenticated ? s.session.user : null;
});

final isAuthenticatedProvider = Provider<bool>(
  (ref) => ref.watch(authProvider) is AuthAuthenticated,
);

