// HTTP-backed [SocialRepository]. Follow / unfollow / feed / reviews / invites.

import "package:dio/dio.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/core/error/failures.dart";
import "package:silklens/core/utils/result.dart";
import "package:silklens/data/api/dio_client.dart";
import "package:silklens/domain/social/entities/feed_item.dart";
import "package:silklens/domain/social/entities/review_dimensions.dart";
import "package:silklens/domain/social/entities/user_profile.dart";
import "package:silklens/domain/social/repositories/social_repository.dart";

class SocialRepositoryImpl implements SocialRepository {
  SocialRepositoryImpl({required Dio dio}) : _dio = dio;

  final Dio _dio;

  @override
  Future<Result<List<FeedItem>>> feed({int page = 1, int pageSize = 20}) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        "/v1/social/feed",
        queryParameters: <String, dynamic>{
          "page": page,
          "page_size": pageSize,
        },
      );
      final items = (response.data?["items"] as List<dynamic>? ?? const <dynamic>[])
          .whereType<Map<String, dynamic>>()
          .map(_parseFeedItem)
          .whereType<FeedItem>()
          .toList(growable: false);
      return Success<List<FeedItem>>(items);
    } on DioException catch (e, st) {
      return FailureResult<List<FeedItem>>(
        NetworkFailure(e.message ?? "Dio error", cause: e, stackTrace: st),
      );
    }
  }

  @override
  Future<Result<UserProfile>> getUser(String pubId) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>("/v1/users/$pubId");
      final user = _parseUser(response.data ?? const <String, dynamic>{});
      if (user == null) {
        return const FailureResult<UserProfile>(
          ServerFailure("User not found"),
        );
      }
      return Success<UserProfile>(user);
    } on DioException catch (e, st) {
      return FailureResult<UserProfile>(
        NetworkFailure(e.message ?? "Dio error", cause: e, stackTrace: st),
      );
    }
  }

  @override
  Future<Result<List<UserProfile>>> following(String pubId) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        "/v1/social/following/$pubId",
      );
      final items = (response.data?["items"] as List<dynamic>? ?? const <dynamic>[])
          .whereType<Map<String, dynamic>>()
          .map(_parseUser)
          .whereType<UserProfile>()
          .toList(growable: false);
      return Success<List<UserProfile>>(items);
    } on DioException catch (e, st) {
      return FailureResult<List<UserProfile>>(
        NetworkFailure(e.message ?? "Dio error", cause: e, stackTrace: st),
      );
    }
  }

  @override
  Future<Result<void>> follow(String pubId) async {
    try {
      await _dio.post<void>("/v1/social/follow/$pubId");
      return const Success<void>(null);
    } on DioException catch (e, st) {
      return FailureResult<void>(
        NetworkFailure(e.message ?? "Dio error", cause: e, stackTrace: st),
      );
    }
  }

  @override
  Future<Result<void>> unfollow(String pubId) async {
    try {
      await _dio.delete<void>("/v1/social/follow/$pubId");
      return const Success<void>(null);
    } on DioException catch (e, st) {
      return FailureResult<void>(
        NetworkFailure(e.message ?? "Dio error", cause: e, stackTrace: st),
      );
    }
  }

  @override
  Future<Result<void>> inviteFriend({
    required String channel,
    required String contact,
  }) async {
    try {
      await _dio.post<void>(
        "/v1/social/friends/invite",
        data: <String, dynamic>{"channel": channel, "contact": contact},
      );
      return const Success<void>(null);
    } on DioException catch (e, st) {
      return FailureResult<void>(
        NetworkFailure(e.message ?? "Dio error", cause: e, stackTrace: st),
      );
    }
  }

  @override
  Future<Result<void>> submitReview(ReviewDraft draft) async {
    try {
      await _dio.post<void>(
        "/v1/heritage/${draft.heritagePubId}/reviews",
        data: <String, dynamic>{
          "body": draft.body,
          "language": draft.language,
          "dimensions": <String, int?>{
            "history": draft.dimensions.history,
            "photos": draft.dimensions.photos,
            "access": draft.dimensions.access,
            "value": draft.dimensions.value,
            "atmosphere": draft.dimensions.atmosphere,
            "family_friendly": draft.dimensions.familyFriendly,
          },
        },
      );
      return const Success<void>(null);
    } on DioException catch (e, st) {
      return FailureResult<void>(
        NetworkFailure(e.message ?? "Dio error", cause: e, stackTrace: st),
      );
    }
  }

  UserProfile? _parseUser(Map<String, dynamic> json) {
    final pubId = json["pub_id"] as String? ?? json["id"] as String?;
    final name = json["display_name"] as String? ?? json["name"] as String?;
    if (pubId == null || name == null) return null;
    return UserProfile(
      pubId: pubId,
      displayName: name,
      handle: json["handle"] as String?,
      avatarUrl: json["avatar_url"] as String?,
      bio: json["bio"] as String?,
      country: json["country"] as String?,
      followersCount: (json["followers_count"] as int?) ?? 0,
      followingCount: (json["following_count"] as int?) ?? 0,
      isFollowing: (json["is_following"] as bool?) ?? false,
    );
  }

  FeedItem? _parseFeedItem(Map<String, dynamic> json) {
    final kindStr = json["kind"] as String? ?? "review";
    final actor = _parseUser(
      (json["actor"] as Map<String, dynamic>?) ?? const <String, dynamic>{},
    );
    if (actor == null) return null;
    final createdStr = json["created_at"] as String?;
    final createdAt = createdStr != null
        ? DateTime.tryParse(createdStr) ?? DateTime.now().toUtc()
        : DateTime.now().toUtc();
    return FeedItem(
      id: json["id"] as String? ?? "",
      kind: _parseKind(kindStr),
      actor: actor,
      createdAt: createdAt,
      heritagePubId: json["heritage_pub_id"] as String?,
      heritageName: json["heritage_name"] as String?,
      badgeSlug: json["badge_slug"] as String?,
      badgeName: json["badge_name"] as String?,
      text: json["text"] as String?,
      rating: json["rating"] as int?,
    );
  }

  FeedItemKind _parseKind(String kind) {
    switch (kind) {
      case "check_in":
        return FeedItemKind.checkIn;
      case "badge_unlock":
        return FeedItemKind.badgeUnlock;
      case "follow":
        return FeedItemKind.follow;
      case "comment":
        return FeedItemKind.comment;
      case "review":
      default:
        return FeedItemKind.review;
    }
  }
}

final Provider<SocialRepository> socialRepositoryProvider =
    Provider<SocialRepository>(
  (Ref ref) => SocialRepositoryImpl(dio: ref.watch(dioProvider)),
  name: "socialRepositoryProvider",
);
