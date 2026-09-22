// Repository interface — domain side. Implementations live in
// `lib/data/repositories/`.
//
// Mirrors the FastAPI `GET /v1/heritage` filter surface so we can pass
// search / kind / country / status / pagination straight through.

import 'package:silklens/core/utils/result.dart';
import 'package:silklens/domain/heritage/entities/heritage.dart';

abstract interface class HeritageRepository {
  /// List heritage matching [filters]. Should hit the live API and best-
  /// effort write the result into the offline L1 cache.
  Future<Result<HeritagePage>> list(HeritageFilters filters);

  /// Fetch a single heritage object by its public id (pub_id).
  Future<Result<Heritage>> getByPubId(String pubId);

  /// Pin / unpin a heritage object in the local Isar L2 ("Saved") bundle.
  /// These never round-trip; presentation layer uses them for offline access.
  Future<Result<void>> saveLocally(Heritage heritage);
  Future<Result<void>> removeLocally(String pubId);

  /// Streams the currently-saved set, watched live.
  Stream<List<Heritage>> watchSaved();

  /// One-shot snapshot of saved items (for tests / non-stream callers).
  Future<List<Heritage>> savedSnapshot();

  /// True when the heritage object is in the saved set.
  Future<bool> isSaved(String pubId);
}
