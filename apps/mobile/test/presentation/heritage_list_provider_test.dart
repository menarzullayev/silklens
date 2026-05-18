// Paginated heritage list provider — mocks the HeritageRepository so we
// only exercise the state machine.

import "package:flutter_test/flutter_test.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:mocktail/mocktail.dart";
import "package:silklens/core/utils/result.dart";
import "package:silklens/data/repositories/heritage_repository_impl.dart"
    show heritageRepositoryProvider;
import "package:silklens/domain/heritage/entities/heritage.dart";
import "package:silklens/domain/heritage/repositories/heritage_repository.dart";
import "package:silklens/presentation/providers/heritage_list_provider.dart";

class _MockHeritageRepository extends Mock implements HeritageRepository {}

Heritage _heritage(String pubId) => Heritage(
      id: pubId,
      pubId: pubId,
      kindSlug: "monument",
      name: <String, String>{"en": "Item $pubId"},
    );

HeritagePage _page(List<String> ids, {int total = 100, int offset = 0}) =>
    HeritagePage(
      items: ids.map(_heritage).toList(growable: false),
      total: total,
      limit: 20,
      offset: offset,
    );

void main() {
  setUpAll(() {
    registerFallbackValue(const HeritageFilters());
  });

  group("HeritageListNotifier", () {
    late _MockHeritageRepository repo;
    late ProviderContainer container;

    setUp(() {
      repo = _MockHeritageRepository();
      container = ProviderContainer(
        overrides: <Override>[
          heritageRepositoryProvider.overrideWithValue(repo),
        ],
      );
      addTearDown(container.dispose);
    });

    test("refresh loads first page", () async {
      when(() => repo.list(any())).thenAnswer(
        (_) async => Success<HeritagePage>(_page(<String>["a", "b", "c"])),
      );
      // Initial build triggers refresh()
      container.read(heritageListProvider);
      await Future<void>.delayed(Duration.zero);
      await Future<void>.delayed(Duration.zero);
      await Future<void>.delayed(Duration.zero);

      final state = container.read(heritageListProvider);
      expect(state.items.length, 3);
      expect(state.total, 100);
      expect(state.isLoading, isFalse);
      expect(state.hasMore, isTrue);
    });

    test("loadMore appends the next page", () async {
      when(() => repo.list(any())).thenAnswer(
        (_) async => Success<HeritagePage>(_page(<String>["a", "b"], total: 5)),
      );
      container.read(heritageListProvider);
      await Future<void>.delayed(Duration.zero);
      await Future<void>.delayed(Duration.zero);
      await Future<void>.delayed(Duration.zero);

      when(() => repo.list(any())).thenAnswer(
        (_) async =>
            Success<HeritagePage>(_page(<String>["c", "d"], total: 5, offset: 2)),
      );

      await container.read(heritageListProvider.notifier).loadMore();

      final state = container.read(heritageListProvider);
      expect(state.items.map((Heritage h) => h.pubId).toList(),
          <String>["a", "b", "c", "d"]);
    });

    test("setSearch debounces and re-fetches with the new search term",
        () async {
      when(() => repo.list(any())).thenAnswer(
        (_) async => Success<HeritagePage>(_page(<String>["x"])),
      );
      container.read(heritageListProvider);
      await Future<void>.delayed(Duration.zero);
      await Future<void>.delayed(Duration.zero);

      container.read(heritageListProvider.notifier).setSearch("registan");
      await Future<void>.delayed(Duration.zero);
      await Future<void>.delayed(Duration.zero);

      final state = container.read(heritageListProvider);
      expect(state.filters.search, "registan");
      verify(() => repo.list(any())).called(greaterThanOrEqualTo(2));
    });

    test("setKind updates the kindSlug filter", () async {
      when(() => repo.list(any())).thenAnswer(
        (_) async => Success<HeritagePage>(_page(<String>["x"])),
      );
      container.read(heritageListProvider);
      await Future<void>.delayed(Duration.zero);
      await Future<void>.delayed(Duration.zero);

      container.read(heritageListProvider.notifier).setKind("mosque");
      await Future<void>.delayed(Duration.zero);

      final state = container.read(heritageListProvider);
      expect(state.filters.kindSlug, "mosque");
    });
  });
}
