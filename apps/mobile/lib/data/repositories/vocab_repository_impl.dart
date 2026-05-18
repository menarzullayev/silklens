// Concrete [VocabRepository] backed by the retrofit client.
//
// Lightweight: vocabularies are read-only catalogs, so we don't cache them
// in Isar — Riverpod's in-memory caching is enough.

import "package:dio/dio.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/core/error/exceptions.dart";
import "package:silklens/core/error/failures.dart";
import "package:silklens/core/utils/result.dart";
import "package:silklens/data/api/clients/api_client_provider.dart";
import "package:silklens/data/api/clients/silklens_api_client.dart";
import "package:silklens/data/api/dto/vocab_dto.dart";
import "package:silklens/domain/vocab/entities/vocab_term.dart";
import "package:silklens/domain/vocab/repositories/vocab_repository.dart";

class VocabRepositoryImpl implements VocabRepository {
  VocabRepositoryImpl({required SilkLensApiClient api}) : _api = api;

  final SilkLensApiClient _api;

  @override
  Future<Result<List<VocabTerm>>> list(String vocabularySlug) async {
    try {
      final dto = await _api.getVocabulary(vocabularySlug);
      final entities = dto.items
          .map(
            (VocabTermDto t) => VocabTerm(
              slug: t.slug,
              displayName: t.displayName,
              parentSlug: t.parentSlug,
              sortOrder: t.sortOrder,
            ),
          )
          .toList(growable: false);
      return Success<List<VocabTerm>>(entities);
    } on ApiException catch (e, st) {
      return FailureResult<List<VocabTerm>>(
        ServerFailure(e.message,
            statusCode: e.statusCode, cause: e, stackTrace: st),
      );
    } on DioException catch (e, st) {
      return FailureResult<List<VocabTerm>>(
        NetworkFailure(e.message ?? "Dio error", cause: e, stackTrace: st),
      );
    }
  }
}

final Provider<VocabRepository> vocabRepositoryProvider =
    Provider<VocabRepository>(
  (Ref ref) =>
      VocabRepositoryImpl(api: ref.watch(silkLensApiClientProvider)),
  name: "vocabRepositoryProvider",
);
