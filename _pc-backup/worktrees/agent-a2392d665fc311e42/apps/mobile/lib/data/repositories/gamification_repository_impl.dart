// GamificationRepositoryImpl — wires domain GamificationRepository protocol
// to SilkLensApiClient. Satisfies the interface structurally (no inheritance
// from data layer into domain).
//
// SILK-0108..0112: gamification screens wired to real backend API.

import 'package:dio/dio.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/core/error/failures.dart';
import 'package:silklens/core/utils/result.dart';
import 'package:silklens/data/api/clients/api_client_provider.dart';
import 'package:silklens/data/api/clients/silklens_api_client.dart';
import 'package:silklens/domain/gamification/entities/badge.dart';
import 'package:silklens/domain/gamification/entities/leaderboard_entry.dart';
import 'package:silklens/domain/gamification/entities/streak_entity.dart';
import 'package:silklens/domain/gamification/entities/xp_summary.dart';
import 'package:silklens/domain/gamification/repositories/gamification_repository.dart';

class GamificationRepositoryImpl implements GamificationRepository {
  const GamificationRepositoryImpl(this._client);

  final SilkLensApiClient _client;

  // -------------------------------------------------------------------------
  // Helpers
  // -------------------------------------------------------------------------

  Failure _mapDio(DioException e) {
    final code = e.response?.statusCode;
    if (e.type == DioExceptionType.connectionError ||
        e.type == DioExceptionType.connectionTimeout ||
        e.type == DioExceptionType.receiveTimeout ||
        e.type == DioExceptionType.sendTimeout) {
      return NetworkFailure('Network error: ${e.message}', cause: e);
    }
    if (code == 401 || code == 403) {
      return AuthFailure('Authentication failed ($code)', cause: e);
    }
    return ServerFailure('Server error ($code)', statusCode: code, cause: e);
  }

  // -------------------------------------------------------------------------
  // GamificationRepository implementation
  // -------------------------------------------------------------------------

  @override
  Future<Result<XpSummary>> xpSummary() async {
    try {
      final data = await _client.getXpBalance();
      return Success(XpSummary.fromJson(data));
    } on DioException catch (e) {
      return FailureResult(_mapDio(e));
    } catch (e) {
      return FailureResult(ServerFailure('Unexpected error: $e'));
    }
  }

  @override
  Future<Result<List<Badge>>> badges() async {
    try {
      final items = await _client.getBadges();
      final badges = items.cast<Map<String, dynamic>>().map(Badge.fromJson).toList();
      return Success(badges);
    } on DioException catch (e) {
      return FailureResult(_mapDio(e));
    } catch (e) {
      return FailureResult(ServerFailure('Unexpected error: $e'));
    }
  }

  @override
  Future<Result<List<LeaderboardEntry>>> leaderboard({
    required LeaderboardScope scope,
    int page = 1,
    int pageSize = 50,
  }) async {
    final period = switch (scope) {
      LeaderboardScope.weekly => 'weekly',
      LeaderboardScope.monthly => 'monthly',
      LeaderboardScope.allTime => 'all_time',
      LeaderboardScope.friends => 'friends',
    };
    try {
      // 'global' slug is the default board; extend via param if needed.
      final data = await _client.getLeaderboard(
        'global',
        period: period,
        limit: pageSize,
      ); // slug 'global' is the default board; extend via param if needed
      final entries = ((data['entries'] as List?) ?? [])
          .cast<Map<String, dynamic>>()
          .map(LeaderboardEntry.fromJson)
          .toList();
      return Success(entries);
    } on DioException catch (e) {
      return FailureResult(_mapDio(e));
    } catch (e) {
      return FailureResult(ServerFailure('Unexpected error: $e'));
    }
  }

  @override
  Future<StreakEntity> getStreak() async {
    final data = await _client.getStreak();
    return StreakEntity.fromJson(data);
  }

  // -------------------------------------------------------------------------
  // Extra helpers used by the gamification notifier (not on domain interface)
  // -------------------------------------------------------------------------

  Future<Map<String, dynamic>> getXpRaw() => _client.getXpBalance();
  Future<Map<String, dynamic>> getStreakRaw() => _client.getStreak();
  Future<Map<String, dynamic>> tickStreakRaw() => _client.tickStreak();
  Future<Map<String, dynamic>> getLeaderboardRaw(
    String slug, {
    required String period,
    int limit = 50,
  }) =>
      _client.getLeaderboard(slug, period: period, limit: limit);
}

// ---------------------------------------------------------------------------
// Riverpod provider
// ---------------------------------------------------------------------------

final gamificationRepositoryProvider = Provider<GamificationRepositoryImpl>((ref) {
  return GamificationRepositoryImpl(ref.watch(silkLensApiClientProvider));
});
