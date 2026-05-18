// Implementation of the domain-side [HeritageRepository] using the
// retrofit-generated API client + Isar offline cache.
//
// This file lives in `data/` because it depends on adapter SDKs (Dio, Isar).
// The domain never imports this — only the composition root wires it up.

import "dart:async";
import "dart:convert";

import "package:dio/dio.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:isar/isar.dart";
import "package:silklens/core/error/exceptions.dart";
import "package:silklens/core/error/failures.dart";
import "package:silklens/core/utils/result.dart";
import "package:silklens/data/api/clients/api_client_provider.dart";
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
  Future<Result<HeritagePage>> list(HeritageFilters filters) async {
    try {
      final dto = await _api.listHeritage(
        kind: filters.kindSlug,
        country: filters.countryCode,
        status: filters.status,
        search: filters.search,
        limit: filters.limit,
        offset: filters.offset,
      );
      final entities = dto.items.map(_toEntity).toList(growable: false);
      unawaited(_cache(dto.items, saved: false));
      return Success<HeritagePage>(
        HeritagePage(
          items: entities,
          total: dto.total,
          limit: dto.limit,
          offset: dto.offset,
        ),
      );
    } on ApiException catch (e, st) {
      return FailureResult<HeritagePage>(
        ServerFailure(e.message,
            statusCode: e.statusCode, cause: e, stackTrace: st),
      );
    } on NetworkException catch (e, st) {
      return FailureResult<HeritagePage>(
        NetworkFailure(e.message, cause: e, stackTrace: st),
      );
    } on DioException catch (e, st) {
      return FailureResult<HeritagePage>(
        NetworkFailure(e.message ?? "Dio error", cause: e, stackTrace: st),
      );
    }
  }

  @override
  Future<Result<Heritage>> getByPubId(String pubId) async {
    try {
      final dto = await _api.getHeritage(pubId);
      unawaited(_cache(<HeritageDto>[dto], saved: false));
      return Success<Heritage>(_toEntity(dto));
    } on ApiException catch (e, st) {
      return FailureResult<Heritage>(
        ServerFailure(e.message,
            statusCode: e.statusCode, cause: e, stackTrace: st),
      );
    } on DioException catch (e, st) {
      return FailureResult<Heritage>(
        NetworkFailure(e.message ?? "Dio error", cause: e, stackTrace: st),
      );
    }
  }

  @override
  Future<Result<void>> saveLocally(Heritage heritage) async {
    try {
      await _isar.instance.writeTxn(() async {
        await _isar.instance.cachedHeritages.putByHeritageId(
          _toCacheRow(heritage, saved: true),
        );
      });
      return const Success<void>(null);
    } on Exception catch (e, st) {
      return FailureResult<void>(
        CacheFailure(e.toString(), cause: e, stackTrace: st),
      );
    }
  }

  @override
  Future<Result<void>> removeLocally(String pubId) async {
    try {
      await _isar.instance.writeTxn(() async {
        final existing = await _isar.instance.cachedHeritages
            .where()
            .heritageIdEqualTo(pubId)
            .findFirst();
        if (existing != null) {
          existing.saved = false;
          await _isar.instance.cachedHeritages.put(existing);
        }
      });
      return const Success<void>(null);
    } on Exception catch (e, st) {
      return FailureResult<void>(
        CacheFailure(e.toString(), cause: e, stackTrace: st),
      );
    }
  }

  @override
  Stream<List<Heritage>> watchSaved() => _isar.instance.cachedHeritages
      .filter()
      .savedEqualTo(true)
      .watch(fireImmediately: true)
      .map((List<CachedHeritage> rows) =>
          rows.map(_fromCache).toList(growable: false));

  @override
  Future<List<Heritage>> savedSnapshot() async {
    final rows = await _isar.instance.cachedHeritages
        .filter()
        .savedEqualTo(true)
        .findAll();
    return rows.map(_fromCache).toList(growable: false);
  }

  @override
  Future<bool> isSaved(String pubId) async {
    final row = await _isar.instance.cachedHeritages
        .where()
        .heritageIdEqualTo(pubId)
        .findFirst();
    return row?.saved ?? false;
  }

  Future<void> _cache(List<HeritageDto> dtos, {required bool saved}) async {
    if (dtos.isEmpty) return;
    final now = DateTime.now().toUtc();
    await _isar.instance.writeTxn(() async {
      for (final HeritageDto dto in dtos) {
        final existing = await _isar.instance.cachedHeritages
            .where()
            .heritageIdEqualTo(dto.pubId)
            .findFirst();
        final row = _toCacheRowFromDto(dto,
            saved: saved || (existing?.saved ?? false), cachedAt: now);
        if (existing != null) row.id = existing.id;
        await _isar.instance.cachedHeritages.put(row);
      }
    });
  }

  Heritage _toEntity(HeritageDto dto) => Heritage(
        id: dto.id,
        pubId: dto.pubId,
        kindSlug: dto.kindSlug,
        name: dto.name,
        summaryMd: dto.summaryMd,
        descriptionMd: dto.descriptionMd,
        tags: dto.tags,
        status: dto.status,
        countryCode: dto.countryCode,
        adminPath: dto.adminPath,
        latitude: dto.latitude,
        longitude: dto.longitude,
        periodStartYear: dto.periodStartYear,
        periodEndYear: dto.periodEndYear,
        unescoInscriptionYear: dto.unescoInscriptionYear,
        heroMediaUrl: dto.heroMediaUrl,
        confidenceScore: dto.confidenceScore,
        revision: dto.revision,
        mediaUrls: dto.mediaUrls,
      );

  Heritage _fromCache(CachedHeritage row) => Heritage(
        id: row.heritageId,
        pubId: row.heritageId,
        kindSlug: row.kindSlug,
        name: _decodeMap(row.nameJson),
        summaryMd: _decodeMap(row.summaryMdJson),
        descriptionMd: _decodeMap(row.descriptionMdJson),
        tags: _decodeList(row.tagsJson),
        status: row.status,
        countryCode: row.countryCode,
        latitude: row.latitude,
        longitude: row.longitude,
        periodStartYear: row.periodStartYear,
        periodEndYear: row.periodEndYear,
        unescoInscriptionYear: row.unescoInscriptionYear,
        heroMediaUrl: row.heroMediaUrl,
        revision: row.revision,
      );

  CachedHeritage _toCacheRow(Heritage e, {required bool saved}) =>
      CachedHeritage(
        heritageId: e.pubId,
        kindSlug: e.kindSlug,
        nameJson: json.encode(e.name),
        summaryMdJson: json.encode(e.summaryMd),
        descriptionMdJson: json.encode(e.descriptionMd),
        tagsJson: json.encode(e.tags),
        status: e.status,
        countryCode: e.countryCode,
        latitude: e.latitude,
        longitude: e.longitude,
        periodStartYear: e.periodStartYear,
        periodEndYear: e.periodEndYear,
        unescoInscriptionYear: e.unescoInscriptionYear,
        heroMediaUrl: e.heroMediaUrl,
        revision: e.revision,
        saved: saved,
        cachedAt: DateTime.now().toUtc(),
      );

  CachedHeritage _toCacheRowFromDto(HeritageDto dto,
          {required bool saved, required DateTime cachedAt}) =>
      CachedHeritage(
        heritageId: dto.pubId,
        kindSlug: dto.kindSlug,
        nameJson: json.encode(dto.name),
        summaryMdJson: json.encode(dto.summaryMd),
        descriptionMdJson: json.encode(dto.descriptionMd),
        tagsJson: json.encode(dto.tags),
        status: dto.status,
        countryCode: dto.countryCode,
        latitude: dto.latitude,
        longitude: dto.longitude,
        periodStartYear: dto.periodStartYear,
        periodEndYear: dto.periodEndYear,
        unescoInscriptionYear: dto.unescoInscriptionYear,
        heroMediaUrl: dto.heroMediaUrl,
        revision: dto.revision,
        saved: saved,
        cachedAt: cachedAt,
      );

  Map<String, String> _decodeMap(String? s) {
    if (s == null || s.isEmpty) return const <String, String>{};
    final decoded = json.decode(s);
    if (decoded is! Map) return const <String, String>{};
    return decoded.map(
      (Object? k, Object? v) => MapEntry<String, String>("$k", "$v"),
    );
  }

  List<String> _decodeList(String? s) {
    if (s == null || s.isEmpty) return const <String>[];
    final decoded = json.decode(s);
    if (decoded is! List) return const <String>[];
    return decoded.map((Object? v) => "$v").toList(growable: false);
  }
}

final Provider<HeritageRepository> heritageRepositoryProvider =
    Provider<HeritageRepository>(
  (Ref ref) => HeritageRepositoryImpl(
    api: ref.watch(silkLensApiClientProvider),
    isar: ref.watch(isarDatabaseProvider),
  ),
  name: "heritageRepositoryProvider",
);
