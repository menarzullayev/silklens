import "package:silklens/core/utils/result.dart";
import "package:silklens/domain/identity/entities/auth_session.dart";
import "package:silklens/domain/identity/repositories/identity_repository.dart";

class LoginWithEmail {
  const LoginWithEmail(this._repo);

  final IdentityRepository _repo;

  Future<Result<AuthSession>> call({
    required String email,
    required String password,
  }) =>
      _repo.loginWithEmail(email: email, password: password);
}
