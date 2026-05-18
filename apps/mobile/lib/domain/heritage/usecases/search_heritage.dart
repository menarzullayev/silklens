// `SearchHeritage` is callable directly (instance is a function-like value).
// One file = one use case keeps responsibility crystal-clear.

import "package:silklens/core/utils/result.dart";
import "package:silklens/domain/heritage/entities/heritage.dart";
import "package:silklens/domain/heritage/repositories/heritage_repository.dart";

class SearchHeritage {
  const SearchHeritage(this._repository);

  final HeritageRepository _repository;

  Future<Result<HeritagePage>> call({
    String? query,
    String? kindSlug,
    String? countryCode,
    int limit = 20,
    int offset = 0,
  }) =>
      _repository.list(
        HeritageFilters(
          search: query,
          kindSlug: kindSlug,
          countryCode: countryCode,
          limit: limit,
          offset: offset,
        ),
      );
}
