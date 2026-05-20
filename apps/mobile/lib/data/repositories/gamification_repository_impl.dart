// Stub — full impl in FAZA 2+
import 'package:silklens/domain/gamification/entities/streak_entity.dart';

class GamificationRepositoryImpl {
  const GamificationRepositoryImpl();

  Future<StreakEntity> getStreak() async {
    // TODO(gamification): wire to backend GET /v1/me/streak
    return const StreakEntity(
      currentStreak: 7,
      bestStreak: 14,
      weekDays: [true, true, true, false, true, true, true],
      milestones: [],
    );
  }
}
