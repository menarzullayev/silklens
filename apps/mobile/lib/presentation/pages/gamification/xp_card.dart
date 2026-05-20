import 'package:flutter/material.dart';

class XPDashboardPage extends StatelessWidget {
  const XPDashboardPage({super.key});

  static const _gold = Color(0xFFB78628);
  static const _goldLight = Color(0xFFE5C97A);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0D2337),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header
              const Text('Mening yutuqlarim',
                  style: TextStyle(
                      color: Colors.white,
                      fontSize: 24,
                      fontWeight: FontWeight.w800,),),
              const SizedBox(height: 24),

              // Level hex badge + XP bar
              Container(
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.07),
                  borderRadius: BorderRadius.circular(24),
                  border:
                      Border.all(color: Colors.white.withValues(alpha: 0.12)),
                ),
                child: Column(children: [
                  Row(children: [
                    // Hex badge
                    const _HexLevelBadge(level: 12, name: "Meros Qo'riqchi"),
                    const SizedBox(width: 20),
                    Expanded(
                        child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                          const Text('Daraja 12',
                              style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 18,
                                  fontWeight: FontWeight.w700,),),
                          const SizedBox(height: 4),
                          const Text('+240 XP bugun',
                              style:
                                  TextStyle(color: _gold, fontSize: 13),),
                          const SizedBox(height: 12),
                          // XP progress bar
                          Container(
                            height: 10,
                            decoration: BoxDecoration(
                              color: Colors.white.withValues(alpha: 0.12),
                              borderRadius: BorderRadius.circular(5),
                            ),
                            child: FractionallySizedBox(
                              widthFactor: 0.72,
                              alignment: Alignment.centerLeft,
                              child: Container(
                                decoration: BoxDecoration(
                                  gradient: const LinearGradient(
                                      colors: [_gold, _goldLight],),
                                  borderRadius: BorderRadius.circular(5),
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text('3,240 / 4,500 XP',
                              style: TextStyle(
                                  color: Colors.white.withValues(alpha: 0.5),
                                  fontSize: 11,),),
                        ],),),
                  ],),
                ],),
              ),

              const SizedBox(height: 16),

              // Stats grid
              GridView.count(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                crossAxisCount: 4,
                crossAxisSpacing: 8,
                mainAxisSpacing: 8,
                children: const [
                  _StatCard(Icons.explore_rounded, '47', 'Joy'),
                  _StatCard(Icons.star_rounded, '23', 'Sharh'),
                  _StatCard(
                      Icons.local_fire_department_rounded, '12', 'Streak',),
                  _StatCard(Icons.people_rounded, '89', 'Kuzatuvchi'),
                ],
              ),

              const SizedBox(height: 16),

              // Recent badges
              const Text("So'nggi nishonlar",
                  style: TextStyle(
                      color: Colors.white,
                      fontSize: 16,
                      fontWeight: FontWeight.w600,),),
              const SizedBox(height: 12),
              SizedBox(
                height: 80,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  itemCount: 5,
                  separatorBuilder: (_, __) => const SizedBox(width: 12),
                  itemBuilder: (_, i) => Column(children: [
                    Container(
                      width: 52,
                      height: 52,
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                            colors: [_gold, _goldLight],
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,),
                        shape: BoxShape.circle,
                        boxShadow: [
                          BoxShadow(
                              color: _gold.withValues(alpha: 0.3),
                              blurRadius: 8,),
                        ],
                      ),
                      child: const Icon(
                        Icons.workspace_premium_rounded,
                        color: Color(0xFF1A1200),
                        size: 24,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Nishon ${i + 1}',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 10,
                      ),
                    ),
                  ],),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _HexLevelBadge extends StatelessWidget {
  const _HexLevelBadge({required this.level, required this.name});
  final int level;
  final String name;

  @override
  Widget build(BuildContext context) {
    return Column(children: [
      Container(
        width: 72,
        height: 72,
        decoration: const BoxDecoration(
          gradient: LinearGradient(
              colors: [Color(0xFFB78628), Color(0xFFE5C97A)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,),
          shape: BoxShape.circle,
          boxShadow: [BoxShadow(color: Color(0x40B78628), blurRadius: 16)],
        ),
        child: Center(
            child: Text('$level',
                style: const TextStyle(
                    color: Color(0xFF1A1200),
                    fontSize: 24,
                    fontWeight: FontWeight.w900,),),),
      ),
      const SizedBox(height: 4),
      Text(name,
          style: const TextStyle(color: Color(0xFFB78628), fontSize: 10),
          overflow: TextOverflow.ellipsis,),
    ],);
  }
}

class _StatCard extends StatelessWidget {
  const _StatCard(this.icon, this.value, this.label);
  final IconData icon;
  final String value;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.07),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withValues(alpha: 0.10)),
      ),
      child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
        Icon(icon, color: const Color(0xFFB78628), size: 20),
        const SizedBox(height: 4),
        Text(value,
            style: const TextStyle(
                color: Colors.white,
                fontSize: 16,
                fontWeight: FontWeight.w700,),),
        Text(label,
            style: TextStyle(
                color: Colors.white.withValues(alpha: 0.5), fontSize: 10,),),
      ],),
    );
  }
}
