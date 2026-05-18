// Social state — feed + follow toggles + reviews.

import "package:flutter/foundation.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/core/error/failures.dart";
import "package:silklens/data/repositories/social_repository_impl.dart";
import "package:silklens/domain/social/entities/feed_item.dart";
import "package:silklens/domain/social/entities/review_dimensions.dart";
import "package:silklens/domain/social/entities/user_profile.dart";
import "package:silklens/domain/social/repositories/social_repository.dart";

@immutable
class FeedState {
  const FeedState({
    required this.items,
    this.isLoading = false,
    this.page = 1,
    this.endReached = false,
    this.failure,
  });

  final List<FeedItem> items;
  final bool isLoading;
  final int page;
  final bool endReached;
  final Failure? failure;

  FeedState copyWith({
    List<FeedItem>? items,
    bool? isLoading,
    int? page,
    bool? endReached,
    Failure? failure,
    bool clearFailure = false,
  }) =>
      FeedState(
        items: items ?? this.items,
        isLoading: isLoading ?? this.isLoading,
        page: page ?? this.page,
        endReached: endReached ?? this.endReached,
        failure: clearFailure ? null : failure ?? this.failure,
      );
}

class FeedController extends Notifier<FeedState> {
  static const int _pageSize = 20;

  @override
  FeedState build() => const FeedState(items: <FeedItem>[]);

  Future<void> refresh() async {
    state = state.copyWith(
      isLoading: true,
      page: 1,
      endReached: false,
      clearFailure: true,
    );
    final SocialRepository repo = ref.read(socialRepositoryProvider);
    final result = await repo.feed(page: 1, pageSize: _pageSize);
    result.fold<void>(
      onSuccess: (List<FeedItem> items) {
        state = state.copyWith(
          items: items,
          isLoading: false,
          endReached: items.length < _pageSize,
        );
      },
      onFailure: (Failure f) {
        state = state.copyWith(isLoading: false, failure: f);
      },
    );
  }

  Future<void> loadMore() async {
    if (state.isLoading || state.endReached) return;
    final nextPage = state.page + 1;
    state = state.copyWith(isLoading: true);
    final repo = ref.read(socialRepositoryProvider);
    final result = await repo.feed(page: nextPage, pageSize: _pageSize);
    result.fold<void>(
      onSuccess: (List<FeedItem> items) {
        state = state.copyWith(
          items: <FeedItem>[...state.items, ...items],
          isLoading: false,
          page: nextPage,
          endReached: items.length < _pageSize,
        );
      },
      onFailure: (Failure f) {
        state = state.copyWith(isLoading: false, failure: f);
      },
    );
  }
}

final NotifierProvider<FeedController, FeedState> feedControllerProvider =
    NotifierProvider<FeedController, FeedState>(
  FeedController.new,
  name: "feedControllerProvider",
);

class FollowController extends FamilyAsyncNotifier<UserProfile?, String> {
  @override
  Future<UserProfile?> build(String pubId) async {
    final repo = ref.read(socialRepositoryProvider);
    final result = await repo.getUser(pubId);
    return result.successOrNull;
  }

  Future<void> toggle() async {
    final current = state.valueOrNull;
    if (current == null) return;
    final repo = ref.read(socialRepositoryProvider);
    state = AsyncValue<UserProfile?>.data(
      UserProfile(
        pubId: current.pubId,
        displayName: current.displayName,
        handle: current.handle,
        avatarUrl: current.avatarUrl,
        bio: current.bio,
        country: current.country,
        followersCount: current.followersCount + (current.isFollowing ? -1 : 1),
        followingCount: current.followingCount,
        isFollowing: !current.isFollowing,
      ),
    );
    final result = current.isFollowing
        ? await repo.unfollow(current.pubId)
        : await repo.follow(current.pubId);
    if (result.isFailure) {
      // Roll back optimistic update on failure.
      state = AsyncValue<UserProfile?>.data(current);
    }
  }
}

final AsyncNotifierProviderFamily<FollowController, UserProfile?, String>
    followControllerProvider =
    AsyncNotifierProvider.family<FollowController, UserProfile?, String>(
  FollowController.new,
  name: "followControllerProvider",
);

class ReviewSubmissionController extends Notifier<AsyncValue<void>> {
  @override
  AsyncValue<void> build() => const AsyncValue<void>.data(null);

  Future<void> submit(ReviewDraft draft) async {
    state = const AsyncValue<void>.loading();
    final repo = ref.read(socialRepositoryProvider);
    final result = await repo.submitReview(draft);
    state = result.fold<AsyncValue<void>>(
      onSuccess: (_) => const AsyncValue<void>.data(null),
      onFailure: (Failure f) =>
          AsyncValue<void>.error(f, f.stackTrace ?? StackTrace.current),
    );
  }
}

final NotifierProvider<ReviewSubmissionController, AsyncValue<void>>
    reviewSubmissionControllerProvider =
    NotifierProvider<ReviewSubmissionController, AsyncValue<void>>(
  ReviewSubmissionController.new,
  name: "reviewSubmissionControllerProvider",
);
