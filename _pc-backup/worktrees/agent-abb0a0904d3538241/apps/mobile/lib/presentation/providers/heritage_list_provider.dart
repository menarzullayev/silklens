import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/domain/heritage/entities/heritage.dart';

class HeritageListState {
  const HeritageListState({
    this.items = const [],
    this.total = 0,
    this.isLoading = false,
    this.error,
    this.filters = const HeritageFilters(),
  });
  final List<Heritage> items;
  final int total;
  final bool isLoading;
  final String? error;
  final HeritageFilters filters;
  bool get hasMore => items.length < total;
  HeritageListState copyWith({
    List<Heritage>? items, int? total, bool? isLoading,
    String? error, HeritageFilters? filters,
  }) => HeritageListState(
        items: items ?? this.items, total: total ?? this.total,
        isLoading: isLoading ?? this.isLoading, error: error,
        filters: filters ?? this.filters,
      );
}

class HeritageListNotifier extends Notifier<HeritageListState> {
  @override
  HeritageListState build() => const HeritageListState();

  Future<void> loadMore() async {}
  Future<void> refresh() async {}
  void updateFilter(HeritageFilters filters) =>
      state = state.copyWith(filters: filters);
}

final heritageListProvider =
    NotifierProvider<HeritageListNotifier, HeritageListState>(
  HeritageListNotifier.new,
);
