// Riverpod auth controller — the single source of truth for the current
// session at the presentation layer. The router redirect rule, the splash
// page silent refresh, the profile sign-out button — all read this.
//
// Clean-Architecture: this file lives in `presentation/` and depends only
// on the `domain/identity/...` protocol — never on the concrete
// implementation. Wiring of [authRepositoryProvider] happens in `data/`.

import "package:flutter/foundation.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:meta/meta.dart";
import "package:silklens/core/error/failures.dart";
import "package:silklens/core/utils/result.dart";
import "package:silklens/data/repositories/auth_repository_impl.dart"
    show authRepositoryProvider;
import "package:silklens/domain/identity/entities/auth_session.dart";
import "package:silklens/domain/identity/entities/auth_user.dart";
import "package:silklens/domain/identity/repositories/auth_repository.dart";

/// Discriminated union of the three states the UI cares about. We model it
/// as a sealed class so go_router's redirect can do exhaustive switching.
@immutable
sealed class AuthState {
  const AuthState();

  const factory AuthState.loading() = AuthLoading;
  const factory AuthState.anonymous() = AuthAnonymous;
  const factory AuthState.authenticated(AuthSession session) = AuthAuthenticated;

  bool get isAuthenticated => this is AuthAuthenticated;
  bool get isAnonymous => this is AuthAnonymous;
  bool get isLoading => this is AuthLoading;

  AuthSession? get session => switch (this) {
        AuthAuthenticated(:final session) => session,
        _ => null,
      };

  AuthUser? get user => session?.user;
}

class AuthLoading extends AuthState {
  const AuthLoading();
}

class AuthAnonymous extends AuthState {
  const AuthAnonymous();
}

class AuthAuthenticated extends AuthState {
  const AuthAuthenticated(this.session);
  final AuthSession session;
}

/// Notifier that owns [AuthState]. Persists across restarts via the secure
/// storage backing the underlying [AuthRepository].
class AuthNotifier extends Notifier<AuthState> {
  @override
  AuthState build() {
    // Kick off a non-blocking bootstrap. The router redirect waits on the
    // [bootstrapped] future once before deciding what to render.
    _bootstrap();
    return const AuthState.loading();
  }

  AuthRepository get _repo => ref.read(authRepositoryProvider);

  Future<void> _bootstrap() async {
    final cached = await _repo.currentSession();
    if (cached == null) {
      state = const AuthState.anonymous();
      return;
    }
    // Try a silent refresh to validate the session. The repo writes the
    // fresh tokens to secure storage on success.
    final refreshed = await _repo.refresh();
    refreshed.fold<void>(
      onSuccess: (AuthSession session) =>
          state = AuthState.authenticated(session),
      onFailure: (Failure _) async {
        // The refresh failed — clear local session.
        await _repo.signOut();
        state = const AuthState.anonymous();
      },
    );
  }

  /// Sign-in. Returns [null] on success or the [Failure] on error so the
  /// sign-in page can render a localized error message.
  Future<Failure?> signIn({
    required String email,
    required String password,
  }) async {
    final previous = state;
    state = const AuthState.loading();
    final result = await _repo.signIn(email: email, password: password);
    return result.fold<Failure?>(
      onSuccess: (AuthSession session) {
        state = AuthState.authenticated(session);
        return null;
      },
      onFailure: (Failure f) {
        state = previous is AuthAuthenticated ? previous : const AuthState.anonymous();
        return f;
      },
    );
  }

  Future<Failure?> signUp({
    required String email,
    required String password,
    String? displayName,
    String? preferredLocale,
  }) async {
    final previous = state;
    state = const AuthState.loading();
    final result = await _repo.signUp(
      email: email,
      password: password,
      displayName: displayName,
      preferredLocale: preferredLocale,
    );
    return result.fold<Failure?>(
      onSuccess: (AuthSession session) {
        state = AuthState.authenticated(session);
        return null;
      },
      onFailure: (Failure f) {
        state = previous is AuthAuthenticated ? previous : const AuthState.anonymous();
        return f;
      },
    );
  }

  Future<void> signOut() async {
    await _repo.signOut();
    state = const AuthState.anonymous();
  }

  /// Manually force the state into anonymous (used by the auth interceptor
  /// when a refresh family is revoked).
  void markAnonymous() {
    state = const AuthState.anonymous();
  }

  @visibleForTesting
  void debugSet(AuthState newState) => state = newState;
}

final NotifierProvider<AuthNotifier, AuthState> authNotifierProvider =
    NotifierProvider<AuthNotifier, AuthState>(
  AuthNotifier.new,
  name: "authNotifierProvider",
);

/// Convenience selector for code that only needs the user — avoids
/// rebuilds when the tokens rotate but the user stays the same.
final Provider<AuthUser?> currentUserProvider = Provider<AuthUser?>(
  (Ref ref) {
    final state = ref.watch(authNotifierProvider);
    return state.user;
  },
  name: "currentUserProvider",
);

final Provider<bool> isAuthenticatedProvider = Provider<bool>(
  (Ref ref) => ref.watch(authNotifierProvider).isAuthenticated,
  name: "isAuthenticatedProvider",
);
