// Concrete [BrandingRepository] backed by the retrofit API client and the
// Isar offline cache. Cold-start order:
//   1. Read from Isar (fast path — no network).
//   2. Kick off a background fetch; on success, write back to Isar so
//      subsequent boots get the latest.
//
// The provider exposes both the synchronous cached value (initial paint)
// and an async fetch that refreshes the cache.

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
import "package:silklens/data/api/dto/branding_dto.dart";
import "package:silklens/data/local/isar_database.dart";
import "package:silklens/data/local/schemas/cached_branding.dart";
import "package:silklens/domain/branding/entities/branding.dart";
import "package:silklens/domain/branding/repositories/branding_repository.dart";

class BrandingRepositoryImpl implements BrandingRepository {
  BrandingRepositoryImpl({
    required SilkLensApiClient api,
    required IsarDatabase isar,
  })  : _api = api,
        _isar = isar;

  final SilkLensApiClient _api;
  final IsarDatabase _isar;

  @override
  Future<Result<Branding>> fetch({String? tenantSlug}) async {
    try {
      final dto = await _api.getBranding(tenantSlug: tenantSlug);
      final entity = _toEntity(dto);
      await _writeCache(entity);
      return Success<Branding>(entity);
    } on ApiException catch (e, st) {
      final cached = await this.cached(tenantSlug: tenantSlug);
      if (cached != null) return Success<Branding>(cached);
      return FailureResult<Branding>(
        ServerFailure(e.message,
            statusCode: e.statusCode, cause: e, stackTrace: st),
      );
    } on DioException catch (e, st) {
      final cached = await this.cached(tenantSlug: tenantSlug);
      if (cached != null) return Success<Branding>(cached);
      return FailureResult<Branding>(
        NetworkFailure(e.message ?? "Dio error", cause: e, stackTrace: st),
      );
    }
  }

  @override
  Future<Branding?> cached({String? tenantSlug}) async {
    final row = tenantSlug != null
        ? await _isar.instance.cachedBrandings
            .where()
            .tenantSlugEqualTo(tenantSlug)
            .findFirst()
        : await _isar.instance.cachedBrandings.where().findFirst();
    if (row == null) return null;
    return _fromCache(row);
  }

  Future<void> _writeCache(Branding b) async {
    final row = CachedBranding(
      tenantSlug: b.tenantSlug,
      appNameJson: json.encode(b.appName),
      logoUrl: b.logoUrl,
      logoDarkUrl: b.logoDarkUrl,
      primaryColorHex: b.primaryColorHex,
      accentColorHex: b.accentColorHex,
      splashUrl: b.splashUrl,
      fontFamily: b.fontFamily,
      themeModeDefault: b.themeModeDefault,
      extraJson: json.encode(b.extra),
      fetchedAt: DateTime.now().toUtc(),
    );
    await _isar.instance.writeTxn(() async {
      await _isar.instance.cachedBrandings.putByTenantSlug(row);
    });
  }

  Branding _toEntity(BrandingDto dto) => Branding(
        tenantSlug: dto.tenantSlug,
        appName: dto.appName,
        logoUrl: dto.logoUrl,
        logoDarkUrl: dto.logoDarkUrl,
        primaryColorHex: dto.primaryColor,
        accentColorHex: dto.accentColor,
        splashUrl: dto.splashUrl,
        fontFamily: dto.fontFamily,
        themeModeDefault: dto.themeModeDefault,
        extra: dto.extra,
      );

  Branding _fromCache(CachedBranding row) => Branding(
        tenantSlug: row.tenantSlug,
        appName: _decodeStringMap(row.appNameJson),
        logoUrl: row.logoUrl,
        logoDarkUrl: row.logoDarkUrl,
        primaryColorHex: row.primaryColorHex,
        accentColorHex: row.accentColorHex,
        splashUrl: row.splashUrl,
        fontFamily: row.fontFamily,
        themeModeDefault: row.themeModeDefault,
        extra: _decodeAnyMap(row.extraJson),
      );

  Map<String, String> _decodeStringMap(String s) {
    if (s.isEmpty) return const <String, String>{};
    final decoded = json.decode(s);
    if (decoded is! Map) return const <String, String>{};
    return decoded.map(
      (Object? k, Object? v) => MapEntry<String, String>("$k", "$v"),
    );
  }

  Map<String, Object?> _decodeAnyMap(String s) {
    if (s.isEmpty) return const <String, Object?>{};
    final decoded = json.decode(s);
    if (decoded is! Map) return const <String, Object?>{};
    return decoded.map(
      (Object? k, Object? v) => MapEntry<String, Object?>("$k", v),
    );
  }
}

final Provider<BrandingRepository> brandingRepositoryProvider =
    Provider<BrandingRepository>(
  (Ref ref) => BrandingRepositoryImpl(
    api: ref.watch(silkLensApiClientProvider),
    isar: ref.watch(isarDatabaseProvider),
  ),
  name: "brandingRepositoryProvider",
);
