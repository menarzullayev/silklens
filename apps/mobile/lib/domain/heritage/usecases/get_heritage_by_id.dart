import "package:silklens/core/utils/result.dart";
import "package:silklens/domain/heritage/entities/heritage.dart";
import "package:silklens/domain/heritage/repositories/heritage_repository.dart";

class GetHeritageById {
  const GetHeritageById(this._repository);

  final HeritageRepository _repository;

  Future<Result<Heritage>> call(String id) => _repository.getById(id);
}
