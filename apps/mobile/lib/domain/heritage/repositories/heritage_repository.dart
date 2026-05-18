// Repository interface — domain side. Implementations live in
// `lib/data/repositories/`.

import "package:silklens/core/utils/result.dart";
import "package:silklens/domain/heritage/entities/heritage.dart";

abstract interface class HeritageRepository {
  Future<Result<List<Heritage>>> search({
    String? query,
    int page = 1,
    int pageSize = 20,
  });

  Future<Result<Heritage>> getById(String id);

  /// Stream of cached items for offline-first list rendering.
  Stream<List<Heritage>> watchCached();
}
