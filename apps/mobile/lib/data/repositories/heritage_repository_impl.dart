import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/data/api/clients/api_client_provider.dart';
import 'package:silklens/data/api/clients/silklens_api_client.dart';
import 'package:silklens/domain/heritage/entities/heritage.dart';

class HeritageRepositoryImpl {
  const HeritageRepositoryImpl(this._client);
  final SilkLensApiClient _client;

  Future<HeritagePage> listHeritage({
    String? kindSlug,
    String? countryCode,
    String? status,
    String? search,
    int limit = 20,
    int offset = 0,
  }) async {
    final dto = await _client.listHeritage(
      kind: kindSlug,
      country: countryCode,
      status: status,
      search: search,
      limit: limit,
      offset: offset,
    );
    return HeritagePage(
      items: dto.items
          .map(
            (d) => Heritage(
              id: d.id,
              pubId: d.pubId,
              kindSlug: d.kindSlug,
              name: d.name,
              summaryMd: d.summaryMd,
              descriptionMd: d.descriptionMd,
              tags: d.tags,
              status: d.status,
              countryCode: d.countryCode,
              latitude: d.latitude,
              longitude: d.longitude,
              periodStartYear: d.periodStartYear,
              heroMediaId: d.heroMediaId,
              confidenceScore: d.confidenceScore,
              revision: d.revision,
            ),
          )
          .toList(),
      total: dto.total,
      limit: dto.limit,
      offset: dto.offset,
    );
  }

  Future<Heritage> getHeritage(String pubId) async {
    final d = await _client.getHeritage(pubId);
    return Heritage(
      id: d.id,
      pubId: d.pubId,
      kindSlug: d.kindSlug,
      name: d.name,
      summaryMd: d.summaryMd,
      descriptionMd: d.descriptionMd,
      tags: d.tags,
      status: d.status,
      countryCode: d.countryCode,
      latitude: d.latitude,
      longitude: d.longitude,
      periodStartYear: d.periodStartYear,
      heroMediaId: d.heroMediaId,
      confidenceScore: d.confidenceScore,
      revision: d.revision,
    );
  }
}

final heritageRepositoryProvider = Provider<HeritageRepositoryImpl>((ref) {
  return HeritageRepositoryImpl(ref.watch(silkLensApiClientProvider));
});
