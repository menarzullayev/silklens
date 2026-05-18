// HTTP-backed [GamificationRepository]. XP + streak + badges + leaderboards.

import "package:dio/dio.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/core/error/failures.dart";
import "package:silklens/core/utils/result.dart";
import "package:silklens/data/api/dio_client.dart";
import "package:silklens/domain/gamification/entities/badge.dart";
import "package:silklens/domain/gamification/entities/leaderboard_entry.dart";
import "package:silklens/domain/gamification/entities/xp_summary.dart";
import "package:silklens/domain/gamification/repositories/gamification_repository.dart";

class GamificationRepositoryImpl implements GamificationRepository {
  GamificationRepositoryImpl({required Dio dio}) : _dio = dio;

  final Dio _dio;

  @override
  Future<Result<XpSummary>> xpSummary() async {
    try {
      final xpRes = await _dio.get<Map<String, dynamic>>("/v1/me/xp");
      final streakRes = await _dio.get<Map<String, dynamic>>("/v1/me/streak");
      final xpBody = xpRes.data ?? const <String, dynamic>{};
      final streakBody = streakRes.data ?? const <String, dynamic>{};

      return Success<XpSummary>(
        XpSummary(
          totalXp: (xpBody["total_xp"] as int?) ?? 0,
          level: (xpBody["level"] as int?) ?? 1,
          xpIntoCurrentLevel: (xpBody["xp_into_level"] as int?) ?? 0,
          xpForNextLevel: (xpBody["xp_for_next_level"] as int?) ?? 100,
          streakDays: (streakBody["days"] as int?) ?? 0,
          lastActiveDate: streakBody["last_active_at"] is String
              ? DateTime.tryParse(streakBody["last_active_at"] as String)
              : null,
        ),
      );
    } on DioException catch (e, st) {
      return FailureResult<XpSummary>(
        NetworkFailure(e.message ?? "Dio error", cause: e, stackTrace: st),
      );
    }
  }

  @override
  Future<Result<List<Badge>>> badges() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>("/v1/me/badges");
      final items = (response.data?["items"] as List<dynamic>? ?? const <dynamic>[])
          .whereType<Map<String, dynamic>>()
          .map(_parseBadge)
          .toList(growable: false);
      return Success<List<Badge>>(items);
    } on DioException catch (e, st) {
      return FailureResult<List<Badge>>(
        NetworkFailure(e.message ?? "Dio error", cause: e, stackTrace: st),
      );
    }
  }

  @override
  Future<Result<List<LeaderboardEntry>>> leaderboard({
    required LeaderboardScope scope,
    int page = 1,
    int pageSize = 50,
  }) async {
    try {
      final slug = switch (scope) {
        LeaderboardScope.weekly => "weekly",
        LeaderboardScope.monthly => "monthly",
        LeaderboardScope.allTime => "all_time",
        LeaderboardScope.friends => "friends",
      };
      final response = await _dio.get<Map<String, dynamic>>(
        "/v1/leaderboards/$slug",
        queryParameters: <String, dynamic>{
          "page": page,
          "page_size": pageSize,
        },
      );
      final items = (response.data?["items"] as List<dynamic>? ?? const <dynamic>[])
          .whereType<Map<String, dynamic>>()
          .map(_parseEntry)
          .toList(growable: false);
      return Success<List<LeaderboardEntry>>(items);
    } on DioException catch (e, st) {
      return FailureResult<List<LeaderboardEntry>>(
        NetworkFailure(e.message ?? "Dio error", cause: e, stackTrace: st),
      );
    }
  }

  Badge _parseBadge(Map<String, dynamic> json) => Badge(
        slug: json["slug"] as String? ?? "",
        name: json["name"] as String? ?? "",
        description: json["description"] as String? ?? "",
        iconUrl: json["icon_url"] as String?,
        unlockedAt: json["unlocked_at"] is String
            ? DateTime.tryParse(json["unlocked_at"] as String)
            : null,
        criterionHint: json["criterion_hint"] as String?,
        xpValue: (json["xp_value"] as int?) ?? 0,
      );

  LeaderboardEntry _parseEntry(Map<String, dynamic> json) => LeaderboardEntry(
        rank: (json["rank"] as int?) ?? 0,
        userPubId: json["user_pub_id"] as String? ?? "",
        displayName: json["display_name"] as String? ?? "",
        score: (json["score"] as int?) ?? 0,
        avatarUrl: json["avatar_url"] as String?,
        country: json["country"] as String?,
        isMe: (json["is_me"] as bool?) ?? false,
      );
}

final Provider<GamificationRepository> gamificationRepositoryProvider =
    Provider<GamificationRepository>(
  (Ref ref) => GamificationRepositoryImpl(dio: ref.watch(dioProvider)),
  name: "gamificationRepositoryProvider",
);
