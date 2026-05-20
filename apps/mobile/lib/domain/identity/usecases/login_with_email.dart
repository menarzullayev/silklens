import 'package:silklens/core/utils/result.dart';
import 'package:silklens/domain/identity/entities/auth_session.dart';
import 'package:silklens/domain/identity/repositories/auth_repository.dart';

class LoginWithEmail {
  const LoginWithEmail(this._repo);

  final AuthRepository _repo;

  Future<Result<AuthSession>> call({
    required String email,
    required String password,
  }) =>
      _repo.signIn(email: email, password: password);
}
