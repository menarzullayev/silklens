import 'package:flutter/material.dart';

class MissionsPage extends StatefulWidget {
  const MissionsPage({super.key});

  @override
  State<MissionsPage> createState() => _MissionsPageState();
}

class _MissionsPageState extends State<MissionsPage> {
  int _tabIndex = 0;
  static const _tabs = ['Kunlik', 'Haftalik', 'Maxsus'];
  static const _gold = Color(0xFFB78628);
  static const _goldLight = Color(0xFFE5C97A);

  static const _activeMissions = [
    _Mission(
      title: 'Meros joyini tashrif qiling',
      xp: 50,
      progress: 1,
      max: 3,
      icon: Icons.explore_rounded,
    ),
    _Mission(
      title: 'Rasm yuklash',
      xp: 30,
      progress: 2,
      max: 5,
      icon: Icons.photo_camera_rounded,
    ),
    _Mission(
      title: 'Sharh yozing',
      xp: 40,
      progress: 0,
      max: 2,
      icon: Icons.rate_review_rounded,
    ),
    _Mission(
      title: "Do'stingizni taklif qiling",
      xp: 100,
      progress: 1,
      max: 1,
      icon: Icons.people_rounded,
    ),
  ];

  static const _completedMissions = [
    _Mission(
      title: 'Tizimga kiring',
      xp: 10,
      progress: 1,
      max: 1,
      icon: Icons.login_rounded,
    ),
    _Mission(
      title: "Profilni to'ldiring",
      xp: 25,
      progress: 1,
      max: 1,
      icon: Icons.person_rounded,
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0D2337),
      appBar: AppBar(
        backgroundColor: const Color(0xFF0D2337),
        title: const Text(
          'Vazifalar',
          style: TextStyle(color: Colors.white),
        ),
        leading: GestureDetector(
          onTap: () => Navigator.pop(context),
          child: const Icon(
            Icons.arrow_back_ios_new,
            color: Colors.white,
            size: 20,
          ),
        ),
      ),
      body: Column(
        children: [
          // Period tabs
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Container(
              height: 44,
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.07),
                borderRadius: BorderRadius.circular(22),
                border: Border.all(
                  color: Colors.white.withValues(alpha: 0.12),
                ),
              ),
              child: Row(
                children: List.generate(_tabs.length, (i) {
                  final active = _tabIndex == i;
                  return Expanded(
                    child: GestureDetector(
                      onTap: () => setState(() => _tabIndex = i),
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 200),
                        margin: const EdgeInsets.all(4),
                        decoration: BoxDecoration(
                          gradient: active
                              ? const LinearGradient(
                                  colors: [_gold, _goldLight],
                                )
                              : null,
                          borderRadius: BorderRadius.circular(18),
                        ),
                        child: Center(
                          child: Text(
                            _tabs[i],
                            style: TextStyle(
                              color: active
                                  ? const Color(0xFF1A1200)
                                  : Colors.white.withValues(alpha: 0.6),
                              fontSize: 13,
                              fontWeight:
                                  active ? FontWeight.w700 : FontWeight.w400,
                            ),
                          ),
                        ),
                      ),
                    ),
                  );
                }),
              ),
            ),
          ),
          const SizedBox(height: 16),
          // List
          Expanded(
            child: ListView(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              children: [
                // Active missions
                Text(
                  'Faol vazifalar',
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.5),
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 0.8,
                  ),
                ),
                const SizedBox(height: 10),
                ..._activeMissions.map(
                  (m) => Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: _MissionCard(mission: m, completed: false),
                  ),
                ),
                const SizedBox(height: 8),
                // Completed missions
                Text(
                  'Bajarilgan',
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.5),
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 0.8,
                  ),
                ),
                const SizedBox(height: 10),
                ..._completedMissions.map(
                  (m) => Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: _MissionCard(mission: m, completed: true),
                  ),
                ),
                const SizedBox(height: 16),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _Mission {
  const _Mission({
    required this.title,
    required this.xp,
    required this.progress,
    required this.max,
    required this.icon,
  });
  final String title;
  final int xp;
  final int progress;
  final int max;
  final IconData icon;
}

class _MissionCard extends StatelessWidget {
  const _MissionCard({required this.mission, required this.completed});
  final _Mission mission;
  final bool completed;

  static const _gold = Color(0xFFB78628);
  static const _goldLight = Color(0xFFE5C97A);

  @override
  Widget build(BuildContext context) {
    final fraction = mission.max > 0 ? mission.progress / mission.max : 0.0;
    return Opacity(
      opacity: completed ? 0.55 : 1.0,
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.06),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: completed
                ? Colors.white.withValues(alpha: 0.08)
                : Colors.white.withValues(alpha: 0.12),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 42,
                  height: 42,
                  decoration: BoxDecoration(
                    color: completed
                        ? Colors.white.withValues(alpha: 0.08)
                        : _gold.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(
                    completed ? Icons.check_circle_rounded : mission.icon,
                    color:
                        completed ? Colors.white.withValues(alpha: 0.4) : _gold,
                    size: 22,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        mission.title,
                        style: TextStyle(
                          color: completed
                              ? Colors.white.withValues(alpha: 0.5)
                              : Colors.white,
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        '${mission.progress} / ${mission.max}',
                        style: TextStyle(
                          color: Colors.white.withValues(alpha: 0.4),
                          fontSize: 11,
                        ),
                      ),
                    ],
                  ),
                ),
                // XP badge
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    gradient: completed
                        ? null
                        : const LinearGradient(
                            colors: [_gold, _goldLight],
                          ),
                    color:
                        completed ? Colors.white.withValues(alpha: 0.08) : null,
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    '+${mission.xp} XP',
                    style: TextStyle(
                      color: completed
                          ? Colors.white.withValues(alpha: 0.4)
                          : const Color(0xFF1A1200),
                      fontSize: 11,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
              ],
            ),
            if (!completed) ...[
              const SizedBox(height: 12),
              // Progress bar
              Container(
                height: 6,
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.10),
                  borderRadius: BorderRadius.circular(3),
                ),
                child: FractionallySizedBox(
                  widthFactor: fraction.clamp(0.0, 1.0),
                  alignment: Alignment.centerLeft,
                  child: Container(
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [_gold, _goldLight],
                      ),
                      borderRadius: BorderRadius.circular(3),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 10),
              Align(
                alignment: Alignment.centerRight,
                child: GestureDetector(
                  onTap: () {},
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 7,
                    ),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.08),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(
                        color: Colors.white.withValues(alpha: 0.15),
                      ),
                    ),
                    child: const Text(
                      'Davom →',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
