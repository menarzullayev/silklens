import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/data/repositories/heritage_repository_impl.dart';
import 'package:silklens/domain/heritage/entities/heritage.dart';

class HeritageListState {
  const HeritageListState({
    this.items = const [],
    this.total = 0,
    this.isLoading = false,
    this.isLoadingMore = false,
    this.error,
    this.filters = const HeritageFilters(),
  });
  final List<Heritage> items;
  final int total;
  final bool isLoading;
  final bool isLoadingMore;
  final String? error;
  final HeritageFilters filters;

  bool get hasMore => items.length < total;
  bool get isEmpty => items.isEmpty && !isLoading;

  HeritageListState copyWith({
    List<Heritage>? items,
    int? total,
    bool? isLoading,
    bool? isLoadingMore,
    String? error,
    bool clearError = false,
    HeritageFilters? filters,
  }) =>
      HeritageListState(
        items: items ?? this.items,
        total: total ?? this.total,
        isLoading: isLoading ?? this.isLoading,
        isLoadingMore: isLoadingMore ?? this.isLoadingMore,
        error: clearError ? null : (error ?? this.error),
        filters: filters ?? this.filters,
      );
}

class HeritageListNotifier extends Notifier<HeritageListState> {
  static const _pageSize = 20;

  @override
  HeritageListState build() {
    Future.microtask(refresh);
    return const HeritageListState(isLoading: true);
  }

  Future<void> refresh() async {
    state = state.copyWith(
      isLoading: true,
      clearError: true,
      items: [],
      total: 0,
    );
    try {
      final repo = ref.read(heritageRepositoryProvider);
      final page = await repo.listHeritage(
        kindSlug: state.filters.kindSlug,
        countryCode: state.filters.countryCode,
        status: state.filters.status,
        search: state.filters.search,
        limit: _pageSize,
        offset: 0,
      );
      state = state.copyWith(
        items: page.items,
        total: page.total,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<void> loadMore() async {
    if (!state.hasMore || state.isLoadingMore || state.isLoading) return;
    state = state.copyWith(isLoadingMore: true);
    try {
      final repo = ref.read(heritageRepositoryProvider);
      final page = await repo.listHeritage(
        kindSlug: state.filters.kindSlug,
        countryCode: state.filters.countryCode,
        status: state.filters.status,
        search: state.filters.search,
        limit: _pageSize,
        offset: state.items.length,
      );
      state = state.copyWith(
        items: [...state.items, ...page.items],
        total: page.total,
        isLoadingMore: false,
      );
    } catch (e) {
      state = state.copyWith(isLoadingMore: false, error: e.toString());
    }
  }

  void updateFilter(HeritageFilters filters) {
    state = state.copyWith(filters: filters);
    refresh();
  }

  void setKindFilter(String? kindSlug) {
    state = state.copyWith(
      filters: state.filters.copyWith(kindSlug: kindSlug),
    );
    refresh();
  }

  void setSearch(String? query) {
    state = state.copyWith(
      filters: state.filters.copyWith(
        search: (query == null || query.isEmpty) ? null : query,
      ),
    );
    refresh();
  }

  void setCountryFilter(String? countryCode) {
    state = state.copyWith(
      filters: state.filters.copyWith(countryCode: countryCode),
    );
    refresh();
  }
}

final heritageListProvider =
    NotifierProvider<HeritageListNotifier, HeritageListState>(
  HeritageListNotifier.new,
);
