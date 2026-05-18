// Paginated heritage list with search + filter chips.
//
// The notifier owns:
//   * Current filters (search, kind, country)
//   * Loaded items so far
//   * `hasMore` / `nextOffset`
//   * Error / loading transitions per page
//
// The list page calls [setFilters] (resets to first page) and
// [loadMore] (appends the next page). The provider keeps everything in
// memory; reactive cache writes are handled by the repository.

import "package:flutter/foundation.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:meta/meta.dart";
import "package:silklens/core/error/failures.dart";
import "package:silklens/core/logging/app_logger.dart";
import "package:silklens/core/utils/result.dart";
import "package:silklens/data/repositories/heritage_repository_impl.dart"
    show heritageRepositoryProvider;
import "package:silklens/domain/heritage/entities/heritage.dart";

@immutable
class HeritageListState {
  const HeritageListState({
    required this.filters,
    required this.items,
    required this.total,
    required this.isLoading,
    required this.isLoadingMore,
    required this.hasMore,
    this.failure,
  });

  const HeritageListState.initial()
      : filters = const HeritageFilters(),
        items = const <Heritage>[],
        total = 0,
        isLoading = false,
        isLoadingMore = false,
        hasMore = false,
        failure = null;

  final HeritageFilters filters;
  final List<Heritage> items;
  final int total;
  final bool isLoading;
  final bool isLoadingMore;
  final bool hasMore;
  final Failure? failure;

  HeritageListState copyWith({
    HeritageFilters? filters,
    List<Heritage>? items,
    int? total,
    bool? isLoading,
    bool? isLoadingMore,
    bool? hasMore,
    Failure? failure,
    bool clearFailure = false,
  }) =>
      HeritageListState(
        filters: filters ?? this.filters,
        items: items ?? this.items,
        total: total ?? this.total,
        isLoading: isLoading ?? this.isLoading,
        isLoadingMore: isLoadingMore ?? this.isLoadingMore,
        hasMore: hasMore ?? this.hasMore,
        failure: clearFailure ? null : (failure ?? this.failure),
      );
}

class HeritageListNotifier extends Notifier<HeritageListState> {
  static const int _pageSize = 20;

  @override
  HeritageListState build() {
    Future<void>.microtask(refresh);
    return const HeritageListState.initial();
  }

  Future<void> refresh() async {
    state = state.copyWith(isLoading: true, clearFailure: true);
    final filters = state.filters.copyWith(offset: 0, limit: _pageSize);
    final result =
        await ref.read(heritageRepositoryProvider).list(filters);
    state = result.fold<HeritageListState>(
      onSuccess: (HeritagePage page) => state.copyWith(
        items: page.items,
        total: page.total,
        hasMore: page.hasMore,
        isLoading: false,
        clearFailure: true,
      ),
      onFailure: (Failure f) {
        AppLogger.instance
            .w("Heritage list refresh failed: ${f.message}");
        return state.copyWith(isLoading: false, failure: f);
      },
    );
  }

  Future<void> loadMore() async {
    if (state.isLoading || state.isLoadingMore || !state.hasMore) return;
    state = state.copyWith(isLoadingMore: true, clearFailure: true);
    final filters =
        state.filters.copyWith(offset: state.items.length, limit: _pageSize);
    final result =
        await ref.read(heritageRepositoryProvider).list(filters);
    state = result.fold<HeritageListState>(
      onSuccess: (HeritagePage page) => state.copyWith(
        items: <Heritage>[...state.items, ...page.items],
        total: page.total,
        hasMore: page.hasMore,
        isLoadingMore: false,
        clearFailure: true,
      ),
      onFailure: (Failure f) =>
          state.copyWith(isLoadingMore: false, failure: f),
    );
  }

  void setSearch(String? query) {
    final next = (query == null || query.isEmpty) ? null : query;
    if (next == state.filters.search) return;
    state = state.copyWith(
      filters: state.filters.copyWith(search: next, offset: 0),
    );
    Future<void>.microtask(refresh);
  }

  void setKind(String? kindSlug) {
    if (kindSlug == state.filters.kindSlug) return;
    state = state.copyWith(
      filters: state.filters.copyWith(kindSlug: kindSlug, offset: 0),
    );
    Future<void>.microtask(refresh);
  }

  void setCountry(String? country) {
    if (country == state.filters.countryCode) return;
    state = state.copyWith(
      filters: state.filters.copyWith(countryCode: country, offset: 0),
    );
    Future<void>.microtask(refresh);
  }

  void clearFilters() {
    state = const HeritageListState.initial().copyWith(isLoading: true);
    Future<void>.microtask(refresh);
  }

  @visibleForTesting
  void debugSet(HeritageListState newState) => state = newState;
}

final NotifierProvider<HeritageListNotifier, HeritageListState>
    heritageListProvider =
    NotifierProvider<HeritageListNotifier, HeritageListState>(
  HeritageListNotifier.new,
  name: "heritageListProvider",
);
