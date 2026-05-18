// Implementation of the domain-side [HeritageRepository] using the
// retrofit-generated API client + Isar offline cache.
//
// This file lives in `data/` because it depends on adapter SDKs (Dio, Isar).
// The domain never imports this — only the composition root wires it up.

import "dart:async";

import "package:dio/dio.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:isar/isar.dart";
import "package:silklens/core/error/exceptions.dart";
import "package:silklens/core/error/failures.dart";
import "package:silklens/core/utils/result.dart";
import "package:silklens/data/api/clients/silklens_api_client.dart";
import "package:silklens/data/api/dto/heritage_dto.dart";
import "package:silklens/data/local/isar_database.dart";
import "package:silklens/data/local/schemas/cached_heritage.dart";
import "package:silklens/domain/heritage/entities/heritage.dart";
import "package:silklens/domain/heritage/repositories/heritage_repository.dart";

class HeritageRepositoryImpl implements HeritageRepository {
  HeritageRepositoryImpl({
    required SilkLensApiClient api,
    required IsarDatabase isar,
  })  : _api = api,
        _isar = isar;

  final SilkLensApiClient _api;
  final IsarDatabase _isar;

  @override
  Future<Result<List<Heritage>>> search({
    String? query,
    int page = 1,
    int pageSize = 20,
  }) async {
    try {
      final dtos = await _api.listHeritage(
        query: query,
        page: page,
        pageSize: pageSize,
      );
      final entities = dtos.map(_toEntity).toList(growable: false);

      // Best-effort cache write; don't fail the call if Isar hiccups.
      unawaited(_cache(dtos));

      return Success<List<Heritage>>(entities);
    } on ApiException catch (e, st) {
      return FailureResult<List<Heritage>>(
        ServerFailure(e.message, statusCode: e.statusCode, cause: e, stackTrace: st),
      );
    } on NetworkException catch (e, st) {
      return FailureResult<List<Heritage>>(
        NetworkFailure(e.message, cause: e, stackTrace: st),
      );
    } on DioException catch (e, st) {
      return FailureResult<List<Heritage>>(
        NetworkFailure(e.message ?? "Dio error", cause: e, stackTrace: st),
      );
    }
  }

  @override
  Future<Result<Heritage>> getById(String id) async {
    try {
      final dto = await _api.getHeritage(id);
      unawaited(_cache(<HeritageDto>[dto]));
      return Success<Heritage>(_toEntity(dto));
    } on ApiException catch (e, st) {
      return FailureResult<Heritage>(
        ServerFailure(e.message, statusCode: e.statusCode, cause: e, stackTrace: st),
      );
    } on DioException catch (e, st) {
      return FailureResult<Heritage>(
        NetworkFailure(e.message ?? "Dio error", cause: e, stackTrace: st),
      );
    }
  }

  @override
  Stream<List<Heritage>> watchCached() => _isar.instance.cachedHeritages
      .where()
      .watch(fireImmediately: true)
      .map((List<CachedHeritage> rows) => rows.map(_fromCache).toList(growable: false));

  Future<void> _cache(List<HeritageDto> dtos) async {
    if (dtos.isEmpty) return;
    final now = DateTime.now().toUtc();
    final rows = dtos
        .map((HeritageDto d) => CachedHeritage(
              heritageId: d.id,
              name: d.name,
              description: d.description,
              latitude: d.latitude,
              longitude: d.longitude,
              regionId: d.regionId,
              languageCode: d.languageCode,
              cachedAt: now,
            ))
        .toList();
    await _isar.instance.writeTxn(() async {
      await _isar.instance.cachedHeritages.putAll(rows);
    });
  }

  Heritage _toEntity(HeritageDto dto) => Heritage(
        id: dto.id,
        name: dto.name,
        description: dto.description,
        latitude: dto.latitude,
        longitude: dto.longitude,
        mediaUrls: dto.mediaUrls,
        regionId: dto.regionId,
        languageCode: dto.languageCode,
      );

  Heritage _fromCache(CachedHeritage row) => Heritage(
        id: row.heritageId,
        name: row.name,
        description: row.description,
        latitude: row.latitude,
        longitude: row.longitude,
        regionId: row.regionId,
        languageCode: row.languageCode,
      );
}

final Provider<SilkLensApiClient> silkLensApiClientProvider =
    Provider<SilkLensApiClient>(
  (Ref ref) {
    throw UnimplementedError(
      "silkLensApiClientProvider is wired in the composition root once "
      "build_runner has produced silklens_api_client.g.dart.",
    );
  },
  name: "silkLensApiClientProvider",
);

final Provider<HeritageRepository> heritageRepositoryProvider =
    Provider<HeritageRepository>(
  (Ref ref) => HeritageRepositoryImpl(
    api: ref.watch(silkLensApiClientProvider),
    isar: ref.watch(isarDatabaseProvider),
  ),
  name: "heritageRepositoryProvider",
);
